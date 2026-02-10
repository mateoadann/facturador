import pytest
from datetime import date
from arca_integration.builders import FacturaBuilder
from arca_integration.exceptions import ArcaValidationError


class TestFacturaBuilder:
    def _build_basic(self):
        """Helper to create a valid builder."""
        builder = FacturaBuilder()
        builder.set_comprobante(tipo=1, punto_venta=1, numero=100, concepto=1)
        builder.set_fechas(emision=date(2026, 1, 15))
        builder.set_receptor(doc_tipo=80, doc_nro='30-11111111-1')
        builder.set_importes(total=12100.00, neto=10000.00, iva=2100.00)
        return builder

    def test_build_success(self):
        builder = self._build_basic()
        result = builder.build()

        assert 'FeCAEReq' in result
        req = result['FeCAEReq']
        assert req['FeCabReq']['CantReg'] == 1
        assert req['FeCabReq']['PtoVta'] == 1
        assert req['FeCabReq']['CbteTipo'] == 1

        det = req['FeDetReq']['FECAEDetRequest'][0]
        assert det['DocNro'] == 30111111111
        assert det['ImpTotal'] == 12100.00
        assert det['ImpNeto'] == 10000.00
        assert det['ImpIVA'] == 2100.00
        assert det['CbteFch'] == '20260115'
        assert det['CbteDesde'] == 100
        assert det['CbteHasta'] == 100

    def test_build_with_iva(self):
        builder = self._build_basic()
        builder.add_iva(alicuota_id=5, base_imponible=10000, importe=2100)
        result = builder.build()

        det = result['FeCAEReq']['FeDetReq']['FECAEDetRequest'][0]
        assert 'Iva' in det
        assert det['Iva']['AlicIva'][0]['Id'] == 5
        assert det['Iva']['AlicIva'][0]['Importe'] == 2100

    def test_build_with_cbte_asociado(self):
        builder = self._build_basic()
        builder.set_comprobante(tipo=3, punto_venta=1, numero=50, concepto=1)
        builder.set_comprobante_asociado(tipo=1, punto_venta=1, numero=100)
        result = builder.build()

        det = result['FeCAEReq']['FeDetReq']['FECAEDetRequest'][0]
        assert 'CbtesAsoc' in det
        assert det['CbtesAsoc']['CbteAsoc'][0]['Tipo'] == 1
        assert det['CbtesAsoc']['CbteAsoc'][0]['Nro'] == 100

    def test_build_servicios_requires_dates(self):
        builder = FacturaBuilder()
        builder.set_comprobante(tipo=1, punto_venta=1, numero=100, concepto=2)  # Servicios
        builder.set_fechas(emision=date(2026, 1, 15))  # Missing desde/hasta/vto_pago
        builder.set_receptor(doc_tipo=80, doc_nro='30111111111')
        builder.set_importes(total=12100, neto=10000)

        with pytest.raises(ArcaValidationError, match='servicios'):
            builder.build()

    def test_build_servicios_with_dates(self):
        builder = FacturaBuilder()
        builder.set_comprobante(tipo=1, punto_venta=1, numero=100, concepto=2)
        builder.set_fechas(
            emision=date(2026, 1, 15),
            desde=date(2026, 1, 1),
            hasta=date(2026, 1, 31),
            vto_pago=date(2026, 2, 15)
        )
        builder.set_receptor(doc_tipo=80, doc_nro='30111111111')
        builder.set_importes(total=12100, neto=10000)

        result = builder.build()
        det = result['FeCAEReq']['FeDetReq']['FECAEDetRequest'][0]
        assert det['FchServDesde'] == '20260101'
        assert det['FchServHasta'] == '20260131'
        assert det['FchVtoPago'] == '20260215'

    def test_validate_missing_tipo_comprobante(self):
        builder = FacturaBuilder()
        builder.set_fechas(emision=date(2026, 1, 15))
        builder.set_receptor(doc_tipo=80, doc_nro='30111111111')
        builder.set_importes(total=12100, neto=10000)

        with pytest.raises(ArcaValidationError, match='Tipo de comprobante'):
            builder.build()

    def test_validate_missing_receptor(self):
        builder = FacturaBuilder()
        builder.set_comprobante(tipo=1, punto_venta=1, numero=100, concepto=1)
        builder.set_fechas(emision=date(2026, 1, 15))
        builder.set_importes(total=12100, neto=10000)

        with pytest.raises(ArcaValidationError, match='documento del receptor'):
            builder.build()

    def test_clean_receptor_cuit(self):
        builder = self._build_basic()
        builder.set_receptor(doc_tipo=80, doc_nro='30-11111111-1')
        result = builder.build()

        det = result['FeCAEReq']['FeDetReq']['FECAEDetRequest'][0]
        assert det['DocNro'] == 30111111111

    def test_moneda_default(self):
        builder = self._build_basic()
        result = builder.build()

        det = result['FeCAEReq']['FeDetReq']['FECAEDetRequest'][0]
        assert det['MonId'] == 'PES'
        assert det['MonCotiz'] == 1.0

    def test_moneda_custom(self):
        builder = self._build_basic()
        builder.set_moneda('DOL', cotizacion=1050.50)
        result = builder.build()

        det = result['FeCAEReq']['FeDetReq']['FECAEDetRequest'][0]
        assert det['MonId'] == 'DOL'
        assert det['MonCotiz'] == 1050.50

    def test_builder_chaining(self):
        """Verify fluent API works."""
        builder = FacturaBuilder()
        result = (
            builder
            .set_comprobante(tipo=1, punto_venta=1, numero=1, concepto=1)
            .set_fechas(emision=date(2026, 1, 1))
            .set_receptor(doc_tipo=80, doc_nro='30111111111')
            .set_importes(total=100, neto=82.64)
            .set_moneda('PES')
            .build()
        )
        assert result['FeCAEReq']['FeCabReq']['CbteTipo'] == 1
