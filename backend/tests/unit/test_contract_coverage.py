import pytest

from services.contract_coverage import (
    get_contract_coverage,
    normalize_contract_type,
    public_contract_catalog,
    require_supported_contract_type,
)


@pytest.mark.parametrize("raw, expected", [
    ("arrendamiento_vivienda", "arrendamiento_vivienda"),
    ("Contrato de Arrendamiento", "arrendamiento_vivienda"),
    ("Arrendamiento de local", "arrendamiento_local"),
    ("Contrato de Servicios", "prestacion_servicios"),
    ("service contract", "prestacion_servicios"),
])
def test_normalizes_canonical_and_historical_labels(raw, expected):
    assert normalize_contract_type(raw) == expected


@pytest.mark.parametrize("raw", ["compraventa", "contrato laboral", "confidencialidad", "otro", ""])
def test_rejects_contracts_without_coverage(raw):
    with pytest.raises(ValueError, match="no soportado"):
        require_supported_contract_type(raw)


def test_services_have_full_general_coverage_with_limits():
    coverage = get_contract_coverage("prestación de servicios")
    assert coverage["coverage_level"] == "full_general"
    assert "protección de datos" in coverage["legal_sources"]
    assert "sectorial" in coverage["coverage_notice"].lower()
    assert "pendiente" in coverage["coverage_notice"].lower()


def test_catalog_only_exposes_three_enabled_types():
    catalog = public_contract_catalog()
    assert {item["id"] for item in catalog} == {
        "arrendamiento_vivienda", "arrendamiento_local", "prestacion_servicios"
    }
    assert all(item["enabled"] for item in catalog)
