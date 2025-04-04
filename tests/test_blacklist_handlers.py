"""
Testes para os handlers de blacklist.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from telegram import Update, User, Chat, Message, ChatMember, ReactionTypeEmoji, BotCommand
from telegram.constants import ChatType, ParseMode, ReactionType
from telegram.ext import ContextTypes
from datetime import datetime
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId

from src.bot.blacklist_handlers import addblacklist_command, blacklist_command, rmblacklist_command, blacklist_button

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
    
    # Configura mongodb_client.get_blacklist para retornar lista vazia
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
        text="📋 *BLACKLIST*\n\nNão há mensagens na blacklist deste chat.",
        parse_mode=ParseMode.MARKDOWN
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
    mock_context.args = ["GYM", "NATION"]
    
    # Configura mongodb_client.get_blacklist_by_group_name para retornar lista vazia
    get_blacklist_by_group_name_mock = AsyncMock()
    get_blacklist_by_group_name_mock.return_value = []
    mock_mongodb.get_blacklist_by_group_name = get_blacklist_by_group_name_mock
    
    # Executa a função
    await blacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se get_blacklist_by_group_name foi chamado com os parâmetros corretos
    mock_mongodb.get_blacklist_by_group_name.assert_called_once_with("GYM NATION")
    
    # Verifica se a mensagem foi enviada corretamente
    mock_context.bot.send_message.assert_called_once_with(
        chat_id=mock_update.effective_chat.id,
        text="❌ Grupo não encontrado.\n\n"
             "Certifique-se de que:\n"
             "1. O nome do grupo está correto\n"
             "2. O bot está no grupo",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Verifica se a mensagem de comando foi deletada
    mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_blacklist_command_with_items(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /blacklist quando há mensagens na blacklist.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Cria itens da blacklist
    now = datetime.now()
    blacklist_items = [
        {
            "_id": ObjectId("60f1a5b5a9c1e2b3c4d5e6f7"),
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
            "_id": ObjectId("60f1a5b5a9c1e2b3c4d5e6f8"),
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
    
    # Verifica se a mensagem foi enviada corretamente
    # Checamos apenas se o bot.send_message foi chamado uma vez
    # e o chat_id está correto, já que o conteúdo da mensagem é muito longo e variável
    mock_context.bot.send_message.assert_called_once()
    
    # Verifica os elementos essenciais da mensagem
    message_text = mock_context.bot.send_message.call_args[1]["text"]
    
    # Formata o chat_id para o link de forma consistente com a implementação
    chat_id_str = str(mock_update.effective_chat.id)
    if chat_id_str.startswith("-100"):
        chat_id_for_link = chat_id_str[4:]  # Remove os primeiros 4 caracteres ("-100")
    elif chat_id_str.startswith("-"):
        chat_id_for_link = chat_id_str[1:]  # Remove apenas o hífen
    else:
        chat_id_for_link = chat_id_str
    
    assert mock_context.bot.send_message.call_args[1]["chat_id"] == mock_update.effective_chat.id
    assert "BLACKLIST" in message_text
    assert "@targetuser" in message_text
    assert "Another User" in message_text
    assert "Admin User" in message_text
    
    # Verifica se os links foram construídos corretamente
    expected_link1 = f"https://t.me/c/{chat_id_for_link}/1001"
    expected_link2 = f"https://t.me/c/{chat_id_for_link}/1002"
    assert expected_link1 in message_text
    assert expected_link2 in message_text
    
    assert mock_context.bot.send_message.call_args[1]["parse_mode"] == ParseMode.MARKDOWN
    assert mock_context.bot.send_message.call_args[1]["disable_web_page_preview"] is True
    
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
    mock_blacklist = [
        {
            "_id": "60f1a5b5a9c1e2b3c4d5e6f7",
            "chat_id": 12345,
            "message_id": 67890,
            "user_id": 54321,
            "user_name": "Test User",
            "username": "testuser",
            "message_text": "Mensagem inapropriada",
            "added_by": 98765,
            "added_by_name": "Admin User",
            "created_at": datetime.now()
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
    assert "BLACKLIST" in message_text
    assert "@testuser" in message_text
    assert "Admin User" in message_text
    assert "Mensagem inapropriada" in message_text
    assert "Ver mensagem" in message_text
    assert "https://t.me/c/12345/67890" in message_text
    
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
    mock_context.args = ["@nonexistentgroup"]
    
    # Configura o mock para get_blacklist_by_group_name retornar lista vazia
    get_blacklist_by_group_name_mock = AsyncMock()
    get_blacklist_by_group_name_mock.return_value = []
    mock_mongodb.get_blacklist_by_group_name = get_blacklist_by_group_name_mock
    
    # Executa a função
    await blacklist_command(mock_update, mock_context)
    
    # Verifica se is_admin foi chamado corretamente
    mock_is_admin.assert_called_once_with(mock_update, mock_context)
    
    # Verifica se get_blacklist_by_group_name foi chamado com o username correto
    mock_mongodb.get_blacklist_by_group_name.assert_called_once_with("nonexistentgroup")
    
    # Verifica se a mensagem foi enviada corretamente
    mock_context.bot.send_message.assert_called_once_with(
        chat_id=mock_update.effective_chat.id,
        text="❌ Grupo não encontrado.\n\n"
             "Certifique-se de que:\n"
             "1. O nome do grupo está correto\n"
             "2. O bot está no grupo",
        parse_mode=ParseMode.MARKDOWN
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
    blacklist_items = [
        {
            "_id": ObjectId("60f1a5b5a9c1e2b3c4d5e6f7"),
            "chat_id": mock_update.effective_chat.id,
            "message_id": 1001,
            "user_id": 54321,
            "user_name": "Test User",
            "username": "testuser",
            "message_text": "_teste_ *markdown* [link]",
            "added_by": 12345,
            "added_by_name": "Admin (Test)",
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
    
    # Verifica se a mensagem foi enviada corretamente
    mock_context.bot.send_message.assert_called_once()
    message_text = mock_context.bot.send_message.call_args[1]["text"]
    
    # Verifica se os caracteres especiais foram escapados corretamente
    assert "\\_teste\\_" in message_text
    assert "\\*markdown\\*" in message_text
    assert "\\[link\\]" in message_text
    assert "Admin \\(Test\\)" in message_text
    
    # Verifica se a mensagem de comando foi deletada
    mock_update.message.delete.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.blacklist_handlers.is_admin")
@patch("src.bot.blacklist_handlers.mongodb_client")
async def test_blacklist_command_with_long_message(mock_mongodb, mock_is_admin, mock_update, mock_context):
    """
    Testa o comando /blacklist quando há mensagens longas que precisam ser truncadas.
    """
    # Configura is_admin para retornar True
    mock_is_admin.return_value = True
    
    # Cria uma mensagem longa com mais de 50 caracteres
    long_message = "Esta é uma mensagem muito longa que precisa ser truncada pois tem mais de 50 caracteres"
    
    # Cria itens da blacklist
    now = datetime.now()
    blacklist_items = [
        {
            "_id": ObjectId("60f1a5b5a9c1e2b3c4d5e6f7"),
            "chat_id": mock_update.effective_chat.id,
            "message_id": 1001,
            "user_id": 54321,
            "user_name": "Test User",
            "username": "testuser",
            "message_text": long_message,
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
    
    # Verifica se a mensagem foi enviada corretamente
    mock_context.bot.send_message.assert_called_once()
    message_text = mock_context.bot.send_message.call_args[1]["text"]
    
    # Verifica se a mensagem foi truncada corretamente
    truncated_message = "Esta é uma mensagem muito longa que precisa ser..."
    assert truncated_message in message_text
    
    # Verifica se a mensagem de comando foi deletada
    mock_update.message.delete.assert_called_once() 