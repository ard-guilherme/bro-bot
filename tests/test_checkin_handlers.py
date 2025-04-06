"""
Testes para os handlers de check-in.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, ANY, MagicMock
from telegram import Update, User, Chat, Message, PhotoSize
from telegram.ext import ContextTypes, Application
from datetime import datetime, timedelta
from src.bot.checkin_handlers import (
    checkin_command,
    checkinplus_command,
    set_anchor,
    endcheckin_command,
    handle_checkin_response,
    checkinscore_command,
    generate_checkin_response_static,
    confirmcheckin_command
)
from src.utils.mongodb_client import MongoDBClient # Para type hinting se necessário
from bson import ObjectId # Importar ObjectId
from telegram.constants import ParseMode

@pytest.fixture
def setup_mocks(mocker):
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
    message.photo = None # Inicialmente sem mídia
    message.video = None
    message.animation = None
    message.document = None
    message.text = None
    message.caption = None
    message.reply_text = AsyncMock()
    message.delete = AsyncMock()
    
    # Mock para a mensagem respondida
    replied_message = MagicMock(spec=Message)
    replied_message.message_id = 222
    replied_message_user = MagicMock(spec=User)
    replied_message_user.id = 54321
    replied_message_user.full_name = "Replied User"
    replied_message_user.username = "replieduser"
    replied_message.from_user = replied_message_user
    
    # Mock para o update
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_chat = chat
    update.message = message
    
    # Configura a mensagem para ter uma mensagem respondida por padrão
    message.reply_to_message = replied_message
    
    # Mock para o contexto
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    context.bot.set_message_reaction = AsyncMock()
    context.args = []
    context.bot_data = {}
    
    # Mock para o MongoDB client (usando patch)
    mongodb_client_mock = AsyncMock(spec=MongoDBClient)
    mock_mongo_patch = mocker.patch('src.bot.checkin_handlers.mongodb_client', mongodb_client_mock)
    
    # Mock para is_admin (usando patch)
    mock_is_admin = mocker.patch('src.bot.checkin_handlers.is_admin', return_value=True)
    
    # Mock para send_temporary_message (usando patch)
    mock_send_temp_msg = mocker.patch('src.bot.checkin_handlers.send_temporary_message', new_callable=AsyncMock)
    
    # Mock para Anthropic client (opcional, pode ser adicionado no contexto se necessário)
    mock_anthropic_client = AsyncMock()
    mock_anthropic_client.generate_checkin_response = AsyncMock()
    # context.bot_data["anthropic_client"] = mock_anthropic_client # Adicionar nos testes que precisam
    
    return {
        "update": update,
        "context": context,
        "user": user,
        "chat": chat,
        "message": message,
        "replied_message": replied_message,
        "mock_is_admin": mock_is_admin,
        "mock_send_temp_msg": mock_send_temp_msg,
        "mock_mongodb_client": mongodb_client_mock,
        "mock_anthropic_client": mock_anthropic_client # Incluir para conveniência
    }

@pytest.mark.asyncio
async def test_set_anchor_success(setup_mocks):
    """Testa set_anchor com sucesso."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]
    points_value = 3

    mongodb_client.set_checkin_anchor.return_value = True

    await set_anchor(update, context, points_value)

    mongodb_client.set_checkin_anchor.assert_called_once_with(
        mocks["chat"].id, mocks["replied_message"].message_id, points_value
    )
    update.message.delete.assert_called_once()
    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert "Âncora de check-in definida" in args[0]
    assert f"valendo {points_value} pontos" in args[0]

