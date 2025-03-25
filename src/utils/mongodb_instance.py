"""
Instância compartilhada do cliente MongoDB.
"""
from src.utils.mongodb_client import MongoDBClient

# Cria uma única instância do cliente MongoDB para ser compartilhada entre todos os módulos
mongodb_client = MongoDBClient()

# Função para inicializar a conexão com o MongoDB
async def initialize_mongodb():
    """Inicializa a conexão com o MongoDB."""
    await mongodb_client.connect() 