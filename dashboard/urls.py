from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('gantt/', views.GanttView.as_view(), name='gantt'),
]
