"""
Django settings for applymatic project.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================================
# Core Settings
# ==========================================
# Grabs the exact Railway variable names
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-secret-key-for-local-dev-only")

DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", ".railway.app,localhost,127.0.0.1").split(",")

# Trust Railway's domains for form submissions
CSRF_TRUSTED_ORIGINS = ['https://*.up.railway.app', 'https://*.railway.app', 'https://*.onrender.com']

# ==========================================
# Application definition
# ==========================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Custom Apps
    "apps.core",
    "apps.accounts",
    "apps.applications",
    "apps.companies",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware", # Must be directly under SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'applymatic.urls'

template_path = os.path.join(BASE_DIR, 'apps' ,'templates')
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [template_path],
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

WSGI_APPLICATION = 'applymatic.wsgi.application'

# ==========================================
# Database Setup
# ==========================================
# Uses Railway's DATABASE_URL if available, otherwise falls back to local SQLite
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        ssl_require=os.getenv("DATABASE_URL") is not None # Only require SSL if using Railway Postgres
    )
}

# ==========================================
# Password validation
# ==========================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==========================================
# Internationalization
# ==========================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ==========================================
# Static and Media Files
# ==========================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
# Changed this to safely fall back to a local folder if you don't have a /data/ volume mounted in Railway
MEDIA_ROOT = os.getenv("MEDIA_ROOT", BASE_DIR / "media")

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================================
# Authentication & OAuth Settings
# ==========================================
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = 'core:apply'
LOGOUT_REDIRECT_URL = 'core:landing'

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")



GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "1UF33UO2hyCBj76vvzEZrPUcyg9w3XOwl")

import os
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", 
    "path/to/your/local/drive-bot-key.json" # Change this if testing locally!
)