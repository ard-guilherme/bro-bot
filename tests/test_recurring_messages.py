"""
Testes para os comandos de mensagens recorrentes.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from datetime import datetime, timedelta

from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes, Application

from src.bot.handlers import (
    sayrecurrent_command,
    listrecurrent_command,
    delrecurrent_command
)
from src.utils.mongodb_instance import initialize_mongodb
from src.utils.recurring_messages_manager import RecurringMessagesManager

@pytest.mark.asyncio
async def test_sayrecurrent_command():
    """Testa o comando /sayrecurrent."""
    # Configura mocks
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.id = 123456789
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 987654321
    update.message.from_user.full_name = "Usuário de Teste"
    update.message.message_id = 12345
    update.message.text = "/sayrecurrent 30m Mensagem de teste"
    update.message.delete = AsyncMock()
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    
    # Mock para is_admin
    with patch('src.bot.handlers.is_admin', return_value=True):
        # Mock para recurring_messages_manager
        with patch('src.utils.recurring_messages_manager.recurring_messages_manager') as mock_manager:
            mock_manager.add_recurring_message = AsyncMock(return_value="test_message_id")
            
            # Executa o comando
            await sayrecurrent_command(update, context)
            
            # Verifica se o método add_recurring_message foi chamado
            mock_manager.add_recurring_message.assert_called_once()
            call_args = mock_manager.add_recurring_message.call_args[1]
            assert "chat_id" in call_args
            assert "message" in call_args
            assert "interval_hours" in call_args
            assert "added_by" in call_args
            assert "added_by_name" in call_args
            assert call_args["message"] == "Mensagem de teste"
            assert call_args["interval_hours"] == 0.5  # 30 minutos = 0.5 horas
            
            # Verifica se a mensagem de confirmação foi enviada
            context.bot.send_message.assert_called_once()
            send_args = context.bot.send_message.call_args[1]
            assert "chat_id" in send_args
            assert "text" in send_args
            assert "Mensagem recorrente configurada com sucesso" in send_args["text"]
            assert "30 minutos" in send_args["text"]
            assert "test_message_id" in send_args["text"]
            
            # Verifica se a mensagem original foi deletada
            update.message.delete.assert_called_once()

@pytest.mark.asyncio
async def test_listrecurrent_command():
    """Testa o comando /listrecurrent."""
    # Configura mocks
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.id = 123456789
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 987654321
    update.message.text = "/listrecurrent"
    update.message.reply_text = AsyncMock()
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    
    # Mock para is_admin
    with patch('src.bot.handlers.is_admin', return_value=True):
        # Mock para recurring_messages_manager
        with patch('src.utils.recurring_messages_manager.recurring_messages_manager') as mock_manager:
            # Caso 1: Sem mensagens recorrentes
            mock_manager.get_recurring_messages = AsyncMock(return_value=[])
            
            # Executa o comando
            await listrecurrent_command(update, context)
            
            # Verifica se a mensagem "Não há mensagens recorrentes" foi enviada
            update.message.reply_text.assert_called_once()
            reply_args = update.message.reply_text.call_args[0]
            assert len(reply_args) > 0
            assert "Não há mensagens recorrentes" in reply_args[0]
            
            # Reseta os mocks
            update.message.reply_text.reset_mock()
            context.bot.send_message.reset_mock()
            
            # Caso 2: Com mensagens recorrentes
            mock_manager.get_recurring_messages = AsyncMock(return_value=[
                {
                    "_id": "test_message_id",
                    "message": "Mensagem de teste",
                    "interval_hours": 0.5,
                    "added_by": 987654321,
                    "added_by_name": "Usuário de Teste",
                    "created_at": datetime.now(),
                    "last_sent_at": None,
                    "active": True,
                    "chat_id": 123456789
                }
            ])
            
            # Executa o comando
            await listrecurrent_command(update, context)
            
            # Verifica se a lista de mensagens foi enviada
            context.bot.send_message.assert_called_once()
            send_args = context.bot.send_message.call_args[1]
            assert "chat_id" in send_args
            assert "text" in send_args
            assert "Mensagens recorrentes configuradas" in send_args["text"]
            assert "test_message_id" in send_args["text"]
            assert "Mensagem de teste" in send_args["text"]
            assert "30m" in send_args["text"] or "30 minutos" in send_args["text"]

@pytest.mark.asyncio
async def test_delrecurrent_command():
    """Testa o comando /delrecurrent."""
    # Configura mocks
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.id = 123456789
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 987654321
    update.message.message_id = 12345
    update.message.text = "/delrecurrent test_message_id"
    update.message.delete = AsyncMock()
    update.message.reply_text = AsyncMock()
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    
    # Mock para is_admin
    with patch('src.bot.handlers.is_admin', return_value=True):
        # Mock para recurring_messages_manager
        with patch('src.utils.recurring_messages_manager.recurring_messages_manager') as mock_manager:
            # Caso 1: Desativação bem-sucedida
            mock_manager.delete_recurring_message = AsyncMock(return_value=True)
            
            # Executa o comando
            await delrecurrent_command(update, context)
            
            # Verifica se o método delete_recurring_message foi chamado com o ID correto
            mock_manager.delete_recurring_message.assert_called_once_with("test_message_id")
            
            # Verifica se a mensagem de confirmação foi enviada
            context.bot.send_message.assert_called_once()
            send_args = context.bot.send_message.call_args[1]
            assert "chat_id" in send_args
            assert "text" in send_args
            assert "desativada com sucesso" in send_args["text"]
            assert "test_message_id" in send_args["text"]
            
            # Verifica se a mensagem original foi deletada
            update.message.delete.assert_called_once()
            
            # Reseta os mocks
            context.bot.send_message.reset_mock()
            update.message.delete.reset_mock()
            mock_manager.delete_recurring_message.reset_mock()
            
            # Caso 2: Desativação falhou
            mock_manager.delete_recurring_message = AsyncMock(return_value=False)
            
            # Executa o comando
            await delrecurrent_command(update, context)
            
            # Verifica se a mensagem de erro foi enviada
            update.message.reply_text.assert_called_once()
            reply_args = update.message.reply_text.call_args[0]
            assert len(reply_args) > 0
            assert "Erro ao desativar" in reply_args[0]
            assert "test_message_id" in reply_args[0]

@pytest.mark.asyncio
async def test_recurring_messages_manager():
    """Testa o gerenciador de mensagens recorrentes."""
    # Configura mocks
    app = MagicMock(spec=Application)
    app.bot = MagicMock()
    app.bot.send_message = AsyncMock()
    
    # Cria o gerenciador
    manager = RecurringMessagesManager(app)
    
    # Mock para mongodb_client
    with patch('src.utils.recurring_messages_manager.mongodb_client') as mock_db:
        # Configura os mocks para os métodos do MongoDB
        mock_db.add_recurring_message = AsyncMock(return_value="test_message_id")
        mock_db.get_recurring_message = AsyncMock(return_value={
            "_id": "test_message_id",
            "chat_id": 123456789,
            "message": "Mensagem de teste",
            "interval_hours": 0.5,
            "added_by": 987654321,
            "added_by_name": "Usuário de Teste",
            "created_at": datetime.now(),
            "last_sent_at": None,
            "active": True
        })
        mock_db.update_recurring_message_last_sent = AsyncMock(return_value=True)
        mock_db.delete_recurring_message = AsyncMock(return_value=True)
        
        # Testa add_recurring_message
        message_id = await manager.add_recurring_message(
            chat_id=123456789,
            message="Mensagem de teste",
            interval_hours=0.5,
            added_by=987654321,
            added_by_name="Usuário de Teste"
        )
        
        assert message_id == "test_message_id"
        mock_db.add_recurring_message.assert_called_once()
        
        # Testa delete_recurring_message
        result = await manager.delete_recurring_message("test_message_id")
        
        assert result is True
        mock_db.delete_recurring_message.assert_called_once_with("test_message_id")

if __name__ == "__main__":
    asyncio.run(test_sayrecurrent_command())
    asyncio.run(test_listrecurrent_command())
    asyncio.run(test_delrecurrent_command())
    asyncio.run(test_recurring_messages_manager()) 