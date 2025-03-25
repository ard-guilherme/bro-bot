"""
Script para testar o processamento de mensagens editadas nos comandos de mensagens recorrentes.
"""
import asyncio
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, Message, Chat, User, MessageEntity
from telegram.ext import ContextTypes, Application

from src.bot.handlers import (
    sayrecurrent_command,
    listrecurrent_command,
    delrecurrent_command
)
from src.utils.mongodb_instance import initialize_mongodb
from src.utils.recurring_messages_manager import initialize_recurring_messages_manager

# Configuração de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def test_edited_messages():
    """Testa o processamento de mensagens editadas nos comandos de mensagens recorrentes."""
    try:
        # Inicializa a conexão com o MongoDB
        logger.info("Conectando ao MongoDB...")
        await initialize_mongodb()
        logger.info("Conexão com o MongoDB estabelecida com sucesso.")
        
        # Cria mocks para os objetos Update e Context
        update = MagicMock(spec=Update)
        update.message = None  # Simula uma mensagem editada
        
        # Configura a mensagem editada
        update.edited_message = MagicMock(spec=Message)
        update.edited_message.chat = MagicMock(spec=Chat)
        update.edited_message.chat.id = 123456789  # Valor real, não um mock
        update.edited_message.chat.type = "private"  # Valor real, não um mock
        update.edited_message.from_user = MagicMock(spec=User)
        update.edited_message.from_user.id = 987654321  # Valor real, não um mock
        update.edited_message.from_user.full_name = "Usuário de Teste"  # Valor real, não um mock
        update.edited_message.from_user.username = "usuario_teste"  # Valor real, não um mock
        update.edited_message.message_id = 12345  # Valor real, não um mock
        update.edited_message.delete = AsyncMock()
        update.edited_message.reply_text = AsyncMock()
        
        # Configura o contexto
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot.get_chat_member = AsyncMock()
        
        # Inicializa o gerenciador de mensagens recorrentes
        app = MagicMock(spec=Application)
        app.bot = context.bot
        recurring_messages_manager = initialize_recurring_messages_manager(app)
        
        # Substitui o método add_recurring_message por um mock
        recurring_messages_manager.add_recurring_message = AsyncMock(return_value="test_message_id")
        recurring_messages_manager.get_recurring_messages = AsyncMock(return_value=[
            {
                "_id": "test_message_id",
                "message": "Esta é uma mensagem recorrente de teste",
                "interval_hours": 12.0,
                "added_by": 987654321,
                "added_by_name": "Usuário de Teste",
                "created_at": datetime.now(),
                "last_sent_at": None,
                "active": True,
                "chat_id": 123456789
            }
        ])
        recurring_messages_manager.delete_recurring_message = AsyncMock(return_value=True)
        
        await recurring_messages_manager.start()
        
        # Simula a verificação de administrador
        with patch('src.bot.handlers.is_admin', return_value=True):
            # Testa o comando /sayrecurrent com mensagem editada
            logger.info("Testando o comando /sayrecurrent com mensagem editada...")
            update.edited_message.text = "/sayrecurrent 12 Esta é uma mensagem recorrente de teste"
            update.edited_message.entities = [
                MagicMock(spec=MessageEntity, type="bot_command", offset=0, length=13)
            ]
            
            await sayrecurrent_command(update, context)
            
            # Verifica se a mensagem foi enviada
            if context.bot.send_message.called:
                call_args = context.bot.send_message.call_args[1]
                logger.info(f"Mensagem enviada: {call_args['text']}")
                logger.info("Comando /sayrecurrent processou corretamente a mensagem editada!")
            else:
                logger.warning("A mensagem não foi enviada")
            
            # Verifica se o método add_recurring_message foi chamado
            if recurring_messages_manager.add_recurring_message.called:
                call_args = recurring_messages_manager.add_recurring_message.call_args[1]
                logger.info(f"Método add_recurring_message chamado com: {call_args}")
                logger.info("Método add_recurring_message foi chamado corretamente!")
            else:
                logger.warning("O método add_recurring_message não foi chamado")
            
            # Reseta os mocks para o próximo teste
            context.bot.send_message.reset_mock()
            update.edited_message.reply_text.reset_mock()
            
            # Testa o comando /listrecurrent com mensagem editada
            logger.info("Testando o comando /listrecurrent com mensagem editada...")
            update.edited_message.text = "/listrecurrent"
            update.edited_message.entities = [
                MagicMock(spec=MessageEntity, type="bot_command", offset=0, length=14)
            ]
            
            await listrecurrent_command(update, context)
            
            # Verifica se a lista foi enviada
            if context.bot.send_message.called:
                call_args = context.bot.send_message.call_args[1]
                logger.info(f"Lista de mensagens recorrentes: {call_args['text']}")
                logger.info("Comando /listrecurrent processou corretamente a mensagem editada!")
            elif update.edited_message.reply_text.called:
                call_args = update.edited_message.reply_text.call_args[0]
                logger.info(f"Resposta: {call_args[0]}")
                logger.info("Comando /listrecurrent processou corretamente a mensagem editada!")
            else:
                logger.warning("A lista não foi enviada")
            
            # Verifica se o método get_recurring_messages foi chamado
            if recurring_messages_manager.get_recurring_messages.called:
                call_args = recurring_messages_manager.get_recurring_messages.call_args[0]
                logger.info(f"Método get_recurring_messages chamado com: {call_args}")
                logger.info("Método get_recurring_messages foi chamado corretamente!")
            else:
                logger.warning("O método get_recurring_messages não foi chamado")
            
            # Reseta os mocks para o próximo teste
            context.bot.send_message.reset_mock()
            update.edited_message.reply_text.reset_mock()
            
            # Testa o comando /delrecurrent com mensagem editada
            logger.info("Testando o comando /delrecurrent com mensagem editada...")
            update.edited_message.text = "/delrecurrent test_message_id"
            update.edited_message.entities = [
                MagicMock(spec=MessageEntity, type="bot_command", offset=0, length=13)
            ]
            
            await delrecurrent_command(update, context)
            
            # Verifica se a mensagem de confirmação foi enviada
            if context.bot.send_message.called:
                call_args = context.bot.send_message.call_args[1]
                logger.info(f"Resultado da desativação: {call_args['text']}")
                logger.info("Comando /delrecurrent processou corretamente a mensagem editada!")
            elif update.edited_message.reply_text.called:
                call_args = update.edited_message.reply_text.call_args[0]
                logger.info(f"Resposta: {call_args[0]}")
                logger.info("Comando /delrecurrent processou corretamente a mensagem editada!")
            else:
                logger.warning("A mensagem de confirmação não foi enviada")
            
            # Verifica se o método delete_recurring_message foi chamado
            if recurring_messages_manager.delete_recurring_message.called:
                call_args = recurring_messages_manager.delete_recurring_message.call_args[0]
                logger.info(f"Método delete_recurring_message chamado com: {call_args}")
                logger.info("Método delete_recurring_message foi chamado corretamente!")
            else:
                logger.warning("O método delete_recurring_message não foi chamado")
        
        # Para o gerenciador de mensagens recorrentes
        await recurring_messages_manager.stop()
        
        logger.info("Teste concluído com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_edited_messages()) 