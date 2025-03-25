"""
Script para verificar as mensagens recorrentes.
"""
import asyncio
import logging
from datetime import datetime
from bson import ObjectId

from src.utils.mongodb_instance import initialize_mongodb, mongodb_client

# Configuração de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def check_recurring_messages():
    """Verifica as mensagens recorrentes."""
    try:
        # Inicializa a conexão com o MongoDB
        logger.info("Conectando ao MongoDB...")
        await initialize_mongodb()
        logger.info("Conexão com o MongoDB estabelecida com sucesso.")
        
        # Verifica mensagens recorrentes
        logger.info("Verificando mensagens recorrentes...")
        if mongodb_client.db is None:
            logger.error("MongoDB não está conectado!")
            return
            
        # Verifica se a coleção existe
        collections = await mongodb_client.db.list_collection_names()
        logger.info(f"Coleções disponíveis: {collections}")
        
        if "recurring_messages" not in collections:
            logger.warning("A coleção 'recurring_messages' não existe!")
            return
        
        # Conta mensagens ativas
        active_count = await mongodb_client.db.recurring_messages.count_documents({"active": True})
        logger.info(f"Mensagens recorrentes ativas: {active_count}")
        
        # Conta mensagens inativas
        inactive_count = await mongodb_client.db.recurring_messages.count_documents({"active": False})
        logger.info(f"Mensagens recorrentes inativas: {inactive_count}")
        
        # Lista todas as mensagens
        logger.info("Lista de mensagens recorrentes:")
        cursor = mongodb_client.db.recurring_messages.find({})
        count = 0
        async for doc in cursor:
            count += 1
            # Formata o intervalo para exibição
            interval_hours = doc.get("interval_hours", 0)
            if interval_hours < 1:
                interval_display = f"{int(interval_hours * 60)} minutos"
            else:
                hours = int(interval_hours)
                minutes = int((interval_hours - hours) * 60)
                if minutes > 0:
                    interval_display = f"{hours}h{minutes}m"
                else:
                    interval_display = f"{hours}h"
            
            # Formata a data de criação
            created_at = doc.get("created_at", datetime.now())
            created_at_str = created_at.strftime("%d/%m/%Y %H:%M")
            
            # Formata a data do último envio
            last_sent_at = doc.get("last_sent_at")
            if last_sent_at:
                last_sent_at_str = last_sent_at.strftime("%d/%m/%Y %H:%M")
            else:
                last_sent_at_str = "Nunca"
            
            # Limita o tamanho da mensagem para exibição
            message_text = doc.get("message", "")
            if len(message_text) > 50:
                message_text = message_text[:47] + "..."
            
            logger.info(
                f"ID: {doc['_id']}, Ativa: {doc['active']}, Chat: {doc['chat_id']}, "
                f"Intervalo: {interval_display}, Último envio: {last_sent_at_str}, "
                f"Adicionada por: {doc.get('added_by_name', 'Desconhecido')}, "
                f"Mensagem: {message_text}"
            )
        
        if count == 0:
            logger.info("Nenhuma mensagem recorrente encontrada.")
        
        logger.info("Verificação concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante a verificação: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_recurring_messages()) 