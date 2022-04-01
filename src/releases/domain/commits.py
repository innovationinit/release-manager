import re
from datetime import datetime
from typing import (
    Optional,
    Set,
)


class Commit:
    def __init__(self, id: str, message: str, created_at: datetime, parent_ids: Set[str]):
        self.id = id
        self.message = message
        self.created_at = created_at
        self.parent_ids = parent_ids

    @property
    def jira_reference(self) -> Optional[str]:
        match = re.match('\[(\w+-\d+)\]', self.message)
        if match:
            return match.groups()[0]
