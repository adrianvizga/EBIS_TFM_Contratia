from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Literal


PartyRelation = Literal["b2b", "b2c", "unknown"]
ContractChannel = Literal["in_person", "distance", "electronic", "unknown"]
TriState = Literal["yes", "no", "unknown"]
ProviderKind = Literal["company", "self_employed", "unknown"]


@dataclass(frozen=True)
class ContractContext:
    party_relation: PartyRelation = "unknown"
    channel: ContractChannel = "unknown"
    personal_data: TriState = "unknown"
    intellectual_property: TriState = "unknown"
    provider_kind: ProviderKind = "unknown"
    regulated_sector: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()


def classify_contract_context(text: str, contract_type: str = "") -> ContractContext:
    value = _plain(text)
    consumer = bool(re.search(r"\b(consumidor|usuario final|particular)\b", value))
    business = bool(re.search(r"\b(sociedad|empresa|mercantil|profesional|autonom[oa])\b", value))
    relation: PartyRelation = "b2c" if consumer else ("b2b" if business else "unknown")
    channel: ContractChannel = "electronic" if re.search(r"\b(online|electronico|plataforma|web|email)\b", value) else ("distance" if "a distancia" in value else "unknown")
    personal_data: TriState = "yes" if re.search(r"\b(datos personales|rgpd|encargado del tratamiento|subencargado)\b", value) else "unknown"
    intellectual_property: TriState = "yes" if re.search(r"\b(propiedad intelectual|derechos de autor|licencia|software|codigo fuente|entregables)\b", value) else "unknown"
    provider_kind: ProviderKind = "self_employed" if re.search(r"\b(autonom[oa]|trade)\b", value) else ("company" if re.search(r"\b(sociedad|empresa)\b", value) else "unknown")
    sectors = {
        "banking": r"\b(banco|credito|financier[oa]s?)\b", "insurance": r"\b(seguro|aseguradora)\b",
        "health": r"\b(sanitario|medico|clinica)\b", "telecom": r"\b(telecomunicaciones|telefonia)\b",
        "transport": r"\b(transporte|transportista)\b", "tourism": r"\b(turismo|hotel|viaje combinado)\b",
        "energy": r"\b(energia|electricidad|gas)\b", "education": r"\b(educacion|academia|universidad)\b",
        "construction": r"\b(construccion|obra de edificacion)\b", "public_contracting": r"\b(contratacion publica|administracion publica)\b",
    }
    sector = next((name for name, pattern in sectors.items() if re.search(pattern, value)), None)
    return ContractContext(relation, channel, personal_data, intellectual_property, provider_kind, sector)


def coerce_contract_context(value: ContractContext | dict | None, text: str = "", contract_type: str = "") -> ContractContext:
    if isinstance(value, ContractContext):
        return value
    if isinstance(value, dict):
        allowed = ContractContext.__dataclass_fields__.keys()
        return ContractContext(**{key: item for key, item in value.items() if key in allowed})
    return classify_contract_context(text, contract_type)
