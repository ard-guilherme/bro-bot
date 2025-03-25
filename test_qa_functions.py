"""
Script para testar as funções de perguntas e respostas.
"""
import asyncio
import os
from src.utils.mongodb_client import MongoDBClient

async def test_qa_functions():
    """Testa as funções de perguntas e respostas."""
    # Obtém a string de conexão do ambiente
    connection_string = os.getenv("MONGODB_CONNECTION_STRING", "mongodb://admin:password@localhost:27017")
    
    # Cria o cliente do MongoDB
    client = MongoDBClient(connection_string)
    
    try:
        # Conecta ao banco de dados
        print("Conectando ao MongoDB...")
        await client.connect("gym_nation_bot")
        print("Conectado ao MongoDB")
        
        # Verifica se a conexão foi estabelecida
        if client.db is None:
            print("Erro: Não foi possível conectar ao banco de dados.")
            return
        
        print("Testando get_daily_qa_count...")
        count = await client.get_daily_qa_count(123, 456)
        print(f"Contagem: {count}")
        
        print("Testando get_last_qa_timestamp...")
        timestamp = await client.get_last_qa_timestamp(123, 456)
        print(f"Timestamp: {timestamp}")
        
        print("Testando increment_qa_usage...")
        result = await client.increment_qa_usage(123, 456)
        print(f"Resultado: {result}")
        
        # Testa store_qa_interaction
        print("Testando store_qa_interaction...")
        qa_interaction = {
            "chat_id": 456,
            "message_id": 789,
            "user_id": 123,
            "question": "Como fazer agachamento?",
            "answer": "Aqui está uma resposta sobre agachamento.",
            "category": "Treino"
        }
        result = await client.store_qa_interaction(qa_interaction)
        print(f"Resultado: {result}")
        
        # Testa get_qa_interaction
        print("Testando get_qa_interaction...")
        interaction = await client.get_qa_interaction(456, 789)
        print(f"Interação: {interaction}")
        
        # Testa store_qa_feedback
        print("Testando store_qa_feedback...")
        result = await client.store_qa_feedback(456, 789, "positive")
        print(f"Resultado: {result}")
        
        # Verifica se o feedback foi armazenado
        print("Verificando se o feedback foi armazenado...")
        interaction = await client.get_qa_interaction(456, 789)
        print(f"Interação com feedback: {interaction}")
        
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        # Fecha a conexão com o MongoDB
        if client.client:
            await client.close()
            print("Conexão com o MongoDB fechada")

if __name__ == "__main__":
    asyncio.run(test_qa_functions()) 