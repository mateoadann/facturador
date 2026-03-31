import uuid
from datetime import datetime

from ..extensions import db


class DownloadArtifact(db.Model):
    __tablename__ = 'download_artifact'

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('tenant.id'), nullable=False, index=True)
    task_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False, default='application/octet-stream')
    file_data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
