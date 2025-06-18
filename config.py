import os

basedir = os.path.abspath(os.path.dirname(__file__))

# Базовые настройки
SECRET_KEY = 'your-secret-key-here'
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'offenses.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False