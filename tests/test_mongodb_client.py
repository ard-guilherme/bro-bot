"""
Testes para o cliente MongoDB.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from pymongo.errors import PyMongoError
from src.utils.mongodb_client import MongoDBClient
import re # Importar re
from bson import ObjectId # Adicionar importação
# Imports que estavam faltando
from motor.motor_asyncio import AsyncIOMotorCursor, AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

@pytest_asyncio.fixture
async def mongodb_setup(mocker):
    """Configura o ambiente de teste para o MongoDB."""
    mock_motor_client_constructor = mocker.patch('motor.motor_asyncio.AsyncIOMotorClient')
    mock_motor_instance = AsyncMock(spec=AsyncIOMotorClient)
    mock_motor_client_constructor.return_value = mock_motor_instance
    mock_db = AsyncMock(spec=AsyncIOMotorDatabase)
    mock_motor_instance.__getitem__.return_value = mock_db
    mock_motor_instance.close = AsyncMock() # Garantir que close seja AsyncMock

    # --- Mocks das coleções e métodos --- #
    # Função auxiliar para criar coleção mockada com métodos async
    def create_mock_collection(spec=AsyncIOMotorCollection):
        collection = AsyncMock(spec=spec)
        # Métodos que são awaitable no código de produção
        collection.find_one = AsyncMock()
        collection.insert_one = AsyncMock()
        collection.update_one = AsyncMock()
        collection.update_many = AsyncMock()
        collection.delete_one = AsyncMock()
        collection.delete_many = AsyncMock() # Adicionar se usado
        collection.count_documents = AsyncMock()
        collection.distinct = AsyncMock()
        # Métodos que retornam cursores (não são await diretos)
        collection.find = MagicMock() # Retorna um cursor mockado
        collection.aggregate = MagicMock() # Retorna um cursor mockado
        return collection

    mock_checkin_anchors = create_mock_collection()
    mock_user_checkins = create_mock_collection()
    mock_qa_interactions = create_mock_collection()
    mock_qa_usage = create_mock_collection()
    mock_monitored_chats = create_mock_collection()
    mock_monitored_messages = create_mock_collection()
    mock_bot_admins = create_mock_collection()
    mock_blacklist = create_mock_collection()

    # Atribui coleções mockadas ao db mockado
    mock_db.checkin_anchors = mock_checkin_anchors
    mock_db.user_checkins = mock_user_checkins
    mock_db.qa_interactions = mock_qa_interactions
    mock_db.qa_usage = mock_qa_usage
    mock_db.monitored_chats = mock_monitored_chats
    mock_db.monitored_messages = mock_monitored_messages
    mock_db.bot_admins = mock_bot_admins
    mock_db.blacklist = mock_blacklist

    mongodb_client = MongoDBClient("mongodb://test:test@localhost:27017")
    await mongodb_client.connect("test_db")

    mocks = {
        "client_wrapper": mongodb_client,
        "mock_motor_client_constructor": mock_motor_client_constructor,
        "mock_motor_instance": mock_motor_instance,
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
    yield mocks
    await mongodb_client.close()

@pytest.mark.asyncio
async def test_connect(mongodb_setup):
    """Testa a conexão com o MongoDB."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_motor_client_constructor = mongodb_setup["mock_motor_client_constructor"]
    mock_motor_instance = mongodb_setup["mock_motor_instance"]
    mock_db = mongodb_setup["mock_db"]

    # Verifica se o cliente foi criado com a string de conexão correta
    mock_motor_client_constructor.assert_called_once_with("mongodb://test:test@localhost:27017")

    # Verifica se o banco de dados foi selecionado corretamente
    mock_motor_instance.__getitem__.assert_called_once_with("test_db")

    # Verifica se o cliente e o banco de dados foram armazenados
    assert mongodb_client.client == mock_motor_instance
    assert mongodb_client.db == mock_db

