"""
Handlers para menções ao bot.

Este módulo implementa a funcionalidade de Assistente de Dúvidas Fitness por Menção,
que permite que qualquer membro do grupo possa mencionar o bot (@Nations_bro_bot) 
em resposta a uma mensagem contendo uma dúvida fitness para obter uma resposta.
"""
import logging
import re
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from src.utils.anthropic_client import AnthropicClient
from src.utils.mongodb_instance import mongodb_client
from src.utils.config import Config
from src.bot.fitness_qa import generate_fitness_answer
import asyncio
import time

# Configuração de logging
logger = logging.getLogger(__name__)

# Cliente da Anthropic
anthropic_client = AnthropicClient()

# Limite diário de consultas por usuário por chat
QA_DAILY_LIMIT = int(Config.get_env("QA_DAILY_LIMIT", "2"))

# Nome de usuário do bot
BOT_USERNAME = Config.get_bot_username()

# Categorias de perguntas fitness
CATEGORIES = {
    "nutrição": {
        "prefix": "Resposta Nutricional:",
        "emoji": "🥗",
        "keywords": ["comer", "dieta", "proteína", "carboidrato", "gordura", "nutrição", "alimento", "caloria", "whey", "suplemento", "refeição", "jejum", "macros", "déficit", "superávit"]
    },
    "treino": {
        "prefix": "Resposta de Treino:",
        "emoji": "💪",
        "keywords": ["treino", "exercício", "musculação", "peso", "série", "repetição", "academia", "hipertrofia", "força", "aeróbico", "anaeróbico", "cardio", "alongamento", "músculo", "lesão", "descanso"]
    },
    "motivação": {
        "prefix": "Resposta Motivacional:",
        "emoji": "🔥",
        "keywords": ["motivação", "consistência", "disciplina", "hábito", "progresso", "meta", "objetivo", "foco", "determinação", "transformação", "resultado", "mudança", "perseverança"]
    },
    "suplementação": {
        "prefix": "Resposta sobre Suplementação:",
        "emoji": "💊",
        "keywords": ["suplemento", "whey", "creatina", "proteína", "pré-treino", "pós-treino", "bcaa", "aminoácido", "glutamina", "caseína", "termogênico", "cafeína"]
    },
    "progresso": {
        "prefix": "Resposta sobre Progresso:",
        "emoji": "📊",
        "keywords": ["progresso", "resultado", "medida", "peso", "balança", "composição", "gordura", "massa", "muscular", "circunferência", "perímetro", "foto", "comparação", "estagnação", "platô"]
    },
    "Off-topic": {
        "prefix": "Resposta sobre Progresso:",
        "emoji": "😜",
        "keywords": []
    }
}


