from typing import (
    List,
    Optional,
)

from releases.domain.commits import Commit
from releases.domain.jira import JiraIssue


class Change:
    def __init__(self, commit: Commit, jira_issue: Optional[JiraIssue], warning_labels: List[str]):
        self.commit = commit
        self.jira_issue = jira_issue
        self.warning_labels = warning_labels
