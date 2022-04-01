import logging
from typing import (
    Generator,
    List,
    Optional,
)

from cached_property import cached_property
from jira import (
    JIRA,
    JIRAError,
)
from unstdlib import listify

from django.conf import settings

from .domain.jira import JiraIssue


logger = logging.getLogger(__name__)


class JiraClient:

    @classmethod
    def is_configured_properly(cls) -> bool:
        return (settings.JIRA_HOST and settings.JIRA_USERNAME and settings.JIRA_PASSWORD)

    def get_issue(self, issue_key: str) -> Optional[JiraIssue]:
        try:
            issue = self.api_client.issue(issue_key, fields=['summary', 'labels'])
        except JIRAError as e:
            if e.status_code == 404:
                return None
            logger.exception('Got an error while retrieving issue %s', issue_key)
            return None
        return JiraIssue(
            key=issue.key,
            summary=issue.fields.summary,
            labels=issue.fields.labels,
        )

    def add_fix_version(self, issue_key: str, fix_version: str) -> bool:
        try:
            issue = self.api_client.issue(issue_key, fields=['fixVersions', 'project'])
        except JIRAError:
            logger.exception('Got an error while finding issue %s', issue_key)
            return False
        fix_versions = issue.fields.fixVersions
        if fix_version not in {v.name for v in fix_versions}:
            try:
                version = next((v for v in self.api_client.project_versions(issue.fields.project) if v.name == fix_version), None)
            except JIRAError:
                logger.exception('Got an error while retrieving project %s versions', issue.fields.project.key)
                return False
            if not version:
                try:
                    version = self.api_client.create_version(name=fix_version, project=issue.fields.project.key)
                except JIRAError:
                    logger.exception('Got an error while creating %s version in project %s', fix_version, issue.fields.project.key)
                    return False
            fix_versions.append(version)
            try:
                issue.update(fields={'fixVersions': [{'id': fv.id} for fv in fix_versions]}, notify=False)
            except JIRAError:
                logger.exception('Got an error while setting fixVersions of issue %s', issue_key)
                return False
        return True

    @listify
    def make_transitions(self, issue_key: str, transition_names: List[str]) -> Generator[str, None, None]:
        for transition_name in transition_names:
            try:
                transition_to_apply = self.api_client.find_transitionid_by_name(issue_key, transition_name)
            except JIRAError:
                logger.exception('Got an error while finding transition for issue %s by name: %s', issue_key, transition_name)
            else:
                if transition_to_apply:
                    try:
                        self.api_client.transition_issue(issue_key, transition_to_apply)
                    except JIRAError:
                        logger.exception('Got an error while making %s transition for issue %s', transition_name, issue_key)
                    else:
                        yield transition_name

    @cached_property
    def api_client(self):
        if not self.is_configured_properly():
            raise JIRAError('Insufficient Jira configuration.')
        return JIRA(
            server=settings.JIRA_HOST,
            auth=(
                settings.JIRA_USERNAME,
                settings.JIRA_PASSWORD,
            ),
        )
