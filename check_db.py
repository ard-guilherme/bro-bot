import asyncio
from src.utils.mongodb_instance import mongodb_client, initialize_mongodb

async def main():
    # Inicializa a conexão com o MongoDB
    await initialize_mongodb()
    
    # Verifica se a conexão foi estabelecida
    if mongodb_client.db is None:
        print("Erro: Não foi possível conectar ao banco de dados.")
        return
    
    # Lista todas as coleções disponíveis
    collections = await mongodb_client.db.list_collection_names()
    print(f"Coleções disponíveis: {collections}")
    
    # Verifica se a coleção bot_admins existe
    if "bot_admins" in collections:
        # Lista todos os administradores
        admins = []
        cursor = mongodb_client.db.bot_admins.find()
        async for doc in cursor:
            admins.append(doc)
        
        print(f"\nAdministradores encontrados: {len(admins)}")
        for admin in admins:
            print(f"  - ID: {admin.get('admin_id', 'N/A')}, Nome: {admin.get('admin_name', 'N/A')}")
    else:
        print("\nA coleção 'bot_admins' não existe.")
        
        # Cria a coleção bot_admins
        print("\nCriando a coleção 'bot_admins'...")
        await mongodb_client.db.create_collection("bot_admins")
        print("Coleção 'bot_admins' criada com sucesso.")
    
    # Verifica a estrutura da coleção bot_admins
    print("\nEstrutura da coleção 'bot_admins':")
    indexes = await mongodb_client.db.bot_admins.index_information()
    print(f"Índices: {indexes}")
    
    # Fecha a conexão com o MongoDB
    await mongodb_client.close()

if __name__ == "__main__":
    asyncio.run(main()) 