@pytest.mark.asyncio
async def test_connect_error(mongodb_setup):
    """Testa a conexão com o MongoDB com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_motor_client_constructor = mongodb_setup["mock_motor_client_constructor"]
    
    # Configura o mock para lançar uma exceção
    mock_motor_client_constructor.side_effect = PyMongoError("Connection error")
    
    # Verifica se a exceção é propagada
    with pytest.raises(PyMongoError):
        await mongodb_client.connect("test_db")

@pytest.mark.asyncio
async def test_close(mongodb_setup):
    """Testa o fechamento da conexão com o MongoDB."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_motor_instance = mongodb_setup["mock_motor_instance"]
    
    # Configura o cliente
    mongodb_client.client = mock_motor_instance
    
    # Executa o método close
    await mongodb_client.close()
    
    # Verifica se o método close foi chamado
    mock_motor_instance.close.assert_called_once()

@pytest.mark.asyncio
async def test_set_checkin_anchor(mongodb_setup):
    """Testa a definição de uma mensagem como âncora de check-in."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
async def test_record_user_checkin_success(mongodb_setup, mocker):
    """Testa o registro de check-in com sucesso."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_user_checkins = mongodb_setup["mock_user_checkins"]

    # Mock para a âncora ativa
    mock_active_anchor = {"_id": ObjectId(), "points_value": 1}
    mongodb_client.get_active_checkin = AsyncMock(return_value=mock_active_anchor)

    # Mock para find_one (usuário não fez check-in ainda)
    mock_user_checkins.find_one.return_value = None
    # Mock para insert_one (sucesso)
    mock_insert_result = MagicMock()
    mock_insert_result.acknowledged = True
    mock_user_checkins.insert_one.return_value = mock_insert_result

    # Mock para calculate_user_total_score (deve ser AsyncMock)
    mock_calculate_score = mocker.patch.object(mongodb_client, 'calculate_user_total_score', new_callable=AsyncMock)
    mock_calculate_score.return_value = 5

    # Executa o método record_user_checkin
    result = await mongodb_client.record_user_checkin(123, 456, "Test User", "testuser")

    # Verifica se get_active_checkin foi chamado
    mongodb_client.get_active_checkin.assert_called_once_with(123)
    # Verifica se find_one foi chamado para checar check-in existente
    mock_user_checkins.find_one.assert_called_once_with({
        "chat_id": 123,
        "user_id": 456,
        "anchor_id": mock_active_anchor["_id"]
    })
    # Verifica se insert_one foi chamado
    mock_user_checkins.insert_one.assert_called_once()
    # Verifica se calculate_user_total_score foi chamado
    mock_calculate_score.assert_called_once_with(123, 456)
    # Verifica se o método retornou o score calculado
    assert result == 5

@pytest.mark.asyncio
async def test_record_user_checkin_error(mongodb_setup):
    """Testa o registro de check-in com erro."""
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
async def test_get_checkin_scoreboard(mongodb_setup, mocker):
    """Testa o método get_checkin_scoreboard."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_user_checkins = mongodb_setup["mock_user_checkins"]

    scoreboard_data = [
        {"user_id": 1, "user_name": "User A", "username": "usera", "score": 10, "last_checkin": datetime(2023, 1, 10)},
        {"user_id": 2, "user_name": "User B", "username": "userb", "score": 5, "last_checkin": datetime(2023, 1, 9)},
    ]

    # Configura o mock da agregação
    mock_aggregate_cursor = MagicMock()
    mock_aggregate_cursor.to_list = AsyncMock(return_value=scoreboard_data) # Mock to_list como AsyncMock
    mock_user_checkins.aggregate.return_value = mock_aggregate_cursor

    result = await mongodb_client.get_checkin_scoreboard(123)

    mock_user_checkins.aggregate.assert_called_once()
    pipeline_arg = mock_user_checkins.aggregate.call_args[0][0]
    assert isinstance(pipeline_arg, list)
    assert len(pipeline_arg) > 0
    assert pipeline_arg[0] == {"$match": {"chat_id": 123, "points_value": {"$exists": True}}}

    mock_aggregate_cursor.to_list.assert_called_once_with(length=None)
    assert result == scoreboard_data

@pytest.mark.asyncio
async def test_get_checkin_scoreboard_error(mongodb_setup, mocker):
    """Testa o método get_checkin_scoreboard com erro."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_user_checkins = mongodb_setup["mock_user_checkins"]

    # Configura aggregate para lançar erro
    mock_user_checkins.aggregate.side_effect = PyMongoError("Erro de agregação")

    result = await mongodb_client.get_checkin_scoreboard(123)

    mock_user_checkins.aggregate.assert_called_once()
    assert result == [] # Espera lista vazia em caso de erro

