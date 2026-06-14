"""Root URL configuration: every app mounts under /api/."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.users.auth_urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.masterdata.urls")),
    path("api/", include("apps.menu.urls")),
    path("api/pos/", include("apps.pos_ingest.urls")),
    path("api/", include("apps.kitchen.urls")),
    path("api/", include("apps.inventory.urls")),
    path("api/", include("apps.procurement.urls")),
    path("api/", include("apps.wastage.urls")),
    path("api/pastel/", include("apps.pastel.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/reports/", include("apps.reports.urls")),
]
