"""
Script para testar o gerenciador de mensagens recorrentes.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from bson.objectid import ObjectId

from src.utils.mongodb_instance import initialize_mongodb, mongodb_client
from src.utils.recurring_messages_manager import RecurringMessagesManager

# Configuração de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MockApplication:
    """Mock para a aplicação do Telegram."""
    
    def __init__(self):
        """Inicializa o mock."""
        self.bot = MockBot()

class MockBot:
    """Mock para o bot do Telegram."""
    
    async def send_message(self, chat_id, text, parse_mode=None):
        """Mock para o método send_message."""
        logger.info(f"Enviando mensagem para o chat {chat_id}: {text}")
        return True

async def test_recurring_messages():
    """Testa o gerenciador de mensagens recorrentes."""
    try:
        # Inicializa a conexão com o MongoDB
        logger.info("Conectando ao MongoDB...")
        await initialize_mongodb()
        logger.info("Conexão com o MongoDB estabelecida com sucesso.")
        
        # Cria uma instância do gerenciador de mensagens recorrentes
        app = MockApplication()
        manager = RecurringMessagesManager(app)
        
        # Limpa mensagens recorrentes existentes
        logger.info("Limpando mensagens recorrentes existentes...")
        if mongodb_client.db is not None:
            await mongodb_client.db.recurring_messages.delete_many({})
        
        # Adiciona uma mensagem recorrente de teste
        chat_id = 123456789
        message = "Esta é uma mensagem recorrente de teste"
        interval_hours = 0.01  # 36 segundos para teste
        added_by = 987654321
        added_by_name = "Usuário de Teste"
        
        logger.info("Adicionando mensagem recorrente de teste...")
        message_id = await mongodb_client.add_recurring_message(
            chat_id, message, interval_hours, added_by, added_by_name
        )
        
        if not message_id:
            logger.error("Falha ao adicionar mensagem recorrente")
            return
        
        logger.info(f"Mensagem recorrente adicionada com ID: {message_id}")
        
        # Verifica se a mensagem foi adicionada corretamente
        message_data = await mongodb_client.get_recurring_message(message_id)
        logger.info(f"Dados da mensagem: {message_data}")
        
        # Inicia o gerenciador
        logger.info("Iniciando o gerenciador de mensagens recorrentes...")
        await manager.start()
        
        # Aguarda para ver se a mensagem é enviada
        logger.info("Aguardando o envio da mensagem (60 segundos)...")
        await asyncio.sleep(60)
        
        # Verifica se a mensagem foi enviada (verificando o last_sent_at)
        message_data = await mongodb_client.get_recurring_message(message_id)
        if message_data and message_data.get("last_sent_at"):
            logger.info(f"Mensagem enviada em: {message_data['last_sent_at']}")
        else:
            logger.warning("A mensagem não foi enviada ou o timestamp não foi atualizado")
        
        # Testa a desativação da mensagem
        logger.info("Desativando a mensagem recorrente...")
        result = await mongodb_client.delete_recurring_message(message_id)
        logger.info(f"Resultado da desativação: {result}")
        
        # Verifica se a mensagem foi desativada
        message_data = await mongodb_client.get_recurring_message(message_id)
        logger.info(f"Estado da mensagem após desativação: {message_data}")
        
        # Para o gerenciador
        logger.info("Parando o gerenciador de mensagens recorrentes...")
        await manager.stop()
        
        logger.info("Teste concluído com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante o teste: {e}")
    finally:
        # Limpa as mensagens de teste
        if mongodb_client.db is not None:
            await mongodb_client.db.recurring_messages.delete_many({})

if __name__ == "__main__":
    asyncio.run(test_recurring_messages()) 