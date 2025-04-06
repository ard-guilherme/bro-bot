"""
Testes para os comandos de administração do bot.
"""
# import unittest # Remover unittest
from unittest.mock import AsyncMock, MagicMock # Manter mocks
import pytest
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

from src.bot.handlers import setadmin_command, deladmin_command, listadmins_command
from src.utils.config import Config

OWNER_ID = 123456789
USER_ID = 123456789 # O usuário que executa o comando é o proprietário neste setup
OTHER_USER_ID = 987654321
CHAT_ID = -1001234567890

@pytest.fixture
def admin_mocks(mocker): # Usar mocker do pytest-mock
    """Fixture para configurar mocks comuns para testes de admin."""
    # Mock Update
    update = MagicMock(spec=Update)
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    # Mock User (o usuário que envia o comando)
    user = MagicMock(spec=User)
    user.id = USER_ID
    user.full_name = "Test Owner User"

    # Mock Message
    message = MagicMock(spec=Message)
    message.from_user = user
    message.chat = MagicMock(spec=Chat)
    message.chat.id = CHAT_ID
    message.reply_text = AsyncMock() # Mock assíncrono para reply_text
    message.reply_to_message = None

    # Configura Update e Context
    update.effective_user = user
    update.message = message
    update.effective_message = message
    context.args = []

    # Patch Config.get_owner_id
    mock_get_owner_id = mocker.patch('src.utils.config.Config.get_owner_id', return_value=OWNER_ID)

    # Patch mongodb_client
    mock_mongodb = mocker.patch('src.bot.handlers.mongodb_client')
    # Assegurar que as funções mockadas do mongodb são AsyncMocks
    mock_mongodb.add_admin = AsyncMock()
    mock_mongodb.remove_admin = AsyncMock()
    mock_mongodb.get_admins = AsyncMock()
    mock_mongodb.db = MagicMock() # Se necessário mockar db diretamente

    return {
        "update": update,
        "context": context,
        "message": message,
        "user": user,
        "mock_mongodb": mock_mongodb,
        "mock_get_owner_id": mock_get_owner_id
    }

# Remover a classe TestAdminCommands
# class TestAdminCommands(unittest.TestCase):
#     ...

# Testes individuais como funções, usando a fixture

@pytest.mark.asyncio
async def test_setadmin_command_no_args_no_reply(admin_mocks):
    """Testa o comando /setadmin sem argumentos e sem resposta."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]

    await setadmin_command(update, context)

    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert "Erro: Você deve fornecer o ID do usuário ou responder a uma mensagem" in args[0]

@pytest.mark.asyncio
async def test_setadmin_command_with_args(admin_mocks):
    """Testa o comando /setadmin com ID do usuário como argumento."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]
    mock_mongodb = admin_mocks["mock_mongodb"]

    # Configura o argumento
    context.args = [str(OTHER_USER_ID)]

    # Configura o mock para add_admin
    mock_mongodb.add_admin.return_value = True

    await setadmin_command(update, context)

    # Verifica se add_admin foi chamado com os parâmetros corretos
    mock_mongodb.add_admin.assert_called_once_with(
        admin_id=OTHER_USER_ID,
        admin_name=f"Usuário {OTHER_USER_ID}", # Nome padrão quando não há reply
        added_by=USER_ID
    )

    # Verifica a mensagem de resposta
    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert "foi adicionado como administrador do bot" in args[0]

