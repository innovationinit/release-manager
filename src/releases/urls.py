from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views


app_name = 'releases'
urlpatterns = [
    path('', views.ReleasesView.as_view(), name='releases'),
    path('create-merge-request/', views.CreateMergeRequestView.as_view(), name='create-merge-request'),
    path('create-tag/', views.CreateTagView.as_view(), name='create-tag'),
    path('post-deployment-hook/', csrf_exempt(views.PostDeploymentHookView.as_view()), name='post-deployment-hook'),
]
