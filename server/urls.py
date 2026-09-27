"""
URL configuration for server project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path


def health_check(request):
    """Health check endpoint for Docker and monitoring."""
    return JsonResponse({'status': 'healthy', 'service': 'sensor_server'})


urlpatterns = [
    path('', lambda request: redirect('login'), name='home'),
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/', include('treeapi.urls')),
    path('', include('treeapi.urls')),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