@pytest.mark.asyncio
async def test_get_daily_qa_count(mongodb_setup):
    """Testa a função get_daily_qa_count."""
    # Configura o mock
    mock_db = mongodb_setup["mock_db"]
    mock_db.qa_usage.count_documents = AsyncMock(return_value=5)
    
    # Executa a função
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
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
    mongodb_client = mongodb_setup["client_wrapper"]
    result = await mongodb_client.increment_qa_usage(123, 456)
    
    # Verifica o resultado
    assert result is False

@pytest.mark.asyncio
async def test_add_to_blacklist(mongodb_setup):
    """Testa a função add_to_blacklist."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client_wrapper"]
    
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
    mongodb_client = mongodb_setup["client_wrapper"]
    
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
async def test_get_blacklist(mongodb_setup, mocker):
    """Testa a função get_blacklist."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_blacklist_collection = mongodb_setup["mock_blacklist"]

    fake_data = [
        {"_id": "1", "user_name": "User 1", "added_at": datetime(2023, 1, 1)},
        {"_id": "2", "user_name": "User 2", "added_at": datetime(2023, 1, 2)}
    ]

    # Abordagem Simplificada: Mockar o resultado final da iteração
    mock_cursor_final = AsyncMock()
    mock_cursor_final.__aiter__.return_value = iter(fake_data) # Simular iterador síncrono aqui pode funcionar

    # Mock find().sort() para retornar algo que seja async iterable
    mock_cursor_intermediate = MagicMock(spec=AsyncIOMotorCursor)
    # O sort retorna o iterável mockado final
    mock_cursor_intermediate.sort.return_value = mock_cursor_final
    # O find retorna o cursor intermediário
    mock_blacklist_collection.find.return_value = mock_cursor_intermediate

    # Executa a função que será testada
    result = await mongodb_client.get_blacklist(123456)

    # Verificações
    mock_blacklist_collection.find.assert_called_once_with({"chat_id": 123456})
    mock_cursor_intermediate.sort.assert_called_once_with("added_at", -1)
    assert result == fake_data

@pytest.mark.asyncio
async def test_get_blacklist_empty(mongodb_setup, mocker):
    """Testa a função get_blacklist quando a lista está vazia."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_blacklist_collection = mongodb_setup["mock_blacklist"]

    # Mock para cursor vazio
    mock_async_iterator = mocker.AsyncMock()
    mock_async_iterator.__anext__.side_effect = StopAsyncIteration()

    mock_cursor = MagicMock(spec=AsyncIOMotorCursor)
    mock_cursor.sort.return_value = mock_cursor # Sort retorna ele mesmo
    mock_cursor.__aiter__.return_value = mock_async_iterator # Iterador vazio

    # Find retorna o MagicMock síncrono
    mock_blacklist_collection.find.return_value = mock_cursor

    # Testa a função
    result = await mongodb_client.get_blacklist(123456)

    # Verifica
    mock_blacklist_collection.find.assert_called_once_with({"chat_id": 123456})
    mock_cursor.sort.assert_called_once_with("added_at", -1)
    assert result == []

@pytest.mark.asyncio
async def test_get_blacklist_error(mongodb_setup):
    """Testa a função get_blacklist quando ocorre um erro."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_blacklist_collection = mongodb_setup["mock_blacklist"]

    # Find retorna um MagicMock cujo método sort levanta erro
    mock_cursor = MagicMock(spec=AsyncIOMotorCursor)
    mock_cursor.sort.side_effect = PyMongoError("Erro de teste sort")
    mock_blacklist_collection.find.return_value = mock_cursor

    # Testa a função
    result = await mongodb_client.get_blacklist(123456)

    # Verifica chamada
    mock_blacklist_collection.find.assert_called_once_with({"chat_id": 123456})
    mock_cursor.sort.assert_called_once_with("added_at", -1)
    # Verifica o resultado
    assert result == []

