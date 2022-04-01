import logging
import urllib.parse
from multiprocessing.pool import ThreadPool
from operator import attrgetter
from typing import (
    Generator,
    List,
    Optional,
    Tuple,
)

import gitlab.exceptions
from unstdlib import listify

from django.conf import settings
from django.contrib import messages
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import (
    redirect,
    resolve_url,
)
from django.views.generic import (
    FormView,
    TemplateView,
)

from .domain.changes import Change
from .domain.merge_requests import MergeRequest
from .domain.projects import Project
from .domain.tags import Tag
from .forms import (
    MergeRequestForm,
    PostDeploymentHookForm,
    TagForm,
)
from .gitlab import GitlabClient
from .jira import JiraClient
from .rocket import RocketClient
from .versioning import (
    VersioningScheme,
    get_versioning_scheme,
)


logger = logging.getLogger(__name__)


class ChangesGettingMixin:

    @listify
    def get_changes(self, project: Project, source: str, target: str) -> Generator[Change, None, None]:
        gitlab_client = GitlabClient()
        difference = gitlab_client.compare_refs(project, source, target)
        if difference.has_diff:
            jira_client = JiraClient()
            for commit in difference.commit_log:
                jira_issue = jira_client.get_issue(commit.jira_reference) if commit.jira_reference else None
                yield Change(
                    commit=commit,
                    jira_issue=jira_issue,
                    warning_labels=list(set(project.jira_warning_labels) & set(jira_issue.labels if jira_issue else [])),
                )


class ReleasesView(TemplateView, ChangesGettingMixin):

    template_name = 'releases/releases.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        warning_messages = []
        if not JiraClient.is_configured_properly():
            warning_messages.append('Jira configuration is not sufficient.')
        if not RocketClient.is_configured_properly():
            warning_messages.append('Rocket.chat configuration is not sufficient.')
        pool = ThreadPool(processes=len(settings.PROJECTS))
        projects_latest_tags = dict(pool.map(self.get_project_latest_tag, settings.PROJECTS))
        tag_groups = {p.tag_group for p in settings.PROJECTS if p.tag_group}
        latest_tag_group_tags = {
            tag_group: max(latest_tag for p, latest_tag in projects_latest_tags.items() if p.tag_group == tag_group)
            for tag_group in tag_groups
        }
        projects_latest_tag_group_tags = {p: latest_tag_group_tags.get(p.tag_group) for p in settings.PROJECTS}
        projects_context = pool.starmap(
            self.get_project_context_data,
            [(p, projects_latest_tags.get(p), projects_latest_tag_group_tags.get(p)) for p in settings.PROJECTS]
        )
        context.update({
            'gitlab_host': settings.GITLAB_HOST,
            'jira_host': settings.JIRA_HOST,
            'projects': projects_context,
            'warning_messages': warning_messages,
        })
        return context

    def get_project_latest_tag(self, project: Project) -> Tuple[Project, Optional[Tag]]:
        gitlab_client = GitlabClient()
        return project, gitlab_client.get_latest_tag(project)

    def get_project_context_data(self, project: Project, latest_tag: Optional[Tag], latest_tag_group_tag: Optional[Tag]):
        versioning_scheme = get_versioning_scheme(project.versioning_scheme)
        merge_requests_context = []
        has_awaiting_dev_merges = has_awaiting_maintenance_merges = has_awaiting_prod_merges = False
        for merge_request in project.merge_requests:
            changes = self.get_changes(project, merge_request.source_branch, merge_request.target_branch)
            if changes and merge_request.merge_type == MergeRequest.MergeType.DEV:
                has_awaiting_dev_merges = True
            if changes and merge_request.merge_type == MergeRequest.MergeType.MAINTENANCE:
                has_awaiting_maintenance_merges = True
            if changes and merge_request.merge_type == MergeRequest.MergeType.PROD:
                has_awaiting_prod_merges = True
            merge_requests_context.append({
                'merge_request': merge_request,
                'merge_request_form': MergeRequestForm(initial={
                    'project_gitlab_id': project.gitlab_id,
                    'source_branch': merge_request.source_branch,
                    'target_branch': merge_request.target_branch,
                }),
                'changes': changes,
            })
        tag_for_suggestions = latest_tag_group_tag or latest_tag
        return {
            'project': project,
            'merge_requests': merge_requests_context,
            'tag_form': TagForm(
                initial={
                    'project_gitlab_id': project.gitlab_id,
                    'major': tag_for_suggestions.major if tag_for_suggestions else None,
                    'minor': tag_for_suggestions.minor if tag_for_suggestions else None,
                    'patch': tag_for_suggestions.patch if tag_for_suggestions else None,
                    'fix': tag_for_suggestions.fix if tag_for_suggestions else None,
                },
                versioning_scheme=versioning_scheme,
            ),
            'tag_changes': self.get_changes(project, project.production_environment_branch, str(latest_tag)) if latest_tag else [],
            'latest_tag': latest_tag,
            'tag_suggestions': versioning_scheme.get_tag_suggestions(tag_for_suggestions) if tag_for_suggestions else [],
            'other_projects_in_tag_group': [
                p for p in sorted(settings.PROJECTS, key=attrgetter('name')) if p != project and p.tag_group and p.tag_group == project.tag_group
            ],
            'latest_tag_group_tag': latest_tag_group_tag,
            'has_awaiting_dev_merges': has_awaiting_dev_merges,
            'has_awaiting_maintenance_merges': has_awaiting_maintenance_merges,
            'has_awaiting_prod_merges': has_awaiting_prod_merges,
        }


