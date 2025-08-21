"""
Database models for the Nicmah System Management.
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class Product(models.Model):
    """Product model for managing inventory items."""
    
    name = models.CharField(max_length=200, verbose_name="Product Name")
    sku = models.CharField(max_length=50, unique=True, verbose_name="SKU")
    category = models.CharField(max_length=100, verbose_name="Category")
    unit = models.CharField(max_length=20, verbose_name="Unit (kg, L, pcs)")
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Cost Price"
    )
    selling_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Selling Price"
    )
    vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=16.0,
        verbose_name="VAT Rate (%)"
    )
    reorder_level = models.IntegerField(verbose_name="Reorder Level")
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Product"
        verbose_name_plural = "Products"
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def gross_profit_margin(self):
        """Calculate gross profit margin percentage."""
        if self.selling_price > 0:
            return ((self.selling_price - self.cost_price) / self.selling_price) * 100
        return 0

    @property
    def vat_amount(self):
        """Calculate VAT amount for this product."""
        return (self.selling_price * self.vat_rate) / 100

    @property
    def price_without_vat(self):
        """Calculate price excluding VAT."""
        return self.selling_price - self.vat_amount

    @property
    def current_stock(self):
        """Get current total stock across all batches."""
        return sum(batch.quantity for batch in self.batches.all())

    @property
    def stock_status(self):
        """Get stock status (In Stock, Low Stock, Out of Stock)."""
        current_stock = self.current_stock
        if current_stock == 0:
            return "Out of Stock"
        elif current_stock <= self.reorder_level:
            return "Low Stock"
        else:
            return "In Stock"


class Batch(models.Model):
    """Batch model for tracking product batches and expiry dates."""
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='batches',
        verbose_name="Product"
    )
    batch_number = models.CharField(max_length=100, verbose_name="Batch Number")
    quantity = models.IntegerField(
        validators=[MinValueValidator(0)], 
        verbose_name="Quantity"
    )
    expiry_date = models.DateField(verbose_name="Expiry Date")
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Batch Cost Price"
    )
    supplier = models.CharField(max_length=200, blank=True, verbose_name="Supplier")
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['expiry_date']
        verbose_name = "Batch"
        verbose_name_plural = "Batches"
        indexes = [
            models.Index(fields=['expiry_date']),
            models.Index(fields=['batch_number']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.batch_number}"

    @property
    def days_to_expiry(self):
        """Calculate days until expiry."""
        today = timezone.now().date()
        days = (self.expiry_date - today).days
        return days

    @property
    def expiry_status(self):
        """Get expiry status."""
        days = self.days_to_expiry
        if days < 0:
            return "Expired"
        elif days <= 30:
            return "Expiring Soon"
        else:
            return "Good"


class Sale(models.Model):
    """Sale model for recording customer transactions."""
    
    SALE_TYPES = [
        ('cash', 'Cash'),
        ('credit', 'Credit'),
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
    ]
    
    invoice_number = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Invoice Number"
    )
    seller_name = models.CharField(max_length=200, verbose_name="Seller Name", default="Unknown Seller")
    sale_type = models.CharField(
        max_length=20, 
        choices=SALE_TYPES, 
        verbose_name="Sale Type"
    )
    subtotal = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Subtotal (Excluding VAT)",
        default=0
    )
    total_vat = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Total VAT Amount",
        default=0
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Total Amount (Including VAT)"
    )
    discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="Discount"
    )
    tax_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="Tax Amount (Legacy)"
    )
    sale_date = models.DateTimeField(auto_now_add=True, verbose_name="Sale Date")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        ordering = ['-sale_date']
        verbose_name = "Sale"
        verbose_name_plural = "Sales"
        indexes = [
            models.Index(fields=['sale_date']),
            models.Index(fields=['seller_name']),
            models.Index(fields=['sale_type']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.seller_name}"

    @property
    def net_amount(self):
        """Calculate net amount after discount."""
        return self.total_amount - self.discount

    @property
    def vat_rate_percentage(self):
        """Calculate overall VAT rate percentage for the sale."""
        if self.subtotal > 0:
            return (self.total_vat / self.subtotal) * 100
        return 0


class SaleItem(models.Model):
    """Individual items within a sale."""
    
    sale = models.ForeignKey(
        Sale, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name="Sale"
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        verbose_name="Product"
    )
    batch = models.ForeignKey(
        Batch, 
        on_delete=models.CASCADE,
        verbose_name="Batch"
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Quantity"
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Unit Price"
    )
    vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="VAT Rate (%)",
        default=16.0
    )
    vat_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="VAT Amount",
        default=0
    )
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Total Price (Including VAT)"
    )
    price_without_vat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Price Without VAT",
        default=0
    )

    class Meta:
        verbose_name = "Sale Item"
        verbose_name_plural = "Sale Items"

    def save(self, *args, **kwargs):
        """Calculate prices and VAT before saving."""
        # Set VAT rate from product if not specified
        if not self.vat_rate:
            self.vat_rate = self.product.vat_rate
        
        # Calculate price without VAT
        self.price_without_vat = self.quantity * self.unit_price
        
        # Calculate VAT amount
        self.vat_amount = (self.price_without_vat * self.vat_rate) / 100
        
        # Calculate total price including VAT
        self.total_price = self.price_without_vat + self.vat_amount
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} - {self.sale.invoice_number}"


class StockAdjustment(models.Model):
    """Model for tracking stock adjustments (additions, subtractions, etc.)."""
    
    ADJUSTMENT_TYPES = [
        ('addition', 'Stock Addition'),
        ('subtraction', 'Stock Subtraction'),
        ('damage', 'Damaged Stock'),
        ('expiry', 'Expired Stock'),
        ('theft', 'Theft/Loss'),
        ('correction', 'Stock Correction'),
    ]
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        verbose_name="Product"
    )
    batch = models.ForeignKey(
        Batch, 
        on_delete=models.CASCADE,
        verbose_name="Batch"
    )
    adjustment_type = models.CharField(
        max_length=20, 
        choices=ADJUSTMENT_TYPES,
        verbose_name="Adjustment Type"
    )
    quantity = models.IntegerField(verbose_name="Quantity")
    reason = models.TextField(verbose_name="Reason")
    adjusted_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Adjusted By"
    )
    adjusted_at = models.DateTimeField(auto_now_add=True, verbose_name="Adjusted At")

    class Meta:
        ordering = ['-adjusted_at']
        verbose_name = "Stock Adjustment"
        verbose_name_plural = "Stock Adjustments"
        indexes = [
            models.Index(fields=['adjusted_at']),
            models.Index(fields=['adjustment_type']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.adjustment_type} ({self.quantity})"


class BackupLog(models.Model):
    """Model for tracking automated backup operations."""
    
    backup_file = models.CharField(max_length=255, verbose_name="Backup File")
    backup_size = models.BigIntegerField(verbose_name="Backup Size (bytes)")
    backup_date = models.DateTimeField(auto_now_add=True, verbose_name="Backup Date")
    status = models.CharField(
        max_length=20, 
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('partial', 'Partial'),
        ],
        verbose_name="Status"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    duration = models.DurationField(null=True, blank=True, verbose_name="Duration")

    class Meta:
        ordering = ['-backup_date']
        verbose_name = "Backup Log"
        verbose_name_plural = "Backup Logs"
        indexes = [
            models.Index(fields=['backup_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Backup {self.backup_file} - {self.status}"

    @property
    def backup_size_mb(self):
        """Convert backup size to MB."""
        return round(self.backup_size / (1024 * 1024), 2)
