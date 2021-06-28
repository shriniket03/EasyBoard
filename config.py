"""Flask configuration."""
from os import environ

class Config:
    """Base config."""
    DEBUG = False


class ProdConfig(Config):
    FLASK_ENV = 'production'
    TESTING = False
    GOOGLE_API_KEY = environ.get('GOOGLE_API_KEY')


class DevConfig(Config):
    FLASK_ENV = 'development'
    TESTING = True
    GOOGLE_API_KEY = 'xxx'
