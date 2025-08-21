"""
Management command to create sample data for testing the system.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from core.models import Product, Batch


class Command(BaseCommand):
    help = 'Create sample products and batches for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Sample products
        products_data = [
            {
                'name': 'Maize Seeds',
                'sku': 'MS001',
                'category': 'Seeds',
                'unit': 'kg',
                'cost_price': 150.00,
                'selling_price': 200.00,
                'reorder_level': 50,
                'description': 'High-quality maize seeds for planting'
            },
            {
                'name': 'Fertilizer NPK',
                'sku': 'FN001',
                'category': 'Fertilizers',
                'unit': 'kg',
                'cost_price': 80.00,
                'selling_price': 120.00,
                'reorder_level': 100,
                'description': 'Balanced NPK fertilizer for crops'
            },
            {
                'name': 'Pesticide Spray',
                'sku': 'PS001',
                'category': 'Pesticides',
                'unit': 'liters',
                'cost_price': 200.00,
                'selling_price': 280.00,
                'reorder_level': 20,
                'description': 'Effective pest control spray'
            },
            {
                'name': 'Garden Tools Set',
                'sku': 'GT001',
                'category': 'Tools',
                'unit': 'set',
                'cost_price': 500.00,
                'selling_price': 750.00,
                'reorder_level': 10,
                'description': 'Complete set of essential garden tools'
            },
            {
                'name': 'Irrigation Hose',
                'sku': 'IH001',
                'category': 'Irrigation',
                'unit': 'meters',
                'cost_price': 25.00,
                'selling_price': 35.00,
                'reorder_level': 200,
                'description': 'Durable irrigation hose for farming'
            }
        ]
        
        created_products = []
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                sku=product_data['sku'],
                defaults=product_data
            )
            if created:
                self.stdout.write(f'Created product: {product.name}')
            else:
                self.stdout.write(f'Product already exists: {product.name}')
            created_products.append(product)
        
        # Sample batches
        today = date.today()
        batch_data = [
            {
                'product': created_products[0],  # Maize Seeds
                'batch_number': 'MS001-B001',
                'quantity': 200,
                'cost_price': 150.00,
                'expiry_date': today + timedelta(days=365),
                'supplier': 'Seed Co Ltd',
                'notes': 'Fresh batch from main supplier'
            },
            {
                'product': created_products[1],  # Fertilizer NPK
                'batch_number': 'FN001-B001',
                'quantity': 500,
                'cost_price': 80.00,
                'expiry_date': today + timedelta(days=730),
                'supplier': 'Fertilizer Kenya Ltd',
                'notes': 'Premium quality NPK fertilizer'
            },
            {
                'product': created_products[2],  # Pesticide Spray
                'batch_number': 'PS001-B001',
                'quantity': 100,
                'cost_price': 200.00,
                'expiry_date': today + timedelta(days=548),
                'supplier': 'AgroChem Ltd',
                'notes': 'Environmentally friendly pesticide'
            },
            {
                'product': created_products[3],  # Garden Tools
                'batch_number': 'GT001-B001',
                'quantity': 25,
                'cost_price': 500.00,
                'expiry_date': today + timedelta(days=1825),  # 5 years
                'supplier': 'ToolMaster Ltd',
                'notes': 'Professional grade garden tools'
            },
            {
                'product': created_products[4],  # Irrigation Hose
                'batch_number': 'IH001-B001',
                'quantity': 1000,
                'cost_price': 25.00,
                'expiry_date': today + timedelta(days=1825),  # 5 years
                'supplier': 'Irrigation Solutions Ltd',
                'notes': 'Heavy-duty irrigation hose'
            }
        ]
        
        for batch_data_item in batch_data:
            batch, created = Batch.objects.get_or_create(
                batch_number=batch_data_item['batch_number'],
                defaults=batch_data_item
            )
            if created:
                self.stdout.write(f'Created batch: {batch.batch_number} for {batch.product.name}')
            else:
                self.stdout.write(f'Batch already exists: {batch.batch_number}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {len(created_products)} products with sample batches!'
            )
        )
        self.stdout.write('You can now test the sales entry system with these products.')
