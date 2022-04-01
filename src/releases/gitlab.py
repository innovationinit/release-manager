import re
import time
from typing import (
    Generator,
    Optional,
)

import dateutil.parser
import gitlab
from cached_property import cached_property
from unstdlib import listify

from django.conf import settings

from .domain.branch_difference import BranchDifference
from .domain.commits import Commit
from .domain.merge_requests import MergeRequest
from .domain.projects import Project
from .domain.tags import Tag
from .versioning import get_versioning_scheme


class GitlabClient:

    MERGE_AUTOMATICALLY_MAX_TRIES = 3

    def create_merge_request(self, project: Project, merge_request: MergeRequest):
        gitlab_project = self.api_client.projects.get(project.gitlab_id)
        return gitlab_project.mergerequests.create({
            'source_branch': merge_request.source_branch,
            'target_branch': merge_request.target_branch,
            'title': f'[Release Manager] {merge_request}',
            'labels': ['release-manager', merge_request.merge_type],
        })

    def merge_automatically(self, project: Project, merge_request_id: int):
        gitlab_project = self.api_client.projects.get(project.gitlab_id)
        gitlab_merge_request = gitlab_project.mergerequests.get(merge_request_id)
        for try_number in range(1, self.MERGE_AUTOMATICALLY_MAX_TRIES + 1):
            try:
                gitlab_merge_request.merge(merge_when_pipeline_succeeds=True)
            except gitlab.exceptions.GitlabError:
                if try_number == self.MERGE_AUTOMATICALLY_MAX_TRIES:
                    raise
                # there is a known bug in GitLab that new merge requests are likely to raise a 405 response for that merge command
                time.sleep(3)  # this will make them a bit older
            else:
                break
        gitlab_merge_request = gitlab_project.mergerequests.get(merge_request_id)
        if gitlab_merge_request.state == 'opened' and not gitlab_merge_request.merge_when_pipeline_succeeds:
            gitlab_merge_request.merge()

    def create_tag(self, project: Project, tag: Tag):
        gitlab_project = self.api_client.projects.get(project.gitlab_id)
        versioning_scheme = get_versioning_scheme(project.versioning_scheme)
        gitlab_project.tags.create({
            'tag_name': str(tag),
            'ref': project.production_environment_branch,
            'message': versioning_scheme.get_tag_description(tag),
        })

    @listify
    def get_last_tags(self, project: Project, tag_count: int) -> Generator[Tag, None, None]:
        gitlab_project = self.api_client.projects.get(project.gitlab_id)
        tags = gitlab_project.tags.list(per_page=tag_count, search='v')
        for tag in tags:
            match = re.search('^v(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?$', tag.name)
            if match:
                segments = tuple(filter(None, match.groups()))
                if 3 <= len(segments) <= 4:
                    yield Tag(*map(int, segments))

    def get_latest_tag(self, project: Project) -> Optional[Tag]:
        return next(iter(self.get_last_tags(project, tag_count=1)), None)

    def compare_refs(self, project: Project, source: str, target: str) -> BranchDifference:
        gitlab_project = self.api_client.projects.get(project.gitlab_id)
        commit_log = []
        comparation_result = gitlab_project.repository_compare(target, source)
        for commit in comparation_result['commits']:
            commit_log.append(Commit(
                id=commit['id'],
                message=commit['title'],
                created_at=dateutil.parser.parse(commit['created_at']),
                parent_ids=commit['parent_ids']
            ))
        return BranchDifference(
            commit_log=commit_log,
            has_diff=bool(comparation_result['diffs']),
        )

    @cached_property
    def api_client(self) -> gitlab.Gitlab:
        return gitlab.Gitlab(settings.GITLAB_HOST, private_token=settings.GITLAB_PRIVATE_TOKEN)
