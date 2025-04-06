import asyncio
import os
import sys
from dotenv import load_dotenv
import motor.motor_asyncio
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Adiciona o diretório raiz ao path (opcional, mas boa prática se importar de src/)
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def migrate_checkins():
    """
    Adiciona o campo 'points_value' com valor 1 aos documentos antigos
    na coleção 'user_checkins' que não o possuem.
    """
    # Carrega variáveis de ambiente do .env na raiz do projeto
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)

    connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    # Usa o nome do banco de dados padrão, ajuste se for diferente
    db_name = "gym_nation_bot"

    if not connection_string:
        logger.error("MONGODB_CONNECTION_STRING não encontrada no .env.")
        return

    client = None
    try:
        logger.info("Conectando ao MongoDB...")
        # Aumenta o timeout padrão (opcional, pode ajudar em conexões lentas)
        client = motor.motor_asyncio.AsyncIOMotorClient(
            connection_string,
            serverSelectionTimeoutMS=5000 # Timeout de 5 segundos para seleção do servidor
        )
        # Verifica a conexão antes de prosseguir
        await client.admin.command('ping')
        db = client[db_name]
        user_checkins_collection = db.user_checkins

        logger.info(f"Conectado ao banco '{db_name}'.")

        # Filtro para encontrar documentos sem 'points_value'
        filter_query = {"points_value": {"$exists": False}}

        # Atualização para definir 'points_value' como 1
        update_operation = {"$set": {"points_value": 1}}

        logger.info("Procurando e atualizando documentos antigos de check-in...")

        # Executa a atualização em massa
        result = await user_checkins_collection.update_many(filter_query, update_operation)

        if result.acknowledged:
            logger.info("Migração concluída com sucesso!")
            logger.info(f"Documentos encontrados que correspondiam ao critério: {result.matched_count}")
            logger.info(f"Documentos modificados ('points_value: 1' adicionado): {result.modified_count}")
            if result.matched_count > result.modified_count:
                 logger.warning("Alguns documentos que correspondiam ao critério não foram modificados (isso pode acontecer se já tivessem o valor correto ou por outros motivos).")
        else:
            logger.error("A operação de atualização não foi reconhecida pelo servidor MongoDB.")

    except motor.motor_asyncio.errors.ServerSelectionTimeoutError as e:
         logger.error(f"Não foi possível conectar ao MongoDB (timeout): {e}. Verifique a connection string e se o MongoDB está acessível.")
    except PyMongoError as e:
        logger.error(f"Ocorreu um erro de banco de dados durante a migração: {e}")
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado durante a migração: {e}")
    finally:
        if client:
            client.close()
            logger.info("Conexão com o MongoDB fechada.")

if __name__ == "__main__":
    logger.info("Iniciando script de migração de pontos de check-in...")
    asyncio.run(migrate_checkins())
    logger.info("Script de migração finalizado.")
