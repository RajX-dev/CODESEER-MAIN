import os

# App environment
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = APP_ENV == "development"

# Database
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "codeseer-postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "codeseer")
POSTGRES_USER = os.getenv("POSTGRES_USER", "codeseer")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "codeseer")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:"
    f"{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:5432/"
    f"{POSTGRES_DB}"
)

# Elasticsearch
ES_HOST = os.getenv("ES_HOST", "http://codeseer-es:9200")
