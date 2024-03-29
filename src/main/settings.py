"""
Django settings for release_manager project.

Generated by 'django-admin startproject' using Django 2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import json
import os
from typing import List

from checksumdir import dirhash

from releases.domain.merge_requests import MergeRequest
from releases.domain.projects import Project
from .environment import (
    boolean_mapper,
    get_environment,
    list_mapper_factory,
)


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '_@*ps%k)!f&i^*yxqniy^4b6$uc$&6amury(4e6noh0$ocn+p!'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_environment('DEBUG', mapper=boolean_mapper)

ALLOWED_HOSTS = get_environment('ALLOWED_HOSTS', mapper=list_mapper_factory())
ALLOWED_CIDR_NETS = get_environment('ALLOWED_CIDR_NETS', mapper=list_mapper_factory())


# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'main.middleware.AllowCIDRMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'main.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_URL = f'/static/{dirhash(STATICFILES_DIRS[0])}/'

GITLAB_HOST = get_environment('GITLAB_HOST')
GITLAB_PRIVATE_TOKEN = get_environment('GITLAB_PRIVATE_TOKEN')

JIRA_HOST = get_environment('JIRA_HOST')
JIRA_USERNAME = get_environment('JIRA_USERNAME')
JIRA_PASSWORD = get_environment('JIRA_PASSWORD')
JIRA_PROJECTS = get_environment('JIRA_PROJECTS', mapper=list_mapper_factory())

ROCKET_HOOK_URL = get_environment('ROCKET_HOOK_URL', default=None)

def load_projects(raw: str) -> List[Project]:
    data = json.loads(raw)
    projects = []
    for entry in data:
        projects.append(
            Project(
                name=entry['name'],
                gitlab_id=entry['gitlab_id'],
                production_environment_branch=entry['production_environment_branch'],
                merge_requests=[MergeRequest(
                    merge_type=getattr(MergeRequest.MergeType, mr_data['merge_type']),
                    source_branch=mr_data['source_branch'],
                    target_branch=mr_data['target_branch'],
                ) for mr_data in entry['merges']],
                versioning_scheme=entry['versioning_scheme'],
                tag_group=entry['tag_group'],
                production_release_jira_transitions=entry['production_release_jira_transitions'],
                jira_warning_labels=entry['jira_warning_labels'],
            )
        )
    return projects


PROJECTS = get_environment('PROJECTS', mapper=load_projects)
