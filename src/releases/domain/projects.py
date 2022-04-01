from typing import (
    List,
    Optional,
)

from .merge_requests import MergeRequest


class Project:
    def __init__(
        self,
        name: str,
        gitlab_id: str,
        production_environment_branch: str,
        merge_requests: List[MergeRequest],
        versioning_scheme: str,
        tag_group: Optional[str],
        production_release_jira_transitions: List[str],
        jira_warning_labels: List[str],
    ):
        self.name = name
        self.gitlab_id = gitlab_id
        self.production_environment_branch = production_environment_branch
        self.merge_requests = merge_requests
        self.versioning_scheme = versioning_scheme
        self.tag_group = tag_group
        self.production_release_jira_transitions = production_release_jira_transitions
        self.jira_warning_labels = jira_warning_labels

    def __eq__(self, other: 'Project'):
        return self.gitlab_id == other.gitlab_id

    def __hash__(self):
        return hash(self.gitlab_id)

    def __str__(self):
        return self.name
