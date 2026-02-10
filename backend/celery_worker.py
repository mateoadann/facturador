from app import create_app
from app.extensions import celery, init_celery
from app.tasks import procesar_lote  # noqa: F401

app = create_app()
init_celery(app)

if __name__ == '__main__':
    celery.start()
