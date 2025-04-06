import asyncio
import os
import sys
from dotenv import load_dotenv
import motor.motor_asyncio
from bson import ObjectId  # Import ObjectId to handle MongoDB IDs
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Adiciona o diretório raiz ao path (opcional, mas boa prática se importar de src/)
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def update_specific_anchor_points():
    """
    Atualiza o campo 'points_value' para 2 em todos os check-ins
    associados a uma âncora específica.
    """
    # Defina o ID da âncora alvo aqui
    target_anchor_id_str = "67f28e3092c7901675592dfd"
    new_points_value = 2

    # Carrega variáveis de ambiente do .env na raiz do projeto
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)

    connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    db_name = "gym_nation_bot" # Nome padrão do banco de dados

    if not connection_string:
        logger.error("MONGODB_CONNECTION_STRING não encontrada no .env.")
        return

    client = None
    try:
        # Converte a string do ID da âncora para ObjectId
        try:
            target_anchor_oid = ObjectId(target_anchor_id_str)
        except Exception as e:
            logger.error(f"ID da âncora inválido: '{target_anchor_id_str}'. Erro: {e}")
            return

        logger.info("Conectando ao MongoDB...")
        client = motor.motor_asyncio.AsyncIOMotorClient(
            connection_string,
            serverSelectionTimeoutMS=5000
        )
        await client.admin.command('ping') # Verifica a conexão
        db = client[db_name]
        user_checkins_collection = db.user_checkins

        logger.info(f"Conectado ao banco '{db_name}'.")

        # Filtro para encontrar check-ins da âncora específica
        filter_query = {"anchor_id": target_anchor_oid}

        # Atualização para definir 'points_value' como o novo valor
        update_operation = {"$set": {"points_value": new_points_value}}

        logger.info(f"Procurando e atualizando check-ins para a âncora ID: {target_anchor_id_str} para {new_points_value} pontos...")

        # Executa a atualização em massa
        result = await user_checkins_collection.update_many(filter_query, update_operation)

        if result.acknowledged:
            logger.info("Atualização concluída com sucesso!")
            logger.info(f"Check-ins encontrados para esta âncora: {result.matched_count}")
            logger.info(f"Check-ins modificados (points_value = {new_points_value} definido): {result.modified_count}")
            if result.matched_count > result.modified_count:
                 logger.warning("Alguns check-ins encontrados não foram modificados (podem já ter o valor correto ou outros motivos).")
        else:
            logger.error("A operação de atualização não foi reconhecida pelo servidor MongoDB.")

    except motor.motor_asyncio.errors.ServerSelectionTimeoutError as e:
         logger.error(f"Não foi possível conectar ao MongoDB (timeout): {e}. Verifique a connection string e se o MongoDB está acessível.")
    except PyMongoError as e:
        logger.error(f"Ocorreu um erro de banco de dados durante a atualização: {e}")
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado durante a atualização: {e}")
    finally:
        if client:
            client.close()
            logger.info("Conexão com o MongoDB fechada.")

if __name__ == "__main__":
    logger.info("Iniciando script de atualização de pontos para âncora específica...")
    asyncio.run(update_specific_anchor_points())
    logger.info("Script de atualização finalizado.")