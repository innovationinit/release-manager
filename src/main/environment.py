"""Utils for accessing process environment variables"""

import os
from typing import (
    Any,
    Callable,
    List,
    Optional,
)

from django.core.exceptions import ImproperlyConfigured


NOT_SET = object()


def get_environment(name: str, mapper: Optional[Callable[[str], Any]]=None, default=NOT_SET) -> Any:
    """Return a value with the given name from the process environment variables"""
    possible_environ_names = [
        'MARATHON_APP_LABEL_{}'.format(name),
        name,
    ]
    for environ_name in possible_environ_names:
        try:
            value = os.environ[environ_name]
        except KeyError:
            continue
        else:
            break
    else:
        if default is NOT_SET:
            raise ImproperlyConfigured('The {} environment variable is not present under names: {}'.format(name, ', '.join(possible_environ_names)))
        else:
            return default
    mapper = mapper or str
    return mapper(value)


def boolean_mapper(value: str) -> bool:
    """Map a string representation on a boolean value to Python bool"""
    if value.lower() in {'true', '1', 'yes'}:
        return True
    if value.lower() in {'false', '0', 'no'}:
        return False
    raise ImproperlyConfigured('Boolean mapper cannot map the {} value to bool'.format(value))


def list_mapper_factory(delimiter: Optional[str]=None, item_mapper: Optional[Callable[[str], Any]]=None) -> Callable[[str], List[Any]]:
    """Return a function that maps lists serialized to a string with a specified delimiter to a Python list

    :param delimiter: the item delimiter in the serialized list
    :param item_mapper: the mapper for list elements
    :return: the mapper function
    """
    delimiter = delimiter or ','
    item_mapper = item_mapper or str

    def list_mapper(value: str) -> List[Any]:
        """Map a list serialized to a string to a Python list

        Assumes an empty string represents an empty list, not a list containing an empty string.

        :param value: the list serialized to string
        :return: the parsed list
        """
        if value == '':
            return []
        return [item_mapper(item) for item in value.split(delimiter)]

    return list_mapper
