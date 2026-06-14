"""Menu item and recipe version endpoints."""

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.menu.models import MenuItem, RecipeVersion
from apps.menu.serializers import (
    MenuItemSerializer,
    PublishSerializer,
    RecipeVersionCreateSerializer,
    RecipeVersionSerializer,
)
from apps.menu.services import (
    create_recipe_version,
    deactivate_menu_item,
    guard_delete,
    publish_version,
    submit_for_review,
)
from apps.users.permissions import IsAdmin


class MenuItemListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/menu-items/."""

    serializer_class = MenuItemSerializer
    filterset_fields = ["status", "category"]

    def get_permissions(self):
        """Reads open to any authenticated user; writes admin-only."""
        return [IsAdmin()] if self.request.method == "POST" else super().get_permissions()

    def get_queryset(self):
        return MenuItem.objects.all().order_by("name")


class MenuItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/menu-items/{id}/ — delete guarded by history."""

    serializer_class = MenuItemSerializer
    queryset = MenuItem.objects.all()

    def get_permissions(self):
        return [IsAdmin()] if self.request.method != "GET" else super().get_permissions()

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        menu_item = self.get_object()
        guard_delete(menu_item=menu_item)
        menu_item.delete()
        return Response(status=204)


class DeactivateMenuItemView(APIView):
    """POST /api/menu-items/{id}/deactivate/."""

    permission_classes = [IsAdmin]

    def post(self, request: Request, pk) -> Response:
        menu_item = get_object_or_404(MenuItem, pk=pk)
        deactivate_menu_item(menu_item=menu_item, user=request.user)
        return Response(MenuItemSerializer(menu_item).data)


class RecipeVersionListCreateView(APIView):
    """GET/POST /api/menu-items/{id}/recipe-versions/."""

    def get_permissions(self):
        return [IsAdmin()] if self.request.method == "POST" else super().get_permissions()

    def get(self, request: Request, pk) -> Response:
        versions = RecipeVersion.objects.filter(menu_item_id=pk).prefetch_related("lines")
        return Response(RecipeVersionSerializer(versions, many=True).data)

    def post(self, request: Request, pk) -> Response:
        menu_item = get_object_or_404(MenuItem, pk=pk)
        serializer = RecipeVersionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lines = [(row["product"], row["qty_per_serving"]) for row in serializer.validated_data["lines"]]
        version = create_recipe_version(
            menu_item=menu_item,
            lines=lines,
            selling_price=serializer.validated_data.get("selling_price"),
            user=request.user,
        )
        return Response(RecipeVersionSerializer(version).data, status=201)


class RecipeVersionDetailView(generics.RetrieveAPIView):
    """GET /api/recipe-versions/{id}/."""

    serializer_class = RecipeVersionSerializer
    queryset = RecipeVersion.objects.prefetch_related("lines")


class SubmitReviewView(APIView):
    """POST /api/recipe-versions/{id}/submit-review/."""

    permission_classes = [IsAdmin]

    def post(self, request: Request, pk) -> Response:
        version = get_object_or_404(RecipeVersion, pk=pk)
        submit_for_review(version=version, user=request.user)
        return Response(RecipeVersionSerializer(version).data)


class PublishView(APIView):
    """POST /api/recipe-versions/{id}/publish/."""

    permission_classes = [IsAdmin]

    def post(self, request: Request, pk) -> Response:
        version = get_object_or_404(RecipeVersion, pk=pk)
        serializer = PublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        publish_version(
            version=version,
            effective_from=serializer.validated_data["effective_from"],
            user=request.user,
        )
        return Response(RecipeVersionSerializer(version).data)
