import io
import logging
import zipfile

from celery import shared_task

from ..extensions import db
from ..models import DownloadArtifact, Factura, Lote
from ..services.comprobante_filename import build_comprobante_pdf_filename

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generar_comprobantes_zip_lote(self, lote_id: str, tenant_id: str):
    lote = Lote.query.filter_by(id=lote_id, tenant_id=tenant_id).first()
    zip_filename = _build_zip_filename(lote)

    facturas = Factura.query.filter(
        Factura.tenant_id == tenant_id,
        Factura.lote_id == lote_id,
        Factura.estado == 'autorizado',
    ).order_by(Factura.created_at.asc()).all()

    total = len(facturas)
    if total == 0:
        return {
            'status': 'completed',
            'processed': 0,
            'total': 0,
            'filename': zip_filename,
            'download_ready': False,
        }

    from ..services.comprobante_pdf import html_to_pdf_bytes
    from ..services.comprobante_renderer import render_comprobante_html

    zip_buffer = io.BytesIO()
    used_names = set()
    processed = 0

    with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zip_file:
        for factura in facturas:
            html = render_comprobante_html(factura)
            pdf_bytes = html_to_pdf_bytes(html)
            filename = _unique_name(build_comprobante_pdf_filename(factura), used_names)
            zip_file.writestr(filename, pdf_bytes)

            processed += 1
            self.update_state(state='PROGRESS', meta={
                'current': processed,
                'total': total,
                'percent': int((processed / total) * 100),
            })

    zip_bytes = zip_buffer.getvalue()
    artifact = DownloadArtifact(
        tenant_id=tenant_id,
        task_id=self.request.id,
        filename=zip_filename,
        mime_type='application/zip',
        file_data=zip_bytes,
    )
    db.session.add(artifact)
    db.session.commit()

    logger.info('ZIP de comprobantes generado task_id=%s lote=%s total=%s', self.request.id, lote_id, total)

    return {
        'status': 'completed',
        'processed': processed,
        'total': total,
        'filename': zip_filename,
        'download_ready': True,
    }


def _build_zip_filename(lote) -> str:
    etiqueta = getattr(lote, 'etiqueta', '') or ''
    cleaned = ''.join(ch for ch in etiqueta.strip() if ch.isalnum() or ch in (' ', '-', '_'))
    cleaned = ' '.join(cleaned.split())
    if not cleaned:
        return 'comprobantes-lote.zip'
    return f'{cleaned}.zip'


def _unique_name(filename: str, used_names: set[str]) -> str:
    if filename not in used_names:
        used_names.add(filename)
        return filename

    base, dot, ext = filename.rpartition('.')
    if not dot:
        base = filename
        ext = ''

    idx = 1
    while True:
        candidate = f'{base}_{idx}'
        if ext:
            candidate = f'{candidate}.{ext}'
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        idx += 1
