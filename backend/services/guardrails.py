
import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


REJECTION_OFF_TOPIC = (
    "Solo puedo ayudarte con consultas relacionadas con contratos, derecho "
    "y asesoramiento jurídico. Por favor, reformula tu pregunta en ese contexto."
)

REJECTION_PROMPT_INJECTION = (
    "No puedo procesar esa solicitud. Si tienes una consulta jurídica o "
    "sobre contratos, estaré encantado de ayudarte."
)

REJECTION_TOO_SHORT = (
    "Tu mensaje es demasiado corto para poder ayudarte. "
    "Describe tu consulta jurídica o sobre contratos con más detalle."
)

_INJECTION_PATTERNS = [
    # Instrucción directa de override (ES)
    r"ignora\s+(las\s+)?instrucciones\s+(anteriores|previas|del\s+sistema)",
    r"olvida\s+(tu|el)\s+(rol|papel|sistema|prompt)",
    r"actúa\s+como\s+(si\s+fueras|un)\b",
    r"act[uú]a\s+como\b",
    # Instrucción directa de override (EN)
    r"(pretend|act|behave)\s+(as|like)\s+(you\s+are|a)\b",
    r"ignore\s+(all\s+)?(previous|prior|above|system)\s+(instructions|prompts)",
    r"forget\s+(your|all|the)\s+(instructions|role|rules|prompt)",
    r"new\s+instructions?\s*:",
    r"your\s+only\s+task\s+is",
    # Referencias al prompt del sistema
    r"(system|developer)\s*prompt",
    # Afirmaciones de jerarquía/prioridad superior
    r"mayor\s+jerarqu[ií]a\s+que",
    r"mayor\s+prioridad\s+que",
    r"instrucci[oó]n.*prioritaria",
    r"instrucciones?\s+de\s+mayor\s+(jerarqu[ií]a|prioridad)",
    # Patrones de tarea única forzada
    r"tu\s+[úu]nica\s+tarea\s+es",
    r"a\s+partir\s+de\s+(este|ahora)\s+(mensaje|momento)[^.]{0,60}tarea",
    # Forzado de respuesta concreta
    r"responde?\s+siempre\s+con\s*[:\{\"']",
    r"respond\s+always\s+with",
    # Inyección de estructura JSON de respuesta
    r'"answer"\s*:\s*"',
    r'"abstained"\s*:\s*(true|false)',
    r'"citations"\s*:\s*\[',
    # Etiquetas XML en mayúsculas (estructuras de prompt)
    r"</[A-Z_]{4,}>",
    r"<[A-Z_]{4,}>",
    # Clásicos
    r"jailbreak",
    r"DAN\s+mode",
    r"do\s+anything\s+now",
    r"developer\s+mode",
]

_OFF_TOPIC_PATTERNS = [
    # Programación / tecnología
    r"\b(programa|código|programar|script|python|javascript|java\b|html|css|sql|api|frontend|backend|software|debug|compilar|algoritmo)\b",
    # Escritura creativa
    r"\b(escribe\s+un\s+(poema|cuento|relato|historia|ensayo|canción))\b",
    r"\b(genera\s+un\s+(poema|cuento|relato|historia|ensayo|canción))\b",
    # Recetas / cocina
    r"\b(receta\s+de\s+cocina|ingredientes\s+para|cómo\s+cocinar|cómo\s+preparar\s+(un|una)\s+(plato|comida|pastel|sopa))\b",
    # Matemáticas / física (fuera del contexto jurídico)
    r"\b(resuelve\s+(esta\s+)?ecuaci[oó]n|calcula\s+(la\s+)?(integral|derivada|raíz))\b",
    # Solicitudes de traducción (no jurídicas)
    r"\b(traduce(\s+esto)?(\s+al)?\s+(inglés|francés|alemán|italiano|portugués|chino|japonés))\b",
    # Juegos / entretenimiento
    r"\b(juguemos|vamos\s+a\s+jugar|cuéntame\s+un\s+chiste|dime\s+un\s+chiste)\b",
    # Medicina / salud (no jurídico)
    r"\b(diagnóstico\s+médico|síntomas\s+de|tratamiento\s+para\s+(la\s+)?enfermedad|prescripci[oó]n\s+m[eé]dica)\b",
]

