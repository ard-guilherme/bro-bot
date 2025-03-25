"""
Script para testar os comandos de mensagens recorrentes.
"""
import asyncio
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import re

from telegram import Update, Message, Chat, User
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

async def test_recurring_commands():
    """Testa os comandos de mensagens recorrentes."""
    try:
        # Inicializa a conexão com o MongoDB
        logger.info("Conectando ao MongoDB...")
        await initialize_mongodb()
        logger.info("Conexão com o MongoDB estabelecida com sucesso.")
        
        # Cria mocks para os objetos Update e Context
        update = MagicMock(spec=Update)
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.effective_chat.type = "private"  # Simula um chat privado para simplificar o teste
        update.effective_user = MagicMock(spec=User)
        update.effective_user.id = 987654321
        update.effective_user.full_name = "Usuário de Teste"
        update.effective_user.username = "usuario_teste"
        update.message = MagicMock(spec=Message)
        update.message.chat = MagicMock(spec=Chat)
        update.message.chat.id = 123456789
        update.message.from_user = update.effective_user
        update.message.delete = AsyncMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot.get_chat_member = AsyncMock()
        
        # Inicializa o gerenciador de mensagens recorrentes
        app = MagicMock(spec=Application)
        app.bot = context.bot
        recurring_messages_manager = initialize_recurring_messages_manager(app)
        await recurring_messages_manager.start()
        
        # Simula a verificação de administrador
        with patch('src.bot.handlers.is_admin', return_value=True):
            # Testa o comando /sayrecurrent
            logger.info("Testando o comando /sayrecurrent...")
            update.message.text = "/sayrecurrent 12 Esta é uma mensagem recorrente de teste"
            await sayrecurrent_command(update, context)
            
            # Verifica se a mensagem foi enviada
            if context.bot.send_message.called:
                call_args = context.bot.send_message.call_args[1]
                message_text = call_args['text']
                logger.info(f"Mensagem enviada: {message_text}")
                
                # Extrai o ID da mensagem usando regex
                # O padrão é: 🆔 *ID:* `ID_AQUI`
                match = re.search(r'🆔 \*ID:\* `([^`]+)`', message_text)
                if match:
                    message_id = match.group(1)
                    logger.info(f"Mensagem recorrente adicionada com ID: {message_id}")
                else:
                    # Tenta outro padrão
                    match = re.search(r'ID:\s*`([^`]+)`', message_text)
                    if match:
                        message_id = match.group(1)
                        logger.info(f"Mensagem recorrente adicionada com ID: {message_id}")
                    else:
                        logger.warning("Não foi possível extrair o ID da mensagem")
                        logger.warning(f"Texto da mensagem: {message_text}")
                        return
            else:
                logger.warning("A mensagem não foi enviada")
                return
            
            # Testa o comando /listrecurrent
            logger.info("Testando o comando /listrecurrent...")
            update.message.text = "/listrecurrent"
            await listrecurrent_command(update, context)
            
            # Verifica se a lista foi enviada
            if context.bot.send_message.call_count > 1:
                call_args = context.bot.send_message.call_args[1]
                logger.info(f"Lista de mensagens recorrentes: {call_args['text']}")
            else:
                logger.warning("A lista não foi enviada")
            
            # Testa o comando /delrecurrent
            logger.info("Testando o comando /delrecurrent...")
            update.message.text = f"/delrecurrent {message_id}"
            await delrecurrent_command(update, context)
            
            # Verifica se a mensagem de confirmação foi enviada
            if context.bot.send_message.call_count > 2:
                call_args = context.bot.send_message.call_args[1]
                logger.info(f"Resultado da desativação: {call_args['text']}")
            else:
                logger.warning("A mensagem de confirmação não foi enviada")
            
            # Testa o comando /listrecurrent novamente para verificar se a mensagem foi desativada
            logger.info("Testando o comando /listrecurrent novamente...")
            update.message.text = "/listrecurrent"
            context.bot.send_message.reset_mock()
            update.message.reply_text.reset_mock()
            await listrecurrent_command(update, context)
            
            # Verifica se a lista está vazia
            if update.message.reply_text.called:
                call_args = update.message.reply_text.call_args[0]
                logger.info(f"Resultado da listagem após desativação: {call_args[0]}")
            elif context.bot.send_message.called:
                call_args = context.bot.send_message.call_args[1]
                logger.info(f"Resultado da listagem após desativação: {call_args['text']}")
            else:
                logger.warning("Nenhuma mensagem foi enviada")
        
        # Para o gerenciador de mensagens recorrentes
        await recurring_messages_manager.stop()
        
        logger.info("Teste concluído com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_recurring_commands()) 