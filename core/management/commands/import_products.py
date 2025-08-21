"""
Management command to import products from Excel/CSV files.
"""

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from core.models import Product, Batch
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Import products from Excel/CSV file with batch information'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to Excel/CSV file')
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing products instead of skipping them'
        )
        parser.add_argument(
            '--create-batches',
            action='store_true',
            help='Create batch records for imported products'
        )
        parser.add_argument(
            '--default-expiry-days',
            type=int,
            default=365,
            help='Default expiry days for batches (default: 365)'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        update_existing = options['update_existing']
        create_batches = options['create_batches']
        default_expiry_days = options['default_expiry_days']

        try:
            # Read the file
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                raise CommandError('Unsupported file format. Please use .xlsx or .csv files.')

            # Validate required columns
            required_columns = ['Name', 'SKU', 'Category', 'Unit', 'Cost Price', 'Selling Price']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise CommandError(f'Missing required columns: {", ".join(missing_columns)}')

            # Clean and validate data
            df = self.clean_dataframe(df)
            
            # Import products
            imported_count = 0
            updated_count = 0
            skipped_count = 0
            errors = []

            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        # Check if product exists
                        product, created = Product.objects.get_or_create(
                            sku=row['SKU'],
                            defaults={
                                'name': row['Name'],
                                'category': row['Category'],
                                'unit': row['Unit'],
                                'cost_price': row['Cost Price'],
                                'selling_price': row['Selling Price'],
                                'reorder_level': row.get('Reorder Level', 10),
                                'description': row.get('Description', ''),
                                'is_active': True
                            }
                        )

                        if created:
                            imported_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'Created product: {product.name} ({product.sku})')
                            )
                        elif update_existing:
                            # Update existing product
                            product.name = row['Name']
                            product.category = row['Category']
                            product.unit = row['Unit']
                            product.cost_price = row['Cost Price']
                            product.selling_price = row['Selling Price']
                            product.reorder_level = row.get('Reorder Level', product.reorder_level)
                            product.description = row.get('Description', product.description)
                            product.save()
                            
                            updated_count += 1
                            self.stdout.write(
                                self.style.WARNING(f'Updated product: {product.name} ({product.sku})')
                            )
                        else:
                            skipped_count += 1
                            self.stdout.write(
                                self.style.WARNING(f'Skipped existing product: {row["Name"]} ({row["SKU"]})')
                            )

                        # Create batch if requested
                        if create_batches and (created or update_existing):
                            self.create_batch_for_product(product, row, default_expiry_days)

                    except Exception as e:
                        error_msg = f'Row {index + 2}: {str(e)}'
                        errors.append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))

            # Summary
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('IMPORT SUMMARY'))
            self.stdout.write('='*50)
            self.stdout.write(f'Total rows processed: {len(df)}')
            self.stdout.write(f'Products created: {imported_count}')
            self.stdout.write(f'Products updated: {updated_count}')
            self.stdout.write(f'Products skipped: {skipped_count}')
            
            if errors:
                self.stdout.write(f'Errors: {len(errors)}')
                self.stdout.write(self.style.ERROR('\nERRORS:'))
                for error in errors:
                    self.stdout.write(self.style.ERROR(f'  {error}'))

        except Exception as e:
            raise CommandError(f'Import failed: {str(e)}')

    def clean_dataframe(self, df):
        """Clean and validate the dataframe."""
        # Remove empty rows
        df = df.dropna(subset=['Name', 'SKU'])
        
        # Clean SKU (remove spaces, convert to uppercase)
        df['SKU'] = df['SKU'].astype(str).str.strip().str.upper()
        
        # Clean names
        df['Name'] = df['Name'].astype(str).str.strip()
        
        # Clean categories
        df['Category'] = df['Category'].astype(str).str.strip()
        
        # Convert numeric columns
        df['Cost Price'] = pd.to_numeric(df['Cost Price'], errors='coerce')
        df['Selling Price'] = pd.to_numeric(df['Selling Price'], errors='coerce')
        df['Reorder Level'] = pd.to_numeric(df.get('Reorder Level', 10), errors='coerce').fillna(10)
        
        # Validate prices
        df = df[df['Cost Price'] > 0]
        df = df[df['Selling Price'] > 0]
        
        # Remove duplicates based on SKU
        df = df.drop_duplicates(subset=['SKU'])
        
        return df

    def create_batch_for_product(self, product, row, default_expiry_days):
        """Create a batch record for the imported product."""
        try:
            # Generate batch number
            batch_number = f"BATCH_{product.sku}_{datetime.now().strftime('%Y%m%d')}"
            
            # Calculate expiry date
            expiry_date = datetime.now().date() + timedelta(days=default_expiry_days)
            
            # Create batch
            batch, created = Batch.objects.get_or_create(
                product=product,
                batch_number=batch_number,
                defaults={
                    'quantity': row.get('Initial Stock', 0),
                    'expiry_date': expiry_date,
                    'cost_price': row['Cost Price'],
                    'supplier': row.get('Supplier', ''),
                    'notes': f'Imported from file on {datetime.now().strftime("%Y-%m-%d")}'
                }
            )
            
            if created:
                self.stdout.write(f'  Created batch: {batch_number}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Failed to create batch: {str(e)}'))
