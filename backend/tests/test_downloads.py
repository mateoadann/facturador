from app.models import DownloadArtifact


class TestDownloads:
    def test_download_zip_by_task(self, client, auth_headers, tenant, db):
        artifact = DownloadArtifact(
            tenant_id=tenant.id,
            task_id='task-zip-download-1',
            filename='comprobantes-lote-test.zip',
            mime_type='application/zip',
            file_data=b'ZIPDATA',
        )
        db.session.add(artifact)
        db.session.commit()

        response = client.get('/api/downloads/task-zip-download-1', headers=auth_headers)
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/zip'
        assert 'comprobantes-lote-test.zip' in response.headers['Content-Disposition']
        assert response.data == b'ZIPDATA'

    def test_download_zip_not_found(self, client, auth_headers):
        response = client.get('/api/downloads/task-missing', headers=auth_headers)
        assert response.status_code == 404
