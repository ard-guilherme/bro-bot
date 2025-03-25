"""
Testes para os handlers de menção.
"""
import os
import unittest
from unittest.mock import AsyncMock, patch, MagicMock, call
from datetime import datetime
import pytest
from telegram import Update, User, Message, Chat, InlineKeyboardMarkup, CallbackQuery

from src.bot.mention_handlers import (
    handle_mention,
    handle_qa_feedback,
    classify_question,
    CATEGORIES,
    QA_DAILY_LIMIT,
    BOT_USERNAME
)

class TestClassifyQuestion(unittest.TestCase):
    """Testes para a função de classificação de perguntas."""
    
    def test_classify_treino(self):
        """Testa classificação de pergunta sobre treino."""
        question = "Qual o melhor exercício para hipertrofia de pernas? Preciso melhorar meu agachamento e técnica."
        category = classify_question(question)
        self.assertEqual(category["prefix"], "Resposta de Treino:")
    
    def test_classify_nutricao(self):
        """Testa classificação de pergunta sobre nutrição."""
        question = "Quantas calorias e proteínas devo consumir para perder peso? Minha dieta está com poucos carboidratos."
        category = classify_question(question)
        self.assertEqual(category["prefix"], "Resposta Nutricional:")
    
    def test_classify_suplementacao(self):
        """Testa classificação de pergunta sobre suplementação."""
        question = "Whey protein e creatina fazem mal para os rins? Qual o melhor suplemento pré-treino?"
        category = classify_question(question)
        self.assertEqual(category["prefix"], "Resposta sobre Suplementação:")
    
    def test_classify_motivacao(self):
        """Testa classificação de pergunta sobre motivação."""
        question = "Como manter a disciplina e foco para treinar todos os dias? Estou sem motivação."
        category = classify_question(question)
        self.assertEqual(category["prefix"], "Resposta Motivacional:")
    
    def test_classify_progresso(self):
        """Testa classificação de pergunta sobre progresso."""
        question = "Como medir meu progresso na academia além da balança? Quero acompanhar minha perda de gordura."
        category = classify_question(question)
        self.assertEqual(category["prefix"], "Resposta sobre Progresso:")
    
    def test_classify_default(self):
        """Testa classificação padrão para pergunta ambígua."""
        question = "O que você acha sobre esportes?"
        category = classify_question(question)
        self.assertEqual(category["prefix"], "Resposta de Treino:")

@pytest.mark.asyncio
async def test_handle_mention_no_reply():
    """Testa handler de menção sem responder a uma mensagem."""
    # Configura mock
    update = AsyncMock()
    update.message.reply_to_message = None
    update.message.text = None
    context = AsyncMock()
    
    # Executa a função
    await handle_mention(update, context)
    
    # Verifica que não enviou resposta
    update.message.reply_text.assert_not_called()

@pytest.mark.asyncio
@patch("src.bot.mention_handlers.BOT_USERNAME", "Nations_bro_bot")
async def test_handle_mention_no_bot_mention():
    """Testa handler de menção sem mencionar o bot."""
    # Configura mock
    update = AsyncMock()
    update.message.reply_to_message = AsyncMock()
    update.message.text = "Alguma mensagem sem mencionar o bot"
    context = AsyncMock()
    context.bot.username = "Nations_bro_bot"
    
    # Executa a função
    await handle_mention(update, context)
    
    # Verifica que não chamou nenhum método de resposta
    update.message.reply_text.assert_not_called()

