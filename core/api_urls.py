"""
API URL configuration for the core app.
"""

from django.urls import path
from . import views

app_name = 'core_api'

urlpatterns = [
    # Dashboard data API
    path('dashboard-data/', views.api_dashboard_data, name='dashboard_data'),
]