async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para processar menções ao bot em mensagens.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se a mensagem é uma resposta a outra mensagem
    if not update.message or not update.message.text:
        return
    
    # Extrai informações da mensagem
    message = update.message
    text = message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    chat_id = update.effective_chat.id
    
    # Verifica se o bot foi mencionado na mensagem
    bot_username = context.bot.username
    if not re.search(f"@{bot_username}", text, re.IGNORECASE):
        return
    
    # Remove a menção ao bot do texto
    original_question = re.sub(f"@{bot_username}", "", text, flags=re.IGNORECASE).strip()
    if not original_question:
        await message.reply_text("Por favor, faça uma pergunta junto com a menção.")
        return
    
    try:
        # Verifica se o usuário atingiu o limite diário
        daily_count = await mongodb_client.get_daily_qa_count(user_id, chat_id)
        if daily_count >= QA_DAILY_LIMIT:
            last_timestamp = await mongodb_client.get_last_qa_timestamp(user_id, chat_id)
            if last_timestamp:
                reset_time = last_timestamp + timedelta(days=1)
                now = datetime.now()
                if now < reset_time:
                    time_left = reset_time - now
                    hours = time_left.seconds // 3600
                    minutes = (time_left.seconds % 3600) // 60
                    await message.reply_text(
                        f"Você atingiu o limite diário de {QA_DAILY_LIMIT} perguntas. "
                        f"Tente novamente em {hours}h {minutes}min."
                    )
                    return
        
        # Envia mensagem de espera
        wait_message = await context.bot.send_message(
            chat_id=chat_id,
            text="🤔 Analisando sua pergunta... Aguarde um momento.",
            reply_to_message_id=message.message_id
        )
        
        # Classifica a pergunta
        category = classify_question(original_question)
        
        # Gera resposta usando o modelo Claude da Anthropic
        start_time = time.time()
        # Mapeia o nome da categoria com base nas chaves do dicionário CATEGORIES
        category_name = ""
        for cat_key, cat_data in CATEGORIES.items():
            if cat_data["prefix"] == category["prefix"]:
                category_name = cat_data["prefix"].replace("Resposta ", "").replace(":", "")
                break
        
        # Se não encontrou, use um valor padrão
        if not category_name:
            category_name = "Fitness Geral"
            
        response_text = await generate_fitness_answer(original_question, category["emoji"], category_name)
        end_time = time.time()
        
        # Registra tempo de resposta
        response_time = end_time - start_time
        logging.info(f"Tempo de resposta da API: {response_time:.2f}s")
        
        # Add feedback buttons
        keyboard = [
            [
                InlineKeyboardButton("👍", callback_data=f"qa_like_{chat_id}_{wait_message.message_id}_{user_id}"),
                InlineKeyboardButton("👎", callback_data=f"qa_dislike_{chat_id}_{wait_message.message_id}_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Edit the message with answer and feedback buttons
        await wait_message.edit_text(
            response_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Save interaction for feedback
        qa_interaction = {
            "question": original_question,
            "answer": response_text,
            "user_id": user_id,
            "chat_id": chat_id,
            "message_id": wait_message.message_id,
            "category": category["prefix"],
            "timestamp": datetime.now()
        }
        qa_id = await mongodb_client.store_qa_interaction(qa_interaction)
        
        # Incrementa contador de uso
        await mongodb_client.increment_qa_usage(user_id, chat_id)
        
    except Exception as e:
        error_message = f"❌ Ocorreu um erro ao processar sua pergunta: {str(e)}"
        logging.error(f"Erro ao processar menção: {e}")
        
        try:
            # Tenta editar a mensagem de espera, se existir
            if 'wait_message' in locals():
                await wait_message.edit_text(error_message)
            else:
                # Caso contrário, envia uma nova mensagem
                await message.reply_text(error_message)
        except Exception as reply_error:
            logging.error(f"Erro ao enviar mensagem de erro: {reply_error}")

async def handle_qa_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle feedback for Q&A responses from the bot."""
    query = update.callback_query
    
    # Parse callback data
    callback_data = query.data
    if not callback_data.startswith(("qa_like_", "qa_dislike_")):
        await query.answer()
        return
    
    parts = callback_data.split("_")
    if len(parts) < 5:
        await query.answer()
        return
    
    action = parts[1]  # like or dislike
    chat_id = parts[2]
    message_id = parts[3]
    original_user_id = parts[4]
    
    # Check if this user is allowed to give feedback
    if str(query.from_user.id) != original_user_id:
        await query.answer("Sorry, only the person who asked the question can provide feedback.", show_alert=True)
        return None
    
    # Store feedback
    try:
        qa_interaction = await mongodb_client.get_qa_interaction(chat_id, message_id)
        
        if qa_interaction and qa_interaction.get("feedback_used", False):
            await query.answer("You have already provided feedback for this answer.", show_alert=True)
            return None
        
        feedback = "positive" if action == "like" else "negative"
        await mongodb_client.store_qa_feedback(chat_id, message_id, feedback)
        
        # Remove feedback buttons
        await query.edit_message_reply_markup(reply_markup=None)
        
        if feedback == "positive":
            await query.answer("Thank you for your positive feedback!")
            return "Thank you for your positive feedback! I'm glad I could help."
        else:
            await query.answer("Thank you for your feedback!")
            return "I'm sorry my answer wasn't helpful. I'll try to do better next time."
    except Exception as e:
        logging.error(f"Error handling feedback: {e}")
        await query.answer("An error occurred while processing your feedback.", show_alert=True)
        return None

def classify_question(question: str) -> Dict[str, Any]:
    """
    Classifica uma pergunta em uma das categorias predefinidas.
    
    Args:
        question (str): A pergunta a ser classificada.
        
    Returns:
        Dict[str, Any]: Um dicionário com informações da categoria.
    """
    # Converte a pergunta para minúsculas
    question_lower = question.lower()
    
    # Conta a ocorrência de palavras-chave para cada categoria
    category_scores = {}
    
    for category, data in CATEGORIES.items():
        score = 0
        for keyword in data["keywords"]:
            # Procura pela palavra-chave na pergunta
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, question_lower)
            score += len(matches)
        
        category_scores[category] = score
    
    # Encontra a categoria com maior pontuação
    best_category = max(category_scores.items(), key=lambda x: x[1])
    
    # Se nenhuma categoria tiver pontuação, usa "treino" como padrão
    if best_category[1] == 0:
        return CATEGORIES["Off-topic"]
    
    return CATEGORIES[best_category[0]] 