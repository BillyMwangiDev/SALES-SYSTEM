"""
Admin interface configuration for the Nicmah System Management.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import date, timedelta
from .models import Product, Batch, Sale, SaleItem, StockAdjustment, BackupLog


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin interface for Product model."""
    
    list_display = [
        'name', 'sku', 'category', 'cost_price', 'selling_price', 'vat_rate',
        'gross_profit_margin', 'current_stock', 'stock_status', 'reorder_level', 'is_active'
    ]
    list_filter = ['category', 'is_active', 'created_at', 'vat_rate']
    search_fields = ['name', 'sku', 'category', 'description']
    readonly_fields = ['gross_profit_margin', 'current_stock', 'stock_status', 'vat_amount', 'price_without_vat', 'created_at', 'updated_at']
    list_editable = ['is_active', 'reorder_level', 'vat_rate']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'sku', 'category', 'unit', 'description', 'is_active')
        }),
        ('Pricing', {
            'fields': ('cost_price', 'selling_price', 'vat_rate', 'reorder_level')
        }),
        ('Calculated Fields', {
            'fields': ('gross_profit_margin', 'vat_amount', 'price_without_vat'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def gross_profit_margin(self, obj):
        """Display gross profit margin with color coding."""
        margin = obj.gross_profit_margin
        if margin >= 30:
            color = 'green'
        elif margin >= 15:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {};">{:.2f}%</span>', color, margin)
    gross_profit_margin.short_description = "Gross Profit Margin"
    
    def current_stock(self, obj):
        """Display current stock with color coding."""
        stock = obj.current_stock
        if stock == 0:
            color = 'red'
        elif stock <= obj.reorder_level:
            color = 'orange'
        else:
            color = 'green'
        return format_html('<span style="color: {};">{}</span>', color, stock)
    current_stock.short_description = "Current Stock"
    
    def stock_status(self, obj):
        """Display stock status with color coding."""
        status = obj.stock_status
        if status == "Out of Stock":
            color = 'red'
        elif status == "Low Stock":
            color = 'orange'
        else:
            color = 'green'
        return format_html('<span style="color: {};">{}</span>', color, status)
    stock_status.short_description = "Stock Status"
    
    actions = ['activate_products', 'deactivate_products', 'export_products']
    
    def activate_products(self, request, queryset):
        """Activate selected products."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} products activated successfully.')
    activate_products.short_description = "Activate selected products"
    
    def deactivate_products(self, request, queryset):
        """Deactivate selected products."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} products deactivated successfully.')
    deactivate_products.short_description = "Deactivate selected products"


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    """Admin interface for Batch model."""
    
    list_display = [
        'product', 'batch_number', 'quantity', 'expiry_date', 
        'cost_price', 'days_to_expiry', 'expiry_status', 'supplier'
    ]
    list_filter = ['expiry_date', 'product__category', 'supplier', 'created_at']
    search_fields = ['batch_number', 'product__name', 'supplier']
    readonly_fields = ['days_to_expiry', 'expiry_status', 'created_at']
    list_editable = ['quantity', 'cost_price']
    
    fieldsets = (
        ('Batch Information', {
            'fields': ('product', 'batch_number', 'supplier', 'notes')
        }),
        ('Stock Details', {
            'fields': ('quantity', 'cost_price', 'expiry_date')
        }),
        ('System Information', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def days_to_expiry(self, obj):
        """Display days to expiry with color coding."""
        days = obj.days_to_expiry
        if days < 0:
            color = 'red'
            text = 'Expired'
        elif days <= 30:
            color = 'orange'
            text = f'{days} days'
        else:
            color = 'green'
            text = f'{days} days'
        return format_html('<span style="color: {};">{}</span>', color, text)
    days_to_expiry.short_description = "Days to Expiry"
    
    def expiry_status(self, obj):
        """Display expiry status with color coding."""
        status = obj.expiry_status
        if status == "Expired":
            color = 'red'
        elif status == "Expiring Soon":
            color = 'orange'
        else:
            color = 'green'
        return format_html('<span style="color: {};">{}</span>', color, status)
    expiry_status.short_description = "Expiry Status"
    
    actions = ['mark_as_expired', 'export_batches']
    
    def mark_as_expired(self, request, queryset):
        """Mark selected batches as expired."""
        today = date.today()
        updated = queryset.filter(expiry_date__lt=today).update(quantity=0)
        self.message_user(request, f'{updated} expired batches marked as zero quantity.')
    mark_as_expired.short_description = "Mark expired batches as zero quantity"


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    """Admin interface for Sale model."""
    
    list_display = [
        'invoice_number', 'seller_name', 'sale_type', 
        'subtotal', 'total_vat', 'total_amount', 'net_amount', 'sale_date', 'items_count'
    ]
    list_filter = ['sale_type', 'sale_date', 'seller_name']
    search_fields = ['invoice_number', 'seller_name']
    readonly_fields = ['sale_date', 'net_amount', 'items_count', 'vat_rate_percentage']
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('invoice_number', 'seller_name', 'sale_type')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'total_vat', 'total_amount', 'discount', 'net_amount', 'vat_rate_percentage')
        }),
        ('Legacy Fields', {
            'fields': ('tax_amount',),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'sale_date'),
            'classes': ('collapse',)
        }),
    )
    
    def net_amount(self, obj):
        """Display net amount."""
        return f"KES {obj.net_amount:.2f}"
    net_amount.short_description = "Net Amount"
    
    def subtotal(self, obj):
        """Display subtotal."""
        return f"KES {obj.subtotal:.2f}"
    subtotal.short_description = "Subtotal"
    
    def total_vat(self, obj):
        """Display total VAT."""
        return f"KES {obj.total_vat:.2f}"
    total_vat.short_description = "Total VAT"
    
    def vat_rate_percentage(self, obj):
        """Display VAT rate percentage."""
        return f"{obj.vat_rate_percentage:.2f}%"
    vat_rate_percentage.short_description = "VAT Rate %"
    
    def items_count(self, obj):
        """Display count of items in sale."""
        return obj.items.count()
    items_count.short_description = "Items Count"
    
    actions = ['export_sales', 'generate_invoice']
    
    def export_sales(self, request, queryset):
        """Export selected sales to CSV."""
        # Implementation for CSV export
        pass
    export_sales.short_description = "Export selected sales to CSV"


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    """Admin interface for SaleItem model."""
    
    list_display = [
        'sale', 'product', 'batch', 'quantity', 
        'unit_price', 'vat_rate', 'vat_amount', 'price_without_vat', 'total_price', 'sale_link'
    ]
    list_filter = ['sale__sale_date', 'product__category', 'sale__sale_type', 'vat_rate']
    search_fields = ['sale__invoice_number', 'product__name', 'batch__batch_number']
    readonly_fields = ['total_price', 'price_without_vat', 'vat_amount', 'sale_link']
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('sale', 'product', 'batch')
        }),
        ('Item Details', {
            'fields': ('quantity', 'unit_price', 'vat_rate')
        }),
        ('Calculated Fields', {
            'fields': ('price_without_vat', 'vat_amount', 'total_price'),
            'classes': ('collapse',)
        }),
    )
    
    def sale_link(self, obj):
        """Create a link to the sale."""
        url = reverse('admin:core_sale_change', args=[obj.sale.id])
        return format_html('<a href="{}">{}</a>', url, obj.sale.invoice_number)
    sale_link.short_description = "Sale"
    
    def has_add_permission(self, request):
        """Prevent adding sale items directly."""
        return False


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    """Admin interface for StockAdjustment model."""
    
    list_display = [
        'product', 'batch', 'adjustment_type', 'quantity', 
        'adjusted_by', 'adjusted_at', 'reason_short'
    ]
    list_filter = ['adjustment_type', 'adjusted_at', 'product__category', 'adjusted_by']
    search_fields = ['product__name', 'batch__batch_number', 'reason']
    readonly_fields = ['adjusted_at', 'adjusted_by']
    
    fieldsets = (
        ('Adjustment Information', {
            'fields': ('product', 'batch', 'adjustment_type', 'quantity')
        }),
        ('Details', {
            'fields': ('reason', 'adjusted_by', 'adjusted_at')
        }),
    )
    
    def reason_short(self, obj):
        """Display shortened reason."""
        return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
    reason_short.short_description = "Reason"
    
    def save_model(self, request, obj, form, change):
        """Set adjusted_by to current user."""
        if not change:  # Only for new adjustments
            obj.adjusted_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['export_adjustments']


