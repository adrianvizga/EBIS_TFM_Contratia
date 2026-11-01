from services.contract_context import ContractContext, classify_contract_context, coerce_contract_context


def test_classifies_b2c_electronic_privacy_and_ip():
    context = classify_contract_context("Contrato online entre la empresa y el consumidor con datos personales y licencia de software")
    assert context.party_relation == "b2c"
    assert context.channel == "electronic"
    assert context.personal_data == "yes"
    assert context.intellectual_property == "yes"


def test_classifies_b2b_self_employed_and_sector():
    context = classify_contract_context("Profesional autónomo que presta servicios financieros a una sociedad")
    assert context.party_relation == "b2b"
    assert context.provider_kind == "self_employed"
    assert context.regulated_sector == "banking"


def test_unknown_is_safe_default_and_dict_is_coerced():
    assert classify_contract_context("cláusula de duración") == ContractContext()
    assert coerce_contract_context({"party_relation": "b2b"}).party_relation == "b2b"
