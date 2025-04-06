"""
Testes para os handlers de monitoramento.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes
from src.bot.handlers import (
    monitor_command,
    unmonitor_command,
    handle_monitored_message,
    send_temporary_message
)
from src.utils.mongodb_instance import mongodb_client

@pytest.fixture
def setup_mocks():
    """Configura o ambiente de teste."""
    # Mock para o usuário
    user = MagicMock(spec=User)
    user.id = 12345
    user.full_name = "Test User"
    user.username = "testuser"
    
    # Mock para o chat
    chat = MagicMock(spec=Chat)
    chat.id = 67890
    chat.type = "group"
    
    # Mock para a mensagem
    message = MagicMock(spec=Message)
    message.message_id = 111
    message.from_user = user
    message.chat = chat
    message.text = "Test message"
    message.date = MagicMock()
    message.delete = AsyncMock()
    
    # Mock para o update
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_chat = chat
    update.message = message
    
    # Mock para o contexto
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    
    # Mock para o MongoDB
    mock_mongodb_client = MagicMock()
    mock_mongodb_client.start_monitoring = AsyncMock()
    mock_mongodb_client.stop_monitoring = AsyncMock()
    mock_mongodb_client.is_chat_monitored = AsyncMock()
    mock_mongodb_client.store_message = AsyncMock()
    
    # Mock para send_temporary_message
    mock_send_temporary_message = AsyncMock()
    
    # Patch para mongodb_client e send_temporary_message
    with patch('src.bot.handlers.mongodb_client', mock_mongodb_client), \
         patch('src.bot.handlers.send_temporary_message', mock_send_temporary_message):
        
        yield {
            "user": user,
            "chat": chat,
            "message": message,
            "update": update,
            "context": context,
            "mock_mongodb_client": mock_mongodb_client,
            "send_temporary_message": mock_send_temporary_message
        }

@pytest.mark.asyncio
async def test_monitor_command_not_group(setup_mocks):
    """Testa o comando /monitor em um chat que não é grupo."""
    mocks = setup_mocks
    
    # Configura o chat para não ser um grupo
    mocks["chat"].type = "private"
    
    # Executa o comando
    await monitor_command(mocks["update"], mocks["context"])
    
    # Verifica se a mensagem temporária foi enviada
    mocks["send_temporary_message"].assert_called_once()
    args = mocks["send_temporary_message"].call_args[0]
    assert "Este comando só pode ser usado em grupos" in args[2]
    
    # Verifica se o método start_monitoring não foi chamado
    mocks["mock_mongodb_client"].start_monitoring.assert_not_called()

@pytest.mark.asyncio
async def test_monitor_command_success(setup_mocks):
    """Testa o comando /monitor com sucesso."""
    mocks = setup_mocks
    
    # Configura o chat para ser um grupo
    mocks["chat"].type = "group"
    mocks["chat"].title = "Test Group Title"
    mocks["chat"].username = "testgroupusername"
    
    # Configura o mock para start_monitoring
    mocks["mock_mongodb_client"].start_monitoring.return_value = True
    
    # Executa o comando
    await monitor_command(mocks["update"], mocks["context"])
    
    # Verifica se o método start_monitoring foi chamado corretamente
    mocks["mock_mongodb_client"].start_monitoring.assert_called_once_with(
        chat_id=mocks["chat"].id, 
        title=mocks["chat"].title,
        username=mocks["chat"].username
    )
    
    # Verifica se a mensagem de comando foi deletada
    mocks["message"].delete.assert_called_once()
    
    # Verifica se a mensagem de confirmação foi enviada
    mocks["context"].bot.send_message.assert_called_once()
    kwargs = mocks["context"].bot.send_message.call_args[1]
    assert kwargs["chat_id"] == mocks["chat"].id
    assert "✅ Monitoramento de mensagens iniciado neste grupo." in kwargs["text"]

@pytest.mark.asyncio
async def test_monitor_command_failure(setup_mocks):
    """Testa o comando /monitor com falha."""
    mocks = setup_mocks
    
    # Configura o chat para ser um grupo
    mocks["chat"].type = "group"
    mocks["chat"].title = "Test Group Title Fail"
    mocks["chat"].username = "testgroupusernamefail"
    
    # Configura o mock para start_monitoring
    mocks["mock_mongodb_client"].start_monitoring.return_value = False
    
    # Executa o comando
    await monitor_command(mocks["update"], mocks["context"])
    
    # Verifica se o método start_monitoring foi chamado corretamente
    mocks["mock_mongodb_client"].start_monitoring.assert_called_once_with(
        chat_id=mocks["chat"].id, 
        title=mocks["chat"].title,
        username=mocks["chat"].username
    )
    
    # Verifica se a mensagem de comando foi deletada
    mocks["message"].delete.assert_called_once()
    
    # Verifica se a mensagem temporária foi enviada
    mocks["send_temporary_message"].assert_called_once()
    args = mocks["send_temporary_message"].call_args[0]
    assert "❌ Erro ao iniciar monitoramento. Por favor, tente novamente." in args[2]

@pytest.mark.asyncio
async def test_unmonitor_command_not_group(setup_mocks):
    """Testa o comando /unmonitor em um chat que não é grupo."""
    mocks = setup_mocks
    
    # Configura o chat para não ser um grupo
    mocks["chat"].type = "private"
    
    # Executa o comando
    await unmonitor_command(mocks["update"], mocks["context"])
    
    # Verifica se a mensagem temporária foi enviada
    mocks["send_temporary_message"].assert_called_once()
    args = mocks["send_temporary_message"].call_args[0]
    assert "Este comando só pode ser usado em grupos" in args[2]
    
    # Verifica se o método stop_monitoring não foi chamado
    mocks["mock_mongodb_client"].stop_monitoring.assert_not_called()

@pytest.mark.asyncio
async def test_unmonitor_command_success(setup_mocks):
    """Testa o comando /unmonitor com sucesso."""
    mocks = setup_mocks
    
    # Configura o chat para ser um grupo
    mocks["chat"].type = "group"
    
    # Configura o mock para stop_monitoring
    mocks["mock_mongodb_client"].stop_monitoring.return_value = True
    
    # Executa o comando
    await unmonitor_command(mocks["update"], mocks["context"])
    
    # Verifica se o método stop_monitoring foi chamado corretamente
    mocks["mock_mongodb_client"].stop_monitoring.assert_called_once_with(mocks["chat"].id)
    
    # Verifica se a mensagem de comando foi deletada
    mocks["message"].delete.assert_called_once()
    
    # Verifica se a mensagem de confirmação foi enviada
    mocks["context"].bot.send_message.assert_called_once()
    kwargs = mocks["context"].bot.send_message.call_args[1]
    assert kwargs["chat_id"] == mocks["chat"].id
    assert "Monitoramento de mensagens parado" in kwargs["text"]

@pytest.mark.asyncio
async def test_unmonitor_command_failure(setup_mocks):
    """Testa o comando /unmonitor com falha."""
    mocks = setup_mocks
    
    # Configura o chat para ser um grupo
    mocks["chat"].type = "group"
    
    # Configura o mock para stop_monitoring
    mocks["mock_mongodb_client"].stop_monitoring.return_value = False
    
    # Executa o comando
    await unmonitor_command(mocks["update"], mocks["context"])
    
    # Verifica se o método stop_monitoring foi chamado corretamente
    mocks["mock_mongodb_client"].stop_monitoring.assert_called_once_with(mocks["chat"].id)
    
    # Verifica se a mensagem de comando foi deletada
    mocks["message"].delete.assert_called_once()
    
    # Verifica se a mensagem temporária foi enviada
    mocks["send_temporary_message"].assert_called_once()
    args = mocks["send_temporary_message"].call_args[0]
    assert "Erro ao parar monitoramento" in args[2]

@pytest.mark.asyncio
async def test_handle_monitored_message_no_text(setup_mocks):
    """Testa o handler de mensagens monitoradas sem texto."""
    mocks = setup_mocks
    
    # Configura a mensagem para não ter texto
    mocks["message"].text = None
    
    # Executa o handler
    await handle_monitored_message(mocks["update"], mocks["context"])
    
    # Verifica se o método is_chat_monitored não foi chamado
    mocks["mock_mongodb_client"].is_chat_monitored.assert_not_called()
    
    # Verifica se o método store_message não foi chamado
    mocks["mock_mongodb_client"].store_message.assert_not_called()

@pytest.mark.asyncio
async def test_handle_monitored_message_not_group(setup_mocks):
    """Testa o handler de mensagens monitoradas em um chat que não é grupo."""
    mocks = setup_mocks
    
    # Configura a mensagem para ter texto
    mocks["message"].text = "Test message"
    
    # Configura o chat para não ser um grupo
    mocks["chat"].type = "private"
    
    # Executa o handler
    await handle_monitored_message(mocks["update"], mocks["context"])
    
    # Verifica se o método is_chat_monitored não foi chamado
    mocks["mock_mongodb_client"].is_chat_monitored.assert_not_called()
    
    # Verifica se o método store_message não foi chamado
    mocks["mock_mongodb_client"].store_message.assert_not_called()

@pytest.mark.asyncio
async def test_handle_monitored_message_not_monitored(setup_mocks):
    """Testa o handler de mensagens monitoradas em um chat que não está sendo monitorado."""
    mocks = setup_mocks
    
    # Configura a mensagem para ter texto
    mocks["message"].text = "Test message"
    
    # Configura o chat para ser um grupo
    mocks["chat"].type = "group"
    
    # Configura o mock para is_chat_monitored
    mocks["mock_mongodb_client"].is_chat_monitored.return_value = False
    
    # Executa o handler
    await handle_monitored_message(mocks["update"], mocks["context"])
    
    # Verifica se o método is_chat_monitored foi chamado corretamente
    mocks["mock_mongodb_client"].is_chat_monitored.assert_called_once_with(mocks["chat"].id)
    
    # Verifica se o método store_message não foi chamado
    mocks["mock_mongodb_client"].store_message.assert_not_called()

@pytest.mark.asyncio
async def test_handle_monitored_message_success(setup_mocks):
    """Testa o handler de mensagens monitoradas com sucesso."""
    mocks = setup_mocks
    
    # Configura a mensagem para ter texto
    mocks["message"].text = "Test message"
    
    # Configura o chat para ser um grupo
    mocks["chat"].type = "group"
    
    # Configura o mock para is_chat_monitored
    mocks["mock_mongodb_client"].is_chat_monitored.return_value = True
    
    # Configura o mock para store_message
    mocks["mock_mongodb_client"].store_message.return_value = True
    
    # Executa o handler
    await handle_monitored_message(mocks["update"], mocks["context"])
    
    # Verifica se o método is_chat_monitored foi chamado corretamente
    mocks["mock_mongodb_client"].is_chat_monitored.assert_called_once_with(mocks["chat"].id)
    
    # Verifica se o método store_message foi chamado corretamente
    mocks["mock_mongodb_client"].store_message.assert_called_once()
    args = mocks["mock_mongodb_client"].store_message.call_args[1]
    assert args["chat_id"] == mocks["chat"].id
    assert args["message_id"] == mocks["message"].message_id
    assert args["user_id"] == mocks["user"].id
    assert args["user_name"] == mocks["user"].full_name
    assert args["text"] == "Test message"
    assert args["timestamp"] == mocks["message"].date 