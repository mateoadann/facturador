class TestHelpGuide:
    def test_guia_importacion_csv_devuelve_html(self, client, auth_headers):
        response = client.get('/api/help/guia-importacion-csv', headers=auth_headers)

        assert response.status_code == 200
        assert response.mimetype == 'text/html'
        body = response.get_data(as_text=True)
        assert '<!doctype html>' in body.lower()
        assert 'Guía simple para importar facturas por CSV' in body

    def test_guia_importacion_csv_permite_viewer(self, client, viewer_headers):
        response = client.get('/api/help/guia-importacion-csv', headers=viewer_headers)
        assert response.status_code == 200

    def test_guia_importacion_csv_requiere_auth(self, client):
        response = client.get('/api/help/guia-importacion-csv')
        assert response.status_code == 401
