from pathlib import Path

from flask import Blueprint, Response, jsonify

from ..utils import permission_required

help_bp = Blueprint('help', __name__)


@help_bp.route('/guia-importacion-csv', methods=['GET'])
@permission_required('dashboard:ver')
def guia_importacion_csv():
    """Devuelve la guía HTML de importación CSV para la sección Ayuda."""
    candidates = [
        Path('/docs/guia_importacion_csv.html'),
        Path(__file__).resolve().parents[3] / 'docs' / 'guia_importacion_csv.html',
        Path(__file__).resolve().parents[2] / 'docs' / 'guia_importacion_csv.html',
    ]
    guia_path = next((path for path in candidates if path.exists()), None)

    if not guia_path:
        return jsonify({'error': 'Guía no encontrada'}), 404

    html = guia_path.read_text(encoding='utf-8')
    return Response(html, mimetype='text/html; charset=utf-8')
