
import re
import unicodedata
from typing import Optional

CONTRACT_COVERAGE = {
    "arrendamiento_vivienda": {
        "id": "arrendamiento_vivienda", "label": "Arrendamiento de vivienda",
        "enabled": True, "coverage_level": "full",
        "legal_sources": ["Ley de Arrendamientos Urbanos", "Código Civil"],
        "coverage_notice": "Análisis limitado a la LAU y al Código Civil disponibles en el corpus.",
    },
    "arrendamiento_local": {
        "id": "arrendamiento_local", "label": "Arrendamiento de local",
        "enabled": True, "coverage_level": "full",
        "legal_sources": ["Ley de Arrendamientos Urbanos", "Código Civil"],
        "coverage_notice": "Análisis limitado a la LAU y al Código Civil disponibles en el corpus.",
    },
    "prestacion_servicios": {
        "id": "prestacion_servicios", "label": "Prestación de servicios",
        "enabled": True, "coverage_level": "full_general",
        "legal_sources": [
            "Código Civil", "consumo", "condiciones generales", "morosidad B2B",
            "comercio electrónico", "protección de datos", "propiedad intelectual",
            "contratación mercantil", "autónomos y TRADE", "firma electrónica",
        ],
        "coverage_notice": "Cobertura general B2B/B2C. Excluye normativa sectorial, contratación pública y conflictos internacionales; no sustituye revisión profesional. La revisión jurídica humana final del corpus v2 está pendiente.",
    },
}

ALIASES = {
    "arrendamiento_vivienda": "arrendamiento_vivienda", "arrendamiento de vivienda": "arrendamiento_vivienda",
    "alquiler de vivienda": "arrendamiento_vivienda", "rental": "arrendamiento_vivienda",
    "arrendamiento": "arrendamiento_vivienda", "contrato de arrendamiento": "arrendamiento_vivienda",
    "arrendamiento_local": "arrendamiento_local", "arrendamiento de local": "arrendamiento_local",
    "alquiler de local": "arrendamiento_local", "commercial lease": "arrendamiento_local",
    "prestacion_servicios": "prestacion_servicios", "prestacion de servicios": "prestacion_servicios",
    "contrato de servicios": "prestacion_servicios", "services": "prestacion_servicios", "service contract": "prestacion_servicios",
}

def _key(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", text.replace("-", " ")).strip()

def normalize_contract_type(value: Optional[str]) -> Optional[str]:
    return ALIASES.get(_key(value or ""))

def get_contract_coverage(value: Optional[str]) -> Optional[dict]:
    canonical = normalize_contract_type(value)
    return CONTRACT_COVERAGE.get(canonical) if canonical else None

def require_supported_contract_type(value: Optional[str]) -> dict:
    coverage = get_contract_coverage(value)
    if not coverage:
        raise ValueError("Tipo de contrato no soportado por el corpus legal actual")
    return coverage

def public_contract_catalog() -> list[dict]:
    return list(CONTRACT_COVERAGE.values())