@pytest.mark.asyncio
async def test_set_anchor_failure(setup_mocks):
    """Testa set_anchor com falha no MongoDB."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]
    points_value = 1

    mongodb_client.set_checkin_anchor.return_value = False

    await set_anchor(update, context, points_value)

    mongodb_client.set_checkin_anchor.assert_called_once_with(
        mocks["chat"].id, mocks["replied_message"].message_id, points_value
    )
    update.message.delete.assert_called_once() # Deleta mesmo em falha
    mocks["mock_send_temp_msg"].assert_called_once()
    args, kwargs = mocks["mock_send_temp_msg"].call_args
    assert "Falha ao definir âncora" in args[1]

@pytest.mark.asyncio
async def test_set_anchor_not_admin(setup_mocks):
    """Testa set_anchor quando usuário não é admin."""
    mocks = setup_mocks
    mocks["mock_is_admin"].return_value = False
    points_value = 1

    # Chama diretamente set_anchor pois checkin_command faria a verificação
    await set_anchor(mocks["update"], mocks["context"], points_value)

    mocks["mock_send_temp_msg"].assert_called_once()
    mocks["mock_mongodb_client"].set_checkin_anchor.assert_not_called()

@pytest.mark.asyncio
async def test_set_anchor_no_reply(setup_mocks):
    """Testa set_anchor sem mensagem respondida."""
    mocks = setup_mocks
    mocks["message"].reply_to_message = None
    points_value = 1

    await set_anchor(mocks["update"], mocks["context"], points_value)

    mocks["mock_send_temp_msg"].assert_called_once()
    mocks["mock_mongodb_client"].set_checkin_anchor.assert_not_called()

@pytest.mark.asyncio
async def test_endcheckin_command_not_admin(setup_mocks):
    """Testa o comando /endcheckin quando o usuário não é administrador."""
    mocks = setup_mocks
    mocks["mock_is_admin"].return_value = False

    await endcheckin_command(mocks["update"], mocks["context"])

    mocks["mock_send_temp_msg"].assert_called_once()
    mocks["mock_mongodb_client"].end_checkin.assert_not_called()

@pytest.mark.asyncio
async def test_endcheckin_command_success(setup_mocks):
    """Testa o comando /endcheckin com sucesso."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]

    # Simula um check-in ativo e contagem
    active_checkin = {"_id": "anchor123", "message_id": 222}
    mongodb_client.get_active_checkin.return_value = active_checkin
    mongodb_client.get_anchor_checkin_count.return_value = 5
    mongodb_client.end_checkin.return_value = True

    await endcheckin_command(update, context)

    mongodb_client.get_active_checkin.assert_called_once_with(mocks["chat"].id)
    mongodb_client.get_anchor_checkin_count.assert_called_once_with(mocks["chat"].id, "anchor123")
    mongodb_client.end_checkin.assert_called_once_with(mocks["chat"].id)
    update.message.delete.assert_called_once()
    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert "Check-in encerrado!" in args[0]
    assert "Foram registrados 5 check-ins" in args[0]

@pytest.mark.asyncio
async def test_endcheckin_command_no_active(setup_mocks):
    """Testa /endcheckin sem check-in ativo."""
    mocks = setup_mocks
    mongodb_client = mocks["mock_mongodb_client"]

    mongodb_client.get_active_checkin.return_value = None # Nenhum ativo

    await endcheckin_command(mocks["update"], mocks["context"])

    mongodb_client.get_active_checkin.assert_called_once_with(mocks["chat"].id)
    mongodb_client.end_checkin.assert_not_called()
    mocks["message"].delete.assert_called_once() # Deleta mesmo assim
    mocks["mock_send_temp_msg"].assert_called_once()
    args, kwargs = mocks["mock_send_temp_msg"].call_args
    assert "Nenhuma âncora de check-in ativa" in args[1]

@pytest.mark.asyncio
async def test_endcheckin_command_failure(setup_mocks):
    """Testa /endcheckin com falha no MongoDB ao encerrar."""
    mocks = setup_mocks
    mongodb_client = mocks["mock_mongodb_client"]

    active_checkin = {"_id": "anchor123", "message_id": 222}
    mongodb_client.get_active_checkin.return_value = active_checkin
    mongodb_client.get_anchor_checkin_count.return_value = 3
    mongodb_client.end_checkin.return_value = False # Falha ao encerrar

    await endcheckin_command(mocks["update"], mocks["context"])

    mongodb_client.get_active_checkin.assert_called_once_with(mocks["chat"].id)
    mongodb_client.get_anchor_checkin_count.assert_called_once_with(mocks["chat"].id, "anchor123")
    mongodb_client.end_checkin.assert_called_once_with(mocks["chat"].id)
    mocks["message"].delete.assert_called_once() # Deleta mesmo assim
    mocks["mock_send_temp_msg"].assert_called_once()
    args, kwargs = mocks["mock_send_temp_msg"].call_args
    assert "Falha ao encerrar check-in" in args[1]

