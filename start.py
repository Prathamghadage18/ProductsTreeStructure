"""Start script for production deployment using Gunicorn."""
import os
import subprocess

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')

port = os.environ.get('PORT', '8000')

# Use gunicorn with proper Django WSGI application
subprocess.run([
    'gunicorn', 
    '--bind', f'0.0.0.0:{port}',
    '--config', 'gunicorn.conf.py',
    'server.wsgi:application'
])