@pytest.mark.asyncio
async def test_setadmin_command_with_reply(admin_mocks):
    """Testa o comando /setadmin respondendo a uma mensagem."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]
    mock_mongodb = admin_mocks["mock_mongodb"]

    # Configura a mensagem de resposta
    reply_user = MagicMock(spec=User)
    reply_user.id = OTHER_USER_ID
    reply_user.full_name = "Reply User Name"

    reply_message = MagicMock(spec=Message)
    reply_message.from_user = reply_user

    message.reply_to_message = reply_message

    # Configura o mock para add_admin
    mock_mongodb.add_admin.return_value = True

    await setadmin_command(update, context)

    # Verifica se add_admin foi chamado com os parâmetros corretos
    mock_mongodb.add_admin.assert_called_once_with(
        admin_id=OTHER_USER_ID,
        admin_name="Reply User Name", # Nome do usuário da mensagem respondida
        added_by=USER_ID
    )

    # Verifica a mensagem de resposta
    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert "foi adicionado como administrador do bot" in args[0]

@pytest.mark.asyncio
async def test_setadmin_command_user_already_admin(admin_mocks):
    """Testa o comando /setadmin quando o usuário já é administrador."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]
    mock_mongodb = admin_mocks["mock_mongodb"]

    context.args = [str(OTHER_USER_ID)]
    mock_mongodb.add_admin.return_value = False # Simula que o usuário já existe

    await setadmin_command(update, context)

    mock_mongodb.add_admin.assert_called_once_with(
        admin_id=OTHER_USER_ID,
        admin_name=f"Usuário {OTHER_USER_ID}",
        added_by=USER_ID
    )
    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert "já é um administrador do bot" in args[0]

@pytest.mark.asyncio
async def test_setadmin_command_invalid_user_id(admin_mocks):
    """Testa o comando /setadmin com ID de usuário inválido."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]

    context.args = ["invalid_id"]

    await setadmin_command(update, context)

    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert "Erro: O ID do usuário deve ser um número inteiro" in args[0]

@pytest.mark.asyncio
async def test_setadmin_command_add_self(admin_mocks):
    """Testa o comando /setadmin tentando adicionar a si mesmo."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]

    context.args = [str(USER_ID)] # ID do próprio usuário

    await setadmin_command(update, context)

    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    # Como USER_ID == OWNER_ID no setup, a mensagem será sobre ser proprietário
    assert "Você já é o proprietário do bot" in args[0]

@pytest.mark.asyncio
async def test_setadmin_command_add_owner(admin_mocks):
    """Testa o comando /setadmin tentando adicionar o proprietário."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]
    mock_mongodb = admin_mocks["mock_mongodb"]

    # Configura a mensagem de resposta com o usuário sendo o OWNER_ID
    reply_user = MagicMock(spec=User)
    reply_user.id = OWNER_ID # ID do proprietário
    reply_user.full_name = "Test Owner User"

    reply_message = MagicMock(spec=Message)
    reply_message.from_user = reply_user

    message.reply_to_message = reply_message

    await setadmin_command(update, context)

    # Verifica a mensagem de erro correta usando reply_text
    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert args[0] == "Você já é o proprietário do bot e tem acesso total. Não é necessário adicionar a si mesmo como administrador."
    mock_mongodb.add_admin.assert_not_called()

# --- Testes para deladmin_command --- #

@pytest.mark.asyncio
async def test_deladmin_command_no_args_no_reply(admin_mocks):
    """Testa o comando /deladmin sem argumentos e sem resposta."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]

    await deladmin_command(update, context)

    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert "Erro: Você deve fornecer o ID do usuário ou responder a uma mensagem" in args[0]

@pytest.mark.asyncio
async def test_deladmin_command_with_args(admin_mocks):
    """Testa o comando /deladmin com ID do usuário como argumento."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]
    mock_mongodb = admin_mocks["mock_mongodb"]

    context.args = [str(OTHER_USER_ID)]
    mock_mongodb.remove_admin.return_value = True # Simula remoção bem-sucedida

    await deladmin_command(update, context)

    mock_mongodb.remove_admin.assert_called_once_with(user_id=OTHER_USER_ID)
    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert "foi removido da lista de administradores do bot" in args[0]

@pytest.mark.asyncio
async def test_deladmin_command_with_reply(admin_mocks):
    """Testa o comando /deladmin respondendo a uma mensagem."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]
    mock_mongodb = admin_mocks["mock_mongodb"]

    # Configura a mensagem de resposta
    reply_user = MagicMock(spec=User)
    reply_user.id = OTHER_USER_ID

    reply_message = MagicMock(spec=Message)
    reply_message.from_user = reply_user

    message.reply_to_message = reply_message
    mock_mongodb.remove_admin.return_value = True

    await deladmin_command(update, context)

    mock_mongodb.remove_admin.assert_called_once_with(user_id=OTHER_USER_ID)
    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert "foi removido da lista de administradores do bot" in args[0]

