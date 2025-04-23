"""
Testes para os handlers de blacklist.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from telegram import Update, User, Chat, Message, ChatMember, ReactionTypeEmoji, BotCommand
from telegram.constants import ChatType, ParseMode, ReactionType
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from datetime import datetime
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
from html import escape as escape_html

from src.bot.blacklist_handlers import addblacklist_command, blacklist_command, rmblacklist_command, blacklist_button, ban_blacklist_command

@pytest.fixture
def mock_update():
    """
    Mock para Update do Telegram.
    """
    update = MagicMock(spec=Update)
    
    # Configure user
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.effective_user.full_name = "Test User"
    update.effective_user.first_name = "Test"
    
    # Configure chat
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 67890
    update.effective_chat.type = ChatType.GROUP
    
    # Configure message
    update.message = MagicMock(spec=Message)
    update.message.message_id = 111
    update.message.from_user = update.effective_user
    update.message.chat = update.effective_chat
    update.message.delete = AsyncMock()
    update.message.reply_text = AsyncMock()
    
    return update

@pytest.fixture
def mock_context():
    """
    Mock para ContextTypes.DEFAULT_TYPE do Telegram.
    """
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.set_message_reaction = AsyncMock()
    context.args = []
    
    return context

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.send_temporary_message")
async def test_addblacklist_command_not_admin(mock_send_temp, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /addblacklist quando o usuário não é administrador.
    """
    # Configura is_admin para retornar False
    mock_is_admin.return_value = False
    
    # Executa a função
    await addblacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se send_temporary_message foi chamado corretamente
    mock_send_temp.assert_called_once_with(
        mock_update,
        mock_context,
        "Apenas administradores podem usar este comando."
    )
    
    # Verifica que nenhuma outra ação foi realizada
    mock_update.message.delete.assert_not_called()
    mock_context.bot.set_message_reaction.assert_not_called()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.send_temporary_message")
