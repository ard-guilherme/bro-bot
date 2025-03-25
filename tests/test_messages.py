"""
Testes para o módulo de mensagens.
"""
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from src.bot.messages import Messages
import re

class TestMessages(unittest.TestCase):
    """Testes para a classe Messages."""
    
    def test_get_welcome_message(self):
        """Testa se a mensagem de boas-vindas é personalizada corretamente."""
        # Arrange
        user_name = "John Doe"
        expected_prefix = f"Olá, {user_name}!"
        
        # Act
        result = Messages.get_welcome_message(user_name)
        
        # Assert
        self.assertTrue(result.startswith(expected_prefix))
        self.assertIn("fitness", result)
    
    def test_get_help_message(self):
        """Testa se a mensagem de ajuda contém os comandos esperados."""
        # Act
        result = Messages.get_help_message()
        
        # Assert
        self.assertIn("/start", result)
        self.assertIn("/help", result)
        self.assertIn("GYM NATION Bot", result)
    
    def test_get_start_message(self):
        """Testa se a mensagem de início contém as informações esperadas."""
        # Act
        result = Messages.get_start_message()
        
        # Assert
        self.assertIn("GYM NATION Bot", result)
        self.assertIn("assistente", result)
        self.assertIn("/help", result)

    def test_get_welcome_message(self):
        """Testa a mensagem de boas-vindas."""
        # Arrange
        name = "Test"
        
        # Act
        message = Messages.get_welcome_message(name)
        
        # Assert
        self.assertIn(name, message)
        self.assertIn("bem-vindo", message.lower())
        
    def test_get_help_message(self):
        """Testa a mensagem de ajuda."""
        # Act
        message = Messages.get_help_message()
        
        # Assert
        self.assertIn("/start", message)
        self.assertIn("/help", message)
        self.assertIn("/motivacao", message)
        self.assertIn("/apresentacao", message)
        
    def test_get_random_motivation_message(self):
        """Testa a mensagem de motivação aleatória da lista fixa."""
        # Act
        message = Messages.get_random_motivation_message()
        
        # Assert
        self.assertIsNotNone(message)
        self.assertIsInstance(message, str)
        
        # Verifica se a mensagem contém emojis de fitness comuns
        fitness_emojis = ["💪", "🏋️", "🏃", "🧘", "🏆", "🥇", "🔥", "⚡", "🚴", "🏊", "⏱️", "💯", "🧠", "💦", "🔄", "🌟", "🔑", "🚀"]
        has_fitness_emoji = any(emoji in message for emoji in fitness_emojis)
        self.assertTrue(has_fitness_emoji, f"A mensagem '{message}' não contém emojis de fitness comuns")

    def test_get_random_positive_emoji(self):
        """Testa a obtenção de um emoji positivo aleatório."""
        # Act
        emoji = Messages.get_random_positive_emoji()
        
        # Assert
        self.assertIsNotNone(emoji)
        self.assertIsInstance(emoji, str)
        self.assertIn(emoji, Messages.POSITIVE_REACTION_EMOJIS)

    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_presentation_response_success(self, mock_generate_response):
        """Testa a obtenção de resposta de apresentação com sucesso."""
        # Arrange
        mock_generate_response.return_value = "Resposta personalizada"
        presentation_message = "Olá, sou novo no grupo!"
        
        # Act
        response = await Messages.get_presentation_response(presentation_message)
        
        # Assert
        self.assertEqual(response, "Resposta personalizada")
        mock_generate_response.assert_called_once_with(
            prompt_template=unittest.mock.ANY,
            message_content=presentation_message,
            max_tokens=200
        )
        
    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_presentation_response_with_image_success(self, mock_generate_response):
        """Testa a obtenção de resposta de apresentação com imagem e com sucesso."""
        # Arrange
        # Configura o mock para retornar valores diferentes em cada chamada
        mock_generate_response.side_effect = [
            "Pessoa em roupas de treino na academia usando equipamentos de musculação.",  # Descrição da imagem
            "Resposta personalizada com análise da imagem"  # Resposta final
        ]
        presentation_message = "Olá, sou novo no grupo!"
        image_data = b"fake_image_data"
        image_mime_type = "image/jpeg"
        
        # Act
        response = await Messages.get_presentation_response(
            presentation_message,
            image_data=image_data,
            image_mime_type=image_mime_type
        )
        
        # Assert
        self.assertEqual(response, "Resposta personalizada com análise da imagem")
        
        # Verifica se o mock foi chamado duas vezes
        self.assertEqual(mock_generate_response.call_count, 2)
        
        # Verifica a primeira chamada (análise da imagem)
        first_call_args = mock_generate_response.call_args_list[0][1]
        self.assertEqual(first_call_args["message_content"], "")
        self.assertEqual(first_call_args["image_data"], image_data)
        self.assertEqual(first_call_args["image_mime_type"], image_mime_type)
        self.assertEqual(first_call_args["max_tokens"], 150)
        
        # Verifica a segunda chamada (resposta final)
        second_call_args = mock_generate_response.call_args_list[1][1]
        self.assertEqual(second_call_args["message_content"], presentation_message)
        self.assertEqual(second_call_args["max_tokens"], 200)
        self.assertNotIn("image_data", second_call_args)
        
    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_presentation_response_with_image_first_call_error(self, mock_generate_response):
        """Testa o fallback quando a primeira chamada (análise da imagem) falha."""
        # Arrange
        # Configura o mock para lançar exceção na primeira chamada e retornar valor na segunda
        mock_generate_response.side_effect = [
            Exception("Erro na análise da imagem"),  # Primeira chamada falha
            "Resposta personalizada sem análise da imagem"  # Segunda chamada (fallback)
        ]
        presentation_message = "Olá, sou novo no grupo!"
        image_data = b"fake_image_data"
        image_mime_type = "image/jpeg"
        
        # Act
        response = await Messages.get_presentation_response(
            presentation_message,
            image_data=image_data,
            image_mime_type=image_mime_type
        )
        
        # Assert
        self.assertEqual(response, "Resposta personalizada sem análise da imagem")
        
        # Verifica se o mock foi chamado duas vezes
        self.assertEqual(mock_generate_response.call_count, 2)
        
    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_presentation_response_error(self, mock_generate_response):
        """Testa a obtenção de resposta de apresentação com erro."""
        # Arrange
        mock_generate_response.side_effect = Exception("Erro na API")
        presentation_message = "Olá, sou novo no grupo!"
        
        # Act
        response = await Messages.get_presentation_response(presentation_message)
        
        # Assert
        self.assertIn("Bem-vindo", response)
        mock_generate_response.assert_called_once()
        
    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_presentation_response_with_image_error(self, mock_generate_response):
        """Testa a obtenção de resposta de apresentação com imagem e com erro."""
        # Arrange
        # Configura o mock para lançar exceção em todas as chamadas
        mock_generate_response.side_effect = Exception("Erro na API")
        presentation_message = "Olá, sou novo no grupo!"
        image_data = b"fake_image_data"
        image_mime_type = "image/jpeg"
        
        # Act
        response = await Messages.get_presentation_response(
            presentation_message,
            image_data=image_data,
            image_mime_type=image_mime_type
        )
        
        # Assert
        self.assertIn("Bem-vindo", response)
        mock_generate_response.assert_called_once()
        
    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_presentation_response_empty_message(self, mock_get_presentation):
        """Testa a obtenção de resposta de apresentação com mensagem vazia."""
        # Arrange
        presentation_message = ""
        
        # Act
        response = await Messages.get_presentation_response(presentation_message)
        
        # Assert
        self.assertIn("Bem-vindo", response)
        mock_get_presentation.assert_not_called()

    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_motivation_message_async_success(self, mock_generate_response):
        """Testa a geração de mensagem de motivação com sucesso."""
        # Arrange
        mock_response = "💪 Mensagem de motivação gerada pela API"
        mock_generate_response.return_value = mock_response
        
        # Act
        result = await Messages.get_motivation_message_async()
        
        # Assert
        self.assertEqual(result, mock_response)
        mock_generate_response.assert_called_once()
    
    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_motivation_message_async_error(self, mock_generate_response):
        """Testa o fallback quando a API falha."""
        # Arrange
        mock_generate_response.side_effect = Exception("API Error")
        
        # Act
        result = await Messages.get_motivation_message_async()
        
        # Assert
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        mock_generate_response.assert_called_once()
    
    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_fecho_message_async_success(self, mock_generate_response):
        """Testa a geração de mensagem sarcástica com sucesso."""
        # Arrange
        mock_response = "😂 Tirada sarcástica gerada pela API"
        mock_generate_response.return_value = mock_response
        
        # Act
        result = await Messages.get_fecho_message_async()
        
        # Assert
        self.assertEqual(result, mock_response)
        mock_generate_response.assert_called_once()
    
    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_fecho_message_async_with_user(self, mock_generate_response):
        """Testa a geração de mensagem sarcástica personalizada para um usuário."""
        # Arrange
        user_name = "João"
        mock_response = "🤣 Tirada sarcástica personalizada para João"
        mock_generate_response.return_value = mock_response
        
        # Act
        result = await Messages.get_fecho_message_async(user_name=user_name)
        
        # Assert
        self.assertEqual(result, mock_response)
        mock_generate_response.assert_called_once()
        # Verifica se o nome do usuário foi passado para o prompt
        call_args = mock_generate_response.call_args[0]
        self.assertIn(user_name, call_args[0])
    
    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_fecho_message_async_with_content(self, mock_generate_response):
        """Testa a geração de mensagem sarcástica baseada no conteúdo da mensagem."""
        # Arrange
        message_content = "Hoje eu fiz 10 repetições de supino"
        mock_response = "😂 Tirada sarcástica sobre supino"
        mock_generate_response.return_value = mock_response
        
        # Act
        result = await Messages.get_fecho_message_async(message_content=message_content)
        
        # Assert
        self.assertEqual(result, mock_response)
        mock_generate_response.assert_called_once()
        # Verifica se o conteúdo da mensagem foi passado para o prompt
        call_args = mock_generate_response.call_args[0]
        self.assertIn(message_content, call_args[0])
    
    @patch('src.utils.anthropic_client.AnthropicClient.generate_response')
    async def test_get_fecho_message_async_error(self, mock_generate_response):
        """Testa o fallback quando a API falha ao gerar uma mensagem sarcástica."""
        # Arrange
        mock_generate_response.side_effect = Exception("API Error")
        
        # Act
        result = await Messages.get_fecho_message_async()
        
        # Assert
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        # Verifica se a mensagem de fallback contém emojis de humor
        self.assertTrue(any(emoji in result for emoji in ["😂", "🤣", "😅", "😆"]))
        mock_generate_response.assert_called_once()

if __name__ == "__main__":
    unittest.main() 