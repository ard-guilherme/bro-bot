"""
Testes para o cliente da Anthropic.
"""
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import os
import httpx
from src.utils.anthropic_client import AnthropicClient

class TestAnthropicClient(unittest.TestCase):
    """Testes para o cliente da Anthropic."""
    
    def setUp(self):
        """Configuração inicial para os testes."""
        # Define uma chave de API de teste
        self.test_api_key = "test_api_key"
        
        # Cria um cliente com a chave de API de teste
        self.client = AnthropicClient(self.test_api_key)
    
    def test_init_with_api_key(self):
        """Testa a inicialização do cliente com uma chave de API fornecida."""
        # Assert
        self.assertEqual(self.client.api_key, self.test_api_key)
    
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env_api_key"})
    def test_init_with_env_var(self):
        """Testa a inicialização do cliente com a variável de ambiente."""
        # Act
        client = AnthropicClient()
        
        # Assert
        self.assertEqual(client.api_key, "env_api_key")
    
    def test_init_without_api_key(self):
        """Testa a inicialização do cliente sem chave de API."""
        # Salva o valor original da variável de ambiente
        original_api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        try:
            # Remove a variável de ambiente
            if "ANTHROPIC_API_KEY" in os.environ:
                del os.environ["ANTHROPIC_API_KEY"]
            
            # Act & Assert
            with self.assertRaises(ValueError):
                AnthropicClient()
        finally:
            # Restaura o valor original da variável de ambiente
            if original_api_key is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_api_key
    
    @patch("httpx.AsyncClient.post")
    async def test_generate_response_success(self, mock_post):
        """Testa a geração de resposta com sucesso."""
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.json.return_value = {
            "content": [{"text": "Test response"}]
        }
        mock_post.return_value = mock_response
        
        # Act
        result = await self.client.generate_response(
            "Test prompt {{mensagem_de_apresentacao_membro}}",
            "Test message"
        )
        
        # Assert
        self.assertEqual(result, "Test response")
        mock_post.assert_called_once()
        
        # Verifica se o prompt foi substituído corretamente
        args, kwargs = mock_post.call_args
        self.assertIn("Test prompt Test message", str(kwargs["json"]))
    
    @patch("httpx.AsyncClient.post")
    async def test_generate_response_error(self, mock_post):
        """Testa a geração de resposta com erro."""
        # Arrange
        mock_post.side_effect = Exception("Test error")
        
        # Act & Assert
        with self.assertRaises(Exception):
            await self.client.generate_response(
                "Test prompt {{mensagem_de_apresentacao_membro}}",
                "Test message"
            )
    
    @patch("httpx.AsyncClient.post")
    async def test_generate_response_invalid_response(self, mock_post):
        """Testa a geração de resposta com resposta inválida."""
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.json.return_value = {}  # Resposta sem o campo 'content'
        mock_post.return_value = mock_response
        
        # Act
        result = await self.client.generate_response(
            "Test prompt {{mensagem_de_apresentacao_membro}}",
            "Test message"
        )
        
        # Assert
        self.assertIn("Desculpe", result)
        mock_post.assert_called_once()

if __name__ == "__main__":
    unittest.main() 