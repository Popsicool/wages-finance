from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from django.conf import settings
from drf_yasg import openapi
from rest_framework import permissions
from django.conf.urls.static import static
from user.consumers import UserConsumer
schema_view = get_schema_view(
   openapi.Info(
      title="WAGES-FINANCE",
      default_version='v1',
      description="This is the backend APIs for Wages Finance",
      contact=openapi.Contact(email="akinolasamson1234@gmail.com"),
      license=openapi.License(name="Wages Finance"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('wages/', admin.site.urls),
    path('api/v1/auth/', include('authentication.urls')),
    path('api/v1/admin/', include('admin.urls')),
    path('api/v1/user/', include('user.urls')),
    path('api/v1/notification/', include('notification.urls')),
]
websocket_urlpatterns = [
    path("ws/user/", UserConsumer.as_asgi())
]
urlpatterns += static(settings.STATIC_URL,
                      document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)