@pytest.mark.asyncio
@patch("src.bot.mention_handlers.mongodb_client")
@patch("src.bot.mention_handlers.BOT_USERNAME", "Nations_bro_bot")
async def test_handle_mention_limit_exceeded(mock_mongodb):
    """Testa handler de menção com limite excedido."""
    # Configura mocks
    update = AsyncMock()
    update.message.reply_to_message = AsyncMock()
    update.message.reply_to_message.text = "Esta é uma pergunta de teste"
    update.message.text = "@Nations_bro_bot ajude com esta dúvida"
    update.message.photo = None
    update.effective_user.id = 12345
    update.effective_user.full_name = "Test User"
    update.effective_chat.id = 67890
    
    context = AsyncMock()
    context.bot.username = "Nations_bro_bot"
    
    # Configura comportamento do MongoDB mock para retornar awaitable
    mock_mongodb.get_daily_qa_count = AsyncMock(return_value=QA_DAILY_LIMIT)
    mock_mongodb.get_last_qa_timestamp = AsyncMock(return_value=datetime.now())
    
    # Executa a função
    await handle_mention(update, context)
    
    # Verifica que enviou mensagem de limite excedido
    update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.mention_handlers.mongodb_client")
@patch("src.bot.mention_handlers.BOT_USERNAME", "Nations_bro_bot")
@patch("src.bot.mention_handlers.generate_fitness_answer")
async def test_handle_mention_successful(mock_generate_fitness, mock_mongodb):
    """Testa handler de menção com sucesso."""
    # Configura mocks
    update = AsyncMock()
    update.message.text = "@Nations_bro_bot Como fazer agachamento corretamente?"
    update.message.photo = None
    update.effective_user.id = 12345
    update.effective_user.full_name = "Test User"
    update.effective_chat.id = 67890
    update.message.message_id = 54321
    
    # Mock para mensagem de espera
    wait_message = AsyncMock()
    wait_message.message_id = 98765
    context = AsyncMock()
    context.bot.username = "Nations_bro_bot"
    context.bot.send_message = AsyncMock(return_value=wait_message)
    
    # Configura comportamento do MongoDB mock para retornar awaitable
    mock_mongodb.get_daily_qa_count = AsyncMock(return_value=0)
    mock_mongodb.store_qa_interaction = AsyncMock(return_value=True)
    mock_mongodb.increment_qa_usage = AsyncMock(return_value=True)
    
    # Configura comportamento do generate_fitness_answer mock
    mock_generate_fitness.return_value = "Esta é uma resposta de teste sobre agachamento."
    
    # Executa a função
    await handle_mention(update, context)
    
    # Verifica se a mensagem de espera foi enviada
    context.bot.send_message.assert_called_once()
    assert "Analisando" in context.bot.send_message.call_args[1]["text"]
    
    # Verifica se generate_fitness_answer foi chamado corretamente com os três parâmetros
    mock_generate_fitness.assert_called_once()
    # Verifica o primeiro parâmetro (a pergunta)
    assert mock_generate_fitness.call_args[0][0] == "Como fazer agachamento corretamente?"
    # Verifica que foram passados três parâmetros
    assert len(mock_generate_fitness.call_args[0]) == 3
    
    # Verifica que editou a mensagem com a resposta
    wait_message.edit_text.assert_called_once()
    
    # Verifica que a resposta contém o texto gerado
    assert "Esta é uma resposta de teste sobre agachamento." in wait_message.edit_text.call_args[0][0]
    
    # Verifica que armazenou a interação no MongoDB
    mock_mongodb.store_qa_interaction.assert_called_once()
    # Verifica que o dicionário passado contém os campos necessários
    qa_interaction = mock_mongodb.store_qa_interaction.call_args[0][0]
    assert qa_interaction["question"] == "Como fazer agachamento corretamente?"
    assert qa_interaction["answer"] == "Esta é uma resposta de teste sobre agachamento."
    assert qa_interaction["user_id"] == 12345
    assert qa_interaction["chat_id"] == 67890
    assert qa_interaction["message_id"] == 98765
    assert "timestamp" in qa_interaction
    
    mock_mongodb.increment_qa_usage.assert_called_once()
    
    # Verifica que a mensagem editada tem botões de feedback
    reply_markup = wait_message.edit_text.call_args[1]["reply_markup"]
    assert reply_markup is not None
    
    # Verifica os botões de feedback
    like_button = reply_markup.inline_keyboard[0][0]
    dislike_button = reply_markup.inline_keyboard[0][1]
    
    assert "👍" == like_button.text
    assert "👎" == dislike_button.text
    assert f"qa_like_{update.effective_chat.id}_{wait_message.message_id}_{update.effective_user.id}" == like_button.callback_data
    assert f"qa_dislike_{update.effective_chat.id}_{wait_message.message_id}_{update.effective_user.id}" == dislike_button.callback_data

