"""
Django settings for server project.
"""
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Toggle to enable production-level security even when DEBUG is False.
USE_PROD_SECURITY = os.getenv('USE_PROD_SECURITY', 'False').lower() == 'true'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY') 

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,sisai.azurewebsites.net').split(',')

# CSRF trusted origins (recommended for production behind proxies)
_raw_csrf = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://e2e-60-5.sscloudindia.net:8081')
if _raw_csrf:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _raw_csrf.split(',') if o.strip()]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'treeapi',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS settings
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = 'server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Production security settings
# Only enable production-level security when DEBUG is False AND
# USE_PROD_SECURITY is explicitly turned on via environment variable.
if not DEBUG and USE_PROD_SECURITY:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = 'Lax'
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_PROXY_SSL_HEADER = None
    USE_X_FORWARDED_HOST = False


# Database configuration
# DB_MODE controls which DB backend is used.
# - sqlite: force SQLite (recommended for local/offline development)
# - postgres: force PostgreSQL (DATABASE_URL preferred, otherwise DB_* vars)
# - auto: choose PostgreSQL if configured, otherwise SQLite
# Defaults:
# - DEBUG=True  -> sqlite
# - DEBUG=False -> auto
DB_MODE = os.getenv('DB_MODE', '').strip().lower()
if not DB_MODE:
    DB_MODE = 'sqlite' if DEBUG else 'auto'

def _sqlite_db():
    return {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

def _postgres_db_from_url():
    import dj_database_url
    db = {
        'default': dj_database_url.config(
            default=os.getenv('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    if 'OPTIONS' not in db['default']:
        db['default']['OPTIONS'] = {}
    db['default']['OPTIONS'].update({
        'sslmode': 'require',
        'connect_timeout': 10,
    })
    return db

def _postgres_db_from_vars():
    return {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv("DB_NAME"),
            'USER': os.getenv("DB_USER"),
            'PASSWORD': os.getenv("DB_PASSWORD"),
            'HOST': os.getenv("DB_HOST", "localhost"),
            'PORT': os.getenv("DB_PORT", "5432"),
            'OPTIONS': {
                'connect_timeout': 10,
                'sslmode': os.getenv("DB_SSLMODE", "prefer"),
            }
        }
    }

if DB_MODE == 'sqlite':
    DATABASES = _sqlite_db()
elif DB_MODE == 'postgres':
    if os.getenv('DATABASE_URL'):
        try:
            DATABASES = _postgres_db_from_url()
        except ImportError:
            DATABASES = _postgres_db_from_vars() if all([os.getenv('DB_NAME'), os.getenv('DB_USER'), os.getenv('DB_PASSWORD')]) else _sqlite_db()
    elif all([os.getenv('DB_NAME'), os.getenv('DB_USER'), os.getenv('DB_PASSWORD')]):
        DATABASES = _postgres_db_from_vars()
    else:
        DATABASES = _sqlite_db()
else:
    # auto
    if os.getenv('DATABASE_URL'):
        try:
            DATABASES = _postgres_db_from_url()
        except ImportError:
            DATABASES = _sqlite_db()
    elif all([os.getenv('DB_NAME'), os.getenv('DB_USER'), os.getenv('DB_PASSWORD')]):
        DATABASES = _postgres_db_from_vars()
    else:
        DATABASES = _sqlite_db()

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'treeapi': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

try:
    os.makedirs(BASE_DIR / 'logs', exist_ok=True)
    test_log = BASE_DIR / 'logs' / 'test.log'
    with open(test_log, 'w') as f:
        f.write('test')
    os.remove(test_log)

    LOGGING['handlers']['file'] = {
        'level': 'INFO',
        'class': 'logging.FileHandler',
        'filename': BASE_DIR / 'logs' / 'django.log',
        'formatter': 'verbose',
    }
    LOGGING['root']['handlers'].append('file')
    LOGGING['loggers']['django']['handlers'].append('file')
    LOGGING['loggers']['treeapi']['handlers'].append('file')

except (OSError, PermissionError):
    pass

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Excel / upload configuration
_raw_allowed = os.getenv("ALLOWED_EXCEL_DIRS", "")
ALLOWED_EXCEL_DIRS = [d.strip() for d in _raw_allowed.split(",") if d.strip()] if _raw_allowed else []

# Optional default excel path used when frontend calls endpoint without specifying path
EXCEL_DEFAULT_PATH = os.getenv("EXCEL_DEFAULT_PATH", None)

# Temporary upload directory
TMP_UPLOAD_DIR = os.path.join(BASE_DIR, "tmp_uploads")

try:
    os.makedirs(TMP_UPLOAD_DIR, exist_ok=True)
    test_file = os.path.join(TMP_UPLOAD_DIR, 'test.txt')
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
except (OSError, PermissionError):
    TMP_UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "django_sensor_uploads")
    os.makedirs(TMP_UPLOAD_DIR, exist_ok=True)

# Authentication settings
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/sensor-tree/'
LOGOUT_REDIRECT_URL = '/login/'
