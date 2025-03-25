"""
Script para obter usernames diretamente do Telegram e atualizar os check-ins.

Este script usa a API do Telegram para obter os usernames dos usuários
e atualizar os documentos de check-in com esses usernames.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Bot
from src.utils.mongodb_client import MongoDBClient

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_usernames():
    """
    Obtém os usernames do Telegram e atualiza os documentos de check-in.
    """
    # Verifica se o token do Telegram está definido
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("Token do Telegram não encontrado nas variáveis de ambiente.")
        return
    
    # Inicializa o bot do Telegram
    bot = Bot(token=os.environ.get("TELEGRAM_TOKEN"))
    
    # Conecta ao MongoDB
    mongodb_client = MongoDBClient()
    await mongodb_client.connect()
    
    logger.info("Conectado ao banco de dados. Iniciando obtenção de usernames...")
    
    # Obtém todos os user_ids únicos da coleção de check-ins
    user_ids = await mongodb_client.db.user_checkins.distinct("user_id")
    logger.info(f"Encontrados {len(user_ids)} usuários distintos na coleção de check-ins.")
    
    # Para cada user_id, tenta obter o username do Telegram
    updated_count = 0
    skipped_count = 0
    
    for user_id in user_ids:
        # Busca por check-ins deste usuário que não têm username
        check_ins_without_username = await mongodb_client.db.user_checkins.find(
            {"user_id": user_id, "username": {"$exists": False}}
        ).to_list(None)
        
        if not check_ins_without_username:
            skipped_count += 1
            continue
        
        try:
            # Obtém os dados do usuário do Telegram
            chat_member = None
            
            # Obtém o primeiro chat_id em que este usuário fez check-in
            checkin = await mongodb_client.db.user_checkins.find_one({"user_id": user_id})
            if checkin and "chat_id" in checkin:
                chat_id = checkin["chat_id"]
                
                try:
                    # Tenta obter o membro do chat
                    chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
                except Exception as e:
                    logger.warning(f"Não foi possível obter o membro do chat {chat_id}: {e}")
            
            if chat_member and chat_member.user.username:
                username = chat_member.user.username
                
                # Atualiza todos os check-ins deste usuário
                result = await mongodb_client.db.user_checkins.update_many(
                    {"user_id": user_id, "username": {"$exists": False}},
                    {"$set": {"username": username}}
                )
                
                if result.modified_count > 0:
                    updated_count += result.modified_count
                    logger.info(f"Atualizado {result.modified_count} documento(s) para o usuário {user_id} com username @{username}")
                else:
                    skipped_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            logger.error(f"Erro ao obter username para o usuário {user_id}: {e}")
            skipped_count += 1
    
    logger.info(f"Processo concluído. {updated_count} documentos foram atualizados. {skipped_count} usuários foram ignorados.")

if __name__ == "__main__":
    logger.info("Iniciando script de obtenção de usernames...")
    asyncio.run(get_usernames())
    logger.info("Script concluído.") 