@pytest.mark.asyncio
async def test_handle_checkin_response_not_reply(setup_mocks):
    """Testa o handler quando a mensagem não é uma resposta."""
    mocks = setup_mocks
    mocks["message"].reply_to_message = None # Não é resposta

    await handle_checkin_response(mocks["update"], mocks["context"])

    # Não deve chamar o mongodb nem responder
    mocks["mock_mongodb_client"].get_active_checkin.assert_not_called()
    mocks["message"].reply_text.assert_not_called()
    mocks["context"].bot.set_message_reaction.assert_not_called()

@pytest.mark.asyncio
async def test_handle_checkin_response_no_media(setup_mocks):
    """Testa o handler quando a mensagem de resposta não contém mídia."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    # Garante que não há mídia
    update.message.photo = None
    update.message.video = None
    update.message.animation = None
    update.message.document = None

    await handle_checkin_response(update, context)

    # Não deve chamar o mongodb nem responder
    mocks["mock_mongodb_client"].get_active_checkin.assert_not_called()
    update.message.reply_text.assert_not_called()
    context.bot.set_message_reaction.assert_not_called()

@pytest.mark.asyncio
async def test_handle_checkin_response_no_active_checkin(setup_mocks):
    """Testa o handler quando não há check-in ativo."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]

    update.message.photo = [MagicMock(spec=PhotoSize)] # Adiciona mídia
    mongodb_client.get_active_checkin.return_value = None # Sem check-in ativo

    await handle_checkin_response(update, context)

    mongodb_client.get_active_checkin.assert_called_once_with(mocks["chat"].id)
    mongodb_client.record_user_checkin.assert_not_called()
    update.message.reply_text.assert_not_called()
    context.bot.set_message_reaction.assert_not_called()

@pytest.mark.asyncio
async def test_handle_checkin_response_wrong_anchor(setup_mocks):
    """Testa o handler quando a resposta não é para a âncora ativa."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]

    update.message.photo = [MagicMock(spec=PhotoSize)] # Adiciona mídia
    update.message.reply_to_message.message_id = 999 # ID diferente da âncora
    active_checkin = {"_id": "anchor123", "message_id": 222} # Âncora tem ID 222
    mongodb_client.get_active_checkin.return_value = active_checkin

    await handle_checkin_response(update, context)

    mongodb_client.get_active_checkin.assert_called_once_with(mocks["chat"].id)
    mongodb_client.record_user_checkin.assert_not_called()
    update.message.reply_text.assert_not_called()
    context.bot.set_message_reaction.assert_not_called()

@pytest.mark.asyncio
async def test_handle_checkin_response_already_checked_in(setup_mocks):
    """Testa o handler quando o usuário já fez check-in para esta âncora."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]
    send_temp_msg = mocks["mock_send_temp_msg"]

    update.message.photo = [MagicMock(spec=PhotoSize)] # Adiciona mídia
    update.message.reply_to_message.message_id = 222 # Responde à âncora correta
    active_checkin = {"_id": "anchor123", "message_id": 222}
    mongodb_client.get_active_checkin.return_value = active_checkin
    mongodb_client.record_user_checkin.return_value = None # Indica que já fez check-in

    await handle_checkin_response(update, context)

    mongodb_client.get_active_checkin.assert_called_once_with(mocks["chat"].id)
    mongodb_client.record_user_checkin.assert_called_once_with(
        mocks["chat"].id, mocks["user"].id, mocks["user"].full_name, mocks["user"].username
    )
    # Verifica a mensagem temporária de aviso
    send_temp_msg.assert_called_once()
    args, kwargs = send_temp_msg.call_args
    assert update == args[0]
    assert context == args[1]
    assert "você já marcou presença nesta âncora" in args[2]
    # Nenhuma outra resposta ou reação
    update.message.reply_text.assert_not_called()
    context.bot.set_message_reaction.assert_not_called()

