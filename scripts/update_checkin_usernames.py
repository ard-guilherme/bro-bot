"""
Script para atualizar os usernames em check-ins existentes.

Este script consulta a tabela de usuários do telegram e atualiza os documentos
de check-in com o username mais recente de cada usuário.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from src.utils.mongodb_client import MongoDBClient

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def update_usernames():
    """
    Atualiza os usernames nos documentos de check-in existentes.
    """
    # Conecta ao MongoDB usando o cliente do projeto
    mongodb_client = MongoDBClient()
    await mongodb_client.connect()
    
    logger.info("Conectado ao banco de dados. Iniciando atualização de usernames...")
    
    # Obtém todos os user_ids únicos da coleção de check-ins
    user_ids = await mongodb_client.db.user_checkins.distinct("user_id")
    logger.info(f"Encontrados {len(user_ids)} usuários distintos na coleção de check-ins.")
    
    # Para cada user_id, verifica se existe um documento na coleção de usuários telegram
    updated_count = 0
    skipped_count = 0
    
    for user_id in user_ids:
        # Verifica se o usuário existe na coleção de usuários do telegram
        user = await mongodb_client.db.telegram_users.find_one({"id": user_id})
        
        if user and "username" in user and user["username"]:
            username = user["username"]
            
            # Atualiza todos os check-ins deste usuário que não têm username
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
    
    logger.info(f"Processo concluído. {updated_count} documentos foram atualizados. {skipped_count} usuários foram ignorados.")

if __name__ == "__main__":
    logger.info("Iniciando script de atualização de usernames...")
    asyncio.run(update_usernames())
    logger.info("Script concluído.") 