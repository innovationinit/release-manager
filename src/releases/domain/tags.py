from functools import total_ordering
from typing import (
    Tuple,
    Union,
)

from typing import Optional


@total_ordering
class Tag:
    def __init__(self, major: int, minor: int, patch: int, fix: Optional[int] = None):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.fix = fix

    def __str__(self) -> str:
        tag = f'v{self.major}.{self.minor}.{self.patch}'
        if self.fix is not None:
            tag += f'.{self.fix}'
        return tag

    def __eq__(self, other: 'Tag') -> bool:
        return (self.major, self.minor, self.patch, self.fix) == (other.major, other.minor, other.patch, other.fix)

    def __lt__(self, other: 'Tag') -> bool:
        def get_tuple_for_comparison(tag: Tag) -> Tuple[int, int, int, Union[int, float]]:
            return tag.major, tag.minor, tag.patch, float('-inf') if tag.fix is None else tag.fix
        return get_tuple_for_comparison(self) < get_tuple_for_comparison(other)
