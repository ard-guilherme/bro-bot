"""
Testes para o cliente MongoDB.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from pymongo.errors import PyMongoError
from src.utils.mongodb_client import MongoDBClient

@pytest.fixture
async def mongodb_setup():
    """Configura o ambiente de teste para o MongoDB."""
    # Patch para motor.motor_asyncio.AsyncIOMotorClient
    with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_motor_client:
        # Mock para o cliente do MongoDB
        mock_client = MagicMock()
        mock_motor_client.return_value = mock_client
        
        # Mock para o banco de dados
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        # Mock para as coleções
        mock_checkin_anchors = AsyncMock()
        mock_user_checkins = AsyncMock()
        mock_qa_interactions = AsyncMock()
        mock_qa_usage = AsyncMock()
        mock_monitored_chats = AsyncMock()
        mock_monitored_messages = AsyncMock()
        mock_bot_admins = AsyncMock()
        mock_blacklist = AsyncMock()
        
        mock_db.checkin_anchors = mock_checkin_anchors
        mock_db.user_checkins = mock_user_checkins
        mock_db.qa_interactions = mock_qa_interactions
        mock_db.qa_usage = mock_qa_usage
        mock_db.monitored_chats = mock_monitored_chats
        mock_db.monitored_messages = mock_monitored_messages
        mock_db.bot_admins = mock_bot_admins
        mock_db.blacklist = mock_blacklist
        
        # Cria o cliente MongoDB
        mongodb_client = MongoDBClient("mongodb://test:test@localhost:27017")
        
        # Conecta ao banco de dados para que self.db não seja None
        await mongodb_client.connect("test_db")
        
        yield {
            "client": mongodb_client,
            "mock_motor_client": mock_motor_client,
            "mock_client": mock_client,
            "mock_db": mock_db,
            "mock_checkin_anchors": mock_checkin_anchors,
            "mock_user_checkins": mock_user_checkins,
            "mock_qa_interactions": mock_qa_interactions,
            "mock_qa_usage": mock_qa_usage,
            "mock_monitored_chats": mock_monitored_chats,
            "mock_monitored_messages": mock_monitored_messages,
            "mock_bot_admins": mock_bot_admins,
            "mock_blacklist": mock_blacklist
        }

@pytest.mark.asyncio
async def test_connect(mongodb_setup):
    """Testa a conexão com o MongoDB."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_motor_client = mongodb_setup["mock_motor_client"]
    mock_client = mongodb_setup["mock_client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Executa o método connect
    await mongodb_client.connect("test_db")
    
    # Verifica se o cliente foi criado com a string de conexão correta
    mock_motor_client.assert_called_once_with("mongodb://test:test@localhost:27017")
    
    # Verifica se o banco de dados foi selecionado corretamente
    mock_client.__getitem__.assert_called_once_with("test_db")
    
    # Verifica se o cliente e o banco de dados foram armazenados
    assert mongodb_client.client == mock_client
    assert mongodb_client.db == mock_db

@pytest.mark.asyncio
async def test_connect_error(mongodb_setup):
    """Testa a conexão com o MongoDB com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_motor_client = mongodb_setup["mock_motor_client"]
    
    # Configura o mock para lançar uma exceção
    mock_motor_client.side_effect = PyMongoError("Connection error")
    
    # Verifica se a exceção é propagada
    with pytest.raises(PyMongoError):
        await mongodb_client.connect("test_db")

@pytest.mark.asyncio
async def test_close(mongodb_setup):
    """Testa o fechamento da conexão com o MongoDB."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_client = mongodb_setup["mock_client"]
    
    # Configura o cliente
    mongodb_client.client = mock_client
    
    # Executa o método close
    await mongodb_client.close()
    
    # Verifica se o método close foi chamado
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_set_checkin_anchor(mongodb_setup):
    """Testa a definição de uma mensagem como âncora de check-in."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    mock_checkin_anchors = mongodb_setup["mock_checkin_anchors"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para end_checkin
    mongodb_client.end_checkin = AsyncMock(return_value=True)
    
    # Configura o mock para insert_one
    mock_checkin_anchors.insert_one.return_value = MagicMock(acknowledged=True)
    
    # Executa o método set_checkin_anchor
    result = await mongodb_client.set_checkin_anchor(12345, 67890)
    
    # Verifica se o método end_checkin foi chamado
    mongodb_client.end_checkin.assert_called_once_with(12345)
    
    # Verifica se o método insert_one foi chamado com os parâmetros corretos
    mock_checkin_anchors.insert_one.assert_called_once()
    args, _ = mock_checkin_anchors.insert_one.call_args
    assert args[0]["chat_id"] == 12345
    assert args[0]["message_id"] == 67890
    assert args[0]["active"] is True
    assert isinstance(args[0]["created_at"], datetime)
    
    # Verifica o resultado
    assert result is True

@pytest.mark.asyncio
async def test_set_checkin_anchor_error(mongodb_setup):
    """Testa a definição de uma mensagem como âncora de check-in com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    mock_checkin_anchors = mongodb_setup["mock_checkin_anchors"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para end_checkin
    mongodb_client.end_checkin = AsyncMock(return_value=True)
    
    # Configura o mock para insert_one para lançar uma exceção
    mock_checkin_anchors.insert_one.side_effect = PyMongoError("Insert error")
    
    # Executa o método set_checkin_anchor
    result = await mongodb_client.set_checkin_anchor(12345, 67890)
    
    # Verifica o resultado
    assert result is False

@pytest.mark.asyncio
async def test_end_checkin(mongodb_setup):
    """Testa a desativação do check-in atual."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    mock_checkin_anchors = mongodb_setup["mock_checkin_anchors"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para update_many
    mock_checkin_anchors.update_many.return_value = MagicMock(acknowledged=True)
    
    # Executa o método end_checkin
    result = await mongodb_client.end_checkin(12345)
    
    # Verifica se o método update_many foi chamado com os parâmetros corretos
    mock_checkin_anchors.update_many.assert_called_once_with(
        {"chat_id": 12345, "active": True},
        {"$set": {"active": False}}
    )
    
    # Verifica o resultado
    assert result is True

@pytest.mark.asyncio
async def test_end_checkin_error(mongodb_setup):
    """Testa a desativação do check-in atual com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    mock_checkin_anchors = mongodb_setup["mock_checkin_anchors"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para update_many para lançar uma exceção
    mock_checkin_anchors.update_many.side_effect = PyMongoError("Update error")
    
    # Executa o método end_checkin
    result = await mongodb_client.end_checkin(12345)
    
    # Verifica o resultado
    assert result is False

@pytest.mark.asyncio
async def test_get_active_checkin(mongodb_setup):
    """Testa a obtenção do check-in ativo."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    mock_checkin_anchors = mongodb_setup["mock_checkin_anchors"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para find_one
    expected_checkin = {"_id": "123", "chat_id": 12345, "message_id": 67890, "active": True}
    mock_checkin_anchors.find_one.return_value = expected_checkin
    
    # Executa o método get_active_checkin
    result = await mongodb_client.get_active_checkin(12345)
    
    # Verifica se o método find_one foi chamado com os parâmetros corretos
    mock_checkin_anchors.find_one.assert_called_once_with(
        {"chat_id": 12345, "active": True}
    )
    
    # Verifica o resultado
    assert result == expected_checkin

@pytest.mark.asyncio
async def test_get_active_checkin_error(mongodb_setup):
    """Testa a obtenção do check-in ativo com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    mock_checkin_anchors = mongodb_setup["mock_checkin_anchors"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para find_one para lançar uma exceção
    mock_checkin_anchors.find_one.side_effect = PyMongoError("Find error")
    
    # Executa o método get_active_checkin
    result = await mongodb_client.get_active_checkin(12345)
    
    # Verifica o resultado
    assert result is None

@pytest.mark.asyncio
async def test_record_user_checkin_already_checked_in(mongodb_setup):
    """Testa o registro de check-in quando o usuário já fez check-in para a âncora atual."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = MagicMock()
    mock_user_checkins = MagicMock()
    mock_user_checkins.find_one = AsyncMock(return_value={"_id": "existing_checkin"})
    mock_db.user_checkins = mock_user_checkins
    mongodb_client.db = mock_db
    
    # Configura o mock para get_active_checkin retornar um check-in ativo
    mongodb_client.get_active_checkin = AsyncMock(return_value={"_id": "anchor123"})
    
    # Executa o método record_user_checkin
    result = await mongodb_client.record_user_checkin(123, 456, "Test User")
    
    # Verifica se o método retornou None
    assert result is None
    
    # Verifica se o método find_one foi chamado com os parâmetros corretos
    mock_user_checkins.find_one.assert_called_once_with({
        "chat_id": 123,
        "user_id": 456,
        "anchor_id": "anchor123"
    })
    
    # Verifica se o método insert_one não foi chamado
    mock_user_checkins.insert_one.assert_not_called()

@pytest.mark.asyncio
async def test_record_user_checkin_success(mongodb_setup):
    """Testa o registro de check-in com sucesso."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = MagicMock()
    mock_user_checkins = MagicMock()
    mock_user_checkins.find_one = AsyncMock(return_value=None)
    mock_user_checkins.insert_one = AsyncMock()
    mock_user_checkins.count_documents = AsyncMock(return_value=5)
    mock_db.user_checkins = mock_user_checkins
    mongodb_client.db = mock_db
    
    # Configura o mock para get_active_checkin retornar um check-in ativo
    mongodb_client.get_active_checkin = AsyncMock(return_value={"_id": "anchor123"})
    
    # Executa o método record_user_checkin
    result = await mongodb_client.record_user_checkin(123, 456, "Test User")
    
    # Verifica se o método retornou 5
    assert result == 5
    
    # Verifica se o método find_one foi chamado com os parâmetros corretos
    mock_user_checkins.find_one.assert_called_once_with({
        "chat_id": 123,
        "user_id": 456,
        "anchor_id": "anchor123"
    })
    
    # Verifica se o método insert_one foi chamado com os parâmetros corretos
    mock_user_checkins.insert_one.assert_called_once()
    call_args = mock_user_checkins.insert_one.call_args[0][0]
    assert call_args["chat_id"] == 123
    assert call_args["user_id"] == 456
    assert call_args["user_name"] == "Test User"
    assert call_args["anchor_id"] == "anchor123"
    assert "created_at" in call_args
    
    # Verifica se o método count_documents foi chamado com os parâmetros corretos
    mock_user_checkins.count_documents.assert_called_once_with({
        "chat_id": 123,
        "user_id": 456
    })

@pytest.mark.asyncio
async def test_record_user_checkin_error(mongodb_setup):
    """Testa o registro de check-in com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = MagicMock()
    mock_user_checkins = MagicMock()
    mock_user_checkins.find_one = AsyncMock(side_effect=PyMongoError("Erro simulado"))
    mock_db.user_checkins = mock_user_checkins
    mongodb_client.db = mock_db
    
    # Configura o mock para get_active_checkin retornar um check-in ativo
    mongodb_client.get_active_checkin = AsyncMock(return_value={"_id": "anchor123"})
    
    # Executa o método record_user_checkin
    result = await mongodb_client.record_user_checkin(123, 456, "Test User")
    
    # Verifica se o método retornou None
    assert result is None

@pytest.mark.asyncio
async def test_get_user_count(mongodb_setup):
    """Testa a obtenção da contagem de check-ins de um usuário."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    mock_user_checkins = mongodb_setup["mock_user_checkins"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para count_documents
    mock_user_checkins.count_documents.return_value = 5
    
    # Executa o método get_user_checkin_count
    result = await mongodb_client.get_user_checkin_count(12345, 67890)
    
    # Verifica se o método count_documents foi chamado com os parâmetros corretos
    mock_user_checkins.count_documents.assert_called_once_with(
        {"chat_id": 12345, "user_id": 67890}
    )
    
    # Verifica o resultado
    assert result == 5

@pytest.mark.asyncio
async def test_get_user_count_error(mongodb_setup):
    """Testa o método get_user_checkin_count com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_user_checkins = mongodb_setup["mock_user_checkins"]
    
    # Configura o mock para lançar uma exceção
    mock_user_checkins.count_documents.side_effect = PyMongoError("Erro de teste")
    
    # Conecta ao banco de dados
    await mongodb_client.connect()
    
    # Executa o método get_user_checkin_count
    result = await mongodb_client.get_user_checkin_count(123, 456)
    
    # Verifica se o método count_documents foi chamado com os parâmetros corretos
    mock_user_checkins.count_documents.assert_called_once_with(
        {"chat_id": 123, "user_id": 456}
    )
    
    # Verifica se o resultado é 0 (valor padrão em caso de erro)
    assert result == 0

@pytest.mark.asyncio
async def test_get_checkin_scoreboard(mongodb_setup):
    """Testa o método get_checkin_scoreboard."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_user_checkins = mongodb_setup["mock_user_checkins"]
    
    # Configura os mocks para os métodos usados
    mock_user_checkins.distinct.return_value = [123, 456]
    
    # Mock para find_one
    mock_user_checkins.find_one.side_effect = [
        {"user_id": 123, "user_name": "Usuário 1", "chat_id": 123},
        {"user_id": 456, "user_name": "Usuário 2", "chat_id": 123}
    ]
    
    # Mock para count_documents
    mock_user_checkins.count_documents.side_effect = [2, 1]
    
    # Conecta ao banco de dados
    await mongodb_client.connect()
    
    # Executa o método get_checkin_scoreboard
    result = await mongodb_client.get_checkin_scoreboard(123)
    
    # Verifica se os métodos foram chamados com os parâmetros corretos
    mock_user_checkins.distinct.assert_called_once_with("user_id", {"chat_id": 123})
    
    # Verifica se find_one foi chamado para cada usuário
    assert mock_user_checkins.find_one.call_count == 2
    
    # Verifica se count_documents foi chamado para cada usuário
    assert mock_user_checkins.count_documents.call_count == 2
    
    # Verifica se o resultado é o esperado
    assert len(result) == 2
    assert result[0]["user_id"] == 123
    assert result[0]["user_name"] == "Usuário 1"
    assert result[0]["count"] == 2
    assert result[1]["user_id"] == 456
    assert result[1]["user_name"] == "Usuário 2"
    assert result[1]["count"] == 1

@pytest.mark.asyncio
async def test_get_checkin_scoreboard_error(mongodb_setup):
    """Testa o método get_checkin_scoreboard com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_user_checkins = mongodb_setup["mock_user_checkins"]
    
    # Configura o mock para lançar uma exceção
    mock_user_checkins.distinct.side_effect = PyMongoError("Erro de teste")
    
    # Conecta ao banco de dados
    await mongodb_client.connect()
    
    # Executa o método get_checkin_scoreboard
    result = await mongodb_client.get_checkin_scoreboard(123)
    
    # Verifica se o método distinct foi chamado
    mock_user_checkins.distinct.assert_called_once_with("user_id", {"chat_id": 123})
    
    # Verifica se o resultado é uma lista vazia (valor padrão em caso de erro)
    assert result == []

@pytest.mark.asyncio
async def test_start_monitoring(mongodb_setup):
    """Testa o início do monitoramento de mensagens."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Mock para a coleção monitored_chats
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura o mock para find_one
    mock_monitored_chats.find_one.return_value = None
    
    # Configura o mock para update_one
    mock_update_result = MagicMock()
    mock_update_result.acknowledged = True
    mock_monitored_chats.update_one.return_value = mock_update_result
    
    # Executa o método start_monitoring
    await mongodb_client.connect()
    result = await mongodb_client.start_monitoring(12345)
    
    # Verifica se o método find_one foi chamado corretamente
    mock_monitored_chats.find_one.assert_called_once_with({"chat_id": 12345})
    
    # Verifica se o método update_one foi chamado corretamente
    mock_monitored_chats.update_one.assert_called_once()
    args, kwargs = mock_monitored_chats.update_one.call_args
    assert args[0] == {"chat_id": 12345}
    assert "active" in args[1]["$set"]
    assert args[1]["$set"]["active"] is True
    assert "started_at" in args[1]["$set"]
    assert kwargs["upsert"] is True
    
    # Verifica o resultado
    assert result is True

@pytest.mark.asyncio
async def test_start_monitoring_already_active(mongodb_setup):
    """Testa o início do monitoramento quando já está ativo."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Mock para a coleção monitored_chats
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura o mock para find_one
    mock_monitored_chats.find_one.return_value = {"chat_id": 12345, "active": True}
    
    # Executa o método start_monitoring
    await mongodb_client.connect()
    result = await mongodb_client.start_monitoring(12345)
    
    # Verifica se o método find_one foi chamado corretamente
    mock_monitored_chats.find_one.assert_called_once_with({"chat_id": 12345})
    
    # Verifica se o método update_one não foi chamado
    mock_monitored_chats.update_one.assert_not_called()
    
    # Verifica o resultado
    assert result is True

@pytest.mark.asyncio
async def test_start_monitoring_error(mongodb_setup):
    """Testa o início do monitoramento com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Mock para a coleção monitored_chats
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura o mock para find_one para lançar uma exceção
    mock_monitored_chats.find_one.side_effect = PyMongoError("Erro de teste")
    
    # Executa o método start_monitoring
    await mongodb_client.connect()
    result = await mongodb_client.start_monitoring(12345)
    
    # Verifica se o método find_one foi chamado corretamente
    mock_monitored_chats.find_one.assert_called_once_with({"chat_id": 12345})
    
    # Verifica se o método update_one não foi chamado
    mock_monitored_chats.update_one.assert_not_called()
    
    # Verifica o resultado
    assert result is False

@pytest.mark.asyncio
async def test_stop_monitoring(mongodb_setup):
    """Testa a parada do monitoramento de mensagens."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Mock para a coleção monitored_chats
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura o mock para update_one
    mock_update_result = MagicMock()
    mock_update_result.acknowledged = True
    mock_monitored_chats.update_one.return_value = mock_update_result
    
    # Executa o método stop_monitoring
    await mongodb_client.connect()
    result = await mongodb_client.stop_monitoring(12345)
    
    # Verifica se o método update_one foi chamado corretamente
    mock_monitored_chats.update_one.assert_called_once()
    args, kwargs = mock_monitored_chats.update_one.call_args
    assert args[0] == {"chat_id": 12345}
    assert "active" in args[1]["$set"]
    assert args[1]["$set"]["active"] is False
    assert "stopped_at" in args[1]["$set"]
    
    # Verifica o resultado
    assert result is True

@pytest.mark.asyncio
async def test_stop_monitoring_error(mongodb_setup):
    """Testa a parada do monitoramento com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Mock para a coleção monitored_chats
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura o mock para update_one para lançar uma exceção
    mock_monitored_chats.update_one.side_effect = PyMongoError("Erro de teste")
    
    # Executa o método stop_monitoring
    await mongodb_client.connect()
    result = await mongodb_client.stop_monitoring(12345)
    
    # Verifica se o método update_one foi chamado corretamente
    mock_monitored_chats.update_one.assert_called_once()
    
    # Verifica o resultado
    assert result is False

@pytest.mark.asyncio
async def test_is_chat_monitored(mongodb_setup):
    """Testa a verificação se um chat está sendo monitorado."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Mock para a coleção monitored_chats
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura o mock para find_one
    mock_monitored_chats.find_one.return_value = {"chat_id": 12345, "active": True}
    
    # Executa o método is_chat_monitored
    await mongodb_client.connect()
    result = await mongodb_client.is_chat_monitored(12345)
    
    # Verifica se o método find_one foi chamado corretamente
    mock_monitored_chats.find_one.assert_called_once_with({"chat_id": 12345})
    
    # Verifica o resultado
    assert result is True

@pytest.mark.asyncio
async def test_is_chat_monitored_not_active(mongodb_setup):
    """Testa a verificação quando o chat não está sendo monitorado."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Mock para a coleção monitored_chats
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura o mock para find_one
    mock_monitored_chats.find_one.return_value = {"chat_id": 12345, "active": False}
    
    # Executa o método is_chat_monitored
    await mongodb_client.connect()
    result = await mongodb_client.is_chat_monitored(12345)
    
    # Verifica se o método find_one foi chamado corretamente
    mock_monitored_chats.find_one.assert_called_once_with({"chat_id": 12345})
    
    # Verifica o resultado
    assert result is False

@pytest.mark.asyncio
async def test_is_chat_monitored_not_found(mongodb_setup):
    """Testa a verificação quando o chat não é encontrado."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Mock para a coleção monitored_chats
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura o mock para find_one
    mock_monitored_chats.find_one.return_value = None
    
    # Executa o método is_chat_monitored
    await mongodb_client.connect()
    result = await mongodb_client.is_chat_monitored(12345)
    
    # Verifica se o método find_one foi chamado corretamente
    mock_monitored_chats.find_one.assert_called_once_with({"chat_id": 12345})
    
    # Verifica o resultado
    assert result is False

@pytest.mark.asyncio
async def test_is_chat_monitored_error(mongodb_setup):
    """Testa a verificação com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Mock para a coleção monitored_chats
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura o mock para find_one para lançar uma exceção
    mock_monitored_chats.find_one.side_effect = PyMongoError("Erro de teste")
    
    # Executa o método is_chat_monitored
    await mongodb_client.connect()
    result = await mongodb_client.is_chat_monitored(12345)
    
    # Verifica se o método find_one foi chamado corretamente
    mock_monitored_chats.find_one.assert_called_once_with({"chat_id": 12345})
    
    # Verifica o resultado
    assert result is False

@pytest.mark.asyncio
async def test_store_message(mongodb_setup):
    """Testa o armazenamento de uma mensagem."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Mock para a coleção monitored_messages
    mock_monitored_messages = AsyncMock()
    mock_db.monitored_messages = mock_monitored_messages
    
    # Configura o mock para insert_one
    mock_insert_result = MagicMock()
    mock_insert_result.acknowledged = True
    mock_monitored_messages.insert_one.return_value = mock_insert_result
    
    # Executa o método store_message
    await mongodb_client.connect()
    timestamp = datetime.now()
    result = await mongodb_client.store_message(
        chat_id=12345,
        message_id=67890,
        user_id=54321,
        user_name="Test User",
        text="Test message",
        timestamp=timestamp
    )
    
    # Verifica se o método insert_one foi chamado corretamente
    mock_monitored_messages.insert_one.assert_called_once()
    args = mock_monitored_messages.insert_one.call_args[0][0]
    assert args["chat_id"] == 12345
    assert args["message_id"] == 67890
    assert args["user_id"] == 54321
    assert args["user_name"] == "Test User"
    assert args["text"] == "Test message"
    assert args["timestamp"] == timestamp
    
    # Verifica o resultado
    assert result is True

@pytest.mark.asyncio
async def test_store_message_error(mongodb_setup):
    """Testa o armazenamento de uma mensagem com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    
    # Mock para a coleção monitored_messages
    mock_monitored_messages = AsyncMock()
    mock_db.monitored_messages = mock_monitored_messages
    
    # Configura o mock para insert_one para lançar uma exceção
    mock_monitored_messages.insert_one.side_effect = PyMongoError("Erro de teste")
    
    # Executa o método store_message
    await mongodb_client.connect()
    timestamp = datetime.now()
    result = await mongodb_client.store_message(
        chat_id=12345,
        message_id=67890,
        user_id=54321,
        user_name="Test User",
        text="Test message",
        timestamp=timestamp
    )
    
    # Verifica se o método insert_one foi chamado corretamente
    mock_monitored_messages.insert_one.assert_called_once()
    
    # Verifica o resultado
    assert result is False

@pytest.mark.asyncio
async def test_get_qa_interaction(mongodb_setup):
    """Testa a função get_qa_interaction."""
    # Configura o mock
    mock_db = mongodb_setup["mock_db"]
    mock_db.qa_interactions.find_one = AsyncMock(return_value={"question": "test"})
    
    # Executa a função
    mongodb_client = mongodb_setup["client"]
    result = await mongodb_client.get_qa_interaction(123, 456)
    
    # Verifica o resultado
    assert result == {"question": "test"}
    mock_db.qa_interactions.find_one.assert_called_once_with({"chat_id": 123, "message_id": 456})

@pytest.mark.asyncio
async def test_get_qa_interaction_error(mongodb_setup):
    """Testa a função get_qa_interaction com erro."""
    # Configura o mock para lançar uma exceção
    mock_db = mongodb_setup["mock_db"]
    mock_db.qa_interactions.find_one = AsyncMock(side_effect=Exception("Test error"))
    
    # Executa a função
    mongodb_client = mongodb_setup["client"]
    result = await mongodb_client.get_qa_interaction(123, 456)
    
    # Verifica o resultado
    assert result is None

@pytest.mark.asyncio
async def test_get_daily_qa_count(mongodb_setup):
    """Testa a função get_daily_qa_count."""
    # Configura o mock
    mock_db = mongodb_setup["mock_db"]
    mock_db.qa_usage.count_documents = AsyncMock(return_value=5)
    
    # Executa a função
    mongodb_client = mongodb_setup["client"]
    result = await mongodb_client.get_daily_qa_count(123, 456)
    
    # Verifica o resultado
    assert result == 5
    mock_db.qa_usage.count_documents.assert_called_once()
    # Verifica se o filtro contém os campos corretos
    call_args = mock_db.qa_usage.count_documents.call_args[0][0]
    assert call_args["user_id"] == 123
    assert call_args["chat_id"] == 456
    assert "$gte" in call_args["timestamp"]

@pytest.mark.asyncio
async def test_get_daily_qa_count_error(mongodb_setup):
    """Testa a função get_daily_qa_count com erro."""
    # Configura o mock para lançar uma exceção
    mock_db = mongodb_setup["mock_db"]
    mock_db.qa_usage.count_documents = AsyncMock(side_effect=Exception("Test error"))
    
    # Executa a função
    mongodb_client = mongodb_setup["client"]
    result = await mongodb_client.get_daily_qa_count(123, 456)
    
    # Verifica o resultado
    assert result == 0

@pytest.mark.asyncio
async def test_get_last_qa_timestamp(mongodb_setup):
    """Testa a função get_last_qa_timestamp."""
    # Configura o mock
    mock_db = mongodb_setup["mock_db"]
    timestamp = datetime.now()
    mock_db.qa_usage.find_one = AsyncMock(return_value={"timestamp": timestamp})
    
    # Executa a função
    mongodb_client = mongodb_setup["client"]
    result = await mongodb_client.get_last_qa_timestamp(123, 456)
    
    # Verifica o resultado
    assert result == timestamp
    mock_db.qa_usage.find_one.assert_called_once()
    # Verifica se os parâmetros estão corretos
    call_args = mock_db.qa_usage.find_one.call_args[0][0]
    assert call_args["user_id"] == 123
    assert call_args["chat_id"] == 456
    # Verifica se a ordenação está correta
    sort_args = mock_db.qa_usage.find_one.call_args[1]["sort"]
    assert sort_args == [("timestamp", -1)]

@pytest.mark.asyncio
async def test_get_last_qa_timestamp_not_found(mongodb_setup):
    """Testa a função get_last_qa_timestamp quando não há registros."""
    # Configura o mock para retornar None
    mock_db = mongodb_setup["mock_db"]
    mock_db.qa_usage.find_one = AsyncMock(return_value=None)
    
    # Executa a função
    mongodb_client = mongodb_setup["client"]
    result = await mongodb_client.get_last_qa_timestamp(123, 456)
    
    # Verifica o resultado
    assert result is None

@pytest.mark.asyncio
async def test_get_last_qa_timestamp_error(mongodb_setup):
    """Testa a função get_last_qa_timestamp com erro."""
    # Configura o mock para lançar uma exceção
    mock_db = mongodb_setup["mock_db"]
    mock_db.qa_usage.find_one = AsyncMock(side_effect=Exception("Test error"))
    
    # Executa a função
    mongodb_client = mongodb_setup["client"]
    result = await mongodb_client.get_last_qa_timestamp(123, 456)
    
    # Verifica o resultado
    assert result is None

@pytest.mark.asyncio
async def test_increment_qa_usage(mongodb_setup):
    """Testa a função increment_qa_usage."""
    # Configura o mock
    mock_db = mongodb_setup["mock_db"]
    mock_db.qa_usage.insert_one = AsyncMock(return_value=MagicMock(acknowledged=True))
    
    # Executa a função
    mongodb_client = mongodb_setup["client"]
    result = await mongodb_client.increment_qa_usage(123, 456)
    
    # Verifica o resultado
    assert result is True
    mock_db.qa_usage.insert_one.assert_called_once()
    # Verifica se os dados inseridos estão corretos
    call_args = mock_db.qa_usage.insert_one.call_args[0][0]
    assert call_args["user_id"] == 123
    assert call_args["chat_id"] == 456
    assert "timestamp" in call_args

@pytest.mark.asyncio
async def test_increment_qa_usage_error(mongodb_setup):
    """Testa a função increment_qa_usage com erro."""
    # Configura o mock para lançar uma exceção
    mock_db = mongodb_setup["mock_db"]
    mock_db.qa_usage.insert_one = AsyncMock(side_effect=Exception("Test error"))
    
    # Executa a função
    mongodb_client = mongodb_setup["client"]
    result = await mongodb_client.increment_qa_usage(123, 456)
    
    # Verifica o resultado
    assert result is False

@pytest.mark.asyncio
async def test_add_to_blacklist(mongodb_setup):
    """Testa a função add_to_blacklist."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para blacklist collection
    mock_blacklist = AsyncMock()
    mock_db.blacklist = mock_blacklist
    
    # Configura mock para insert_one
    mock_blacklist.insert_one.return_value = MagicMock()
    mock_blacklist.insert_one.return_value.inserted_id = "1234567890"
    
    # Testa a função
    result = await mongodb_client.add_to_blacklist(
        chat_id=123456,
        message_id=789,
        user_id=111,
        user_name="Test User",
        username="testuser",
        message_text="Mensagem inapropriada",
        added_by=222,
        added_by_name="Admin User"
    )
    
    # Verifica se o resultado está correto
    assert result == "1234567890"
    
    # Verifica se insert_one foi chamado com os parâmetros corretos
    mock_blacklist.insert_one.assert_called_once()
    call_args = mock_blacklist.insert_one.call_args[0][0]
    assert call_args["chat_id"] == 123456
    assert call_args["message_id"] == 789
    assert call_args["user_id"] == 111
    assert call_args["user_name"] == "Test User"
    assert call_args["username"] == "testuser"
    assert call_args["message_text"] == "Mensagem inapropriada"
    assert call_args["added_by"] == 222
    assert call_args["added_by_name"] == "Admin User"
    assert "added_at" in call_args

@pytest.mark.asyncio
async def test_add_to_blacklist_error(mongodb_setup):
    """Testa a função add_to_blacklist quando ocorre um erro."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para blacklist collection
    mock_blacklist = AsyncMock()
    mock_db.blacklist = mock_blacklist
    
    # Configura mock para insert_one para lançar exceção
    mock_blacklist.insert_one.side_effect = PyMongoError("Erro de teste")
    
    # Testa a função
    result = await mongodb_client.add_to_blacklist(
        chat_id=123456,
        message_id=789,
        user_id=111,
        user_name="Test User"
    )
    
    # Verifica se o resultado está correto
    assert result is None
    
    # Verifica se insert_one foi chamado
    mock_blacklist.insert_one.assert_called_once()

@pytest.mark.asyncio
async def test_get_blacklist(mongodb_setup):
    """Testa a função get_blacklist."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para blacklist collection
    mock_blacklist = AsyncMock()
    mock_db.blacklist = mock_blacklist
    
    # Cria mock para cursor com itens falsos
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = [
        {"_id": "1", "user_name": "User 1"},
        {"_id": "2", "user_name": "User 2"}
    ]
    
    # Configura find e sort para retornar o cursor
    mock_find = AsyncMock()
    mock_find.sort.return_value = mock_cursor
    mock_blacklist.find.return_value = mock_find
    
    # Testa a função
    result = await mongodb_client.get_blacklist(123456)
    
    # Verifica se o resultado está correto
    assert len(result) == 2
    assert result[0]["_id"] == "1"
    assert result[0]["user_name"] == "User 1"
    assert result[1]["_id"] == "2"
    assert result[1]["user_name"] == "User 2"
    
    # Verifica se find foi chamado com os parâmetros corretos
    mock_blacklist.find.assert_called_once_with({"chat_id": 123456})
    mock_find.sort.assert_called_once_with("added_at", -1)

@pytest.mark.asyncio
async def test_get_blacklist_empty(mongodb_setup):
    """Testa a função get_blacklist quando a lista está vazia."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para blacklist collection
    mock_blacklist = AsyncMock()
    mock_db.blacklist = mock_blacklist
    
    # Cria mock para cursor vazio
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = []
    
    # Configura find e sort para retornar o cursor vazio
    mock_find = AsyncMock()
    mock_find.sort.return_value = mock_cursor
    mock_blacklist.find.return_value = mock_find
    
    # Testa a função
    result = await mongodb_client.get_blacklist(123456)
    
    # Verifica se o resultado está correto
    assert result == []
    
    # Verifica se find foi chamado com os parâmetros corretos
    mock_blacklist.find.assert_called_once_with({"chat_id": 123456})
    mock_find.sort.assert_called_once_with("added_at", -1)

@pytest.mark.asyncio
async def test_get_blacklist_error(mongodb_setup):
    """Testa a função get_blacklist quando ocorre um erro."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para blacklist collection
    mock_blacklist = AsyncMock()
    mock_db.blacklist = mock_blacklist
    
    # Configura find para lançar exceção
    mock_blacklist.find.side_effect = PyMongoError("Erro de teste")
    
    # Testa a função
    result = await mongodb_client.get_blacklist(123456)
    
    # Verifica se o resultado está correto
    assert result == []
    
    # Verifica se find foi chamado
    mock_blacklist.find.assert_called_once()

@pytest.mark.asyncio
async def test_get_blacklist_by_group_name(mongodb_setup):
    """Testa a função get_blacklist_by_group_name."""
    mongodb_client = mongodb_setup["client"]
    
    # Configura mocks
    mongodb_client._get_chat_id_by_name = AsyncMock()
    mongodb_client._get_chat_id_by_name.return_value = 123456
    
    mongodb_client.get_blacklist = AsyncMock()
    mongodb_client.get_blacklist.return_value = [
        {"_id": "1", "user_name": "User 1"},
        {"_id": "2", "user_name": "User 2"}
    ]
    
    # Testa a função
    result = await mongodb_client.get_blacklist_by_group_name("GYM NATION")
    
    # Verifica se o resultado está correto
    assert len(result) == 2
    assert result[0]["_id"] == "1"
    assert result[0]["user_name"] == "User 1"
    assert result[1]["_id"] == "2"
    assert result[1]["user_name"] == "User 2"
    
    # Verifica se as funções internas foram chamadas corretamente
    mongodb_client._get_chat_id_by_name.assert_called_once_with("GYM NATION")
    mongodb_client.get_blacklist.assert_called_once_with(123456)

@pytest.mark.asyncio
async def test_get_blacklist_by_group_name_not_found(mongodb_setup):
    """Testa a função get_blacklist_by_group_name quando o grupo não é encontrado."""
    mongodb_client = mongodb_setup["client"]
    
    # Configura mocks
    mongodb_client._get_chat_id_by_name = AsyncMock()
    mongodb_client._get_chat_id_by_name.return_value = None
    
    # Testa a função
    result = await mongodb_client.get_blacklist_by_group_name("GRUPO INEXISTENTE")
    
    # Verifica se o resultado está correto
    assert result == []
    
    # Verifica se get_chat_id_by_name foi chamado
    mongodb_client._get_chat_id_by_name.assert_called_once_with("GRUPO INEXISTENTE")
    
    # Verifica que get_blacklist não foi chamado
    assert not hasattr(mongodb_client.get_blacklist, "called")

@pytest.mark.asyncio
async def test_get_chat_username(mongodb_setup):
    """Testa a função _get_chat_username."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para monitored_chats collection
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura find_one para retornar um chat com username
    mock_monitored_chats.find_one.return_value = {
        "chat_id": 123456,
        "title": "GYM NATION",
        "username": "gymgroup"
    }
    
    # Testa a função
    result = await mongodb_client._get_chat_username(123456)
    
    # Verifica se o resultado está correto
    assert result == "gymgroup"
    
    # Verifica se find_one foi chamado com os parâmetros corretos
    mock_monitored_chats.find_one.assert_called_once_with({"chat_id": 123456})

@pytest.mark.asyncio
async def test_get_chat_username_not_found(mongodb_setup):
    """Testa a função _get_chat_username quando o chat não é encontrado."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para monitored_chats collection
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura find_one para retornar None
    mock_monitored_chats.find_one.return_value = None
    
    # Testa a função
    result = await mongodb_client._get_chat_username(123456)
    
    # Verifica se o resultado está correto
    assert result is None
    
    # Verifica se find_one foi chamado com os parâmetros corretos
    mock_monitored_chats.find_one.assert_called_once_with({"chat_id": 123456})

@pytest.mark.asyncio
async def test_get_chat_id_by_name(mongodb_setup):
    """Testa a função _get_chat_id_by_name."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para monitored_chats collection
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura find_one para retornar um chat
    mock_monitored_chats.find_one.return_value = {
        "chat_id": 123456,
        "title": "GYM NATION",
        "username": "gymgroup"
    }
    
    # Testa a função
    result = await mongodb_client._get_chat_id_by_name("GYM NATION")
    
    # Verifica se o resultado está correto
    assert result == 123456
    
    # Verifica se find_one foi chamado com os parâmetros corretos
    mock_monitored_chats.find_one.assert_called_once()
    call_args = mock_monitored_chats.find_one.call_args[0][0]
    assert "$regex" in call_args["title"]
    assert call_args["title"]["$regex"] == "GYM NATION"
    assert call_args["title"]["$options"] == "i"

@pytest.mark.asyncio
async def test_get_chat_id_by_name_not_found(mongodb_setup):
    """Testa a função _get_chat_id_by_name quando o grupo não é encontrado."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para monitored_chats collection
    mock_monitored_chats = AsyncMock()
    mock_db.monitored_chats = mock_monitored_chats
    
    # Configura find_one para retornar None
    mock_monitored_chats.find_one.return_value = None
    
    # Testa a função
    result = await mongodb_client._get_chat_id_by_name("GRUPO INEXISTENTE")
    
    # Verifica se o resultado está correto
    assert result is None
    
    # Verifica se find_one foi chamado
    mock_monitored_chats.find_one.assert_called_once()

@pytest.mark.asyncio
async def test_remove_from_blacklist(mongodb_setup):
    """Testa a função remove_from_blacklist."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para blacklist collection
    mock_blacklist = AsyncMock()
    mock_db.blacklist = mock_blacklist
    
    # ID do item a ser removido
    item_id = "60f1a5b5a9c1e2b3c4d5e6f7"
    
    # Configura mock para delete_one
    mock_blacklist.delete_one.return_value = MagicMock()
    mock_blacklist.delete_one.return_value.deleted_count = 1
    
    # Testa a função
    result = await mongodb_client.remove_from_blacklist(item_id)
    
    # Verifica se o resultado está correto
    assert result is True
    
    # Verifica se delete_one foi chamado com os parâmetros corretos
    from bson.objectid import ObjectId
    mock_blacklist.delete_one.assert_called_once()
    call_args = mock_blacklist.delete_one.call_args[0][0]
    assert call_args == {"_id": ObjectId(item_id)}

@pytest.mark.asyncio
async def test_remove_from_blacklist_not_found(mongodb_setup):
    """Testa a função remove_from_blacklist quando o item não é encontrado."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para blacklist collection
    mock_blacklist = AsyncMock()
    mock_db.blacklist = mock_blacklist
    
    # ID do item a ser removido
    item_id = "60f1a5b5a9c1e2b3c4d5e6f7"
    
    # Configura mock para delete_one
    mock_blacklist.delete_one.return_value = MagicMock()
    mock_blacklist.delete_one.return_value.deleted_count = 0
    
    # Testa a função
    result = await mongodb_client.remove_from_blacklist(item_id)
    
    # Verifica se o resultado está correto
    assert result is False

@pytest.mark.asyncio
async def test_remove_from_blacklist_error(mongodb_setup):
    """Testa a função remove_from_blacklist quando ocorre um erro."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para blacklist collection
    mock_blacklist = AsyncMock()
    mock_db.blacklist = mock_blacklist
    
    # Configura mock para delete_one para lançar exceção
    mock_blacklist.delete_one.side_effect = PyMongoError("Erro de teste")
    
    # Testa a função
    result = await mongodb_client.remove_from_blacklist("60f1a5b5a9c1e2b3c4d5e6f7")
    
    # Verifica se o resultado está correto
    assert result is False

@pytest.mark.asyncio
async def test_remove_from_blacklist_by_link(mongodb_setup):
    """Testa a função remove_from_blacklist_by_link."""
    mock_db = monkeypatch_setup(mongodb_setup["client"])  # Ajustado para usar monkeypatch_setup
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para blacklist collection
    mock_blacklist = AsyncMock()
    mock_db.blacklist = mock_blacklist
    
    # Link da mensagem a ser removida
    message_link = "https://t.me/c/2288213607/1452"
    
    # Configura mock para delete_one
    mock_blacklist.delete_one.return_value = MagicMock()
    mock_blacklist.delete_one.return_value.deleted_count = 1
    
    # Testa a função
    result = await mongodb_client.remove_from_blacklist_by_link(message_link)
    
    # Verifica se o resultado está correto
    assert result is True
    
    # Verifica se delete_one foi chamado com os parâmetros corretos
    mock_blacklist.delete_one.assert_called_once()
    call_args = mock_blacklist.delete_one.call_args[0][0]
    assert call_args["chat_id"] == -1002288213607  # -100 + 2288213607
    assert call_args["message_id"] == 1452

@pytest.mark.asyncio
async def test_remove_from_blacklist_by_link_invalid_format(mongodb_setup):
    """Testa a função remove_from_blacklist_by_link com formato inválido."""
    mock_db = monkeypatch_setup(mongodb_setup["client"])  # Ajustado para usar monkeypatch_setup
    mongodb_client = mongodb_setup["client"]
    
    # Link inválido
    invalid_link = "https://t.me/invalid_link"
    
    # Testa a função
    result = await mongodb_client.remove_from_blacklist_by_link(invalid_link)
    
    # Verifica se o resultado está correto
    assert result is False
    
    # Verifica que delete_one não foi chamado
    assert not hasattr(mock_db.blacklist, "delete_one") or not mock_db.blacklist.delete_one.called

@pytest.mark.asyncio
async def test_remove_from_blacklist_by_link_not_found(mongodb_setup):
    """Testa a função remove_from_blacklist_by_link quando a mensagem não é encontrada."""
    mock_db = monkeypatch_setup(mongodb_setup["client"])  # Ajustado para usar monkeypatch_setup
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para blacklist collection
    mock_blacklist = AsyncMock()
    mock_db.blacklist = mock_blacklist
    
    # Link da mensagem a ser removida
    message_link = "https://t.me/c/2288213607/1452"
    
    # Configura mock para delete_one para indicar que nenhum item foi removido
    mock_blacklist.delete_one.return_value = MagicMock()
    mock_blacklist.delete_one.return_value.deleted_count = 0
    
    # Testa a função
    result = await mongodb_client.remove_from_blacklist_by_link(message_link)
    
    # Verifica se o resultado está correto
    assert result is False

@pytest.mark.asyncio
async def test_remove_from_blacklist_by_link_error(mongodb_setup):
    """Testa a função remove_from_blacklist_by_link quando ocorre um erro."""
    mock_db = monkeypatch_setup(mongodb_setup["client"])  # Ajustado para usar monkeypatch_setup
    mongodb_client = mongodb_setup["client"]
    
    # Configura mock para blacklist collection
    mock_blacklist = AsyncMock()
    mock_db.blacklist = mock_blacklist
    
    # Link da mensagem a ser removida
    message_link = "https://t.me/c/2288213607/1452"
    
    # Configura mock para delete_one para lançar exceção
    mock_blacklist.delete_one.side_effect = Exception("Erro de teste")
    
    # Testa a função
    result = await mongodb_client.remove_from_blacklist_by_link(message_link)
    
    # Verifica se o resultado está correto
    assert result is False

@pytest.mark.asyncio
async def test_get_chat_id_by_name_with_username(mongodb_setup):
    """
    Testa a obtenção do ID de um chat pelo username.
    """
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    mock_monitored_chats = mongodb_setup["mock_monitored_chats"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para find_one
    expected_chat = {
        "chat_id": 12345,
        "title": "Test Group",
        "username": "testgroup"
    }
    mock_monitored_chats.find_one.return_value = expected_chat
    
    # Executa o método _get_chat_id_by_name
    result = await mongodb_client._get_chat_id_by_name("testgroup")
    
    # Verifica se o método find_one foi chamado com os parâmetros corretos
    mock_monitored_chats.find_one.assert_called_once_with({
        "$or": [
            {"title": {"$regex": "testgroup", "$options": "i"}},
            {"username": {"$regex": "testgroup", "$options": "i"}}
        ]
    })
    
    # Verifica o resultado
    assert result == expected_chat["chat_id"]

@pytest.mark.asyncio
async def test_get_chat_id_by_name_with_title(mongodb_setup):
    """
    Testa a obtenção do ID de um chat pelo título.
    """
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    mock_monitored_chats = mongodb_setup["mock_monitored_chats"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para find_one
    expected_chat = {
        "chat_id": 12345,
        "title": "Test Group",
        "username": "testgroup"
    }
    mock_monitored_chats.find_one.return_value = expected_chat
    
    # Executa o método _get_chat_id_by_name
    result = await mongodb_client._get_chat_id_by_name("Test Group")
    
    # Verifica se o método find_one foi chamado com os parâmetros corretos
    mock_monitored_chats.find_one.assert_called_once_with({
        "$or": [
            {"title": {"$regex": "Test Group", "$options": "i"}},
            {"username": {"$regex": "Test Group", "$options": "i"}}
        ]
    })
    
    # Verifica o resultado
    assert result == expected_chat["chat_id"]

@pytest.mark.asyncio
async def test_get_chat_id_by_name_not_found(mongodb_setup):
    """
    Testa a obtenção do ID de um chat quando não encontrado.
    """
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    mock_monitored_chats = mongodb_setup["mock_monitored_chats"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para find_one retornar None
    mock_monitored_chats.find_one.return_value = None
    
    # Executa o método _get_chat_id_by_name
    result = await mongodb_client._get_chat_id_by_name("Non Existent Group")
    
    # Verifica se o método find_one foi chamado com os parâmetros corretos
    mock_monitored_chats.find_one.assert_called_once_with({
        "$or": [
            {"title": {"$regex": "Non Existent Group", "$options": "i"}},
            {"username": {"$regex": "Non Existent Group", "$options": "i"}}
        ]
    })
    
    # Verifica o resultado
    assert result is None

@pytest.mark.asyncio
async def test_get_chat_id_by_name_error(mongodb_setup):
    """
    Testa a obtenção do ID de um chat quando ocorre um erro.
    """
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client"]
    mock_db = mongodb_setup["mock_db"]
    mock_monitored_chats = mongodb_setup["mock_monitored_chats"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para find_one lançar uma exceção
    mock_monitored_chats.find_one.side_effect = PyMongoError("Database error")
    
    # Executa o método _get_chat_id_by_name
    result = await mongodb_client._get_chat_id_by_name("Test Group")
    
    # Verifica se o método find_one foi chamado com os parâmetros corretos
    mock_monitored_chats.find_one.assert_called_once_with({
        "$or": [
            {"title": {"$regex": "Test Group", "$options": "i"}},
            {"username": {"$regex": "Test Group", "$options": "i"}}
        ]
    })
    
    # Verifica o resultado
    assert result is None

# Função auxiliar para monkeypatching
def monkeypatch_setup(client):
    """Configura monkeypatching para os testes de MongoDB."""
    mock_db = MagicMock()
    # Substitui o atributo db do cliente pelo mock
    client.db = mock_db
    return mock_db 