@pytest.mark.asyncio
async def test_get_blacklist_by_group_name(mongodb_setup):
    """Testa a função get_blacklist_by_group_name."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_monitored = mongodb_setup["mock_monitored_chats"]
    mock_blacklist = mongodb_setup["mock_blacklist"]
    
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
    mongodb_client = mongodb_setup["client_wrapper"]
    
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
    mongodb_client = mongodb_setup["client_wrapper"]
    
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
    mongodb_client = mongodb_setup["client_wrapper"]
    
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
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_monitored_chats = mongodb_setup["mock_monitored_chats"]

    # Configura o banco de dados
    mongodb_client.db = mock_db

    # Configura find_one para retornar um chat
    expected_chat = {
        "chat_id": 123456,
        "title": "GYM NATION",
        "username": "gymgroup"
    }
    mock_monitored_chats.find_one.return_value = expected_chat

    # Testa a função
    result = await mongodb_client._get_chat_id_by_name("GYM NATION")

    # Verifica se o resultado está correto
    assert result == 123456

    # Verifica se find_one foi chamado com os parâmetros corretos
    expected_query = re.escape("GYM NATION")
    expected_or_query = {
        "$or": [
            {"title": {"$regex": f'^{expected_query}$', "$options": "i"}},
            {"title": {"$regex": expected_query, "$options": "i"}},
            {"username": {"$regex": f'^{expected_query}$', "$options": "i"}},
            {"username": {"$regex": expected_query, "$options": "i"}}
        ]
    }
    mock_monitored_chats.find_one.assert_called_once_with(expected_or_query)

@pytest.mark.asyncio
async def test_get_chat_id_by_name_not_found(mongodb_setup, mocker):
    """Testa a função _get_chat_id_by_name quando o grupo não é encontrado."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_monitored_chats = mongodb_setup["mock_monitored_chats"]

    # Configura o banco de dados
    mongodb_client.db = mock_db

    # Configura find_one para retornar None
    mock_monitored_chats.find_one.return_value = None

    # Configura find({}) para retornar um iterador async vazio (para o logging)
    mock_find_cursor = MagicMock()
    mock_find_iterator = mocker.AsyncMock()
    mock_find_iterator.__anext__.side_effect = StopAsyncIteration()
    mock_find_cursor.__aiter__.return_value = mock_find_iterator
    mock_monitored_chats.find.return_value = mock_find_cursor

    # Executa o método _get_chat_id_by_name
    result = await mongodb_client._get_chat_id_by_name("Non Existent Group")

    # Verifica se o método find_one foi chamado com os parâmetros corretos
    expected_query = re.escape("Non Existent Group")
    expected_or_query = {
        "$or": [
            {"title": {"$regex": f'^{expected_query}$', "$options": "i"}},
            {"title": {"$regex": expected_query, "$options": "i"}},
            {"username": {"$regex": f'^{expected_query}$', "$options": "i"}},
            {"username": {"$regex": expected_query, "$options": "i"}}
        ]
    }
    mock_monitored_chats.find_one.assert_called_once_with(expected_or_query)
    # Verifica a chamada ao find({}) para o logging
    mock_monitored_chats.find.assert_called_once_with({})

    # Verifica o resultado
    assert result is None

