from django.contrib import admin
from django.urls import path, include
from django.views.static import serve
from django.urls import re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect
from django.http import JsonResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('api/payment/', include('payment.urls')),
    path('api/shop/', include('shop.urls')),
    path('', lambda request: HttpResponseRedirect('/api/auth/register/')),

]


urlpatterns += [
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

def custom_404_handler(request, exception):
    return JsonResponse({"error": "Invalid URL, please correct the URL"}, status=404)

handler404 = custom_404_handler