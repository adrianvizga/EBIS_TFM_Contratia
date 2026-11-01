
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


RiskLevel = Literal["none", "low", "medium", "high", "critical"]
Severity = Literal["low", "medium", "high"]
SupportedContractType = Literal[
    "arrendamiento_vivienda", "arrendamiento_local", "prestacion_servicios", "unsupported"
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContractMetadata(StrictModel):
    detected_language: str | None
    contract_type: SupportedContractType
    subtype: str | None
    jurisdiction: str | None
    governing_law: str | None
    page_count_estimate: int | None


class InitialOverview(StrictModel):
    overall_risk: Literal["none"]
    summary: str = Field(min_length=1)
    tokens_used_hint: int | None


class ExtractedClause(StrictModel):
    clause_id: str = Field(min_length=1, max_length=100)
    clause_number: str | None
    title: str | None
    original_text: str = Field(min_length=1)
    plain_explanation: str | None
    legal_advice: None
    risk_level: Literal["none"]
    has_issue: Literal[False]
    category: Literal[
        "objeto", "duracion", "renta", "fianza", "garantias",
        "obligaciones_arrendatario", "obligaciones_arrendador", "gastos",
        "resolucion", "jurisdiccion", "otra",
    ]
    subcategories: list[str]
    order_index: int = Field(ge=0)


class InitialContractAnalysis(StrictModel):
    contract_metadata: ContractMetadata
    analysis_overview: InitialOverview
    clauses: list[ExtractedClause]

    @model_validator(mode="after")
    def validate_clause_order(self):
        indexes = [clause.order_index for clause in self.clauses]
        if len(indexes) != len(set(indexes)):
            raise ValueError("Clause order_index values must be unique")
        return self


class ClauseFinding(StrictModel):
    risk_level: RiskLevel
    has_issue: bool
    plain_explanation: str = Field(min_length=1)
    legal_advice: str | None


class RiskToCreate(StrictModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    severity: Severity
    category: str = Field(min_length=1, max_length=100)


class AspectToCreate(StrictModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    type: Literal["positive", "negative"]


class ClauseLegalAnalysis(StrictModel):
    clause_result: ClauseFinding
    risks_to_create: list[RiskToCreate]
    aspects_to_create: list[AspectToCreate]

    @model_validator(mode="after")
    def validate_issue_consistency(self):
        if self.risks_to_create and not self.clause_result.has_issue:
            raise ValueError("A clause with risks must set has_issue=true")
        if self.clause_result.risk_level in {"medium", "high", "critical"} and not self.clause_result.has_issue:
            raise ValueError("Relevant risk levels must set has_issue=true")
        return self


class MissingElementToCreate(StrictModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    suggested_clause: str | None
    severity: Severity
    category: str = Field(min_length=1, max_length=100)


class AggregatedAnalysis(StrictModel):
    overall_risk: RiskLevel
    summary: str = Field(min_length=1)
    missing_elements_to_create: list[MissingElementToCreate]


class ClauseRelationCandidate(StrictModel):
    type: Literal["dependency", "contradiction", "duplicity"]
    from_index: int = Field(ge=1)
    to_index: int = Field(ge=1)
    severity: Severity
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)


class ClauseRelationsAnalysis(StrictModel):
    relations: list[ClauseRelationCandidate]
