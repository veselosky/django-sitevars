from django.contrib import admin
from django.core.wsgi import get_wsgi_application
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]

application = get_wsgi_application()
