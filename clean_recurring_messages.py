"""
Script para limpar as mensagens recorrentes de teste.
"""
import asyncio
import logging
from datetime import datetime

from src.utils.mongodb_instance import initialize_mongodb, mongodb_client

# Configuração de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def clean_recurring_messages():
    """Limpa as mensagens recorrentes de teste."""
    try:
        # Inicializa a conexão com o MongoDB
        logger.info("Conectando ao MongoDB...")
        await initialize_mongodb()
        logger.info("Conexão com o MongoDB estabelecida com sucesso.")
        
        # Limpa mensagens recorrentes de teste
        logger.info("Limpando mensagens recorrentes de teste...")
        if mongodb_client.db is not None:
            # Desativa todas as mensagens recorrentes (exclusão lógica)
            result = await mongodb_client.db.recurring_messages.update_many(
                {"chat_id": 123456789},  # ID do chat de teste
                {"$set": {"active": False}}
            )
            
            logger.info(f"Mensagens recorrentes desativadas: {result.modified_count}")
            
            # Opcional: excluir fisicamente as mensagens de teste
            # result = await mongodb_client.db.recurring_messages.delete_many({"chat_id": 123456789})
            # logger.info(f"Mensagens recorrentes excluídas: {result.deleted_count}")
        
        logger.info("Limpeza concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante a limpeza: {e}")

if __name__ == "__main__":
    asyncio.run(clean_recurring_messages()) 