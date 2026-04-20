import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    YANDEX_API_KEY = os.environ.get('YANDEX_API_KEY') or 'a4de04aa-6650-4616-990e-5c9e25c6ec9e'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '..', 'db', 'locations.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False