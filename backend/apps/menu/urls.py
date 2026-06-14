"""Menu URL routes, mounted under /api/ by config/urls.py."""

from django.urls import path

from apps.menu.views import (
    DeactivateMenuItemView,
    MenuItemDetailView,
    MenuItemListCreateView,
    PublishView,
    RecipeVersionDetailView,
    RecipeVersionListCreateView,
    SubmitReviewView,
)

urlpatterns = [
    path("menu-items/", MenuItemListCreateView.as_view(), name="menu-item-list"),
    path("menu-items/<uuid:pk>/", MenuItemDetailView.as_view(), name="menu-item-detail"),
    path("menu-items/<uuid:pk>/deactivate/", DeactivateMenuItemView.as_view(), name="menu-item-deactivate"),
    path(
        "menu-items/<uuid:pk>/recipe-versions/",
        RecipeVersionListCreateView.as_view(),
        name="recipe-version-list",
    ),
    path("recipe-versions/<uuid:pk>/", RecipeVersionDetailView.as_view(), name="recipe-version-detail"),
    path("recipe-versions/<uuid:pk>/submit-review/", SubmitReviewView.as_view(), name="recipe-submit-review"),
    path("recipe-versions/<uuid:pk>/publish/", PublishView.as_view(), name="recipe-publish"),
]
