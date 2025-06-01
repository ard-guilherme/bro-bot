#!/usr/bin/env python3
"""
Script para migrar dados do MongoDB local para o MongoDB Atlas.

Uso:
    python scripts/migrate_to_atlas.py

Variáveis de ambiente necessárias:
    MONGODB_LOCAL_CONNECTION_STRING - String de conexão do MongoDB local
    MONGODB_ATLAS_CONNECTION_STRING - String de conexão do MongoDB Atlas
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import motor.motor_asyncio
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MongoDBMigrator:
    """Classe para migrar dados entre instâncias MongoDB."""
    
    def __init__(self, local_connection_string: str, atlas_connection_string: str):
        """
        Inicializa o migrador.
        
        Args:
            local_connection_string (str): String de conexão do MongoDB local
            atlas_connection_string (str): String de conexão do MongoDB Atlas
        """
        self.local_connection_string = local_connection_string
        self.atlas_connection_string = atlas_connection_string
        self.local_client = None
        self.atlas_client = None
        self.local_db = None
        self.atlas_db = None
        
    async def connect(self, db_name: str = "gym_nation_bot"):
        """
        Conecta aos bancos de dados local e Atlas.
        
        Args:
            db_name (str): Nome do banco de dados
        """
        try:
            # Conecta ao MongoDB local
            logger.info("Conectando ao MongoDB local...")
            self.local_client = motor.motor_asyncio.AsyncIOMotorClient(self.local_connection_string)
            self.local_db = self.local_client[db_name]
            
            # Testa a conexão local
            await self.local_client.admin.command('ping')
            logger.info("OK - Conectado ao MongoDB local")
            
            # Conecta ao MongoDB Atlas
            logger.info("Conectando ao MongoDB Atlas...")
            self.atlas_client = motor.motor_asyncio.AsyncIOMotorClient(self.atlas_connection_string)
            self.atlas_db = self.atlas_client[db_name]
            
            # Testa a conexão Atlas
            await self.atlas_client.admin.command('ping')
            logger.info("OK - Conectado ao MongoDB Atlas")
            
        except PyMongoError as e:
            logger.error(f"Erro ao conectar aos bancos de dados: {e}")
            raise
    
    async def close_connections(self):
        """Fecha as conexões com os bancos de dados."""
        if self.local_client:
            self.local_client.close()
            logger.info("Conexão local fechada")
        if self.atlas_client:
            self.atlas_client.close()
            logger.info("Conexão Atlas fechada")
    
    async def get_collections(self) -> List[str]:
        """
        Obtém a lista de coleções no banco local.
        
        Returns:
            List[str]: Lista de nomes das coleções
        """
        try:
            collections = await self.local_db.list_collection_names()
            logger.info(f"Coleções encontradas: {collections}")
            return collections
        except PyMongoError as e:
            logger.error(f"Erro ao listar coleções: {e}")
            return []
    
    async def migrate_collection(self, collection_name: str) -> bool:
        """
        Migra uma coleção específica do local para o Atlas.
        
        Args:
            collection_name (str): Nome da coleção a ser migrada
            
        Returns:
            bool: True se a migração foi bem-sucedida
        """
        try:
            logger.info(f"Iniciando migração da coleção '{collection_name}'...")
            
            # Obtém documentos da coleção local
            local_collection = self.local_db[collection_name]
            atlas_collection = self.atlas_db[collection_name]
            
            # Conta documentos na origem
            total_docs = await local_collection.count_documents({})
            logger.info(f"Total de documentos a migrar: {total_docs}")
            
            if total_docs == 0:
                logger.info(f"Coleção '{collection_name}' está vazia. Pulando...")
                return True
            
            # Obtém todos os documentos
            cursor = local_collection.find({})
            documents = await cursor.to_list(length=None)
            
            # Insere documentos no Atlas (batch insert para melhor performance)
            batch_size = 100
            migrated_count = 0
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                try:
                    # Verifica se há duplicatas antes de inserir
                    new_documents = []
                    for doc in batch:
                        existing = await atlas_collection.find_one({"_id": doc["_id"]})
                        if not existing:
                            new_documents.append(doc)
                    
                    if new_documents:
                        result = await atlas_collection.insert_many(new_documents, ordered=False)
                        migrated_count += len(result.inserted_ids)
                        logger.info(f"Migrados {migrated_count}/{total_docs} documentos...")
                    
                except PyMongoError as e:
                    logger.warning(f"Erro no batch {i//batch_size + 1}: {e}")
                    continue
            
            # Verifica a migração
            atlas_count = await atlas_collection.count_documents({})
            logger.info(f"OK - Migração da coleção '{collection_name}' concluída")
            logger.info(f"  - Documentos na origem: {total_docs}")
            logger.info(f"  - Documentos no destino: {atlas_count}")
            logger.info(f"  - Novos documentos migrados: {migrated_count}")
            
            return True
            
        except PyMongoError as e:
            logger.error(f"Erro ao migrar coleção '{collection_name}': {e}")
            return False
    
    async def create_indexes(self):
        """Cria índices importantes nas coleções do Atlas."""
        try:
            logger.info("Criando índices no Atlas...")
            
            # Índices para checkin_anchors
            await self.atlas_db.checkin_anchors.create_index([("chat_id", 1), ("active", 1)])
            
            # Índices para user_checkins
            await self.atlas_db.user_checkins.create_index([("chat_id", 1), ("user_id", 1)])
            await self.atlas_db.user_checkins.create_index([("chat_id", 1), ("anchor_id", 1)])
            await self.atlas_db.user_checkins.create_index([("checkin_date", 1)])
            
            # Índices para blacklist
            await self.atlas_db.blacklist.create_index([("chat_id", 1)])
            await self.atlas_db.blacklist.create_index([("user_id", 1)])
            
            # Índices para qa_interactions
            await self.atlas_db.qa_interactions.create_index([("chat_id", 1), ("message_id", 1)])
            await self.atlas_db.qa_interactions.create_index([("user_id", 1), ("chat_id", 1)])
            
            # Índices para recurring_messages
            await self.atlas_db.recurring_messages.create_index([("chat_id", 1), ("active", 1)])
            
            logger.info("OK - Índices criados com sucesso")
            
        except PyMongoError as e:
            logger.error(f"Erro ao criar índices: {e}")
    
    async def verify_migration(self) -> bool:
        """
        Verifica se a migração foi bem-sucedida comparando contagens.
        
        Returns:
            bool: True se a verificação passou
        """
        try:
            logger.info("Verificando migração...")
            
            collections = await self.get_collections()
            verification_passed = True
            
            for collection_name in collections:
                local_count = await self.local_db[collection_name].count_documents({})
                atlas_count = await self.atlas_db[collection_name].count_documents({})
                
                logger.info(f"Coleção '{collection_name}': Local={local_count}, Atlas={atlas_count}")
                
                if atlas_count < local_count:
                    logger.warning(f"AVISO - Possível perda de dados na coleção '{collection_name}'")
                    verification_passed = False
            
            if verification_passed:
                logger.info("OK - Verificação de migração passou com sucesso")
            else:
                logger.warning("AVISO - Verificação de migração encontrou problemas")
            
            return verification_passed
            
        except PyMongoError as e:
            logger.error(f"Erro na verificação: {e}")
            return False
    
    async def migrate_all(self) -> bool:
        """
        Executa a migração completa.
        
        Returns:
            bool: True se toda a migração foi bem-sucedida
        """
        try:
            logger.info("=" * 50)
            logger.info("INICIANDO MIGRAÇÃO PARA MONGODB ATLAS")
            logger.info("=" * 50)
            
            # Conecta aos bancos
            await self.connect()
            
            # Obtém lista de coleções
            collections = await self.get_collections()
            
            if not collections:
                logger.warning("Nenhuma coleção encontrada para migrar")
                return True
            
            # Migra cada coleção
            success_count = 0
            for collection_name in collections:
                success = await self.migrate_collection(collection_name)
                if success:
                    success_count += 1
            
            # Cria índices
            await self.create_indexes()
            
            # Verifica migração
            verification_passed = await self.verify_migration()
            
            logger.info("=" * 50)
            logger.info("MIGRAÇÃO CONCLUÍDA")
            logger.info(f"Coleções migradas com sucesso: {success_count}/{len(collections)}")
            logger.info(f"Verificação passou: {'SIM' if verification_passed else 'NAO'}")
            logger.info("=" * 50)
            
            return success_count == len(collections) and verification_passed
            
        except Exception as e:
            logger.error(f"Erro durante a migração: {e}")
            return False
        finally:
            await self.close_connections()

async def main():
    """Função principal."""
    # Obtém strings de conexão
    local_connection = os.getenv("MONGODB_LOCAL_CONNECTION_STRING")
    atlas_connection = os.getenv("MONGODB_ATLAS_CONNECTION_STRING")
    
    if not local_connection:
        logger.error("MONGODB_LOCAL_CONNECTION_STRING não definida")
        sys.exit(1)
    
    if not atlas_connection:
        logger.error("MONGODB_ATLAS_CONNECTION_STRING não definida")
        sys.exit(1)
    
    # Confirma migração
    print("\nATENCAO: Esta operação irá migrar dados do MongoDB local para o Atlas.")
    print(f"Origem: {local_connection[:50]}...")
    print(f"Destino: {atlas_connection[:50]}...")
    
    confirm = input("\nDeseja continuar? (sim/não): ").strip().lower()
    if confirm not in ['sim', 's', 'yes', 'y']:
        print("Migração cancelada.")
        sys.exit(0)
    
    # Executa migração
    migrator = MongoDBMigrator(local_connection, atlas_connection)
    success = await migrator.migrate_all()
    
    if success:
        print("\nOK - Migração concluída com sucesso!")
        print("Você pode agora atualizar a MONGODB_CONNECTION_STRING para apontar para o Atlas.")
    else:
        print("\nERRO - Migração falhou. Verifique os logs para mais detalhes.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 