@pytest.mark.asyncio
@patch("src.bot.mention_handlers.mongodb_client")
async def test_handle_qa_feedback_like(mock_mongodb_client):
    """Testa handler de feedback positivo."""
    # Configura mock
    query = AsyncMock()
    query.data = "qa_like_67890_12345_54321"  # chat_id_message_id_user_id
    query.from_user.id = "54321"  # ID do usuário que fez a pergunta
    
    update = AsyncMock()
    update.callback_query = query
    
    context = AsyncMock()
    
    # Configura comportamento do MongoDB mock
    mock_mongodb_client.get_qa_interaction = AsyncMock(return_value={"feedback_used": False})
    mock_mongodb_client.store_qa_feedback = AsyncMock(return_value=True)
    
    # Executa a função
    result = await handle_qa_feedback(update, context)
    
    # Verifica que respondeu ao callback
    query.answer.assert_awaited_once()
    
    # Verifica que obteve a interação e armazenou o feedback no MongoDB
    mock_mongodb_client.get_qa_interaction.assert_awaited_once_with("67890", "12345")
    mock_mongodb_client.store_qa_feedback.assert_awaited_once_with("67890", "12345", "positive")
    
    # Verifica que removeu os botões de feedback
    query.edit_message_reply_markup.assert_awaited_once_with(reply_markup=None)
    
    # Verifica a mensagem de retorno
    assert "Thank you for your positive feedback" in result

@pytest.mark.asyncio
@patch("src.bot.mention_handlers.mongodb_client")
async def test_handle_qa_feedback_dislike(mock_mongodb_client):
    """Testa handler de feedback negativo."""
    # Configura mock
    query = AsyncMock()
    query.data = "qa_dislike_67890_12345_54321"  # chat_id_message_id_user_id
    query.from_user.id = "54321"  # ID do usuário que fez a pergunta
    
    update = AsyncMock()
    update.callback_query = query
    
    context = AsyncMock()
    
    # Configura comportamento do MongoDB mock
    mock_mongodb_client.get_qa_interaction = AsyncMock(return_value={"feedback_used": False})
    mock_mongodb_client.store_qa_feedback = AsyncMock(return_value=True)
    
    # Executa a função
    result = await handle_qa_feedback(update, context)
    
    # Verifica que respondeu ao callback
    query.answer.assert_awaited_once()
    
    # Verifica que obteve a interação e armazenou o feedback no MongoDB
    mock_mongodb_client.get_qa_interaction.assert_awaited_once_with("67890", "12345")
    mock_mongodb_client.store_qa_feedback.assert_awaited_once_with("67890", "12345", "negative")
    
    # Verifica que removeu os botões de feedback
    query.edit_message_reply_markup.assert_awaited_once_with(reply_markup=None)
    
    # Verifica a mensagem de retorno
    assert "I'm sorry my answer wasn't helpful" in result

