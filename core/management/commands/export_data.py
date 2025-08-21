"""
Management command to export data to Excel/CSV files.
"""

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum, F
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Product, Sale, SaleItem, Batch, StockAdjustment


class Command(BaseCommand):
    help = 'Export data to Excel/CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            'data_type',
            type=str,
            choices=['products', 'sales', 'stock', 'batches', 'adjustments', 'all'],
            help='Type of data to export'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['csv', 'excel'],
            default='excel',
            help='Output format (default: excel)'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='exports',
            help='Output directory (default: exports)'
        )
        parser.add_argument(
            '--date-range',
            type=str,
            choices=['today', 'week', 'month', 'quarter', 'year', 'all'],
            default='all',
            help='Date range for sales data (default: all)'
        )
        parser.add_argument(
            '--include-inactive',
            action='store_true',
            help='Include inactive products in export'
        )

    def handle(self, *args, **options):
        data_type = options['data_type']
        output_format = options['format']
        output_dir = options['output_dir']
        date_range = options['date_range']
        include_inactive = options['include_inactive']

        try:
            # Create output directory
            import os
            os.makedirs(output_dir, exist_ok=True)

            if data_type == 'all':
                self.export_all_data(output_dir, output_format, date_range, include_inactive)
            else:
                # Export specific data type
                if data_type == 'products':
                    self.export_products(output_dir, output_format, include_inactive)
                elif data_type == 'sales':
                    self.export_sales(output_dir, output_format, date_range)
                elif data_type == 'stock':
                    self.export_stock(output_dir, output_format, include_inactive)
                elif data_type == 'batches':
                    self.export_batches(output_dir, output_format, include_inactive)
                elif data_type == 'adjustments':
                    self.export_adjustments(output_dir, output_format, date_range)

            self.stdout.write(
                self.style.SUCCESS(f'Data exported successfully to {output_dir}/')
            )

        except Exception as e:
            raise CommandError(f'Export failed: {str(e)}')

    def export_all_data(self, output_dir, output_format, date_range, include_inactive):
        """Export all data types to separate files."""
        self.stdout.write('Exporting all data types...')
        
        self.export_products(output_dir, output_format, include_inactive)
        self.export_sales(output_dir, output_format, date_range)
        self.export_stock(output_dir, output_format, include_inactive)
        self.export_batches(output_dir, output_format, include_inactive)
        self.export_adjustments(output_dir, output_format, date_range)

    def export_products(self, output_dir, output_format, include_inactive):
        """Export products data."""
        self.stdout.write('Exporting products...')
        
        # Get products
        if include_inactive:
            products = Product.objects.all()
        else:
            products = Product.objects.filter(is_active=True)

        # Prepare data
        data = []
        for product in products:
            data.append({
                'SKU': product.sku,
                'Name': product.name,
                'Category': product.category,
                'Unit': product.unit,
                'Cost Price': float(product.cost_price),
                'Selling Price': float(product.selling_price),
                'Reorder Level': product.reorder_level,
                'Current Stock': product.current_stock,
                'Stock Status': product.stock_status,
                'Gross Profit Margin (%)': round(product.gross_profit_margin, 2),
                'Description': product.description,
                'Active': product.is_active,
                'Created': product.created_at.strftime('%Y-%m-%d %H:%M'),
                'Updated': product.updated_at.strftime('%Y-%m-%d %H:%M')
            })

        # Create DataFrame and export
        df = pd.DataFrame(data)
        filename = f'{output_dir}/products_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.export_dataframe(df, filename, output_format)

    def export_sales(self, output_dir, output_format, date_range):
        """Export sales data."""
        self.stdout.write('Exporting sales...')
        
        # Get date filter
        start_date = self.get_start_date(date_range)
        
        # Get sales
        if start_date:
            sales = Sale.objects.filter(sale_date__date__gte=start_date)
        else:
            sales = Sale.objects.all()

        # Prepare data
        data = []
        for sale in sales:
            data.append({
                'Invoice Number': sale.invoice_number,
                'Seller Name': sale.seller_name,
                'Sale Type': sale.sale_type,
                'Total Amount': float(sale.total_amount),
                'Discount': float(sale.discount),
                'Tax Amount': float(sale.tax_amount),
                'Net Amount': float(sale.net_amount),
                'Sale Date': sale.sale_date.strftime('%Y-%m-%d %H:%M'),
                'Notes': sale.notes,
                'Items Count': sale.items.count()
            })

        # Create DataFrame and export
        df = pd.DataFrame(data)
        filename = f'{output_dir}/sales_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.export_dataframe(df, filename, output_format)

    def export_stock(self, output_dir, output_format, include_inactive):
        """Export stock data."""
        self.stdout.write('Exporting stock data...')
        
        # Get products with stock information
        if include_inactive:
            products = Product.objects.all()
        else:
            products = Product.objects.filter(is_active=True)

        # Prepare data
        data = []
        for product in products:
            # Get stock from batches
            batches = product.batches.filter(quantity__gt=0)
            total_stock = sum(batch.quantity for batch in batches)
            stock_value = sum(batch.quantity * batch.batch.cost_price for batch in batches)
            
            data.append({
                'SKU': product.sku,
                'Product Name': product.name,
                'Category': product.category,
                'Current Stock': total_stock,
                'Stock Value': round(stock_value, 2),
                'Reorder Level': product.reorder_level,
                'Stock Status': product.stock_status,
                'Unit': product.unit,
                'Cost Price': float(product.cost_price),
                'Selling Price': float(product.selling_price)
            })

        # Create DataFrame and export
        df = pd.DataFrame(data)
        filename = f'{output_dir}/stock_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.export_dataframe(df, filename, output_format)

    def export_batches(self, output_dir, output_format, include_inactive):
        """Export batch data."""
        self.stdout.write('Exporting batch data...')
        
        # Get batches
        if include_inactive:
            batches = Batch.objects.all()
        else:
            batches = Batch.objects.filter(product__is_active=True)

        # Prepare data
        data = []
        for batch in batches:
            data.append({
                'Product SKU': batch.product.sku,
                'Product Name': batch.product.name,
                'Batch Number': batch.batch_number,
                'Quantity': batch.quantity,
                'Expiry Date': batch.expiry_date.strftime('%Y-%m-%d'),
                'Days to Expiry': batch.days_to_expiry,
                'Expiry Status': batch.expiry_status,
                'Cost Price': float(batch.cost_price),
                'Supplier': batch.supplier,
                'Notes': batch.notes,
                'Created': batch.created_at.strftime('%Y-%m-%d %H:%M')
            })

        # Create DataFrame and export
        df = pd.DataFrame(data)
        filename = f'{output_dir}/batches_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.export_dataframe(df, filename, output_format)

    def export_adjustments(self, output_dir, output_format, date_range):
        """Export stock adjustments data."""
        self.stdout.write('Exporting stock adjustments...')
        
        # Get date filter
        start_date = self.get_start_date(date_range)
        
        # Get adjustments
        if start_date:
            adjustments = StockAdjustment.objects.filter(adjusted_at__date__gte=start_date)
        else:
            adjustments = StockAdjustment.objects.all()

        # Prepare data
        data = []
        for adjustment in adjustments:
            data.append({
                'Product SKU': adjustment.product.sku,
                'Product Name': adjustment.product.name,
                'Batch Number': adjustment.batch.batch_number,
                'Adjustment Type': adjustment.adjustment_type,
                'Quantity': adjustment.quantity,
                'Reason': adjustment.reason,
                'Adjusted By': adjustment.adjusted_by.username if adjustment.adjusted_by else 'System',
                'Adjusted At': adjustment.adjusted_at.strftime('%Y-%m-%d %H:%M')
            })

        # Create DataFrame and export
        df = pd.DataFrame(data)
        filename = f'{output_dir}/adjustments_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.export_dataframe(df, filename, output_format)

    def get_start_date(self, date_range):
        """Get start date based on date range option."""
        today = timezone.now().date()
        
        if date_range == 'today':
            return today
        elif date_range == 'week':
            return today - timedelta(days=7)
        elif date_range == 'month':
            return today - timedelta(days=30)
        elif date_range == 'quarter':
            return today - timedelta(days=90)
        elif date_range == 'year':
            return today - timedelta(days=365)
        else:  # all
            return None

    def export_dataframe(self, df, filename, output_format):
        """Export DataFrame to file."""
        if output_format == 'csv':
            filepath = f'{filename}.csv'
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
        else:  # excel
            filepath = f'{filename}.xlsx'
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Data']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

        self.stdout.write(f'  Exported to: {filepath}')
        return filepath