@pytest.mark.asyncio
async def test_handle_checkin_response_success_normal(setup_mocks, mocker):
    """Testa o fluxo de sucesso do check-in normal (sem texto)."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]

    update.message.photo = [MagicMock(spec=PhotoSize)] # Mídia
    update.message.reply_to_message.message_id = 222 # Âncora correta
    active_checkin = {"_id": "anchor123", "message_id": 222, "points_value": 1}
    mongodb_client.get_active_checkin.return_value = active_checkin
    mongodb_client.record_user_checkin.return_value = 5 # Novo score total

    await handle_checkin_response(update, context)

    mongodb_client.record_user_checkin.assert_called_once_with(
        mocks["chat"].id, mocks["user"].id, mocks["user"].full_name, mocks["user"].username
    )

    # Verifica a chamada de reply_text (usa msg estática)
    update.message.reply_text.assert_called_once()
    call_args, call_kwargs = update.message.reply_text.call_args
    display_name = f"@{mocks['user'].username}"
    expected_base = generate_checkin_response_static(display_name, 5).split("Você tem")[0].strip()
    expected_score_part = "Você tem <b>5</b> pontos!"
    expected_full_message = f"{expected_base} {expected_score_part}"
    assert call_args[0] == expected_full_message
    assert call_kwargs.get('parse_mode') == ParseMode.HTML

    # Verifica a reação padrão
    context.bot.set_message_reaction.assert_called_once_with(chat_id=mocks["chat"].id, message_id=update.message.message_id, reaction=["🔥"])

@pytest.mark.asyncio
async def test_handle_checkin_response_success_plus_with_text(setup_mocks, mocker):
    """Testa o fluxo de sucesso do check-in plus com texto (usa LLM)."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]
    anthropic_client = mocks["mock_anthropic_client"]
    context.bot_data["anthropic_client"] = anthropic_client # Injеta o cliente LLM

    update.message.photo = [MagicMock(spec=PhotoSize)] # Mídia
    update.message.reply_to_message.message_id = 101 # Âncora correta
    update.message.text = "Treino pago!" # Texto para LLM
    active_checkin = {"_id": "anchor456", "message_id": 101, "points_value": 3}
    mongodb_client.get_active_checkin.return_value = active_checkin
    mongodb_client.record_user_checkin.return_value = 8 # Novo score total
    anthropic_client.generate_checkin_response.return_value = "Ótima energia!" # Mock LLM

    await handle_checkin_response(update, context)

    mongodb_client.record_user_checkin.assert_called_once_with(
        mocks["chat"].id, mocks["user"].id, mocks["user"].full_name, mocks["user"].username
    )
    anthropic_client.generate_checkin_response.assert_called_once_with("Treino pago!", mocks["user"].full_name)

    # Verifica a chamada de reply_text (com LLM)
    update.message.reply_text.assert_called_once()
    call_args, call_kwargs = update.message.reply_text.call_args
    display_name = f"@{mocks['user'].username}"
    expected_base = f"Check-in PLUS confirmado, {display_name}! 🧡"
    expected_score_part = "Você tem <b>8</b> pontos no total!"
    expected_llm_part = "🤖: <i>Ótima energia!</i>"
    expected_full_message = f"{expected_base} {expected_score_part}\n\n{expected_llm_part}"
    assert call_args[0] == expected_full_message
    assert call_kwargs.get('parse_mode') == ParseMode.HTML

    # Verifica a reação plus
    context.bot.set_message_reaction.assert_called_once_with(chat_id=mocks["chat"].id, message_id=update.message.message_id, reaction=["🧡"])

