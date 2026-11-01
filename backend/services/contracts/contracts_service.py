
import logging

logger = logging.getLogger(__name__)


def enqueue_contract_analysis(contract_id: int):
    from workers.tasks import analyze_contract
    
    logger.info("Encolando analisis de contrato: contract_id=%s", contract_id)
    
    task = analyze_contract.delay(contract_id)
    
    logger.info("Tarea de analisis encolada: task_id=%s", task.id)
    
    return task.id
