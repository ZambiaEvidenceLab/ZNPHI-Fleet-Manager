from django.contrib import admin
from django.urls import path, include

from accounts.views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('bookings/', include('bookings.urls')),
    path('fleet/', include('fleet.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('settings/', include('settings_app.urls')),
]
