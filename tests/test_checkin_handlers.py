"""
Testes para os handlers de check-in.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes
from src.bot.checkin_handlers import (
    checkin_command,
    endcheckin_command,
    handle_checkin_response,
    generate_checkin_response,
    checkinscore_command,
    confirmcheckin_command
)
from datetime import datetime, timedelta

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
    
    # Mock para a mensagem respondida
    replied_message = MagicMock(spec=Message)
    replied_message.message_id = 222
    
    # Mock para o update
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_chat = chat
    update.message = message
    
    # Configura a mensagem para ter uma mensagem respondida
    message.reply_to_message = replied_message
    
    # Mock para o contexto
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.bot.set_message_reaction = AsyncMock()
    
    # Mock para o MongoDB client
    mongodb_client_mock = MagicMock()
    mongodb_client_mock.set_checkin_anchor = AsyncMock()
    mongodb_client_mock.end_checkin = AsyncMock()
    mongodb_client_mock.get_active_checkin = AsyncMock()
    mongodb_client_mock.record_user_checkin = AsyncMock()
    mongodb_client_mock.get_anchor_checkin_count = AsyncMock()
    
    # Patch para is_admin
    with patch('src.bot.checkin_handlers.is_admin') as mock_is_admin, \
         patch('src.bot.checkin_handlers.send_temporary_message') as mock_send_temp_msg, \
         patch('src.bot.checkin_handlers.mongodb_client', mongodb_client_mock):
        
        mock_is_admin.return_value = True
        
        yield {
            "update": update,
            "context": context,
            "user": user,
            "chat": chat,
            "message": message,
            "replied_message": replied_message,
            "mock_is_admin": mock_is_admin,
            "mock_send_temp_msg": mock_send_temp_msg,
            "mock_mongodb_client": mongodb_client_mock
        }

@pytest.mark.asyncio
async def test_checkin_command_not_admin(setup_mocks):
    """Testa o comando /checkin quando o usuário não é administrador."""
    mocks = setup_mocks
    
    # Configura o mock para retornar False (não é admin)
    mocks["mock_is_admin"].return_value = False
    
    # Executa o comando
    await checkin_command(mocks["update"], mocks["context"])
    
    # Verifica se a mensagem temporária foi enviada
    mocks["mock_send_temp_msg"].assert_called_once()

@pytest.mark.asyncio
async def test_checkin_command_no_reply(setup_mocks):
    """Testa o comando /checkin quando não há mensagem respondida."""
    mocks = setup_mocks
    
    # Remove a mensagem respondida
    mocks["message"].reply_to_message = None
    
    # Executa o comando
    await checkin_command(mocks["update"], mocks["context"])
    
    # Verifica se a mensagem temporária foi enviada
    mocks["mock_send_temp_msg"].assert_called_once()

@pytest.mark.asyncio
async def test_checkin_command_success(setup_mocks):
    """Testa o comando /checkin com sucesso."""
    mocks = setup_mocks
    
    # Configura o mock do MongoDB para retornar True
    mocks["mock_mongodb_client"].set_checkin_anchor.return_value = True
    
    # Executa o comando
    await checkin_command(mocks["update"], mocks["context"])
    
    # Verifica se o MongoDB foi inicializado
    mocks["mock_mongodb_client"].set_checkin_anchor.assert_called_once_with(
        mocks["chat"].id, mocks["replied_message"].message_id
    )
    
    # Verifica se a mensagem foi deletada
    mocks["message"].delete.assert_called_once()
    
    # Verifica se a mensagem de confirmação foi enviada
    mocks["context"].bot.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_checkin_command_failure(setup_mocks):
    """Testa o comando /checkin com falha no MongoDB."""
    mocks = setup_mocks
    
    # Configura o mock do MongoDB para retornar False
    mocks["mock_mongodb_client"].set_checkin_anchor.return_value = False
    
    # Executa o comando
    await checkin_command(mocks["update"], mocks["context"])
    
    # Verifica se o método set_checkin_anchor foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].set_checkin_anchor.assert_called_once_with(
        mocks["chat"].id, mocks["replied_message"].message_id
    )
    
    # Verifica se a mensagem temporária foi enviada
    mocks["mock_send_temp_msg"].assert_called_once()

@pytest.mark.asyncio
async def test_endcheckin_command_not_admin(setup_mocks):
    """Testa o comando /endcheckin quando o usuário não é administrador."""
    mocks = setup_mocks
    
    # Configura o mock para retornar False (não é admin)
    mocks["mock_is_admin"].return_value = False
    
    # Executa o comando
    await endcheckin_command(mocks["update"], mocks["context"])
    
    # Verifica se a mensagem temporária foi enviada
    mocks["mock_send_temp_msg"].assert_called_once()

@pytest.mark.asyncio
async def test_endcheckin_command_success(setup_mocks):
    """Testa o comando /endcheckin com sucesso."""
    mocks = setup_mocks
    
    # Configura o mock do MongoDB para retornar True
    mocks["mock_mongodb_client"].end_checkin.return_value = True
    
    # Configura o mock para get_active_checkin retornar um check-in ativo
    active_checkin = {"_id": "anchor123", "message_id": 222, "chat_id": mocks["chat"].id, "active": True}
    mocks["mock_mongodb_client"].get_active_checkin.return_value = active_checkin
    
    # Configura o mock para get_anchor_checkin_count retornar uma contagem
    mocks["mock_mongodb_client"].get_anchor_checkin_count.return_value = 5
    
    # Executa o comando
    await endcheckin_command(mocks["update"], mocks["context"])
    
    # Verifica se o método get_active_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].get_active_checkin.assert_called_once_with(mocks["chat"].id)
    
    # Verifica se o método get_anchor_checkin_count foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].get_anchor_checkin_count.assert_called_once_with(mocks["chat"].id, "anchor123")
    
    # Verifica se o método end_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].end_checkin.assert_called_once_with(mocks["chat"].id)
    
    # Verifica se a mensagem foi deletada
    mocks["message"].delete.assert_called_once()
    
    # Verifica se a mensagem de confirmação foi enviada com a contagem de check-ins
    mocks["context"].bot.send_message.assert_called_once()
    args, kwargs = mocks["context"].bot.send_message.call_args
    assert kwargs["chat_id"] == mocks["chat"].id
    assert "Foram registrados 5 check-ins" in kwargs["text"]

@pytest.mark.asyncio
async def test_endcheckin_command_failure(setup_mocks):
    """Testa o comando /endcheckin com falha no MongoDB."""
    mocks = setup_mocks
    
    # Configura o mock para get_active_checkin retornar um check-in ativo
    active_checkin = {"_id": "anchor123", "message_id": 222, "chat_id": mocks["chat"].id, "active": True}
    mocks["mock_mongodb_client"].get_active_checkin.return_value = active_checkin
    
    # Configura o mock para get_anchor_checkin_count retornar uma contagem
    mocks["mock_mongodb_client"].get_anchor_checkin_count.return_value = 3
    
    # Configura o mock do MongoDB para retornar False
    mocks["mock_mongodb_client"].end_checkin.return_value = False
    
    # Executa o comando
    await endcheckin_command(mocks["update"], mocks["context"])
    
    # Verifica se o método get_active_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].get_active_checkin.assert_called_once_with(mocks["chat"].id)
    
    # Verifica se o método get_anchor_checkin_count foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].get_anchor_checkin_count.assert_called_once_with(mocks["chat"].id, "anchor123")
    
    # Verifica se o método end_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].end_checkin.assert_called_once_with(mocks["chat"].id)
    
    # Verifica se a mensagem temporária foi enviada
    mocks["mock_send_temp_msg"].assert_called_once()

@pytest.mark.asyncio
async def test_handle_checkin_response_no_reply(setup_mocks):
    """Testa o handler de check-in quando não há mensagem respondida."""
    mocks = setup_mocks
    
    # Remove a mensagem respondida
    mocks["message"].reply_to_message = None
    
    # Executa o handler
    await handle_checkin_response(mocks["update"], mocks["context"])

@pytest.mark.asyncio
async def test_handle_checkin_response_with_photo(setup_mocks):
    """Testa o handler de check-in quando a resposta contém uma imagem."""
    mocks = setup_mocks

    # Configura a mensagem para ter uma foto para que o handler a processe
    mocks["message"].text = None
    mocks["message"].photo = [MagicMock()]  # Simula uma foto
    mocks["message"].video = None
    mocks["message"].animation = None
    mocks["message"].document = None

    # Configura o mock do MongoDB para retornar um check-in ativo
    mocks["mock_mongodb_client"].get_active_checkin.return_value = {
        "message_id": mocks["replied_message"].message_id
    }

    # Configura o mock para retornar a contagem de check-ins
    mocks["mock_mongodb_client"].record_user_checkin.return_value = 5

    # Executa o handler
    await handle_checkin_response(mocks["update"], mocks["context"])

    # Verifica se o método get_active_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].get_active_checkin.assert_called_once_with(mocks["chat"].id)

    # Verifica se o método record_user_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].record_user_checkin.assert_called_once_with(
        mocks["chat"].id, mocks["user"].id, mocks["user"].full_name, mocks["user"].username
    )

    # Verifica se a reação foi adicionada à mensagem
    mocks["context"].bot.set_message_reaction.assert_called_once_with(
        chat_id=mocks["chat"].id,
        message_id=mocks["message"].message_id,
        reaction=["🔥"]
    )

    # Verifica se a mensagem de resposta foi enviada via send_temporary_message com reply=True
    # Agora usamos send_temporary_message em vez de reply_text
    mocks["mock_send_temp_msg"].assert_called_once()

@pytest.mark.asyncio
async def test_handle_checkin_response_not_anchor(setup_mocks):
    """Testa o handler de check-in quando a mensagem respondida não é âncora."""
    mocks = setup_mocks
    
    # Configura a mensagem para ter uma foto para que o handler a processe
    mocks["message"].photo = [MagicMock()]  # Simula uma foto
    mocks["message"].video = None
    mocks["message"].animation = None
    mocks["message"].document = None
    
    # Configura o mock do MongoDB para retornar None (não há check-in ativo)
    mocks["mock_mongodb_client"].get_active_checkin.return_value = None
    
    # Executa o handler
    await handle_checkin_response(mocks["update"], mocks["context"])
    
    # Verifica se o método get_active_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].get_active_checkin.assert_called_once_with(mocks["chat"].id)
    
    # Verifica se o método record_user_checkin não foi chamado
    mocks["mock_mongodb_client"].record_user_checkin.assert_not_called()

@pytest.mark.asyncio
async def test_handle_checkin_response_already_checked_in(setup_mocks):
    """Testa o handler de check-in quando o usuário já fez check-in para esta âncora."""
    mocks = setup_mocks

    # Configura a mensagem para ter uma foto para que o handler a processe
    mocks["message"].photo = [MagicMock()]  # Simula uma foto
    mocks["message"].video = None
    mocks["message"].animation = None
    mocks["message"].document = None

    # Configura o mock do MongoDB para retornar um check-in ativo
    mocks["mock_mongodb_client"].get_active_checkin.return_value = {
        "message_id": mocks["replied_message"].message_id
    }

    # Configura o mock para retornar None (já fez check-in para esta âncora)
    mocks["mock_mongodb_client"].record_user_checkin.return_value = None

    # Mockamos o username para ser consistente com o teste
    mocks["user"].username = "testuser"

    # Executa o handler
    await handle_checkin_response(mocks["update"], mocks["context"])

    # Verifica se o método get_active_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].get_active_checkin.assert_called_once_with(mocks["chat"].id)

    # Verifica se o método record_user_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].record_user_checkin.assert_called_once_with(
        mocks["chat"].id, mocks["user"].id, mocks["user"].full_name, mocks["user"].username
    )

    # Verifica se a mensagem temporária foi enviada com o display_name correto
    display_name = f"@{mocks['user'].username}" 
    mocks["mock_send_temp_msg"].assert_called_once_with(
        mocks["update"],
        mocks["context"],
        f"Você já fez seu check-in para esta mensagem, {display_name}! 😉"
    )

@pytest.mark.asyncio
async def test_handle_checkin_response_success(setup_mocks):
    """Testa o handler de check-in com sucesso."""
    mocks = setup_mocks

    # Configura a mensagem para ter uma foto para que o handler a processe
    mocks["message"].photo = [MagicMock()]  # Simula uma foto
    mocks["message"].video = None
    mocks["message"].animation = None
    mocks["message"].document = None

    # Configura o mock do MongoDB para retornar um check-in ativo
    mocks["mock_mongodb_client"].get_active_checkin.return_value = {
        "message_id": mocks["replied_message"].message_id
    }

    # Configura o mock para retornar a contagem de check-ins
    mocks["mock_mongodb_client"].record_user_checkin.return_value = 5

    # Executa o handler
    await handle_checkin_response(mocks["update"], mocks["context"])

    # Verifica se o método get_active_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].get_active_checkin.assert_called_once_with(mocks["chat"].id)

    # Verifica se o método record_user_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].record_user_checkin.assert_called_once_with(
        mocks["chat"].id, mocks["user"].id, mocks["user"].full_name, mocks["user"].username
    )

    # Verifica se a reação foi adicionada à mensagem
    mocks["context"].bot.set_message_reaction.assert_called_once_with(
        chat_id=mocks["chat"].id,
        message_id=mocks["message"].message_id,
        reaction=["🔥"]
    )

    # Verifica se a mensagem de resposta foi enviada via send_temporary_message com reply=True
    # Agora usamos send_temporary_message em vez de reply_text
    mocks["mock_send_temp_msg"].assert_called_once()
    # Verifica que foi chamado com os argumentos corretos
    args, kwargs = mocks["mock_send_temp_msg"].call_args
    assert args[0] == mocks["update"]
    assert args[1] == mocks["context"]
    assert isinstance(args[2], str)  # Verifica que o terceiro argumento é uma string (a mensagem)
    assert kwargs.get("reply") == True

@pytest.mark.asyncio
async def test_handle_checkin_response_text_only(setup_mocks):
    """Testa o handler de check-in quando a resposta contém apenas texto."""
    mocks = setup_mocks
    
    # Configura a mensagem para ter apenas texto (sem mídia)
    mocks["message"].photo = None
    mocks["message"].video = None
    mocks["message"].animation = None
    mocks["message"].document = None
    mocks["message"].text = "Check-in"
    
    # Executa o handler
    await handle_checkin_response(mocks["update"], mocks["context"])
    
    # Verifica que não chama o get_active_checkin porque a mensagem só tem texto
    mocks["mock_mongodb_client"].get_active_checkin.assert_not_called()
    
    # Verifica que não registra check-in
    mocks["mock_mongodb_client"].record_user_checkin.assert_not_called()

@pytest.mark.asyncio
async def test_checkinscore_command_no_checkins(setup_mocks):
    """Testa o comando /checkinscore quando não há check-ins registrados."""
    mocks = setup_mocks
    
    # Configura o mock do MongoDB para retornar uma lista vazia
    mocks["mock_mongodb_client"].get_checkin_scoreboard = AsyncMock(return_value=[])
    mocks["mock_mongodb_client"].get_total_checkin_participants = AsyncMock(return_value=0)
    mocks["mock_mongodb_client"].get_first_checkin_date = AsyncMock(return_value=None)
    
    # Executa o comando
    await checkinscore_command(mocks["update"], mocks["context"])
    
    # Verifica se o método get_checkin_scoreboard foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].get_checkin_scoreboard.assert_called_once_with(mocks["chat"].id)
    
    # Verifica se a mensagem de comando foi deletada
    mocks["message"].delete.assert_called_once()
    
    # Verifica se a mensagem de resposta foi enviada diretamente no chat
    mocks["context"].bot.send_message.assert_called_once_with(
        chat_id=mocks["chat"].id,
        text="Ainda não há check-ins registrados neste chat. 😢"
    )

@pytest.mark.asyncio
async def test_checkinscore_command_with_checkins(setup_mocks):
    """Testa o comando /checkinscore quando há check-ins registrados."""
    mocks = setup_mocks
    
    # Configura o mock do MongoDB para retornar uma lista de check-ins
    scoreboard = [
        {"user_id": 123, "user_name": "Usuário 1", "username": "user1", "count": 10},
        {"user_id": 456, "user_name": "Usuário 2", "username": None, "count": 7},
        {"user_id": 789, "user_name": "Usuário 3", "username": "user3", "count": 5},
        {"user_id": 101, "user_name": "Usuário 4", "username": "user4", "count": 3}
    ]
    mocks["mock_mongodb_client"].get_checkin_scoreboard = AsyncMock(return_value=scoreboard)
    mocks["mock_mongodb_client"].get_total_checkin_participants = AsyncMock(return_value=4)
    mocks["mock_mongodb_client"].get_first_checkin_date = AsyncMock(return_value=datetime.now() - timedelta(days=30))
    
    # Executa o comando
    await checkinscore_command(mocks["update"], mocks["context"])
    
    # Verifica se a mensagem de comando foi deletada
    mocks["message"].delete.assert_called_once()
    
    # Verifica se a mensagem de resposta foi enviada diretamente no chat
    mocks["context"].bot.send_message.assert_called_once()
    
    # Verifica se a mensagem contém o título do scoreboard
    args, kwargs = mocks["context"].bot.send_message.call_args
    assert kwargs["chat_id"] == mocks["chat"].id
    message = kwargs["text"]
    assert "GYM NATION CHECK-INS" in message
    
    # Verifica se a mensagem contém os usernames quando disponíveis, nomes quando não
    assert "@user1" in message
    assert "Usuário 2" in message  # Usuário sem username
    assert "@user3" in message
    assert "@user4" in message
    
    # Verifica se a mensagem contém as contagens
    assert "*10*" in message
    assert "*7*" in message
    assert "*5*" in message
    assert "*3*" in message
    
    # Verifica se a mensagem contém as medalhas
    assert "🥇" in message
    assert "🥈" in message
    assert "🥉" in message
    
    # Verifica se a mensagem contém as estatísticas adicionais
    assert "pessoas já participaram dos check-ins" in message
    assert "Primeiro check-in registrado há" in message
    
    # Verifica se a mensagem contém a mensagem motivacional
    assert "Continue mantendo a consistência!" in message
    
    # Verifica se o modo de parse foi definido corretamente
    from telegram.constants import ParseMode
    assert kwargs["parse_mode"] == ParseMode.MARKDOWN

@pytest.mark.asyncio
async def test_checkinscore_command_with_many_checkins(setup_mocks):
    """Testa o comando /checkinscore quando há mais de 10 check-ins registrados."""
    mocks = setup_mocks
    
    # Cria uma lista com mais de 10 usuários
    scoreboard = []
    for i in range(1, 15):  # 14 usuários
        scoreboard.append({
            "user_id": i,
            "user_name": f"Usuário {i}",
            "username": f"user{i}" if i % 3 != 0 else None,  # Alguns sem username
            "count": 20 - i  # Contagem decrescente para manter a ordem
        })
    
    mocks["mock_mongodb_client"].get_checkin_scoreboard = AsyncMock(return_value=scoreboard)
    mocks["mock_mongodb_client"].get_total_checkin_participants = AsyncMock(return_value=14)
    mocks["mock_mongodb_client"].get_first_checkin_date = AsyncMock(return_value=datetime.now() - timedelta(days=60))
    
    # Executa o comando
    await checkinscore_command(mocks["update"], mocks["context"])
    
    # Verifica se a mensagem de comando foi deletada
    mocks["message"].delete.assert_called_once()
    
    # Verifica se a mensagem de resposta foi enviada diretamente no chat
    mocks["context"].bot.send_message.assert_called_once()
    
    # Verifica se a mensagem contém o título do scoreboard
    args, kwargs = mocks["context"].bot.send_message.call_args
    message = kwargs["text"]
    
    # Verifica se contém alguns dos usuários principais
    assert "@user1" in message  # Primeiro lugar
    assert "@user2" in message  # Segundo lugar
    
    # Verifica se há informações estatísticas
    assert "pessoas já participaram dos check-ins" in message
    assert "Primeiro check-in registrado há" in message

def test_generate_checkin_response():
    """Testa a geração de mensagens de resposta para check-ins."""
    # Testa diferentes contagens de check-ins
    assert generate_checkin_response("Test User", 1) == "Primeiro check-in de Test User! 🎉 Bem-vindo ao GYM NATION!"
    assert generate_checkin_response("Test User", 3) == "Terceiro check-in de Test User! 🔥 Você está criando consistência!"
    assert generate_checkin_response("Test User", 5) == "Quinto check-in de Test User! 💪 Você está no caminho certo!"
    assert generate_checkin_response("Test User", 10) == "Uau! Test User já está no check-in #10! Sua consistência é inspiradora! 🔥"
    assert generate_checkin_response("Test User", 30) == "Um mês de check-ins! Test User está construindo um hábito incrível! 🏆"
    assert generate_checkin_response("Test User", 100) == "INACREDITÁVEL! Test User alcançou 100 check-ins! Você é uma lenda! 👑"
    
    # Testa múltiplos de 50
    assert "Test User atingiu 50 check-ins" in generate_checkin_response("Test User", 50)
    
    # Testa múltiplos de 25
    assert "Test User" in generate_checkin_response("Test User", 25)
    assert "25 check-ins" in generate_checkin_response("Test User", 25)
    
    # Testa múltiplos de 10
    assert "Test User" in generate_checkin_response("Test User", 20)
    assert "20 check-ins" in generate_checkin_response("Test User", 20)
    
    # Testa outros números (usando verificações mais flexíveis)
    response = generate_checkin_response("Test User", 7)
    assert "Test User" in response
    assert "#7" in response or "7" in response

@pytest.mark.asyncio
async def test_confirmcheckin_command_not_admin(setup_mocks):
    """Testa o comando /confirmcheckin quando o usuário não é administrador."""
    mocks = setup_mocks
    
    # Configura o mock para retornar False (não é admin)
    mocks["mock_is_admin"].return_value = False
    
    # Executa o comando
    await confirmcheckin_command(mocks["update"], mocks["context"])
    
    # Verifica se a mensagem temporária foi enviada
    mocks["mock_send_temp_msg"].assert_called_once()
    
    # Verifica que nenhuma outra função foi chamada
    mocks["mock_mongodb_client"].get_active_checkin.assert_not_called()
    mocks["mock_mongodb_client"].record_user_checkin.assert_not_called()
    mocks["context"].bot.set_message_reaction.assert_not_called()

@pytest.mark.asyncio
async def test_confirmcheckin_command_no_reply(setup_mocks):
    """Testa o comando /confirmcheckin quando não há mensagem respondida."""
    mocks = setup_mocks
    
    # Configura o mock para retornar True (é admin)
    mocks["mock_is_admin"].return_value = True
    
    # Remove a mensagem respondida
    mocks["message"].reply_to_message = None
    
    # Executa o comando
    await confirmcheckin_command(mocks["update"], mocks["context"])
    
    # Verifica se a mensagem temporária foi enviada
    mocks["mock_send_temp_msg"].assert_called_once()
    
    # Verifica que nenhuma outra função foi chamada
    mocks["mock_mongodb_client"].get_active_checkin.assert_not_called()
    mocks["mock_mongodb_client"].record_user_checkin.assert_not_called()
    mocks["context"].bot.set_message_reaction.assert_not_called()

@pytest.mark.asyncio
async def test_confirmcheckin_command_no_active_checkin(setup_mocks):
    """Testa o comando /confirmcheckin quando não há check-in ativo."""
    mocks = setup_mocks
    
    # Configura o mock para retornar True (é admin)
    mocks["mock_is_admin"].return_value = True
    
    # Configura o mock para retornar None (sem check-in ativo)
    mocks["mock_mongodb_client"].get_active_checkin.return_value = None
    
    # Executa o comando
    await confirmcheckin_command(mocks["update"], mocks["context"])
    
    # Verifica se a mensagem temporária foi enviada
    mocks["mock_send_temp_msg"].assert_called_once()
    
    # Verifica que as funções esperadas foram chamadas
    mocks["mock_mongodb_client"].get_active_checkin.assert_called_once()
    mocks["mock_mongodb_client"].record_user_checkin.assert_not_called()
    mocks["context"].bot.set_message_reaction.assert_not_called()

@pytest.mark.asyncio
async def test_confirmcheckin_command_user_already_checked_in(setup_mocks):
    """Testa o comando /confirmcheckin quando o usuário já fez check-in."""
    mocks = setup_mocks
    
    # Configura o mock para retornar True (é admin)
    mocks["mock_is_admin"].return_value = True

    # Configura o mock para retornar um check-in ativo
    mocks["mock_mongodb_client"].get_active_checkin.return_value = {
        "_id": "test_anchor_id",
        "message_id": mocks["replied_message"].message_id
    }

    # Configura o mock para retornar None (usuário já fez check-in)
    mocks["mock_mongodb_client"].record_user_checkin.return_value = None

    # Executa o comando
    await confirmcheckin_command(mocks["update"], mocks["context"])

    # Verifica que o método record_user_checkin foi chamado com os parâmetros corretos
    mocks["mock_mongodb_client"].record_user_checkin.assert_called_once_with(
        mocks["chat"].id,
        mocks["replied_message"].from_user.id,
        mocks["replied_message"].from_user.full_name,
        mocks["replied_message"].from_user.username
    )

    # Verifica que a mensagem de usuário já checado foi enviada
    mocks["context"].bot.send_message.assert_called_once()
    
    # Verifica que a mensagem de comando foi deletada
    mocks["message"].delete.assert_called_once()

@pytest.mark.asyncio
async def test_confirmcheckin_command_success(setup_mocks):
    """Testa o comando /confirmcheckin com sucesso."""
    mocks = setup_mocks
    
    # Configura o mock para retornar True (é admin)
    mocks["mock_is_admin"].return_value = True
    
    # Configura o mock para retornar um check-in ativo
    mocks["mock_mongodb_client"].get_active_checkin.return_value = {
        "_id": "test_anchor_id",
        "message_id": mocks["replied_message"].message_id
    }
    
    # Configura o mock para retornar a contagem de check-ins
    mocks["mock_mongodb_client"].record_user_checkin.return_value = 5
    
    # Executa o comando
    await confirmcheckin_command(mocks["update"], mocks["context"])
    
    # Verifica que a mensagem de comando foi deletada
    mocks["message"].delete.assert_called_once()
    
    # Verifica que as funções esperadas foram chamadas
    mocks["mock_mongodb_client"].get_active_checkin.assert_called_once_with(mocks["chat"].id)
    mocks["mock_mongodb_client"].record_user_checkin.assert_called_once_with(
        mocks["chat"].id,
        mocks["replied_message"].from_user.id,
        mocks["replied_message"].from_user.full_name,
        mocks["replied_message"].from_user.username
    )
    
    # Verifica se a reação foi adicionada à mensagem
    mocks["context"].bot.set_message_reaction.assert_called_once_with(
        chat_id=mocks["chat"].id,
        message_id=mocks["replied_message"].message_id,
        reaction=["🔥"]
    )
    
    # Verifica se a mensagem de confirmação foi enviada via send_message e não reply_text
    mocks["context"].bot.send_message.assert_called_once() 