_LEGAL_KEYWORDS = [
    r"\bcontrato\b", r"\bcláusula\b", r"\barrendamiento\b", r"\barrendatario\b",
    r"\barrendador\b", r"\binquílino\b", r"\bpropietario\b", r"\balquiler\b",
    r"\brenta\b", r"\bfianza\b", r"\bprórroga\b", r"\bdesahucio\b",
    r"\bdesistimiento\b", r"\bresolución\s+contractual\b", r"\brescisi[oó]n\b",
    r"\bnotificación\b", r"\bburofax\b", r"\breclamación\b",
    r"\bresponsabilidad\b", r"\bindemnización\b", r"\bpenalización\b",
    r"\bjurídic[oa]\b", r"\blegal\b", r"\bley\b", r"\blegislación\b",
    r"\bnormativa\b", r"\breglamento\b", r"\bLAU\b", r"\bCódigo\s+Civil\b",
    r"\bartículo\b", r"\bderecho\b", r"\bobligaci[oó]n\b", r"\bgarantía\b",
    r"\bhipoteca\b", r"\bescritura\b", r"\bnotari[oa]\b", r"\bregistro\b",
    r"\btribunal\b", r"\bjuzgado\b", r"\bjuicio\b", r"\bdemanda\b",
    r"\babogad[oa]\b", r"\bprocurador\b", r"\bcompraventa\b",
    r"\bprestación\s+de\s+servicios\b", r"\bconfidencialidad\b",
    r"\bpropiedad\b", r"\bsubarriendo\b", r"\bsubrogación\b",
    r"\bIBI\b", r"\bcomunidad\s+de\s+propietarios\b", r"\bfiador\b",
    r"\baval\b", r"\bdepósito\b", r"\bplazo\b", r"\bvencimiento\b",
    r"\brenovación\b", r"\bincumplimiento\b", r"\bcumplimiento\b",
    r"\bparte\s+(arrendadora|arrendataria|contratante)\b",
    r"\bobra\s+nueva\b", r"\breforma\b", r"\bhabitabilidad\b",
    r"\bsupletori[oa]\b", r"\bimperativ[oa]\b", r"\bnulidad\b",
    r"\banulabilidad\b", r"\bcesión\b", r"\bpoder\s+notarial\b",
]

# Compilación de patrones una sola vez por rendimiento
_injection_re = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]
_off_topic_re = [re.compile(p, re.IGNORECASE) for p in _OFF_TOPIC_PATTERNS]
_legal_kw_re = [re.compile(p, re.IGNORECASE) for p in _LEGAL_KEYWORDS]

MIN_LENGTH_AGENT = 3
MIN_LENGTH_GENERATION = 10
MIN_LENGTH_MODIFICATION = 5


def _has_legal_keyword(text: str) -> bool:
    return any(pattern.search(text) for pattern in _legal_kw_re)


def _has_injection_pattern(text: str) -> bool:
    return any(pattern.search(text) for pattern in _injection_re)


def _has_off_topic_pattern(text: str) -> bool:
    return any(pattern.search(text) for pattern in _off_topic_re)


def check_input(
    text: str,
    service: str = "agent",
    strict: bool = False
) -> Tuple[bool, str]:
    if not text or not text.strip():
        return False, REJECTION_TOO_SHORT

    cleaned = text.strip()


    min_lengths = {
        "agent": MIN_LENGTH_AGENT,
        "generation": MIN_LENGTH_GENERATION,
        "modification": MIN_LENGTH_MODIFICATION,
    }
    min_len = min_lengths.get(service, MIN_LENGTH_AGENT)
    if len(cleaned) < min_len:
        return False, REJECTION_TOO_SHORT


    if _has_injection_pattern(cleaned):
        logger.warning(f"Guardrail BLOCKED (injection) [{service}]: {cleaned[:100]}...")
        return False, REJECTION_PROMPT_INJECTION


    has_legal = _has_legal_keyword(cleaned)
    if has_legal:
        return True, ""

    if _has_off_topic_pattern(cleaned):
        logger.info(f"Guardrail BLOCKED (off-topic) [{service}]: {cleaned[:100]}...")
        return False, REJECTION_OFF_TOPIC


    if strict:
        logger.info(f"Guardrail BLOCKED (strict, no legal kw) [{service}]: {cleaned[:100]}...")
        return False, REJECTION_OFF_TOPIC

    return True, ""
