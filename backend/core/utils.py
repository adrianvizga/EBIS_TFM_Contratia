import zlib

# Modelos que solo aceptan la temperatura por defecto (1) y rechazan cualquier valor explícito.
_MODELS_WITHOUT_TEMPERATURE = ("nano", "o1", "o3", "o4")

def get_user_seed(user_id: str) -> int:
    if not user_id:
        return 42
    return zlib.crc32(str(user_id).encode('utf-8'))


def get_clause_seed(clause_text: str, contract_type: str = "") -> int:
    """Seed basado en el contenido de la cláusula para que el mismo texto produzca siempre el mismo resultado, independientemente del usuario."""
    key = f"{contract_type}:{(clause_text or '')[:500]}"
    return zlib.crc32(key.encode('utf-8'))


def temperature_kwargs(model: str, temperature: float) -> dict:
    """Return {"temperature": temperature} unless the model rejects that parameter."""
    model_lower = model.lower()
    if any(p in model_lower for p in _MODELS_WITHOUT_TEMPERATURE):
        return {}
    return {"temperature": temperature}
