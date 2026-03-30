from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SaleItem, Sale, Customer, Seller
from decimal import Decimal

@receiver(post_save, sender=SaleItem)
def update_sale_totals(sender, instance, created, **kwargs):
    """Update Sale subtotal, vat and total_amount when an item is added or updated."""
    sale = instance.sale
    items = sale.items.all()
    
    subtotal = sum(item.price_without_vat for item in items)
    total_vat = sum(item.vat_amount for item in items)
    total_amount = subtotal + total_vat
    
    # We update fields directly to avoid infinite loops if Sale has its own post_save
    Sale.objects.filter(id=sale.id).update(
        subtotal=subtotal,
        total_vat=total_vat,
        total_amount=total_amount
    )


@receiver(post_save, sender=Sale)
def process_sale_business_logic(sender, instance, created, **kwargs):
    """Handle loyalty points, debt, and commissions on sale save."""
    # To avoid double-processing, we'd ideally have an 'is_processed' flag.
    # For now, we'll implement the logic based on the created flag or specific triggers.
    
    if created:
        # Initial processing if data is present at creation
        if instance.customer:
            # Initial debt if credit
            if instance.sale_type == 'credit' and not instance.is_paid:
                instance.customer.adjust_debt(instance.total_amount)
            
            # Loyalty points
            instance.customer.update_loyalty_points(instance.total_amount)
            
        if instance.seller:
            # Commission (Revenue based)
            commission = (instance.total_amount * instance.seller.commission_rate / 100)
            instance.seller.total_earned += commission
            instance.seller.save()
