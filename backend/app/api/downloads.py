from flask import Blueprint, g, jsonify, make_response

from ..models import DownloadArtifact
from ..utils import permission_required

downloads_bp = Blueprint('downloads', __name__)


@downloads_bp.route('/<task_id>', methods=['GET'])
@permission_required('facturas:comprobante')
def download_zip(task_id):
    artifact = DownloadArtifact.query.filter_by(
        task_id=task_id,
        tenant_id=g.tenant_id,
    ).first()

    if not artifact:
        return jsonify({'error': 'Archivo no encontrado para esta tarea'}), 404

    response = make_response(artifact.file_data)
    response.headers['Content-Type'] = artifact.mime_type or 'application/octet-stream'
    response.headers['Content-Disposition'] = f'attachment; filename="{artifact.filename}"'
    return response
