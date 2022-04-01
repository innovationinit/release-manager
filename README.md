# Release Manager

## Running the project locally

Just `./run_docker`.

In order to use all the features of the application you will probably need to add some configuration parameters. In such case edit the `.environment`
file and restart the `backend` container.

## Running the project in production

In order to run the project in production, prepare and publish the latest Docker image of the project.

Run the container with environment variables descibed in the secion below.

In order to make transitions of Jira issues after deploying the project, add a step to your project's CI pipeline that will run the post-deployment
hook.

Example CI step of `.gitlab-ci.yml`:

    Notify Release Manager:
      stage: after Production deployment
      script:
        - curl https://$RELEASE_MANAGER_USER:$RELEASE_MANAGER_PASSWORD@release-manager.example.com/post-deployment-hook/ -XPOST --data "project_gitlab_id=$CI_PROJECT_PATH"
      tags:
         - docker-shell
      only:
         - /^v.*$/

## Setting environment variables

### ENVIRONMENT
Either `dev` or `prod`. Determines the type of server for running the application.

### DEBUG
Either `true` or `false`. Enables debugging features like nice post-mortem error pages.

### GITLAB_HOST
Eg. `https://gitlab.com`. The GitLab host to be used for API calls.

### GITLAB_PRIVATE_TOKEN
The token to be used for authenticating GitLab API calls.

### PROJECTS
A JSON document containing the list of projects that will be handled by the application.

Each item in the list contains following fields:
- `name` - a human-readable name of the project
- `gitlab_id` - the name of the GitLab repository
- `production_environment_branch` - the GIT branch that is used for production deployments
- `merges` - the list of supported GIT branch merges with each item containing following fields:
  - `merge_type` - one of `DEV`, `PROD` and `MAINTENANCE`
  - `source_branch` - the source branch of the merge
  - `target_branch` - the target branch of the merge
- `versioning_scheme` - one of `INCREMENTING_SEGMENTS` and `DATE_BASED`
- `tag_group` - an optional name of tag group that will be used for tag suggestions - set it only if you want the tag suggestion to take other
projects into account
- `production_release_jira_transitions` - names of Jira transitions to be applied after creating production deployment tag
- `jira_warning_labels` - names of Jira labels that will cause displaying an alert for a commit in the user interface

Example document for a simple single-project deployment.

    [{
        "name": "Release Manager Test",
        "gitlab_id": "some-group-or-user/release-manager-test",
        "production_environment_branch": "master",
        "merges": [
            {
                "merge_type": "DEV",
                "source_branch": "develop",
                "target_branch": "stage"
            },
            {
                "merge_type": "PROD",
                "source_branch": "stage",
                "target_branch": "master"
            },
            {
                "merge_type": "MAINTENANCE",
                "source_branch": "master",
                "target_branch": "stage"
            },
            {
                "merge_type": "MAINTENANCE",
                "source_branch": "stage",
                "target_branch": "develop"
            }
        ],
        "versioning_scheme": "DATE_BASED",
        "tag_group": null,
        "production_release_jira_transitions": ["To deploy", "Close"],
        "jira_warning_labels": ["DEPLOY-WARN"]
    }]

### BASIC_AUTH_USER
The username for signing in to the application.

### BASIC_AUTH_PASS
The password for signing in to the application.

### ALLOWED_HOSTS
A comma-separated list of hosts for which requests to the application are allowed.

### ALLOWED_CIDR_NETS
A comma-separated list of CIDRs for which requests to the application are allowed, eg. `10.32.94.0/24`.

### JIRA_HOST
Eg. `https://jira.somecompanyname.com`. The Jira host to be used for API calls.

### JIRA_USERNAME
The username to be used for authenticating Jira API calls.

### JIRA_PASSWORD
The password to be used for authenticating Jira API calls.

### JIRA PROJECTS
A comma-separated list of Jira project keys to be used for displaying notifications.

### ROCKET_HOOK_URL
An optional hook URL to be used for sending Rocket.chat notifications, eg. `https://rocket.example.com/hooks/somethingsomething/somethingsomething`.

## License
The Release Manager is licensed under the [FreeBSD
License](https://opensource.org/licenses/BSD-2-Clause).

