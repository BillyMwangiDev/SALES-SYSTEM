"""
Management command to update existing data with VAT information.
This command will:
1. Set default VAT rates for existing products
2. Update existing sales with VAT calculations
3. Update existing sale items with VAT information
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Product, Sale, SaleItem
from decimal import Decimal


class Command(BaseCommand):
    help = 'Update existing data with VAT information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vat-rate',
            type=float,
            default=16.0,
            help='Default VAT rate to apply to existing products (default: 16.0)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )

    def handle(self, *args, **options):
        vat_rate = Decimal(str(options['vat_rate']))
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting VAT data update with rate: {vat_rate}%')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Update products
        products_updated = 0
        products = Product.objects.filter(vat_rate=16.0)  # Only update products with default rate
        
        for product in products:
            if not dry_run:
                product.vat_rate = vat_rate
                product.save()
            products_updated += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Updated {products_updated} products with VAT rate {vat_rate}%')
        )
        
        # Update existing sales
        sales_updated = 0
        sales = Sale.objects.filter(subtotal=0, total_vat=0)  # Only update sales without VAT data
        
        for sale in sales:
            if not dry_run:
                # Calculate subtotal and VAT from sale items
                subtotal = Decimal('0')
                total_vat = Decimal('0')
                
                for item in sale.items.all():
                    item_subtotal = item.quantity * item.unit_price
                    item_vat = (item_subtotal * item.product.vat_rate) / 100
                    
                    # Update sale item
                    item.vat_rate = item.product.vat_rate
                    item.vat_amount = item_vat
                    item.price_without_vat = item_subtotal
                    item.total_price = item_subtotal + item_vat
                    item.save()
                    
                    subtotal += item_subtotal
                    total_vat += item_vat
                
                # Update sale
                sale.subtotal = subtotal
                sale.total_vat = total_vat
                sale.total_amount = subtotal + total_vat
                sale.save()
            
            sales_updated += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Updated {sales_updated} sales with VAT calculations')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN COMPLETED - No changes were made')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('VAT data update completed successfully!')
            )
