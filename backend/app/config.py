import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://facturador:password@localhost:5432/facturador')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Celery
    CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')

    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173')

    # Encryption
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', '32-caracteres-exactos-para-fern')

    # ARCA
    ARCA_AMBIENTE = os.environ.get('ARCA_AMBIENTE', 'testing')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