class ProjectRedirectionMixin:

    @staticmethod
    def redirect_to_project(project: Project) -> HttpResponseRedirect:
        return HttpResponseRedirect(resolve_url('releases:releases') + f'#{project.gitlab_id}')


class CreateMergeRequestView(FormView, ProjectRedirectionMixin):

    form_class = MergeRequestForm

    def form_valid(self, form: MergeRequestForm):
        gitlab_id = form.cleaned_data['project_gitlab_id']
        source_branch = form.cleaned_data['source_branch']
        target_branch = form.cleaned_data['target_branch']

        project: Project = next((project for project in settings.PROJECTS if project.gitlab_id == gitlab_id))
        merge_request: MergeRequest = next((
            mr for mr in project.merge_requests if mr.source_branch == source_branch and mr.target_branch == target_branch
        ))

        gitlab_client = GitlabClient()
        try:
            gitlab_merge_request = gitlab_client.create_merge_request(project, merge_request)
        except gitlab.exceptions.GitlabError as e:
            logger.exception('Got an error while creating a merge request %s in project %s', merge_request, project)
            messages.error(
                self.request,
                f'Could not create merge request {merge_request} in project {project}. An error occurred while consuming the GitLab API: {e}'
            )
        else:
            messages.success(self.request, f'Created a merge request: {merge_request} in project {project}.')
            try:
                gitlab_client.merge_automatically(project, gitlab_merge_request.iid)
            except gitlab.exceptions.GitlabError:
                logger.exception('Got an error while trying to setup an automatic merge for %s in project %s', merge_request, project)
                messages.error(
                    self.request,
                    f'Merge request {merge_request} in project {project} cannot be merged automatically. Please handle conflicts manually.'
                )
        return self.redirect_to_project(project)

    def form_invalid(self, form: TagForm):
        messages.error(self.request, f'Invalid data: {form.errors}')
        return redirect('releases:releases')