@pytest.mark.asyncio
async def test_handle_checkin_response_success_plus_no_text(setup_mocks):
    """Testa o fluxo de sucesso do check-in plus sem texto (usa msg estática)."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]
    # Sem anthropic_client no contexto

    update.message.photo = [MagicMock(spec=PhotoSize)] # Mídia
    update.message.reply_to_message.message_id = 101 # Âncora correta
    # update.message.text = None # Sem texto
    active_checkin = {"_id": "anchor456", "message_id": 101, "points_value": 3}
    mongodb_client.get_active_checkin.return_value = active_checkin
    mongodb_client.record_user_checkin.return_value = 8 # Novo score total

    await handle_checkin_response(update, context)

    mongodb_client.record_user_checkin.assert_called_once_with(
        mocks["chat"].id, mocks["user"].id, mocks["user"].full_name, mocks["user"].username
    )
    # anthropic_client.generate_checkin_response.assert_not_called() # Não deve chamar LLM

    # Verifica a chamada de reply_text (usa msg estática)
    update.message.reply_text.assert_called_once()
    call_args, call_kwargs = update.message.reply_text.call_args
    display_name = f"@{mocks['user'].username}"
    # A msg base vem da generate_static, mas o handler adiciona a parte do score
    expected_base = generate_checkin_response_static(display_name, 8).split("Você tem")[0].strip()
    expected_score_part = "Você tem <b>8</b> pontos!"
    expected_full_message = f"{expected_base} {expected_score_part}"
    assert call_args[0] == expected_full_message
    assert call_kwargs.get('parse_mode') == ParseMode.HTML

    # Verifica a reação plus (mesmo sem resposta LLM)
    context.bot.set_message_reaction.assert_called_once_with(chat_id=mocks["chat"].id, message_id=update.message.message_id, reaction=["🧡"])

@pytest.mark.asyncio
async def test_checkinscore_command_no_checkins(setup_mocks):
    """Testa o comando /checkinscore quando não há check-ins."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]

    mongodb_client.get_checkin_scoreboard.return_value = [] # Lista vazia
    update.effective_chat.type = "group"
    update.effective_chat.title = "Empty Group"

    await checkinscore_command(update, context)

    mongodb_client.get_checkin_scoreboard.assert_called_once_with(mocks["chat"].id)
    update.message.delete.assert_called_once()
    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert "Ainda não há check-ins registrados" in args[0]
    assert "Empty Group" in args[0]

@pytest.mark.asyncio
async def test_checkinscore_command_success(setup_mocks):
    """Testa o comando /checkinscore com sucesso em um grupo."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]

    scoreboard_data = [
        {"_id": 111, "score": 15, "user_name": "User A", "username": "usera"},
        {"_id": 222, "score": 10, "user_name": "User B", "username": "userb"},
        {"_id": 333, "score": 5, "user_name": "User C", "username": "userc_long_name_needs_truncation"}
    ]
    mongodb_client.get_checkin_scoreboard.return_value = scoreboard_data
    update.effective_chat.type = "group"
    update.effective_chat.title = "Active Group"

    await checkinscore_command(update, context)

    mongodb_client.get_checkin_scoreboard.assert_called_once_with(mocks["chat"].id)
    update.message.delete.assert_called_once()
    context.bot.send_message.assert_called_once()

    args, kwargs = context.bot.send_message.call_args
    expected_text_lines = [
        "🏆 Placar de Check-ins - Active Group 🏆",
        "",
        "🥇 @usera (Score: <b>15</b>)",
        "🥈 @userb (Score: <b>10</b>)",
        "🥉 @userc_long_name_needs_t… (Score: <b>5</b>)" # Nome truncado
    ]
    assert args[0] == "\n".join(expected_text_lines)
    assert kwargs.get("parse_mode") == ParseMode.HTML

@pytest.mark.asyncio
async def test_checkinscore_command_with_group_name(setup_mocks):
    """Testa /checkinscore buscando por nome de grupo."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]

    context.args = ["Target", "Group"]
    target_chat_info = {"chat_id": -987, "title": "Target Group Title"}
    mongodb_client._get_chat_id_by_name.return_value = target_chat_info

    scoreboard_data = [
        {"_id": 111, "score": 15, "user_name": "User A", "username": "usera"}
    ]
    mongodb_client.get_checkin_scoreboard.return_value = scoreboard_data

    await checkinscore_command(update, context)

    mongodb_client._get_chat_id_by_name.assert_called_once_with("Target Group")
    mongodb_client.get_checkin_scoreboard.assert_called_once_with(-987)
    update.message.delete.assert_called_once()
    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert "Target Group Title" in args[0]
    assert "@usera (Score: <b>15</b>)" in args[0]
    assert kwargs.get("parse_mode") == ParseMode.HTML

