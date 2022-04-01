from abc import (
    ABC,
    abstractmethod,
)
from datetime import date
from typing import (
    Callable,
    Iterable,
    Optional,
    Union,
)

from django.utils import timezone

from .domain.tags import Tag


class VersioningScheme(ABC):

    class Segment:
        def __init__(
            self,
            label: str,
            help_text: str,
            required: bool,
            initial: Optional[Union[int, Callable[[], Optional[int]]]] = None,
            min_value: Optional[Union[int, Callable[[], Optional[int]]]] = None,
        ):
            self.label = label
            self.help_text = help_text
            self.required = required
            self.initial = initial
            self.min_value = min_value

    @property
    @abstractmethod
    def ID(self) -> str:
        pass

    @property
    @abstractmethod
    def MAJOR_SEGMENT(self) -> Segment:
        pass

    @property
    @abstractmethod
    def MINOR_SEGMENT(self) -> Segment:
        pass

    @property
    @abstractmethod
    def PATCH_SEGMENT(self) -> Segment:
        pass

    @property
    @abstractmethod
    def FIX_SEGMENT(self) -> Segment:
        pass

    @abstractmethod
    def get_tag_suggestions(self, current_tag: Tag) -> Iterable[Tag]:
        pass

    @abstractmethod
    def get_tag_description(self, tag: Tag) -> str:
        pass


class IncrementingSegmentsVersioningScheme(VersioningScheme):

    ID = 'INCREMENTING_SEGMENTS'
    MAJOR_SEGMENT = VersioningScheme.Segment(label='Major', help_text='', required=True, initial=1, min_value=1)
    MINOR_SEGMENT = VersioningScheme.Segment(label='Minor', help_text='Bumped up when new sprint begins', required=True, min_value=0)
    PATCH_SEGMENT = VersioningScheme.Segment(
        label='Patch', help_text='Enumerates consequent planned deployment during sprint', required=True, initial=0, min_value=0)
    FIX_SEGMENT = VersioningScheme.Segment(label='Fix', help_text='Optional segment used for hotfixes', required=False, min_value=0)

    def get_tag_suggestions(self, current_tag: Tag) -> Iterable[Tag]:
        if current_tag.fix is not None:
            yield Tag(current_tag.major, current_tag.minor, current_tag.patch, current_tag.fix + 1)
        else:
            yield Tag(current_tag.major, current_tag.minor, current_tag.patch, 1)
        yield Tag(current_tag.major, current_tag.minor, current_tag.patch + 1, None)
        yield Tag(current_tag.major, current_tag.minor + 1, 0, None)

    def get_tag_description(self, tag: Tag) -> str:
        description = f'Sprint {tag.minor}'
        if tag.patch:
            description += f' revision {tag.patch}'
        if tag.fix is not None:
            description += f' fix {tag.fix}'
        return description


def get_short_year(date_: date) -> int:
    return int(str(date_.year)[-2:])


class DateBasedVersioningScheme(VersioningScheme):

    ID = 'DATE_BASED'
    MAJOR_SEGMENT = VersioningScheme.Segment(
        label='Year',
        help_text='Short year number, eg. 21 for 2021',
        required=True,
        initial=lambda: get_short_year(timezone.now().date()),
        min_value=0,
    )
    MINOR_SEGMENT = VersioningScheme.Segment(label='Month', help_text='', required=True, initial=lambda: timezone.now().month, min_value=1)
    PATCH_SEGMENT = VersioningScheme.Segment(label='Day', help_text='', required=True, initial=lambda: timezone.now().day, min_value=1)
    FIX_SEGMENT = VersioningScheme.Segment(
        label='Deployment',
        help_text='Enumerates consequent deployment during the day',
        required=True,
        initial=0,
        min_value=0,
    )

    def __init__(self):
        self.current_date = timezone.now().date()
        self.current_date_short_year = get_short_year(self.current_date)

    def get_tag_suggestions(self, current_tag: Tag) -> Iterable[Tag]:
        current_tag_year, current_tag_month, current_tag_day = current_tag.major, current_tag.minor, current_tag.patch
        if (current_tag_year, current_tag_month, current_tag_day) == (self.current_date_short_year, self.current_date.month, self.current_date.day):
            yield Tag(current_tag_year, current_tag_month, current_tag_day, (current_tag.fix or 0) + 1)
        else:
            yield Tag(self.current_date_short_year, self.current_date.month, self.current_date.day, 0)

    def get_tag_description(self, tag: Tag) -> str:
        year = str(timezone.now().date().year)[:-2] + str(tag.major)
        return f'{year}-{str(tag.minor).zfill(2)}-{str(tag.patch).zfill(2)} deployment {tag.fix}'


def get_versioning_scheme(scheme_id) -> VersioningScheme:
    scheme_class = next(scheme for scheme in VersioningScheme.__subclasses__() if scheme.ID == scheme_id)
    return scheme_class()