class CreateTagView(FormView, ProjectRedirectionMixin, ChangesGettingMixin):

    form_class = TagForm

    project: Project
    versioning_scheme: VersioningScheme

    def dispatch(self, request, *args, **kwargs):
        try:
            self.project = next((project for project in settings.PROJECTS if project.gitlab_id == request.POST.get('project_gitlab_id')))
        except StopIteration:
            return redirect('releases:releases')
        self.versioning_scheme = get_versioning_scheme(self.project.versioning_scheme)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['versioning_scheme'] = self.versioning_scheme
        return kwargs

    def form_valid(self, form: TagForm):
        gitlab_client = GitlabClient()
        tag = Tag(major=form.cleaned_data['major'], minor=form.cleaned_data['minor'], patch=form.cleaned_data['patch'], fix=form.cleaned_data['fix'])
        latest_tag = gitlab_client.get_latest_tag(self.project)
        changes = self.get_changes(self.project, self.project.production_environment_branch, str(latest_tag)) if latest_tag else []
        try:
            gitlab_client.create_tag(self.project, tag)
        except gitlab.exceptions.GitlabError as e:
            messages.error(
                self.request,
                f'Could not create tag {tag} in project {self.project}. An error occurred while consuming the GitLab API: {e}'
            )
        else:
            message = f'Created a tag {tag} ({self.versioning_scheme.get_tag_description(tag)}) in project {self.project}.'
            messages.success(self.request, message)
            rocket_client = RocketClient()
            message += f'\nJira issues: {settings.JIRA_HOST}/issues/?' + urllib.parse.urlencode({
                'jql': f"project in ({', '.join(settings.JIRA_PROJECTS)}) AND fixVersion = {str(tag)}",
            }, quote_via=urllib.parse.quote)
            rocket_client.send_message(message, color='green')

            success_messages, error_messages = self.update_jira_issues(changes, tag)
            if success_messages:
                messages.success(self.request, ' '.join(success_messages))
                rocket_client.send_message(' '.join(success_messages), color='green')
            if error_messages:
                messages.error(self.request, ' '.join(error_messages))
                rocket_client.send_message(' '.join(error_messages), color='red')

        return self.redirect_to_project(self.project)

    def update_jira_issues(self, changes: List[Change], tag: Tag) -> Tuple[List[str], List[str]]:
        jira_client = JiraClient()
        issues_with_fix_version, issues_without_fix_version = [], []
        issue_lists_by_success = {True: issues_with_fix_version, False: issues_without_fix_version}
        jira_issue_keys = {change.jira_issue.key for change in changes if change.jira_issue}
        for jira_issue_key in jira_issue_keys:
            adding_fix_version_succeeded = jira_client.add_fix_version(issue_key=jira_issue_key, fix_version=str(tag))
            issue_lists_by_success[adding_fix_version_succeeded].append(jira_issue_key)
        success_messages, error_messages = [], []
        if issues_with_fix_version:
            success_messages.append(f"Successfully set fixVersion for issues: {', '.join(issues_with_fix_version)}.")
        if issues_without_fix_version:
            error_messages.append(f"Could not set fixVersion for issues: {', '.join(issues_without_fix_version)}. Please handle it manually.")
        return success_messages, error_messages

    def form_invalid(self, form: TagForm):
        messages.error(self.request, f'Invalid data: {form.errors}')
        return redirect('releases:releases')


class PostDeploymentHookView(FormView, ChangesGettingMixin):

    form_class = PostDeploymentHookForm

    def get(self, *args, **kwargs):
        return HttpResponse('Only POST requests are allowed.', status=405)

    def form_valid(self, form):
        try:
            project = next((project for project in settings.PROJECTS if project.gitlab_id == form.cleaned_data['project_gitlab_id']))
        except StopIteration:
            return HttpResponseBadRequest('Project not found.')

        if not project.production_release_jira_transitions:
            return HttpResponseBadRequest('Nothing to do for this project.')

        gitlab_client = GitlabClient()
        last_tags = gitlab_client.get_last_tags(project, tag_count=2)
        if len(last_tags) != 2:
            return HttpResponseBadRequest('Need at least two tags in the repository to handle changes.')
        latest_tag, previous_tag = last_tags
        changes = self.get_changes(project, str(latest_tag), str(previous_tag))
        success_messages, error_messages = self.transition_jira_issues(project, changes)

        rocket_client = RocketClient()
        if error_messages:
            message = f'Post deployment hook for {project} failed.\n' + '\n'.join(success_messages + error_messages)
            rocket_client.send_message(message, color='red')
            return HttpResponse(message)
        message = f'Post deployment hook for {project} succeeded.\n' + '\n'.join(success_messages)
        rocket_client.send_message(message, color='green')
        return HttpResponse(message)

    def transition_jira_issues(self, project: Project, changes: List[Change]) -> Tuple[List[str], List[str]]:
        jira_client = JiraClient()
        issues_with_transitions, issues_without_transitions = [], []
        issue_lists_by_success = {True: issues_with_transitions, False: issues_without_transitions}
        jira_issue_keys = {change.jira_issue.key for change in changes if change.jira_issue}
        for jira_issue_key in jira_issue_keys:
            transitions_succeeded = bool(jira_client.make_transitions(
                issue_key=jira_issue_key,
                transition_names=project.production_release_jira_transitions,
            ))
            issue_lists_by_success[transitions_succeeded].append(jira_issue_key)
        success_messages, error_messages = [], []
        if issues_with_transitions:
            success_messages.append(f"Successfully transitioned issues: {', '.join(issues_with_transitions)}.")
        if issues_without_transitions:
            error_messages.append(f"Could not transition issues: {', '.join(issues_without_transitions)}. Please handle it manually.")
        return success_messages, error_messages

    def form_invalid(self, form):
        return HttpResponseBadRequest('Invalid request data.')