@pytest.mark.asyncio
async def test_checkinscore_command_group_not_found(setup_mocks):
    """Testa /checkinscore quando o nome do grupo não é encontrado."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]

    context.args = ["Unknown", "Group"]
    mongodb_client._get_chat_id_by_name.return_value = None # Grupo não encontrado

    await checkinscore_command(update, context)

    mongodb_client._get_chat_id_by_name.assert_called_once_with("Unknown Group")
    mongodb_client.get_checkin_scoreboard.assert_not_called()
    # Não deleta a mensagem de comando neste caso, envia erro
    update.message.delete.assert_not_called()
    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert "Não foi possível encontrar informações do grupo 'Unknown Group'" in args[0]

@pytest.mark.asyncio
async def test_checkinscore_command_private_no_args(setup_mocks):
    """Testa /checkinscore em chat privado sem argumentos."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]

    update.effective_chat.type = "private" # Chat privado
    context.args = []

    await checkinscore_command(update, context)

    mongodb_client._get_chat_id_by_name.assert_not_called()
    mongodb_client.get_checkin_scoreboard.assert_not_called()
    update.message.delete.assert_not_called() # Não deleta
    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert "Use /checkinscore <nome_do_grupo>" in args[0]

def test_generate_checkin_response_static():
    """Testa a geração de mensagens estáticas de check-in com base na contagem."""
    user_name = "Tester"
    # Correção: Remover "легенда" e usar ✨
    expected_messages = {
        1: f"Ótimo começo, {user_name}! 🔥 Você tem <b>1</b> ponto!",
        3: f"Mandou bem, {user_name}! 💪 Você tem <b>3</b> pontos!",
        5: f"Mandou bem, {user_name}! 💪 Você tem <b>5</b> pontos!",
        6: f"Consistência é chave, {user_name}! 🔑 Você tem <b>6</b> pontos!",
        10: f"Consistência é chave, {user_name}! 🔑 Você tem <b>10</b> pontos!",
        11: f"Impressionante, {user_name}! 🚀 Você tem <b>11</b> pontos!",
        20: f"Impressionante, {user_name}! 🚀 Você tem <b>20</b> pontos!",
        21: f"Lenda em construção, {user_name}! ✨ Você tem <b>21</b> pontos!",
        30: f"Lenda em construção, {user_name}! ✨ Você tem <b>30</b> pontos!",
        31: f"Você é imparável, {user_name}! 🏆 Você tem <b>31</b> pontos!",
        50: f"Você é imparável, {user_name}! 🏆 Você tem <b>50</b> pontos!"
    }

    for count, expected_msg in expected_messages.items():
        assert generate_checkin_response_static(user_name, count) == expected_msg

@pytest.mark.asyncio
async def test_confirmcheckin_command_not_admin(setup_mocks):
    """Testa o comando /confirmcheckin quando o usuário não é administrador."""
    mocks = setup_mocks
    mocks["mock_is_admin"].return_value = False

    await confirmcheckin_command(mocks["update"], mocks["context"])

    mocks["mock_send_temp_msg"].assert_called_once()
    mocks["mock_mongodb_client"].confirm_manual_checkin.assert_not_called()

