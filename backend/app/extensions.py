from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from celery import Celery

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()

celery = Celery('tasks')


def init_celery(app):
    celery.conf.broker_url = app.config['CELERY_BROKER_URL']
    celery.conf.result_backend = app.config['CELERY_RESULT_BACKEND']
    celery.conf.broker_connection_retry_on_startup = True

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    celery.autodiscover_tasks(['app'])
    return celery
