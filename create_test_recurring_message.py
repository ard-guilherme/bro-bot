"""
Script para criar uma mensagem recorrente de teste.
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

async def create_test_recurring_message():
    """Cria uma mensagem recorrente de teste."""
    try:
        # Inicializa a conexão com o MongoDB
        logger.info("Conectando ao MongoDB...")
        await initialize_mongodb()
        logger.info("Conexão com o MongoDB estabelecida com sucesso.")
        
        # Cria uma mensagem recorrente de teste
        logger.info("Criando mensagem recorrente de teste...")
        if mongodb_client.db is not None:
            # Dados da mensagem
            chat_id = -1002288213607  # ID do chat de teste
            message = "Esta é uma mensagem recorrente de teste criada pelo script"
            interval_hours = 1.0  # 1 hora
            added_by = 1277961359  # ID do usuário de teste
            added_by_name = "Script de Teste"
            
            # Adiciona a mensagem
            message_id = await mongodb_client.add_recurring_message(
                chat_id, message, interval_hours, added_by, added_by_name
            )
            
            if message_id:
                logger.info(f"Mensagem recorrente criada com sucesso! ID: {message_id}")
                
                # Verifica se a mensagem foi adicionada
                message_data = await mongodb_client.get_recurring_message(message_id)
                if message_data:
                    logger.info(f"Mensagem verificada: {message_data}")
                else:
                    logger.warning("Não foi possível verificar a mensagem criada.")
            else:
                logger.error("Erro ao criar a mensagem recorrente.")
        
        logger.info("Operação concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante a criação da mensagem: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_test_recurring_message()) 