@pytest.mark.asyncio
async def test_confirmcheckin_command_no_reply(setup_mocks):
    """Testa o comando /confirmcheckin sem mensagem respondida."""
    mocks = setup_mocks
    mocks["message"].reply_to_message = None

    await confirmcheckin_command(mocks["update"], mocks["context"])

    mocks["mock_send_temp_msg"].assert_called_once()
    mocks["mock_mongodb_client"].confirm_manual_checkin.assert_not_called()

@pytest.mark.asyncio
async def test_confirmcheckin_command_success(setup_mocks):
    """Testa o comando /confirmcheckin com sucesso."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]
    replied_user = mocks["replied_message"].from_user

    # Simula sucesso no registro manual
    mongodb_client.confirm_manual_checkin.return_value = 7 # Novo score total

    await confirmcheckin_command(update, context)

    mongodb_client.confirm_manual_checkin.assert_called_once_with(
        mocks["chat"].id, replied_user.id, replied_user.full_name, replied_user.username
    )
    update.message.delete.assert_called_once()
    # Verifica reação na mensagem respondida
    context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mocks["chat"].id,
        message_id=mocks["replied_message"].message_id,
        reaction=["✅"]
    )
    # Verifica mensagem de confirmação enviada
    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert "Check-in manual confirmado" in args[0]
    assert replied_user.full_name in args[0]
    assert "<b>7</b> pontos" in args[0]
    assert kwargs.get("parse_mode") == ParseMode.HTML

@pytest.mark.asyncio
async def test_confirmcheckin_command_already_checked_in(setup_mocks):
    """Testa /confirmcheckin quando o usuário já fez check-in."""
    mocks = setup_mocks
    update = mocks["update"]
    context = mocks["context"]
    mongodb_client = mocks["mock_mongodb_client"]
    replied_user = mocks["replied_message"].from_user

    # Simula que o usuário já fez check-in (retorna None)
    mongodb_client.confirm_manual_checkin.return_value = None

    await confirmcheckin_command(update, context)

    mongodb_client.confirm_manual_checkin.assert_called_once_with(
        mocks["chat"].id, replied_user.id, replied_user.full_name, replied_user.username
    )
    update.message.delete.assert_called_once()
    # Nenhuma reação ou mensagem de sucesso
    context.bot.set_message_reaction.assert_not_called()
    context.bot.send_message.assert_not_called()
    # Mensagem temporária de aviso
    mocks["mock_send_temp_msg"].assert_called_once()
    args, kwargs = mocks["mock_send_temp_msg"].call_args
    assert "já fez check-in recentemente" in args[1]
    assert replied_user.full_name in args[1]

# Remover testes duplicados/antigos que foram misturados
# @pytest.mark.asyncio
# async def test_checkin_command_failure(setup_mocks): ...
# @pytest.mark.asyncio
# async def test_handle_checkin_response_not_reply(setup_mocks): ... (já coberto)
# @pytest.mark.asyncio
# async def test_handle_checkin_response_with_photo(setup_mocks): ... (coberto por _success_normal)
# @pytest.mark.asyncio
# async def test_handle_checkin_response_not_anchor(setup_mocks): ... (coberto por _wrong_anchor)
# @pytest.mark.asyncio
# async def test_handle_checkin_response_success(setup_mocks): ... (coberto por _success_normal)
# @pytest.mark.asyncio
# async def test_handle_checkin_response_text_only(setup_mocks): ... (coberto por _no_media)
# @pytest.mark.asyncio
# async def test_checkinscore_command_with_checkins(setup_mocks): ... (coberto por _success)
# @pytest.mark.asyncio
# async def test_checkinscore_command_with_many_checkins(setup_mocks): ... (caso implícito)
# @pytest.mark.asyncio
# async def test_checkinscore_command(mocker): ... (Versão antiga/duplicada)
# Fixtures e testes antigos relacionados a mock_update, mock_context, etc. 