@pytest.mark.asyncio
async def test_get_chat_id_by_name_error(mongodb_setup):
    """
    Testa a obtenção do ID de um chat quando ocorre um erro.
    """
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_db = mongodb_setup["mock_db"]
    mock_monitored_chats = mongodb_setup["mock_monitored_chats"]
    
    # Configura o banco de dados
    mongodb_client.db = mock_db
    
    # Configura o mock para find_one lançar uma exceção
    mock_monitored_chats.find_one.side_effect = PyMongoError("Database error")
    
    # Executa o método _get_chat_id_by_name
    result = await mongodb_client._get_chat_id_by_name("Test Group")
    
    # Verifica se o método find_one foi chamado com os parâmetros corretos
    expected_query = re.escape("Test Group")
    expected_or_query = {
        "$or": [
            {"title": {"$regex": f'^{expected_query}$', "$options": "i"}},
            {"title": {"$regex": expected_query, "$options": "i"}},
            {"username": {"$regex": f'^{expected_query}$', "$options": "i"}},
            {"username": {"$regex": expected_query, "$options": "i"}}
        ]
    }
    mock_monitored_chats.find_one.assert_called_once_with(expected_or_query)
    
    # Verifica o resultado
    assert result is None

@pytest.mark.asyncio
async def test_get_chat_id_by_name_with_username(mongodb_setup):
    """
    Testa a obtenção do ID de um chat pelo username.
    """
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client_wrapper"]
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
    expected_query = re.escape("testgroup")
    expected_or_query = {
        "$or": [
            {"title": {"$regex": f'^{expected_query}$', "$options": "i"}},
            {"title": {"$regex": expected_query, "$options": "i"}},
            {"username": {"$regex": f'^{expected_query}$', "$options": "i"}},
            {"username": {"$regex": expected_query, "$options": "i"}}
        ]
    }
    mock_monitored_chats.find_one.assert_called_once_with(expected_or_query)
    
    # Verifica o resultado
    assert result == expected_chat["chat_id"]

@pytest.mark.asyncio
async def test_get_chat_id_by_name_with_title(mongodb_setup):
    """
    Testa a obtenção do ID de um chat pelo título.
    """
    # Obtém os mocks do fixture
    mongodb_client = mongodb_setup["client_wrapper"]
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
    expected_query = re.escape("Test Group")
    expected_or_query = {
        "$or": [
            {"title": {"$regex": f'^{expected_query}$', "$options": "i"}},
            {"title": {"$regex": expected_query, "$options": "i"}},
            {"username": {"$regex": f'^{expected_query}$', "$options": "i"}},
            {"username": {"$regex": expected_query, "$options": "i"}}
        ]
    }
    mock_monitored_chats.find_one.assert_called_once_with(expected_or_query)
    
    # Verifica o resultado
    assert result == expected_chat["chat_id"]

@pytest.mark.asyncio
async def test_remove_from_blacklist(mongodb_setup):
    """Testa a função remove_from_blacklist."""
    mock_db = mongodb_setup["mock_db"]
    mongodb_client = mongodb_setup["client_wrapper"]
    
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
    mongodb_client = mongodb_setup["client_wrapper"]
    
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
    mongodb_client = mongodb_setup["client_wrapper"]
    
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
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_db = monkeypatch_setup(mongodb_client)  # Passa o client_wrapper correto
    
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
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_db = monkeypatch_setup(mongodb_client)  # Passa o client_wrapper correto
    
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
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_db = monkeypatch_setup(mongodb_client)  # Passa o client_wrapper correto
    
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
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_db = monkeypatch_setup(mongodb_client)  # Passa o client_wrapper correto
    
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
@patch("src.utils.mongodb_client.MongoDBClient.get_chat_info_by_title")
async def test_get_chat_id_by_group_name_success(mock_get_chat_info, mongodb_setup):
    """Testa get_chat_id_by_group_name com sucesso."""
    mongodb_client = mongodb_setup["client_wrapper"]
    group_name = "Test Group"
    expected_chat_id = -100123456

    # Mock para get_chat_info_by_title retornar um chat ativo
    mock_get_chat_info.return_value = {
        "chat_id": expected_chat_id,
        "title": group_name,
        "active": True
    }

    result = await mongodb_client.get_chat_id_by_group_name(group_name)

    assert result == expected_chat_id
    mock_get_chat_info.assert_called_once_with(group_name)

