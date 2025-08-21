"""
Views for the Nicmah System Management.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.db.models import Sum, Count, Q, F, Avg
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from datetime import timedelta, date
from decimal import Decimal
import json
import csv
from .models import Product, Sale, SaleItem, Batch, StockAdjustment, BackupLog


def login_view(request):
    """Simple login view for the system."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'core/login.html')


@login_required
def dashboard(request):
    """Main dashboard view with key metrics and charts."""
    
    # Get date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    year_ago = today - timedelta(days=365)
    
    # Sales data
    daily_sales = Sale.objects.filter(
        sale_date__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    weekly_sales = Sale.objects.filter(
        sale_date__date__gte=week_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    monthly_sales = Sale.objects.filter(
        sale_date__date__gte=month_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    yearly_sales = Sale.objects.filter(
        sale_date__date__gte=year_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Sales count
    daily_sales_count = Sale.objects.filter(sale_date__date=today).count()
    weekly_sales_count = Sale.objects.filter(sale_date__date__gte=week_ago).count()
    monthly_sales_count = Sale.objects.filter(sale_date__date__gte=month_ago).count()
    
    # Top movers (last 30 days)
    top_products = SaleItem.objects.filter(
        sale__sale_date__date__gte=month_ago
    ).values('product__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_quantity')[:10]
    
    # Low stock alerts
    low_stock_products = Product.objects.filter(
        is_active=True
    ).annotate(
        total_stock=Sum('batches__quantity')
    ).filter(
        total_stock__lte=F('reorder_level')
    ).filter(
        total_stock__gt=0
    )[:10]
    
    # Expiry alerts
    expiry_30_days = Batch.objects.filter(
        expiry_date__lte=today + timedelta(days=30),
        expiry_date__gt=today,
        quantity__gt=0
    ).select_related('product').order_by('expiry_date')[:10]
    
    # Recent sales
    recent_sales = Sale.objects.select_related().order_by('-sale_date')[:5]
    
    # Stock value
    total_stock_value = sum(
        batch.quantity * batch.cost_price 
        for batch in Batch.objects.filter(quantity__gt=0)
    )
    
    # Seller count
    unique_sellers = Sale.objects.values('seller_name').distinct().count()
    
    # Chart data for sales trend (last 7 days)
    sales_trend = []
    for i in range(7):
        date_check = today - timedelta(days=i)
        day_sales = Sale.objects.filter(
            sale_date__date=date_check
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        sales_trend.append({
            'date': date_check.strftime('%b %d'),
            'sales': float(day_sales)
        })
    sales_trend.reverse()
    
    context = {
        'daily_sales': daily_sales,
        'weekly_sales': weekly_sales,
        'monthly_sales': monthly_sales,
        'yearly_sales': yearly_sales,
        'daily_sales_count': daily_sales_count,
        'weekly_sales_count': weekly_sales_count,
        'monthly_sales_count': monthly_sales_count,
        'top_products': top_products,
        'low_stock_products': low_stock_products,
        'expiry_30_days': expiry_30_days,
        'recent_sales': recent_sales,
        'total_stock_value': total_stock_value,
        'unique_sellers': unique_sellers,
        'sales_trend': sales_trend,
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def reports(request):
    """Reports view for various business metrics."""
    
    # Get date range from request
    date_range = request.GET.get('range', 'month')
    if date_range == 'week':
        start_date = timezone.now().date() - timedelta(days=7)
    elif date_range == 'month':
        start_date = timezone.now().date() - timedelta(days=30)
    elif date_range == 'quarter':
        start_date = timezone.now().date() - timedelta(days=90)
    else:
        start_date = timezone.now().date() - timedelta(days=365)
    
    # Sales report
    sales_data = Sale.objects.filter(
        sale_date__date__gte=start_date
    ).aggregate(
        total_sales=Sum('total_amount'),
        total_discount=Sum('discount'),
        total_tax=Sum('tax_amount'),
        sales_count=Count('id')
    )
    
    # Top products by revenue
    top_products_revenue = SaleItem.objects.filter(
        sale__sale_date__date__gte=start_date
    ).values('product__name', 'product__category').annotate(
        total_revenue=Sum('total_price'),
        total_quantity=Sum('quantity')
    ).order_by('-total_revenue')[:20]
    
    # Top products by quantity
    top_products_quantity = SaleItem.objects.filter(
        sale__sale_date__date__gte=start_date
    ).values('product__name', 'product__category').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_quantity')[:20]
    
    # Sales by payment type
    sales_by_type = Sale.objects.filter(
        sale_date__date__gte=start_date
    ).values('sale_type').annotate(
        total_amount=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total_amount')
    
    # Stock report
    stock_report = Product.objects.filter(
        is_active=True
    ).annotate(
        total_stock=Sum('batches__quantity'),
        stock_value=Sum(F('batches__quantity') * F('batches__cost_price'))
    ).order_by('total_stock')
    
    context = {
        'date_range': date_range,
        'start_date': start_date,
        'sales_data': sales_data,
        'top_products_revenue': top_products_revenue,
        'top_products_quantity': top_products_quantity,
        'sales_by_type': sales_by_type,
        'stock_report': stock_report,
    }
    
    return render(request, 'core/reports.html', context)


@login_required
def product_detail(request, product_id):
    """Detailed view for a specific product."""
    
    product = get_object_or_404(Product, id=product_id)
    
    # Get product sales history
    sales_history = SaleItem.objects.filter(
        product=product
    ).select_related('sale').order_by('-sale__sale_date')[:20]
    
    # Get stock movements
    stock_movements = StockAdjustment.objects.filter(
        product=product
    ).select_related('batch', 'adjusted_by').order_by('-adjusted_at')[:20]
    
    # Get expiry alerts
    expiry_alerts = Batch.objects.filter(
        product=product,
        quantity__gt=0
    ).order_by('expiry_date')
    
    context = {
        'product': product,
        'sales_history': sales_history,
        'stock_movements': stock_movements,
        'expiry_alerts': expiry_alerts,
    }
    
    return render(request, 'core/product_detail.html', context)


@login_required
def export_data(request):
    """Export data view with options."""
    context = {
        'data_types': [
            ('products', 'Products'),
            ('sales', 'Sales'),
            ('stock', 'Stock Levels'),
            ('batches', 'Batches'),
            ('adjustments', 'Stock Adjustments'),
            ('all', 'All Data')
        ],
        'formats': [
            ('excel', 'Excel (.xlsx)'),
            ('csv', 'CSV')
        ]
    }
    return render(request, 'core/export_data.html', context)


@login_required
def sales_entry(request):
    """Daily sales entry form for evening input."""
    if request.method == 'POST':
        try:
            # Get form data
            seller_name = request.POST.get('seller_name', '').strip()
            sale_type = request.POST.get('sale_type', 'retail')
            discount = Decimal(request.POST.get('discount', '0'))
            notes = request.POST.get('notes', '').strip()
            
            # Process sale items first to calculate totals
            items_data = json.loads(request.POST.get('items_data', '[]'))
            subtotal = Decimal('0')
            total_vat = Decimal('0')
            
            # Validate and calculate totals
            for item_data in items_data:
                product_id = item_data.get('product_id')
                quantity = Decimal(item_data.get('quantity', '0'))
                unit_price = Decimal(item_data.get('unit_price', '0'))
                
                if product_id and quantity > 0 and unit_price > 0:
                    product = Product.objects.get(id=product_id)
                    item_subtotal = quantity * unit_price
                    item_vat = (item_subtotal * product.vat_rate) / 100
                    
                    subtotal += item_subtotal
                    total_vat += item_vat
            
            # Calculate total amount including VAT
            total_amount = subtotal + total_vat
            
            # Create sale record
            sale = Sale.objects.create(
                seller_name=seller_name,
                sale_type=sale_type,
                subtotal=subtotal,
                total_vat=total_vat,
                total_amount=total_amount,
                discount=discount,
                notes=notes,
                sale_date=timezone.now()
            )
            
            # Process sale items
            for item_data in items_data:
                product_id = item_data.get('product_id')
                batch_id = item_data.get('batch_id')
                quantity = Decimal(item_data.get('quantity', '0'))
                unit_price = Decimal(item_data.get('unit_price', '0'))
                
                if product_id and quantity > 0 and unit_price > 0:
                    product = Product.objects.get(id=product_id)
                    batch = Batch.objects.get(id=batch_id) if batch_id else None
                    
                    # Calculate item VAT
                    item_subtotal = quantity * unit_price
                    item_vat = (item_subtotal * product.vat_rate) / 100
                    item_total = item_subtotal + item_vat
                    
                    # Create sale item
                    sale_item = SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        batch=batch,
                        quantity=quantity,
                        unit_price=unit_price,
                        vat_rate=product.vat_rate,
                        vat_amount=item_vat,
                        price_without_vat=item_subtotal,
                        total_price=item_total
                    )
                    
                    # Update stock
                    if batch:
                        batch.quantity = max(0, batch.quantity - quantity)
                        batch.save()
            
            messages.success(request, f'Sale recorded successfully! Invoice: {sale.invoice_number}')
            return redirect('core:sales_list')
            
        except Exception as e:
            messages.error(request, f'Error recording sale: {str(e)}')
    
    # Get available products for the form
    products = Product.objects.filter(is_active=True).select_related()
    batches = Batch.objects.filter(quantity__gt=0, expiry_date__gt=timezone.now().date()).select_related('product')
    
    context = {
        'products': products,
        'batches': batches,
        'sale_types': Sale.SALE_TYPES,
    }
    return render(request, 'core/sales_entry.html', context)


@login_required
def api_dashboard_data(request):
    """API endpoint for dashboard chart data."""
    
    # Get date range
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    # Sales trend data
    sales_trend = []
    for i in range(days):
        date_check = start_date + timedelta(days=i)
        day_sales = Sale.objects.filter(
            sale_date__date=date_check
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        sales_trend.append({
            'date': date_check.strftime('%Y-%m-%d'),
            'sales': float(day_sales)
        })
    
    # Top products data
    top_products = SaleItem.objects.filter(
        sale__sale_date__date__gte=start_date
    ).values('product__name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')[:10]
    
    # Category sales data
    category_sales = SaleItem.objects.filter(
        sale__sale_date__date__gte=start_date
    ).values('product__category').annotate(
        total_revenue=Sum('total_price')
    ).order_by('-total_revenue')
    
    data = {
        'sales_trend': sales_trend,
        'top_products': list(top_products),
        'category_sales': list(category_sales),
    }
    
    return JsonResponse(data)


@login_required
def analytics_dashboard(request):
    """Analytics dashboard with comprehensive sales visualizations."""
    
    # Get date range from request or default to last 12 months
    months = int(request.GET.get('months', 12))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=months * 30)
    
    # Monthly sales data
    monthly_sales = []
    monthly_vat = []
    monthly_profit = []
    months_labels = []
    
    for i in range(months):
        month_start = end_date.replace(day=1) - timedelta(days=i * 30)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end.replace(day=1) - timedelta(days=1)
        
        month_sales = Sale.objects.filter(
            sale_date__date__gte=month_start,
            sale_date__date__lte=month_end
        ).aggregate(
            total_sales=Sum('total_amount'),
            total_vat=Sum('total_vat'),
            total_discount=Sum('discount')
        )
        
        total_sales = month_sales['total_sales'] or 0
        total_vat = month_sales['total_vat'] or 0
        total_discount = month_sales['total_discount'] or 0
        total_profit = total_sales - total_discount - total_vat
        
        monthly_sales.append(float(total_sales))
        monthly_vat.append(float(total_vat))
        monthly_profit.append(float(total_profit))
        months_labels.append(month_start.strftime('%b %Y'))
    
    # Reverse to show chronological order
    monthly_sales.reverse()
    monthly_vat.reverse()
    monthly_profit.reverse()
    months_labels.reverse()
    
    # Weekly sales data (last 12 weeks)
    weekly_sales = []
    weekly_labels = []
    
    for i in range(12):
        week_start = end_date - timedelta(weeks=i, days=end_date.weekday())
        week_end = week_start + timedelta(days=6)
        
        week_total = Sale.objects.filter(
            sale_date__date__gte=week_start,
            sale_date__date__lte=week_end
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        weekly_sales.append(float(week_total))
        weekly_labels.append(f"Week {week_start.strftime('%U')}")
    
    weekly_sales.reverse()
    weekly_labels.reverse()
    
    # Day of week analysis (last 3 months)
    day_of_week_sales = []
    day_labels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for i, day_name in enumerate(day_labels):
        day_total = Sale.objects.filter(
            sale_date__date__gte=start_date,
            sale_date__week_day=i+1  # Django uses 1-7 for Monday-Sunday
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        day_of_week_sales.append(float(day_total))
    
    # Top performing months
    top_months = []
    for i, (month, sales) in enumerate(zip(months_labels, monthly_sales)):
        if sales > 0:
            top_months.append({
                'month': month,
                'sales': sales,
                'vat': monthly_vat[i],
                'profit': monthly_profit[i]
            })
    
    top_months.sort(key=lambda x: x['sales'], reverse=True)
    top_months = top_months[:5]  # Top 5 months
    
    # Sales by seller performance
    seller_performance = Sale.objects.filter(
        sale_date__date__gte=start_date
    ).values('seller_name').annotate(
        total_sales=Sum('total_amount'),
        total_vat=Sum('total_vat'),
        sales_count=Count('id')
    ).order_by('-total_sales')[:10]
    
    # Product category performance
    category_performance = SaleItem.objects.filter(
        sale__sale_date__date__gte=start_date
    ).values('product__category').annotate(
        total_revenue=Sum('total_price'),
        total_quantity=Sum('quantity'),
        avg_price=Avg('unit_price')
    ).order_by('-total_revenue')
    
    # VAT analysis
    vat_summary = {
        'total_vat_collected': sum(monthly_vat),
        'avg_vat_rate': 16.0,  # Default VAT rate
        'vat_by_month': monthly_vat,
        'vat_percentage': (sum(monthly_vat) / sum(monthly_sales) * 100) if sum(monthly_sales) > 0 else 0
    }
    
    context = {
        'months_labels': months_labels,
        'monthly_sales': monthly_sales,
        'monthly_vat': monthly_vat,
        'monthly_profit': monthly_profit,
        'weekly_labels': weekly_labels,
        'weekly_sales': weekly_sales,
        'day_labels': day_labels,
        'day_of_week_sales': day_of_week_sales,
        'top_months': top_months,
        'seller_performance': seller_performance,
        'category_performance': category_performance,
        'vat_summary': vat_summary,
        'date_range': f"Last {months} months",
        'total_sales': sum(monthly_sales),
        'total_vat': sum(monthly_vat),
        'total_profit': sum(monthly_profit),
    }
    
    return render(request, 'core/analytics.html', context)


class ProductListView(LoginRequiredMixin, ListView):
    """List view for products with search and filtering."""
    
    model = Product
    template_name = 'core/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Product.objects.all()
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(category__icontains=search)
            )
        
        # Category filter
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Stock status filter
        stock_status = self.request.GET.get('stock_status')
        if stock_status:
            if stock_status == 'in_stock':
                queryset = queryset.filter(batches__quantity__gt=0).distinct()
            elif stock_status == 'low_stock':
                queryset = queryset.filter(
                    batches__quantity__lte=F('reorder_level')
                ).distinct()
            elif stock_status == 'out_of_stock':
                queryset = queryset.filter(batches__quantity=0).distinct()
        
        return queryset.select_related().prefetch_related('batches')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Product.objects.values_list('category', flat=True).distinct()
        return context


class SaleListView(LoginRequiredMixin, ListView):
    """List view for sales with search and filtering."""
    
    model = Sale
    template_name = 'core/sale_list.html'
    context_object_name = 'sales'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Sale.objects.all()
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(seller_name__icontains=search)
            )
        
        # Date range filter
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(sale_date__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(sale_date__date__lte=end_date)
        
        # Sale type filter
        sale_type = self.request.GET.get('sale_type')
        if sale_type:
            queryset = queryset.filter(sale_type=sale_type)
        
        return queryset.select_related().prefetch_related('items')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sale_types'] = Sale.SALE_TYPES
        
        # Calculate summary statistics
        queryset = self.get_queryset()
        context['total_sales'] = queryset.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        context['avg_sale'] = queryset.aggregate(
            avg=Avg('total_amount')
        )['avg'] or 0
        context['unique_sellers'] = queryset.values('seller_name').distinct().count()
        
        return context