@pytest.mark.asyncio
async def test_deladmin_command_user_not_admin(admin_mocks):
    """Testa o comando /deladmin quando o usuário não é administrador."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]
    mock_mongodb = admin_mocks["mock_mongodb"]

    context.args = [str(OTHER_USER_ID)]
    mock_mongodb.remove_admin.return_value = False # Simula que usuário não foi encontrado/removido

    await deladmin_command(update, context)

    mock_mongodb.remove_admin.assert_called_once_with(user_id=OTHER_USER_ID)
    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert "não é um administrador do bot" in args[0]

@pytest.mark.asyncio
async def test_deladmin_command_invalid_user_id(admin_mocks):
    """Testa o comando /deladmin com ID de usuário inválido."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]

    context.args = ["invalid_id"]

    await deladmin_command(update, context)

    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert "Erro: O ID do usuário deve ser um número inteiro" in args[0]

@pytest.mark.asyncio
async def test_deladmin_command_remove_self(admin_mocks):
    """Testa o comando /deladmin tentando remover a si mesmo."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]
    mock_mongodb = admin_mocks["mock_mongodb"]

    # Configura o argumento para ser o ID do próprio usuário
    context.args = [str(update.effective_user.id)]

    await deladmin_command(update, context)

    # Verifica a mensagem de erro correta usando reply_text
    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert args[0] == "Você é o proprietário do bot e não pode remover a si mesmo da lista de administradores."
    mock_mongodb.remove_admin.assert_not_called()

@pytest.mark.asyncio
async def test_deladmin_command_remove_owner(admin_mocks):
    """Testa o comando /deladmin tentando remover o proprietário."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]
    mock_mongodb = admin_mocks["mock_mongodb"]

    # Configura o argumento para ser o ID do OWNER_ID
    context.args = [str(Config.get_owner_id())]

    await deladmin_command(update, context)

    # Verifica a mensagem de erro correta usando reply_text
    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    assert args[0] == "Você é o proprietário do bot e não pode remover a si mesmo da lista de administradores."
    mock_mongodb.remove_admin.assert_not_called()

# --- Testes para listadmins_command --- #

@pytest.mark.asyncio
async def test_listadmins_command_with_admins(admin_mocks):
    """Testa o comando /listadmins quando há administradores."""
    update = admin_mocks["update"]
    context = admin_mocks["context"]
    message = admin_mocks["message"]
    mock_mongodb = admin_mocks["mock_mongodb"]

    admin_data = [
        {"admin_id": 12345, "admin_name": "Admin One"},
        {"admin_id": 67890, "admin_name": "Admin Two"}
    ]
    mock_mongodb.get_admins.return_value = admin_data

    await listadmins_command(update, context)

    # Verifica a mensagem formatada usando reply_text
    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    expected_header = "📋 Lista de administradores do bot:\n\n"
    expected_line1 = "1. Admin One (ID: 12345)\n"
    expected_line2 = "2. Admin Two (ID: 67890)\n"
    expected_footer = "\nTotal: 2 administrador(es)"
    expected_message = expected_header + expected_line1 + expected_line2 + expected_footer
    assert args[0] == expected_message
    mock_mongodb.get_admins.assert_called_once()

@pytest.mark.asyncio
async def test_listadmins_command_no_admins(admin_mocks):
    """Testa o comando /listadmins quando não há administradores."""
    update = admin_mocks["update"]
    message = admin_mocks["message"]
    context = admin_mocks["context"]
    mock_mongodb = admin_mocks["mock_mongodb"]

    # Correção: Usar mock_mongodb
    mock_mongodb.get_admins.return_value = [] # Lista vazia

    await listadmins_command(update, context)

    # Verifica a mensagem de lista vazia usando reply_text
    message.reply_text.assert_called_once()
    args, _ = message.reply_text.call_args
    expected_message = "Não há administradores adicionais configurados para o bot.\n\nVocê, como proprietário, é o único com acesso total ao bot."
    assert args[0] == expected_message
    mock_mongodb.get_admins.assert_called_once() 