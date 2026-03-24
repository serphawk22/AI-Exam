"""
WSGI config for futurproctor project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from pathlib import Path
from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

# Load env from current directory (where settings.py and wsgi.py reside)
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futurproctor.settings')

application = get_wsgi_application()