@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    """Admin interface for BackupLog model."""
    
    list_display = [
        'backup_file', 'backup_size_mb', 'backup_date', 
        'status', 'duration', 'notes_short'
    ]
    list_filter = ['status', 'backup_date']
    search_fields = ['backup_file', 'notes']
    readonly_fields = ['backup_file', 'backup_size', 'backup_date', 'backup_size_mb']
    
    fieldsets = (
        ('Backup Information', {
            'fields': ('backup_file', 'backup_size', 'backup_size_mb', 'backup_date')
        }),
        ('Status Details', {
            'fields': ('status', 'duration', 'notes')
        }),
    )
    
    def backup_size_mb(self, obj):
        """Display backup size in MB."""
        return f"{obj.backup_size_mb} MB"
    backup_size_mb.short_description = "Size (MB)"
    
    def notes_short(self, obj):
        """Display shortened notes."""
        if obj.notes:
            return obj.notes[:50] + '...' if len(obj.notes) > 50 else obj.notes
        return "-"
    notes_short.short_description = "Notes"
    
    def has_add_permission(self, request):
        """Prevent adding backup logs manually."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing backup logs."""
        return False


# Customize admin site
admin.site.site_header = "Nicmah System Management"
admin.site.site_title = "Nicmah Admin"
admin.site.index_title = "Welcome to Nicmah System Management"