async def test_addblacklist_command_not_reply(mock_send_temp, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /addblacklist quando não é uma resposta a outra mensagem.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Configura update para não ter reply_to_message
    mock_update.message.reply_to_message = None
    
    # Executa a função
    await addblacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se send_temporary_message foi chamado corretamente
    mock_send_temp.assert_called_once_with(
        mock_update,
        mock_context,
        "Por favor, use este comando respondendo à mensagem que deseja adicionar à blacklist."
    )
    
    # Verifica que nenhuma outra ação foi realizada
    mock_update.message.delete.assert_not_called()
    mock_context.bot.set_message_reaction.assert_not_called()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.send_temporary_message")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_addblacklist_command_success(mock_mongodb, mock_send_temp, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /addblacklist quando é executado com sucesso.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Configura reply_to_message
    reply_message = MagicMock(spec=Message)
    reply_message.message_id = 222
    reply_message.from_user = MagicMock(spec=User)
    reply_message.from_user.id = 54321
    reply_message.from_user.username = "targetuser"
    reply_message.from_user.full_name = "Target User"
    reply_message.text = "Mensagem inapropriada"
    mock_update.message.reply_to_message = reply_message
    
    # Configura mongodb_client.add_to_blacklist para retornar um ID
    add_to_blacklist_mock = AsyncMock()
    add_to_blacklist_mock.return_value = "60f1a5b5a9c1e2b3c4d5e6f7"
    mock_mongodb.add_to_blacklist = add_to_blacklist_mock
    
    # Executa a função
    await addblacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se add_to_blacklist foi chamado com os parâmetros corretos
    mock_mongodb.add_to_blacklist.assert_called_once_with(
        chat_id=mock_update.effective_chat.id,
        message_id=reply_message.message_id,
        user_id=reply_message.from_user.id,
        user_name=reply_message.from_user.full_name,
        username=reply_message.from_user.username,
        message_text=reply_message.text,
        added_by=mock_update.effective_user.id,
        added_by_name=mock_update.effective_user.full_name
    )
    
    # Verifica se a reação foi adicionada à mensagem com ReactionTypeEmoji
    mock_context.bot.set_message_reaction.assert_called_once()
    call_args = mock_context.bot.set_message_reaction.call_args[1]
    assert call_args["chat_id"] == mock_update.effective_chat.id
    assert call_args["message_id"] == reply_message.message_id
    assert isinstance(call_args["reaction"][0], ReactionTypeEmoji)
    assert call_args["reaction"][0].emoji == "👎"
    
    # Verifica que a mensagem de confirmação NÃO foi enviada
    mock_send_temp.assert_not_called()
    
    # Verifica se a mensagem de comando foi deletada
    mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.send_temporary_message")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_addblacklist_command_error(mock_mongodb, mock_send_temp, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /addblacklist quando ocorre um erro no MongoDB.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Configura reply_to_message
    reply_message = MagicMock(spec=Message)
    reply_message.message_id = 222
    reply_message.from_user = MagicMock(spec=User)
    reply_message.from_user.id = 54321
    reply_message.from_user.username = "targetuser"
    reply_message.from_user.full_name = "Target User"
    reply_message.text = "Mensagem inapropriada"
    mock_update.message.reply_to_message = reply_message
    
    # Configura mongodb_client.add_to_blacklist para retornar None (erro)
    add_to_blacklist_mock = AsyncMock()
    add_to_blacklist_mock.return_value = None
    mock_mongodb.add_to_blacklist = add_to_blacklist_mock
    
    # Executa a função
    await addblacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se add_to_blacklist foi chamado com os parâmetros corretos
    mock_mongodb.add_to_blacklist.assert_called_once()
    
    # Verifica que a reação não foi adicionada à mensagem
    mock_context.bot.set_message_reaction.assert_not_called()
    
    # Verifica se a mensagem de erro foi enviada
    mock_send_temp.assert_called_once_with(
        mock_update,
        mock_context,
        "❌ Erro ao adicionar mensagem à blacklist. Por favor, tente novamente."
    )
    
    # Verifica que a mensagem de comando não foi deletada
    mock_update.message.delete.assert_not_called()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.send_temporary_message")
async def test_blacklist_command_not_admin(mock_send_temp, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /blacklist quando o usuário não é administrador.
    """
    # Configura is_admin para retornar False
    mock_is_admin.return_value = False
    
    # Executa a função
    await blacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se send_temporary_message foi chamado corretamente
    mock_send_temp.assert_called_once_with(
        mock_update,
        mock_context,
        "Apenas administradores podem usar este comando."
    )
    
    # Verifica que nenhuma outra ação foi realizada
    mock_update.message.delete.assert_not_called()
    mock_context.bot.send_message.assert_not_called()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_blacklist_command_current_chat_empty(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /blacklist quando não há mensagens na blacklist do chat atual.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Configura mongodb_client.get_blacklist para retornar lista vazia (usando AsyncMock)
    get_blacklist_mock = AsyncMock()
    get_blacklist_mock.return_value = []
    mock_mongodb.get_blacklist = get_blacklist_mock
    
    # Executa a função
    await blacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se get_blacklist foi chamado com os parâmetros corretos
    mock_mongodb.get_blacklist.assert_called_once_with(mock_update.effective_chat.id)
    
    # Verifica se a mensagem foi enviada corretamente
    mock_context.bot.send_message.assert_called_once_with(
        chat_id=mock_update.effective_chat.id,
        text="📋 BLACKLIST\n\nNão há mensagens na blacklist deste chat."
    )
    
    # Verifica se a mensagem de comando foi deletada
    mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_blacklist_command_with_group_name(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /blacklist com nome de grupo especificado.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Configura args com nome do grupo
    mock_context.args = ["Test", "Group"]
    
    # Configura mongodb_client.get_blacklist_by_group_name (usando AsyncMock)
    item_id = ObjectId()
    mock_item = {
        "_id": item_id,
        "user_name": "User 1",
        "message_id": 101,
        "chat_id": -100987,
        "username": "user1",
        "message_text": "Texto de teste",
        "added_by_name": "Admin GRP",
        "added_at": datetime.now()
    }
    get_blacklist_mock = AsyncMock()
    get_blacklist_mock.return_value = [mock_item]
    mock_mongodb.get_blacklist_by_group_name = get_blacklist_mock
    
    # Executa a função
    await blacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se get_blacklist_by_group_name foi chamado com os parâmetros corretos
    mock_mongodb.get_blacklist_by_group_name.assert_called_once_with("Test Group")
    
    # Verifica se a mensagem foi enviada corretamente
    mock_context.bot.send_message.assert_called_once()
    call_args = mock_context.bot.send_message.call_args[1]
    message_text = call_args["text"]
    
    # Verifica cabeçalho, conteúdo e formato
    assert "<b>📋 BLACKLIST (Parte 1/1)</b>" in message_text
    assert "@user1" in message_text
    assert f"<code>{str(item_id)}</code>" in message_text
    assert "<a href='https://t.me/c/987/101'>Link</a>" in message_text
    assert call_args["parse_mode"] == ParseMode.HTML
    assert "reply_markup" not in call_args
    
    # Verifica se a mensagem de comando foi deletada
    mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_blacklist_command_with_items(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /blacklist quando há mensagens na blacklist (lista curta, 1 página).
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Cria itens da blacklist
    now = datetime.now()
    item1_id = ObjectId("60f1a5b5a9c1e2b3c4d5e6f7")
    item2_id = ObjectId("60f1a5b5a9c1e2b3c4d5e6f8")
    blacklist_items = [
        {
            "_id": item1_id,
            "chat_id": mock_update.effective_chat.id,
            "message_id": 1001,
            "user_id": 54321,
            "user_name": "Target User",
            "username": "targetuser",
            "message_text": "Mensagem inapropriada 1",
            "added_by": 12345,
            "added_by_name": "Admin User",
            "added_at": now
        },
        {
            "_id": item2_id,
            "chat_id": mock_update.effective_chat.id,
            "message_id": 1002,
            "user_id": 54322,
            "user_name": "Another User",
            "username": None,
            "message_text": "Mensagem inapropriada 2",
            "added_by": 12345,
            "added_by_name": "Admin User",
            "added_at": now
        }
    ]
    
    # Configura mongodb_client.get_blacklist para retornar a lista de itens
    get_blacklist_mock = AsyncMock()
    get_blacklist_mock.return_value = blacklist_items
    mock_mongodb.get_blacklist = get_blacklist_mock
    
    # Executa a função
    await blacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se get_blacklist foi chamado com os parâmetros corretos
    mock_mongodb.get_blacklist.assert_called_once_with(mock_update.effective_chat.id)
    
    # Verifica se a mensagem foi enviada corretamente (apenas uma vez para lista curta)
    mock_context.bot.send_message.assert_called_once()
    
    # Verifica os argumentos da chamada
    call_args = mock_context.bot.send_message.call_args[1]
    message_text = call_args["text"]
    
    # Verifica o chat_id
    assert call_args["chat_id"] == mock_update.effective_chat.id
    
    # Verifica o cabeçalho da paginação
    assert "<b>📋 BLACKLIST (Parte 1/1)</b>" in message_text
    
    # Verifica elementos essenciais dos itens
    assert "@targetuser" in message_text
    assert "Another User" in message_text
    assert "Admin User" in message_text
    assert "Mensagem inapropriada 1" in message_text # Verifica se o texto original está lá (antes do escape)
    assert "Mensagem inapropriada 2" in message_text
    
    # Verifica IDs para remoção
    assert f"<code>{str(item1_id)}</code>" in message_text
    assert f"<code>{str(item2_id)}</code>" in message_text
    
    # Formata o chat_id para o link de forma consistente com a implementação
    chat_id_str = str(mock_update.effective_chat.id)
    if chat_id_str.startswith("-100"):
        chat_id_for_link = chat_id_str[4:]
    elif chat_id_str.startswith("-"):
        chat_id_for_link = chat_id_str[1:]
    else:
        chat_id_for_link = chat_id_str
        
    # Verifica se os links foram construídos corretamente
    expected_link1 = f"https://t.me/c/{chat_id_for_link}/1001"
    expected_link2 = f"https://t.me/c/{chat_id_for_link}/1002"
    assert f"<a href='{expected_link1}'>Link</a>" in message_text
    assert f"<a href='{expected_link2}'>Link</a>" in message_text
    
    # Verifica modo de parse e preview
    assert call_args["parse_mode"] == ParseMode.HTML
    assert call_args["disable_web_page_preview"] is True
    
    # Verifica que reply_markup (botões) não foi enviado
    assert "reply_markup" not in call_args
    
    # Verifica se a mensagem de comando foi deletada
    mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_blacklist_command_with_group_username(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /blacklist quando é executado com o username de um grupo.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Configura os argumentos do comando
    mock_context.args = ["@testgroup"]
    
    # Configura o mock para get_blacklist_by_group_name
    item_id = ObjectId("60f1a5b5a9c1e2b3c4d5e6f7")
    mock_blacklist = [
        {
            "_id": item_id,
            "chat_id": -10012345,
            "message_id": 67890,
            "user_id": 54321,
            "user_name": "Test User",
            "username": "testuser",
            "message_text": "Mensagem inapropriada",
            "added_by": 98765,
            "added_by_name": "Admin User",
            "added_at": datetime.now()
        }
    ]
    get_blacklist_by_group_name_mock = AsyncMock()
    get_blacklist_by_group_name_mock.return_value = mock_blacklist
    mock_mongodb.get_blacklist_by_group_name = get_blacklist_by_group_name_mock
    
    # Executa a função
    await blacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se get_blacklist_by_group_name foi chamado com o username correto
    mock_mongodb.get_blacklist_by_group_name.assert_called_once_with("testgroup")
    
    # Verifica se a mensagem foi enviada corretamente
    mock_context.bot.send_message.assert_called_once()
    message_text = mock_context.bot.send_message.call_args[1]["text"]
    assert "BLACKLIST (Parte 1/1)" in message_text
    assert "@testuser" in message_text
    assert "Admin User" in message_text
    assert "Mensagem inapropriada" in message_text
    assert f"<code>{str(item_id)}</code>" in message_text
    assert "<a href='https://t.me/c/12345/67890'>Link</a>" in message_text
    
    # Verifica se a mensagem de comando foi deletada
    mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_blacklist_command_with_group_username_not_found(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /blacklist quando é executado com o username de um grupo que não existe.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Configura os argumentos do comando
    mock_context.args = ["@NonExistentGroup"]
    
    # Configura o mock para get_blacklist_by_group_name retornar lista vazia (usando AsyncMock)
    get_blacklist_by_group_name_mock = AsyncMock()
    get_blacklist_by_group_name_mock.return_value = []
    mock_mongodb.get_blacklist_by_group_name = get_blacklist_by_group_name_mock
    
    # Executa a função
    await blacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se get_blacklist_by_group_name foi chamado com o username correto
    mock_mongodb.get_blacklist_by_group_name.assert_called_once_with("NonExistentGroup")
    
    # Verifica se a mensagem foi enviada corretamente (sem verificar parse_mode)
    mock_context.bot.send_message.assert_called_once_with(
        chat_id=mock_update.effective_chat.id,
        text="❌ Grupo não encontrado.\n\n"
             "Certifique-se de que:\n"
             "1. O nome do grupo está correto\n"
             "2. O bot está no grupo"
    )
    
    # Verifica se a mensagem de comando foi deletada
    mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
async def test_rmblacklist_command_not_admin():
    """
    Testa o comando /rmblacklist quando o usuário não é administrador.
    """
    # Mock para Update e Context
    mock_update = MagicMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Mock para user, chat e message
    mock_user = MagicMock(spec=User)
    mock_user.id = 12345
    mock_user.full_name = "Test User"
    
    mock_chat = MagicMock(spec=Chat)
    mock_chat.id = -1001234567
    
    mock_message = MagicMock(spec=Message)
    mock_message.message_id = 789
    
    # Configura o mock_update
    mock_update.effective_user = mock_user
    mock_update.effective_chat = mock_chat
    mock_update.message = mock_message
    
    # Configura o mock_context
    mock_context.args = ["60f1a5b5a9c1e2b3c4d5e6f7"]
    
    # Mock para is_admin
    with patch("src.bot.blacklist_handlers.is_admin") as mock_is_admin, \
         patch("src.bot.blacklist_handlers.send_temporary_message") as mock_send_temporary_message:
        
        # Configura is_admin para retornar False
        mock_is_admin.return_value = False
        
        # Executa a função
        await rmblacklist_command(mock_update, mock_context)
        
        # Verifica se is_admin foi chamado corretamente
        mock_is_admin.assert_called_once_with(mock_update, mock_context)
        
        # Verifica se a mensagem de erro foi enviada
        mock_send_temporary_message.assert_called_once_with(
            mock_update, 
            mock_context, 
            "Apenas administradores podem usar este comando."
        )

@pytest.mark.asyncio
async def test_rmblacklist_command_no_args():
    """
    Testa o comando /rmblacklist quando não são fornecidos argumentos.
    """
    # Mock para Update e Context
    mock_update = MagicMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Mock para user, chat e message
    mock_user = MagicMock(spec=User)
    mock_user.id = 12345
    mock_user.full_name = "Test User"
    
    mock_chat = MagicMock(spec=Chat)
    mock_chat.id = -1001234567
    
    mock_message = MagicMock(spec=Message)
    mock_message.message_id = 789
    
    # Configura o mock_update
    mock_update.effective_user = mock_user
    mock_update.effective_chat = mock_chat
    mock_update.message = mock_message
    
    # Configura o mock_context sem argumentos
    mock_context.args = []
    
    # Mock para is_admin
    with patch("src.bot.blacklist_handlers.is_admin") as mock_is_admin, \
         patch("src.bot.blacklist_handlers.send_temporary_message") as mock_send_temporary_message:
        
        # Configura is_admin para retornar True
        mock_is_admin.return_value = True
        
        # Executa a função
        await rmblacklist_command(mock_update, mock_context)
        
        # Verifica se is_admin foi chamado corretamente
        mock_is_admin.assert_called_once_with(mock_update, mock_context)
        
        # Verifica se a mensagem de erro foi enviada
        mock_send_temporary_message.assert_called_once()
        args = mock_send_temporary_message.call_args[0]
        assert args[0] == mock_update
        assert args[1] == mock_context
        assert "forneça o ID" in args[2]
        assert mock_send_temporary_message.call_args[1]["parse_mode"] == ParseMode.MARKDOWN

@pytest.mark.asyncio
async def test_rmblacklist_command_success():
    """
    Testa o comando /rmblacklist quando tudo funciona corretamente.
    """
    # Mock para Update e Context
    mock_update = MagicMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Mock para user, chat e message
    mock_user = MagicMock(spec=User)
    mock_user.id = 12345
    mock_user.full_name = "Test User"
    
    mock_chat = MagicMock(spec=Chat)
    mock_chat.id = -1001234567
    
    mock_message = MagicMock(spec=Message)
    mock_message.message_id = 789
    
    # Configura o mock_update
    mock_update.effective_user = mock_user
    mock_update.effective_chat = mock_chat
    mock_update.message = mock_message
    
    # ID do item a ser removido
    item_id = "60f1a5b5a9c1e2b3c4d5e6f7"
    
    # Configura o mock_context com o ID
    mock_context.args = [item_id]
    
    # Mock para is_admin e mongodb_client
    with patch("src.bot.blacklist_handlers.is_admin") as mock_is_admin, \
         patch("src.bot.blacklist_handlers.mongodb_client") as mock_mongodb, \
         patch("src.bot.blacklist_handlers.send_temporary_message") as mock_send_temporary_message:
        
        # Configura is_admin para retornar True
        mock_is_admin.return_value = True
        
        # Configura remove_from_blacklist para retornar True
        mock_mongodb.remove_from_blacklist = AsyncMock()
        mock_mongodb.remove_from_blacklist.return_value = True
        
        # Executa a função
        await rmblacklist_command(mock_update, mock_context)
        
        # Verifica se is_admin foi chamado corretamente
        mock_is_admin.assert_called_once_with(mock_update, mock_context)
        
        # Verifica se remove_from_blacklist foi chamado com os parâmetros corretos
        mock_mongodb.remove_from_blacklist.assert_called_once_with(item_id)
        
        # Verifica que nenhuma mensagem foi enviada
        mock_send_temporary_message.assert_not_called()
        
        # Verifica se a mensagem de comando foi deletada
        mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
async def test_rmblacklist_command_error():
    """
    Testa o comando /rmblacklist quando ocorre um erro ao remover o item.
    """
    # Mock para Update e Context
    mock_update = MagicMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Mock para user, chat e message
    mock_user = MagicMock(spec=User)
    mock_user.id = 12345
    mock_user.full_name = "Test User"
    
    mock_chat = MagicMock(spec=Chat)
    mock_chat.id = -1001234567
    
    mock_message = MagicMock(spec=Message)
    mock_message.message_id = 789
    
    # Configura o mock_update
    mock_update.effective_user = mock_user
    mock_update.effective_chat = mock_chat
    mock_update.message = mock_message
    
    # ID do item a ser removido
    item_id = "60f1a5b5a9c1e2b3c4d5e6f7"
    
    # Configura o mock_context com o ID
    mock_context.args = [item_id]
    
    # Mock para is_admin e mongodb_client
    with patch("src.bot.blacklist_handlers.is_admin") as mock_is_admin, \
         patch("src.bot.blacklist_handlers.mongodb_client") as mock_mongodb, \
         patch("src.bot.blacklist_handlers.send_temporary_message") as mock_send_temporary_message:
        
        # Configura is_admin para retornar True
        mock_is_admin.return_value = True
        
        # Configura remove_from_blacklist para retornar False (erro)
        mock_mongodb.remove_from_blacklist = AsyncMock()
        mock_mongodb.remove_from_blacklist.return_value = False
        
        # Executa a função
        await rmblacklist_command(mock_update, mock_context)
        
        # Verifica se is_admin foi chamado corretamente
        mock_is_admin.assert_called_once_with(mock_update, mock_context)
        
        # Verifica se remove_from_blacklist foi chamado com os parâmetros corretos
        mock_mongodb.remove_from_blacklist.assert_called_once_with(item_id)
        
        # Verifica se a mensagem de erro foi enviada
        mock_send_temporary_message.assert_called_once()
        args = mock_send_temporary_message.call_args[0]
        assert args[0] == mock_update
        assert args[1] == mock_context
        assert "❌" in args[2]
        
        # Verifica se a mensagem de comando foi deletada
        mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
async def test_rmblacklist_command_with_link():
    """
    Testa o comando /rmblacklist com um link de mensagem ao invés de ID.
    """
    # Mock para Update e Context
    mock_update = MagicMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Mock para user, chat e message
    mock_user = MagicMock(spec=User)
    mock_user.id = 12345
    mock_user.full_name = "Test User"
    
    mock_chat = MagicMock(spec=Chat)
    mock_chat.id = -1001234567
    
    mock_message = MagicMock(spec=Message)
    mock_message.message_id = 789
    
    # Configura o mock_update
    mock_update.effective_user = mock_user
    mock_update.effective_chat = mock_chat
    mock_update.message = mock_message
    
    # Link da mensagem a ser removida
    message_link = "https://t.me/c/2288213607/1452"
    
    # Configura o mock_context com o link
    mock_context.args = [message_link]
    
    # Mock para is_admin e mongodb_client
    with patch("src.bot.blacklist_handlers.is_admin") as mock_is_admin, \
         patch("src.bot.blacklist_handlers.mongodb_client") as mock_mongodb, \
         patch("src.bot.blacklist_handlers.send_temporary_message") as mock_send_temporary_message:
        
        # Configura is_admin para retornar True
        mock_is_admin.return_value = True
        
        # Configura remove_from_blacklist_by_link para retornar True
        mock_mongodb.remove_from_blacklist_by_link = AsyncMock()
        mock_mongodb.remove_from_blacklist_by_link.return_value = True
        
        # Executa a função
        await rmblacklist_command(mock_update, mock_context)
        
        # Verifica se is_admin foi chamado corretamente
        mock_is_admin.assert_called_once_with(mock_update, mock_context)
        
        # Verifica se o método correto foi chamado
        mock_mongodb.remove_from_blacklist_by_link.assert_called_once_with(message_link)
        mock_mongodb.remove_from_blacklist.assert_not_called()
        
        # Verifica que nenhuma mensagem foi enviada
        mock_send_temporary_message.assert_not_called()
        
        # Verifica se a mensagem de comando foi deletada
        mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_blacklist_button_success(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o handler de botão da blacklist quando a remoção é bem-sucedida.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Configura o mock para remove_from_blacklist retornar True
    mock_mongodb.remove_from_blacklist = AsyncMock()
    mock_mongodb.remove_from_blacklist.return_value = True
    
    # Configura o mock para get_blacklist retornar uma lista vazia
    mock_mongodb.get_blacklist = AsyncMock()
    mock_mongodb.get_blacklist.return_value = []
    
    # Configura o callback query
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.data = "rmblacklist_123456"
    
    # Executa a função
    await blacklist_button(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    assert mock_is_admin.call_count == 2
    mock_is_admin.assert_has_calls([
        call(mock_update, mock_context),
        call(mock_update, mock_context)
    ])
    
    # Verifica se remove_from_blacklist foi chamado com o ID correto
    mock_mongodb.remove_from_blacklist.assert_called_once_with("123456")
    
    # Verifica se a mensagem de sucesso foi enviada
    mock_update.callback_query.answer.assert_called_once_with("Item removido da blacklist")
    
    # Verifica se blacklist_command foi chamado para atualizar a lista
    mock_context.bot.send_message.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_blacklist_button_not_admin(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o handler de botão da blacklist quando o usuário não é admin.
    """
    # Configura is_admin para retornar False
    mock_is_admin.return_value = False
    
    # Configura o callback query
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.data = "rmblacklist_123456"
    
    # Executa a função
    await blacklist_button(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se a mensagem de erro foi enviada
    mock_update.callback_query.answer.assert_called_once_with("Apenas administradores podem remover itens da blacklist")
    
    # Verifica se remove_from_blacklist não foi chamado
    mock_mongodb.remove_from_blacklist.assert_not_called()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_blacklist_button_error(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o handler de botão da blacklist quando ocorre um erro na remoção.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Configura o mock para remove_from_blacklist retornar False
    mock_mongodb.remove_from_blacklist = AsyncMock()
    mock_mongodb.remove_from_blacklist.return_value = False
    
    # Configura o callback query
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.data = "rmblacklist_123456"
    
    # Executa a função
    await blacklist_button(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se remove_from_blacklist foi chamado com o ID correto
    mock_mongodb.remove_from_blacklist.assert_called_once_with("123456")
    
    # Verifica se a mensagem de erro foi enviada
    mock_update.callback_query.answer.assert_called_once_with("Erro ao remover item da blacklist")
    
    # Verifica se blacklist_command não foi chamado
    mock_context.bot.send_message.assert_not_called()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_blacklist_command_with_special_characters(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /blacklist quando há mensagens com caracteres especiais na blacklist.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Cria itens da blacklist com caracteres especiais
    now = datetime.now()
    item_id = ObjectId("60f1a5b5a9c1e2b3c4d5e6f7")
    blacklist_items = [
        {
            "_id": item_id,
            "chat_id": mock_update.effective_chat.id,
            "message_id": 1001,
            "user_id": 54321,
            "user_name": "Test User",
            "username": "testuser",
            "message_text": "_teste_ *markdown* [link] <script>alert('xss')</script>",
            "added_by": 12345,
            "added_by_name": "Admin (Test)",
            "added_at": now
        }
    ]
    
    # Configura mongodb_client.get_blacklist para retornar a lista de itens (usando AsyncMock)
    get_blacklist_mock = AsyncMock()
    get_blacklist_mock.return_value = blacklist_items
    mock_mongodb.get_blacklist = get_blacklist_mock
    
    # Executa a função
    await blacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se get_blacklist foi chamado com os parâmetros corretos
    mock_mongodb.get_blacklist.assert_called_once_with(mock_update.effective_chat.id)
    
    # Verifica se a mensagem foi enviada corretamente
    mock_context.bot.send_message.assert_called_once()
    message_text = mock_context.bot.send_message.call_args[1]["text"]
    
    # Verifica se os caracteres especiais foram tratados corretamente (escapados por escape_html)
    assert "_teste_" in message_text
    assert "*markdown*" in message_text
    assert "[link]" in message_text
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in message_text
    assert f"<code>{str(item_id)}</code>" in message_text
    assert "<a href='https://t.me/c/" in message_text
    
    # Verifica se a mensagem de comando foi deletada
    mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
@patch("asyncio.sleep", return_value=None)
async def test_blacklist_command_with_long_message(mock_sleep, mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /blacklist quando a lista é longa e requer paginação.
    Verifica também o truncamento do texto da mensagem individual.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Define um texto base longo para cada item
    base_text = "X" * 300
    
    # Calcula quantos itens cabem aproximadamente por página (estimativa grosseira)
    # Formato por item: ~ "N. <b>Usuário:</b> ... <b>ID:</b> <code>...</code>\n"
    # Header: ~ 50 chars
    # Item formatado: ~ 200 chars (sem o texto) + len(escaped_text) + len(id)
    # Texto truncado: 103 chars (100 + ...)
    # ID: 24 chars
    # Total por item: ~ 200 + 103 + 24 = ~330 chars
    # Limite: 4000. Header: 50. Disponível: 3950
    # Itens por página: ~ 3950 / 330 = ~11-12 itens
    
    # Cria uma lista longa (ex: 25 itens, deve gerar 3 páginas)
    num_items = 25
    blacklist_items = []
    now = datetime.now()
    expected_ids = []
    for i in range(num_items):
        item_id = ObjectId()
        expected_ids.append(str(item_id))
        blacklist_items.append({
            "_id": item_id,
            "chat_id": mock_update.effective_chat.id,
            "message_id": 1000 + i,
            "user_id": 50000 + i,
            "user_name": f"Test User {i}",
            "username": f"testuser{i}",
            "message_text": f"{base_text} Item {i}",
            "added_by": 12345,
            "added_by_name": "Admin User",
            "added_at": now
        })
    
    # Configura mongodb_client.get_blacklist para retornar a lista longa
    get_blacklist_mock = AsyncMock()
    get_blacklist_mock.return_value = blacklist_items
    mock_mongodb.get_blacklist = get_blacklist_mock
    
    # Executa a função
    await blacklist_command(mock_update, mock_context)
    
    # Verifica se get_blacklist foi chamado
    mock_mongodb.get_blacklist.assert_called_once_with(mock_update.effective_chat.id)
    
    # Verifica quantas chamadas a send_message foram feitas (deve ser > 1)
    assert mock_context.bot.send_message.call_count > 1 
    
    # Calcula o número esperado de páginas (arredondando para cima)
    # Este cálculo é apenas uma verificação, a lógica real está no código
    # A lógica de paginação no código é baseada em comprimento, não em contagem de itens
    # Por isso, verificamos > 1 e os cabeçalhos
    calls = mock_context.bot.send_message.call_args_list
    total_parts = len(calls)
    
    # Verifica o cabeçalho e conteúdo da primeira parte
    first_call_args = calls[0][1]
    first_message_text = first_call_args["text"]
    assert f"<b>📋 BLACKLIST (Parte 1/{total_parts})</b>" in first_message_text
    assert f"<b>Usuário:</b> @testuser0" in first_message_text
    assert f"<i>{escape_html(base_text[:100] + '...')}</i>" in first_message_text
    assert f"<code>{expected_ids[0]}</code>" in first_message_text
    assert first_call_args["parse_mode"] == ParseMode.HTML
    assert first_call_args["disable_web_page_preview"] is True
    assert "reply_markup" not in first_call_args

    # Verifica o cabeçalho e conteúdo da última parte
    last_call_args = calls[-1][1]
    last_message_text = last_call_args["text"]
    assert f"<b>📋 BLACKLIST (Parte {total_parts}/{total_parts})</b>" in last_message_text
    assert f"<b>Usuário:</b> @testuser{num_items - 1}" in last_message_text
    assert f"<i>{escape_html(base_text[:100] + '...')}</i>" in last_message_text
    assert f"<code>{expected_ids[-1]}</code>" in last_message_text
    assert last_call_args["parse_mode"] == ParseMode.HTML
    assert last_call_args["disable_web_page_preview"] is True
    assert "reply_markup" not in last_call_args

    # Verifica se asyncio.sleep foi chamado entre as mensagens
    assert mock_sleep.call_count == total_parts - 1
    mock_sleep.assert_called_with(0.5)

    # Verifica se a mensagem de comando foi deletada
    mock_update.message.delete.assert_called_once() 

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.send_temporary_message")
async def test_ban_blacklist_command_not_admin(mock_send_temp, mock_is_admin, mock_update, mock_context):
    """Testa /ban_blacklist quando o usuário não é admin."""
    mock_is_admin.return_value = False
    mock_context.args = ["Some Group"]

    await ban_blacklist_command(mock_update, mock_context)

    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    mock_send_temp.assert_called_once_with(mock_update, mock_context, "Apenas administradores do bot podem usar este comando.")
    mock_context.bot.send_message.assert_not_called() # Nenhuma mensagem de processamento

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.send_temporary_message")
async def test_ban_blacklist_command_no_args(mock_send_temp, mock_is_admin, mock_update, mock_context):
    """Testa /ban_blacklist sem argumentos."""
    mock_is_admin.return_value = True
    mock_context.args = [] # Sem argumentos

    await ban_blacklist_command(mock_update, mock_context)

    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    mock_send_temp.assert_called_once_with(mock_update, mock_context, "Uso: /ban_blacklist <nome_do_grupo>")
    mock_context.bot.send_message.assert_not_called()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_ban_blacklist_command_group_not_found(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """Testa /ban_blacklist quando o grupo não é encontrado."""
    mock_is_admin.return_value = True
    mock_context.args = ["NonExistent Group"]
    
    # Mock get_chat_id_by_group_name retornando None
    mock_mongodb.get_chat_id_by_group_name = AsyncMock(return_value=None)
    
    # Mock para a mensagem de processamento
    mock_processing_message = AsyncMock(spec=Message)
    mock_context.bot.send_message.return_value = mock_processing_message

    await ban_blacklist_command(mock_update, mock_context)

    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    mock_mongodb.get_chat_id_by_group_name.assert_called_once_with("NonExistent Group")
    mock_context.bot.send_message.assert_called_once() # Chamada para msg inicial
    mock_processing_message.edit_text.assert_called_once_with("❌ Grupo 'NonExistent Group' não encontrado ou não monitorado ativamente.")
    mock_context.bot.ban_chat_member.assert_not_called()
    mock_mongodb.get_blacklist.assert_not_called()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_ban_blacklist_command_empty_blacklist(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """Testa /ban_blacklist quando a blacklist do grupo está vazia."""
    group_name = "Empty Blacklist Group"
    target_chat_id = -100111222
    mock_is_admin.return_value = True
    mock_context.args = [group_name]
    
    # Mock get_chat_id_by_group_name retornando ID
    mock_mongodb.get_chat_id_by_group_name = AsyncMock(return_value=target_chat_id)
    # Mock get_blacklist retornando lista vazia
    mock_mongodb.get_blacklist = AsyncMock(return_value=[])

    # Mock para a mensagem de processamento
    mock_processing_message = AsyncMock(spec=Message)
    mock_context.bot.send_message.return_value = mock_processing_message

    await ban_blacklist_command(mock_update, mock_context)

    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    mock_mongodb.get_chat_id_by_group_name.assert_called_once_with(group_name)
    mock_mongodb.get_blacklist.assert_called_once_with(target_chat_id)
    mock_context.bot.send_message.assert_called_once() # Chamada para msg inicial
    mock_processing_message.edit_text.assert_called_once_with(f"✅ A blacklist para o grupo '{group_name}' (ID: {target_chat_id}) já está vazia.")
    mock_context.bot.ban_chat_member.assert_not_called()
    mock_mongodb.remove_blacklist_items_by_ids.assert_not_called()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
@patch("asyncio.sleep", return_value=None) # Mock asyncio.sleep
async def test_ban_blacklist_command_success_all(mock_sleep, mock_mongodb, mock_is_admin, mock_update, mock_context):
    """Testa /ban_blacklist com sucesso para todos os usuários."""
    group_name = "Clean Group"
    target_chat_id = -100333444
    mock_is_admin.return_value = True
    mock_context.args = [group_name]

    # Mock get_chat_id_by_group_name
    mock_mongodb.get_chat_id_by_group_name = AsyncMock(return_value=target_chat_id)

    # Mock blacklist com 2 usuários (3 entradas, 1 duplicado)
    user1_id = 50001
    user2_id = 50002
    item1_id = ObjectId()
    item2_id = ObjectId()
    item3_id = ObjectId()
    blacklist_entries = [
        {"_id": item1_id, "chat_id": target_chat_id, "user_id": user1_id, "user_name": "User One"},
        {"_id": item2_id, "chat_id": target_chat_id, "user_id": user2_id, "user_name": "User Two"},
        {"_id": item3_id, "chat_id": target_chat_id, "user_id": user1_id, "user_name": "User One Again"} # Entrada duplicada user1
    ]
    mock_mongodb.get_blacklist = AsyncMock(return_value=blacklist_entries)

    # Mock ban_chat_member retornando True
    mock_context.bot.ban_chat_member = AsyncMock(return_value=True)

    # Mock remove_blacklist_items_by_ids
    mock_mongodb.remove_blacklist_items_by_ids = AsyncMock(return_value=3) # 3 itens removidos

    # Mock para a mensagem de processamento
    mock_processing_message = AsyncMock(spec=Message)
    mock_context.bot.send_message.return_value = mock_processing_message

    await ban_blacklist_command(mock_update, mock_context)

    # Verificações
    mock_mongodb.get_chat_id_by_group_name.assert_called_once_with(group_name)
    mock_mongodb.get_blacklist.assert_called_once_with(target_chat_id)
    assert mock_context.bot.ban_chat_member.call_count == 2 # Chamado para 2 usuários únicos
    mock_context.bot.ban_chat_member.assert_has_calls([
        call(chat_id=target_chat_id, user_id=user1_id),
        call(chat_id=target_chat_id, user_id=user2_id)
    ], any_order=True)
    assert mock_sleep.call_count == 2 # Um sleep após cada ban
    mock_mongodb.remove_blacklist_items_by_ids.assert_called_once_with([item1_id, item3_id, item2_id]) # Todos os IDs devem ser removidos
    
    # Verifica a mensagem final
    mock_processing_message.edit_text.assert_called_with(
        f"<b>📊 Relatório de Banimento da Blacklist</b>\n\n"
        f"<b>Grupo:</b> {group_name} (ID: <code>{target_chat_id}</code>)\n"
        f"<b>Usuários únicos na blacklist:</b> 2\n"
        f"<b>Banidos com sucesso:</b> ✅ 2\n"
        f"<b>Falhas ao banir:</b> ❌ 0\n"
        f"<b>Itens removidos da blacklist:</b> 🗑️ 3\n"
        f"<i>(Apenas itens de usuários banidos com sucesso foram removidos)</i>\n",
        parse_mode=ParseMode.HTML
    )

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
@patch("asyncio.sleep", return_value=None) # Mock asyncio.sleep
async def test_ban_blacklist_command_partial_failure(mock_sleep, mock_mongodb, mock_is_admin, mock_update, mock_context):
    """Testa /ban_blacklist com falha para alguns usuários."""
    group_name = "Mixed Group"
    target_chat_id = -100555666
    mock_is_admin.return_value = True
    mock_context.args = [group_name]

    # Mock get_chat_id_by_group_name
    mock_mongodb.get_chat_id_by_group_name = AsyncMock(return_value=target_chat_id)

    # Mock blacklist com 3 usuários
    user1_id = 50001 # Sucesso
    user2_id = 50002 # Falha (BadRequest)
    user3_id = 50003 # Sucesso
    item1_id = ObjectId()
    item2_id = ObjectId()
    item3_id = ObjectId()
    blacklist_entries = [
        {"_id": item1_id, "chat_id": target_chat_id, "user_id": user1_id, "user_name": "User One"},
        {"_id": item2_id, "chat_id": target_chat_id, "user_id": user2_id, "user_name": "User Two"},
        {"_id": item3_id, "chat_id": target_chat_id, "user_id": user3_id, "user_name": "User Three"}
    ]
    mock_mongodb.get_blacklist = AsyncMock(return_value=blacklist_entries)

    # Mock ban_chat_member com falha para user2
    async def ban_side_effect(chat_id, user_id):
        if user_id == user2_id:
            raise BadRequest("User not found")
        return True
    mock_context.bot.ban_chat_member = AsyncMock(side_effect=ban_side_effect)

    # Mock remove_blacklist_items_by_ids (só remove itens de user1 e user3)
    mock_mongodb.remove_blacklist_items_by_ids = AsyncMock(return_value=2) 

    # Mock para a mensagem de processamento
    mock_processing_message = AsyncMock(spec=Message)
    mock_context.bot.send_message.return_value = mock_processing_message

    await ban_blacklist_command(mock_update, mock_context)

    # Verificações
    mock_mongodb.get_chat_id_by_group_name.assert_called_once_with(group_name)
    mock_mongodb.get_blacklist.assert_called_once_with(target_chat_id)
    assert mock_context.bot.ban_chat_member.call_count == 3 # Chamado para 3 usuários únicos
    assert mock_sleep.call_count == 3
    # Verifica se tentou remover apenas itens de user1 e user3
    mock_mongodb.remove_blacklist_items_by_ids.assert_called_once_with([item1_id, item3_id])
    
    # Verifica a mensagem final (precisa checar o conteúdo)
    assert mock_processing_message.edit_text.call_count == 2 # Corrigido: Verifica 2 chamadas
    
    # Pega os argumentos da *última* chamada a edit_text
    final_call_args = mock_processing_message.edit_text.call_args_list[-1][0]
    final_kwargs = mock_processing_message.edit_text.call_args_list[-1][1]
    final_text = final_call_args[0]
    
    # Verifica o conteúdo da última mensagem
    assert f"<b>Grupo:</b> {escape_html(group_name)}" in final_text # Usa escape_html para comparar
    assert "<b>Usuários únicos na blacklist:</b> 3" in final_text
    assert "<b>Banidos com sucesso:</b> ✅ 2" in final_text
    assert "<b>Falhas ao banir:</b> ❌ 1" in final_text
    assert "<b>Itens removidos da blacklist:</b> 🗑️ 2" in final_text
    assert "<b>Detalhes das Falhas:</b>" in final_text
    # Verifica a falha específica (escape_html aplicado ao nome do usuário)
    expected_failed_user_display = escape_html(f"User Two ({user2_id})")
    expected_failed_error = escape_html("User not found")
    assert f"- {expected_failed_user_display}: {expected_failed_error}" in final_text
    assert final_kwargs.get("parse_mode") == ParseMode.HTML # Verifica parse_mode na última chamada 