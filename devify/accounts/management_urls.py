from django.urls import path

from accounts.views.management import (
    ManagementGroupListView,
    ManagementUserListView,
)


urlpatterns = [
    path("users/", ManagementUserListView.as_view(), name="management-users"),
    path("groups/", ManagementGroupListView.as_view(), name="management-groups"),
]
