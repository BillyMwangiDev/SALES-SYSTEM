"""
Automated backup functionality for the Nicmah System Management.
"""

import os
import shutil
import zipfile
from datetime import datetime, timedelta
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
from django.db import models
from .models import BackupLog


def daily_backup():
    """Create daily database backup with compression and logging."""
    start_time = timezone.now()
    
    try:
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, settings.BACKUP_DIR)
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'nicmah_backup_{timestamp}.json'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create database dump
        call_command('dumpdata', 
                    '--exclude', 'contenttypes',
                    '--exclude', 'sessions',
                    '--exclude', 'admin.logentry',
                    '--indent', '2',
                    '--output', backup_path)
        
        # Create compressed backup
        zip_filename = f'nicmah_backup_{timestamp}.zip'
        zip_path = os.path.join(backup_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(backup_path, os.path.basename(backup_path))
        
        # Remove uncompressed backup
        os.remove(backup_path)
        
        # Get file size
        file_size = os.path.getsize(zip_path)
        
        # Log successful backup
        BackupLog.objects.create(
            backup_type='daily',
            file_path=zip_path,
            file_size=file_size,
            status='completed',
            notes=f'Daily automated backup completed successfully. File: {zip_filename}'
        )
        
        # Clean up old backups
        cleanup_old_backups(backup_dir)
        
        return {
            'status': 'success',
            'file_path': zip_path,
            'file_size': file_size,
            'duration': (timezone.now() - start_time).total_seconds()
        }
        
    except Exception as e:
        # Log failed backup
        BackupLog.objects.create(
            backup_type='daily',
            file_path='',
            file_size=0,
            status='failed',
            notes=f'Daily backup failed: {str(e)}'
        )
        
        return {
            'status': 'error',
            'error': str(e),
            'duration': (timezone.now() - start_time).total_seconds()
        }


def weekly_backup():
    """Create weekly comprehensive backup including media files."""
    start_time = timezone.now()
    
    try:
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, settings.BACKUP_DIR)
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'nicmah_weekly_backup_{timestamp}.json'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create comprehensive database dump
        call_command('dumpdata', 
                    '--indent', '2',
                    '--output', backup_path)
        
        # Create compressed backup
        zip_filename = f'nicmah_weekly_backup_{timestamp}.zip'
        zip_path = os.path.join(backup_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add database dump
            zipf.write(backup_path, os.path.basename(backup_path))
            
            # Add media files if they exist
            media_dir = os.path.join(settings.BASE_DIR, settings.MEDIA_ROOT)
            if os.path.exists(media_dir):
                for root, dirs, files in os.walk(media_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, media_dir)
                        zipf.write(file_path, f'media/{arcname}')
        
        # Remove uncompressed backup
        os.remove(backup_path)
        
        # Get file size
        file_size = os.path.getsize(zip_path)
        
        # Log successful backup
        BackupLog.objects.create(
            backup_type='weekly',
            file_path=zip_path,
            file_size=file_size,
            status='completed',
            notes=f'Weekly comprehensive backup completed successfully. File: {zip_filename}'
        )
        
        return {
            'status': 'success',
            'file_path': zip_path,
            'file_size': file_size,
            'duration': (timezone.now() - start_time).total_seconds()
        }
        
    except Exception as e:
        # Log failed backup
        BackupLog.objects.create(
            backup_type='weekly',
            file_path='',
            file_size=0,
            status='failed',
            notes=f'Weekly backup failed: {str(e)}'
        )
        
        return {
            'status': 'error',
            'error': str(e),
            'duration': (timezone.now() - start_time).total_seconds()
        }


def cleanup_old_backups(backup_dir):
    """Remove old backup files based on retention policy."""
    try:
        retention_days = getattr(settings, 'BACKUP_RETENTION_DAYS', 30)
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        # Get all backup files
        backup_files = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.zip') and filename.startswith('nicmah_backup_'):
                file_path = os.path.join(backup_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                backup_files.append((file_path, file_time))
        
        # Remove old files
        removed_count = 0
        for file_path, file_time in backup_files:
            if file_time < cutoff_date:
                try:
                    os.remove(file_path)
                    removed_count += 1
                    
                    # Log removal
                    BackupLog.objects.create(
                        backup_type='cleanup',
                        file_path=file_path,
                        file_size=0,
                        status='completed',
                        notes=f'Old backup file removed during cleanup: {os.path.basename(file_path)}'
                    )
                except Exception as e:
                    BackupLog.objects.create(
                        backup_type='cleanup',
                        file_path=file_path,
                        file_size=0,
                        status='failed',
                        notes=f'Failed to remove old backup file: {str(e)}'
                    )
        
        return removed_count
        
    except Exception as e:
        BackupLog.objects.create(
            backup_type='cleanup',
            file_path='',
            file_size=0,
            status='failed',
            notes=f'Backup cleanup failed: {str(e)}'
        )
        return 0


def manual_backup(backup_type='manual', include_media=False):
    """Create manual backup on demand."""
    start_time = timezone.now()
    
    try:
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, settings.BACKUP_DIR)
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'nicmah_manual_backup_{timestamp}.json'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create database dump
        call_command('dumpdata', 
                    '--indent', '2',
                    '--output', backup_path)
        
        # Create compressed backup
        zip_filename = f'nicmah_manual_backup_{timestamp}.zip'
        zip_path = os.path.join(backup_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add database dump
            zipf.write(backup_path, os.path.basename(backup_path))
            
            # Add media files if requested
            if include_media:
                media_dir = os.path.join(settings.BASE_DIR, settings.MEDIA_ROOT)
                if os.path.exists(media_dir):
                    for root, dirs, files in os.walk(media_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, media_dir)
                            zipf.write(file_path, f'media/{arcname}')
        
        # Remove uncompressed backup
        os.remove(backup_path)
        
        # Get file size
        file_size = os.path.getsize(zip_path)
        
        # Log successful backup
        BackupLog.objects.create(
            backup_type=backup_type,
            file_path=zip_path,
            file_size=file_size,
            status='completed',
            notes=f'Manual backup completed successfully. File: {zip_filename}'
        )
        
        return {
            'status': 'success',
            'file_path': zip_path,
            'file_size': file_size,
            'duration': (timezone.now() - start_time).total_seconds()
        }
        
    except Exception as e:
        # Log failed backup
        BackupLog.objects.create(
            backup_type=backup_type,
            file_path='',
            file_size=0,
            status='failed',
            notes=f'Manual backup failed: {str(e)}'
        )
        
        return {
            'status': 'error',
            'error': str(e),
            'duration': (timezone.now() - start_time).total_seconds()
        }


def restore_backup(backup_file_path):
    """Restore database from backup file."""
    start_time = timezone.now()
    
    try:
        # Validate backup file
        if not os.path.exists(backup_file_path):
            raise FileNotFoundError(f"Backup file not found: {backup_file_path}")
        
        # Extract backup if it's compressed
        if backup_file_path.endswith('.zip'):
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(backup_file_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                # Find the JSON file
                json_files = [f for f in os.listdir(temp_dir) if f.endswith('.json')]
                if not json_files:
                    raise ValueError("No JSON backup file found in zip")
                
                json_path = os.path.join(temp_dir, json_files[0])
                
                # Restore from JSON
                call_command('loaddata', json_path)
        else:
            # Direct JSON restore
            call_command('loaddata', backup_file_path)
        
        # Log successful restore
        BackupLog.objects.create(
            backup_type='restore',
            file_path=backup_file_path,
            file_size=0,
            status='completed',
            notes=f'Database restored successfully from: {os.path.basename(backup_file_path)}'
        )
        
        return {
            'status': 'success',
            'duration': (timezone.now() - start_time).total_seconds()
        }
        
    except Exception as e:
        # Log failed restore
        BackupLog.objects.create(
            backup_type='restore',
            file_path=backup_file_path,
            file_size=0,
            status='failed',
            notes=f'Database restore failed: {str(e)}'
        )
        
        return {
            'status': 'error',
            'error': str(e),
            'duration': (timezone.now() - start_time).total_seconds()
        }


def get_backup_status():
    """Get current backup status and statistics."""
    try:
        total_backups = BackupLog.objects.count()
        successful_backups = BackupLog.objects.filter(status='completed').count()
        failed_backups = BackupLog.objects.filter(status='failed').count()
        
        # Get latest backup
        latest_backup = BackupLog.objects.filter(status='completed').order_by('-created_at').first()
        
        # Get backup sizes
        total_size = BackupLog.objects.filter(status='completed').aggregate(
            total_size=models.Sum('file_size')
        )['total_size'] or 0
        
        return {
            'total_backups': total_backups,
            'successful_backups': successful_backups,
            'failed_backups': failed_backups,
            'success_rate': (successful_backups / total_backups * 100) if total_backups > 0 else 0,
            'total_size': total_size,
            'latest_backup': latest_backup.created_at if latest_backup else None,
            'latest_backup_size': latest_backup.file_size if latest_backup else 0
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
