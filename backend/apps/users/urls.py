"""User administration URL routes mounted at /api/users/."""

from django.urls import path

from apps.users.views import UserDetailView, UserListCreateView

urlpatterns = [
    path("", UserListCreateView.as_view(), name="user-list"),
    path("<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
]
