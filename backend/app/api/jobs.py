from flask import Blueprint, jsonify
from celery.result import AsyncResult
from ..extensions import celery
from ..utils import tenant_required

jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('/<task_id>/status', methods=['GET'])
@tenant_required
def get_job_status(task_id):
    """Obtener el estado de una tarea de Celery."""
    task = AsyncResult(task_id, app=celery)

    response = {
        'task_id': task_id,
        'status': task.status,
    }

    if task.status == 'PENDING':
        response['progress'] = {
            'current': 0,
            'total': 0,
            'percent': 0
        }
    elif task.status == 'PROGRESS':
        response['progress'] = task.info
    elif task.status == 'SUCCESS':
        response['result'] = task.result
        response['progress'] = {
            'current': task.result.get('processed', 0),
            'total': task.result.get('total', 0),
            'percent': 100
        }
    elif task.status == 'FAILURE':
        response['error'] = str(task.result)

    return jsonify(response), 200
