
from django.contrib import admin
from django.urls import path, include


from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path

from .views import *

schema_view = get_schema_view(
    openapi.Info(
        title="HARPIE Insurance Comparison System API DOCS",
        default_version='v1',
        description="API Documentation for HARPIE Insurance Comparison System",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('core.urls')),
    path('api/v1/', include('bookingApp.urls')),




    #  DOCUMENTATION
    
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('', index, name='index'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)