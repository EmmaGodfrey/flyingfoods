"""Admin registrations for menu models."""

from django.contrib import admin

from apps.menu.models import MenuItem, RecipeLine, RecipeVersion


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "pos_code", "status")
    list_filter = ("status",)


@admin.register(RecipeVersion)
class RecipeVersionAdmin(admin.ModelAdmin):
    list_display = ("menu_item", "version_no", "status", "effective_from", "effective_to")
    list_filter = ("status",)


admin.site.register(RecipeLine)