@pytest.mark.asyncio
@patch("src.utils.mongodb_client.MongoDBClient.get_chat_info_by_title")
async def test_get_chat_id_by_group_name_not_active(mock_get_chat_info, mongodb_setup):
    """Testa get_chat_id_by_group_name quando o chat não está ativo."""
    mongodb_client = mongodb_setup["client_wrapper"]
    group_name = "Inactive Group"

    # Mock para get_chat_info_by_title retornar um chat inativo
    mock_get_chat_info.return_value = {
        "chat_id": -100999888,
        "title": group_name,
        "active": False
    }

    result = await mongodb_client.get_chat_id_by_group_name(group_name)

    assert result is None
    mock_get_chat_info.assert_called_once_with(group_name)

@pytest.mark.asyncio
@patch("src.utils.mongodb_client.MongoDBClient.get_chat_info_by_title")
async def test_get_chat_id_by_group_name_not_found(mock_get_chat_info, mongodb_setup):
    """Testa get_chat_id_by_group_name quando o grupo não é encontrado."""
    mongodb_client = mongodb_setup["client_wrapper"]
    group_name = "NonExistent Group"

    # Mock para get_chat_info_by_title retornar None
    mock_get_chat_info.return_value = None

    result = await mongodb_client.get_chat_id_by_group_name(group_name)

    assert result is None
    mock_get_chat_info.assert_called_once_with(group_name)
    
@pytest.mark.asyncio
@patch("src.utils.mongodb_client.MongoDBClient.get_chat_info_by_title")
async def test_get_chat_id_by_group_name_invalid_id(mock_get_chat_info, mongodb_setup):
    """Testa get_chat_id_by_group_name quando o chat_id não é numérico."""
    mongodb_client = mongodb_setup["client_wrapper"]
    group_name = "Group With Invalid ID"

    # Mock para get_chat_info_by_title retornar um chat ativo com ID inválido
    mock_get_chat_info.return_value = {
        "chat_id": "invalid_id_string",
        "title": group_name,
        "active": True
    }

    result = await mongodb_client.get_chat_id_by_group_name(group_name)

    assert result is None
    mock_get_chat_info.assert_called_once_with(group_name)

@pytest.mark.asyncio
async def test_remove_blacklist_items_by_ids_success(mongodb_setup):
    """Testa remove_blacklist_items_by_ids com sucesso."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_db = mongodb_setup["mock_db"]
    mock_blacklist = mongodb_setup["mock_blacklist"]
    mongodb_client.db = mock_db

    ids_to_remove_str = ["60f1a5b5a9c1e2b3c4d5e6f7", "60f1a5b5a9c1e2b3c4d5e6f8"]
    ids_to_remove_obj = [ObjectId(id_str) for id_str in ids_to_remove_str]
    
    # Mock para delete_many retornar sucesso
    mock_result = MagicMock()
    mock_result.deleted_count = 2
    mock_blacklist.delete_many.return_value = mock_result

    result_count = await mongodb_client.remove_blacklist_items_by_ids(ids_to_remove_str)

    assert result_count == 2
    mock_blacklist.delete_many.assert_called_once_with({"_id": {"$in": ids_to_remove_obj}})

@pytest.mark.asyncio
async def test_remove_blacklist_items_by_ids_mixed_types(mongodb_setup):
    """Testa remove_blacklist_items_by_ids com IDs ObjectId e string."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_db = mongodb_setup["mock_db"]
    mock_blacklist = mongodb_setup["mock_blacklist"]
    mongodb_client.db = mock_db

    obj_id = ObjectId()
    str_id = "60f1a5b5a9c1e2b3c4d5e6f8"
    ids_to_remove_mixed = [obj_id, str_id]
    expected_obj_ids = [obj_id, ObjectId(str_id)]
    
    # Mock para delete_many retornar sucesso
    mock_result = MagicMock()
    mock_result.deleted_count = 2
    mock_blacklist.delete_many.return_value = mock_result

    result_count = await mongodb_client.remove_blacklist_items_by_ids(ids_to_remove_mixed)

    assert result_count == 2
    mock_blacklist.delete_many.assert_called_once_with({"_id": {"$in": expected_obj_ids}})

