import asyncio
from src.utils.mongodb_instance import mongodb_client, initialize_mongodb
from datetime import datetime

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
        # Lista todos os administradores antes da correção
        admins = []
        cursor = mongodb_client.db.bot_admins.find()
        async for doc in cursor:
            admins.append(doc)
        
        print(f"\nAdministradores encontrados antes da correção: {len(admins)}")
        for admin in admins:
            print(f"  - ID: {admin.get('admin_id', 'N/A')}, Nome: {admin.get('admin_name', 'N/A')}")
            print(f"    Documento completo: {admin}")
        
        # Corrige a estrutura dos documentos
        print("\nCorrigindo a estrutura dos documentos...")
        
        # Vamos criar uma nova coleção temporária
        await mongodb_client.db.create_collection("bot_admins_temp", check_exists=False)
        
        # Migra os documentos válidos
        valid_count = 0
        for admin in admins:
            # Se já tem admin_id, apenas copia
            if admin.get('admin_id') is not None:
                await mongodb_client.db.bot_admins_temp.insert_one(admin)
                valid_count += 1
                print(f"Documento já válido: {admin.get('admin_id')}")
                continue
            
            # Se tem user_id, converte para admin_id
            if admin.get('user_id') is not None:
                user_id = admin.get('user_id')
                user_name = admin.get('user_name', f"Usuário {user_id}")
                
                # Cria um novo documento com a estrutura correta
                new_doc = {
                    "admin_id": user_id,
                    "admin_name": user_name,
                    "added_by": admin.get('created_by', 0),
                    "added_at": admin.get('created_at', datetime.now())
                }
                
                # Insere o novo documento
                await mongodb_client.db.bot_admins_temp.insert_one(new_doc)
                valid_count += 1
                print(f"Documento corrigido: {user_id} -> {new_doc}")
        
        # Renomeia as coleções
        if valid_count > 0:
            print("\nRenomeando coleções...")
            await mongodb_client.db.bot_admins.drop()
            await mongodb_client.db.bot_admins_temp.rename("bot_admins")
            print("Coleção renomeada com sucesso.")
        else:
            print("\nNenhum documento válido encontrado. Nenhuma alteração foi feita.")
            await mongodb_client.db.bot_admins_temp.drop()
        
        # Lista todos os administradores após a correção
        admins = []
        cursor = mongodb_client.db.bot_admins.find()
        async for doc in cursor:
            admins.append(doc)
        
        print(f"\nAdministradores encontrados após a correção: {len(admins)}")
        for admin in admins:
            print(f"  - ID: {admin.get('admin_id', 'N/A')}, Nome: {admin.get('admin_name', 'N/A')}")
    else:
        print("\nA coleção 'bot_admins' não existe.")
    
    # Fecha a conexão com o MongoDB
    await mongodb_client.close()

if __name__ == "__main__":
    asyncio.run(main()) 