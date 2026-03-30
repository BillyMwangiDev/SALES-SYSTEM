"""
URL configuration for the core app.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('', views.dashboard, name='dashboard'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('sales/', views.SaleListView.as_view(), name='sale_list'),
    path('sales/new/', views.sales_entry, name='sales_entry'),
    path('reports/', views.reports, name='reports'),
    path('analytics/', views.analytics_dashboard, name='analytics'),
    path('pos/', views.pos_view, name='pos'),
    path('customers/', views.customer_list, name='customer_list'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('export/', views.export_data, name='export_data'),
    path('api/dashboard-data/', views.api_dashboard_data, name='api_dashboard_data'),
]