@pytest.mark.asyncio
@patch("src.bot.mention_handlers.mongodb_client")
async def test_handle_qa_feedback_wrong_user(mock_mongodb_client):
    """Testa handler de feedback quando o usuário não é o que fez a pergunta."""
    # Configura mock
    query = AsyncMock()
    query.data = "qa_like_67890_12345_54321"  # chat_id_message_id_user_id
    query.from_user.id = "99999"  # ID diferente do usuário que fez a pergunta
    
    update = AsyncMock()
    update.callback_query = query
    
    context = AsyncMock()
    
    # Executa a função
    result = await handle_qa_feedback(update, context)
    
    # Verifica que respondeu ao callback
    query.answer.assert_awaited_once_with(
        "Sorry, only the person who asked the question can provide feedback.",
        show_alert=True
    )
    
    # Verifica que não interagiu com o MongoDB
    mock_mongodb_client.get_qa_interaction.assert_not_called()
    mock_mongodb_client.store_qa_feedback.assert_not_called()
    
    # Verifica que não editou a mensagem
    query.edit_message_reply_markup.assert_not_called()
    
    # Verifica que retornou None
    assert result is None

@pytest.mark.asyncio
@patch("src.bot.mention_handlers.mongodb_client")
async def test_handle_qa_feedback_already_used(mock_mongodb_client):
    """Testa handler de feedback quando o feedback já foi usado."""
    # Configura mock
    query = AsyncMock()
    query.data = "qa_like_67890_12345_54321"  # chat_id_message_id_user_id
    query.from_user.id = "54321"  # ID do usuário que fez a pergunta
    
    update = AsyncMock()
    update.callback_query = query
    
    context = AsyncMock()
    
    # Configura comportamento do MongoDB mock - feedback já usado
    mock_mongodb_client.get_qa_interaction = AsyncMock(return_value={"feedback_used": True})
    
    # Executa a função
    result = await handle_qa_feedback(update, context)
    
    # Verifica que respondeu ao callback
    query.answer.assert_awaited_once_with(
        "You have already provided feedback for this answer.",
        show_alert=True
    )
    
    # Verifica que obteve a interação mas não armazenou feedback
    mock_mongodb_client.get_qa_interaction.assert_awaited_once_with("67890", "12345")
    mock_mongodb_client.store_qa_feedback.assert_not_called()
    
    # Verifica que não editou a mensagem
    query.edit_message_reply_markup.assert_not_called()
    
    # Verifica que retornou None
    assert result is None

@pytest.mark.asyncio
@patch("src.bot.mention_handlers.mongodb_client")
@patch("src.bot.mention_handlers.BOT_USERNAME", "Nations_bro_bot")
@patch("src.bot.mention_handlers.asyncio.sleep")
@patch("src.bot.mention_handlers.generate_fitness_answer")
async def test_handle_mention_error(mock_generate_fitness, mock_sleep, mock_mongodb_client):
    """Testa handler de menção com erro na API."""
    # Configura mocks
    update = AsyncMock()
    update.message.text = "@Nations_bro_bot Como fazer agachamento corretamente?"
    update.message.photo = None
    update.effective_user.id = 12345
    update.effective_user.full_name = "Test User"
    update.effective_chat.id = 67890
    update.message.message_id = 54321
    
    # Mock para mensagem de espera
    wait_message = AsyncMock()
    context = AsyncMock()
    context.bot.username = "Nations_bro_bot"
    context.bot.send_message = AsyncMock(return_value=wait_message)
    
    # Configura comportamento do MongoDB mock para retornar awaitable
    mock_mongodb_client.get_daily_qa_count = AsyncMock(return_value=0)
    
    # Configura para gerar uma exceção durante a geração da resposta
    mock_generate_fitness.side_effect = Exception("API Error")
    
    # Pulamos o sleep no teste para não atrasar
    mock_sleep.return_value = None
    
    # Executa a função
    await handle_mention(update, context)
    
    # Verifica que enviou mensagem de espera
    context.bot.send_message.assert_called_once()
    
    # Verifica que editou a mensagem com erro
    wait_message.edit_text.assert_called_once()
    assert "erro" in wait_message.edit_text.call_args[0][0].lower()
    
    # Verifica que não chamou as funções do MongoDB para armazenar a interação
    mock_mongodb_client.store_qa_interaction.assert_not_called()
    mock_mongodb_client.increment_qa_usage.assert_not_called() 