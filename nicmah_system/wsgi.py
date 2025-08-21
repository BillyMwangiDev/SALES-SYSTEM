"""
WSGI config for nicmah_system project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nicmah_system.settings')

application = get_wsgi_application()
