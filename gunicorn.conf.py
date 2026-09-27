"""Gunicorn configuration file for production deployment."""
import os
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', min(multiprocessing.cpu_count() * 2 + 1, 4)))
worker_class = "sync"
worker_connections = 1000
timeout = 600  # Increased for Azure App Service
keepalive = 5

# Restart workers after this many requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = os.environ.get('LOG_LEVEL', 'info')
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'sensor_server'

# Server mechanics
preload_app = True
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# Application
wsgi_module = "server.wsgi:application"

# Environment specific settings
raw_env = ['DJANGO_SETTINGS_MODULE=server.settings']