@pytest.mark.asyncio
async def test_remove_blacklist_items_by_ids_invalid_id(mongodb_setup):
    """Testa remove_blacklist_items_by_ids com um ID inválido na lista."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_db = mongodb_setup["mock_db"]
    mock_blacklist = mongodb_setup["mock_blacklist"]
    mongodb_client.db = mock_db

    valid_id_str = "60f1a5b5a9c1e2b3c4d5e6f7"
    invalid_id_str = "invalid-string"
    ids_to_remove = [valid_id_str, invalid_id_str]
    expected_obj_ids = [ObjectId(valid_id_str)] # Apenas o ID válido deve ser passado

    # Mock para delete_many retornar sucesso (para o ID válido)
    mock_result = MagicMock()
    mock_result.deleted_count = 1
    mock_blacklist.delete_many.return_value = mock_result

    result_count = await mongodb_client.remove_blacklist_items_by_ids(ids_to_remove)

    assert result_count == 1
    mock_blacklist.delete_many.assert_called_once_with({"_id": {"$in": expected_obj_ids}})

@pytest.mark.asyncio
async def test_remove_blacklist_items_by_ids_all_invalid(mongodb_setup):
    """Testa remove_blacklist_items_by_ids quando todos os IDs são inválidos."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_db = mongodb_setup["mock_db"]
    mock_blacklist = mongodb_setup["mock_blacklist"]
    mongodb_client.db = mock_db

    ids_to_remove = ["invalid1", 12345, None] # Tipos e strings inválidas

    result_count = await mongodb_client.remove_blacklist_items_by_ids(ids_to_remove)

    assert result_count == 0
    mock_blacklist.delete_many.assert_not_called() # Não deve tentar deletar

@pytest.mark.asyncio
async def test_remove_blacklist_items_by_ids_empty_list(mongodb_setup):
    """Testa remove_blacklist_items_by_ids com lista vazia."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_db = mongodb_setup["mock_db"]
    mock_blacklist = mongodb_setup["mock_blacklist"]
    mongodb_client.db = mock_db

    result_count = await mongodb_client.remove_blacklist_items_by_ids([])

    assert result_count == 0
    mock_blacklist.delete_many.assert_not_called()

@pytest.mark.asyncio
async def test_remove_blacklist_items_by_ids_mongo_error(mongodb_setup):
    """Testa remove_blacklist_items_by_ids com erro no MongoDB."""
    mongodb_client = mongodb_setup["client_wrapper"]
    mock_db = mongodb_setup["mock_db"]
    mock_blacklist = mongodb_setup["mock_blacklist"]
    mongodb_client.db = mock_db

    ids_to_remove_obj = [ObjectId()]

    # Mock para delete_many lançar erro
    mock_blacklist.delete_many.side_effect = PyMongoError("Delete failed")

    result_count = await mongodb_client.remove_blacklist_items_by_ids(ids_to_remove_obj)

    assert result_count == 0
    mock_blacklist.delete_many.assert_called_once_with({"_id": {"$in": ids_to_remove_obj}})

# Função auxiliar para monkeypatching
def monkeypatch_setup(client_wrapper):
    """Configura monkeypatching para os testes de MongoDB."""
    mock_db = MagicMock()
    # Substitui o atributo db do cliente pelo mock
    client_wrapper.db = mock_db
    return mock_db 
