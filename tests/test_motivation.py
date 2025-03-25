"""
Testes para o módulo de motivação.
"""
import unittest
from src.bot.motivation import get_random_motivation

class TestMotivation(unittest.TestCase):
    """Testes para a funcionalidade de motivação."""
    
    def test_get_random_motivation(self):
        """Testa se a função retorna uma mensagem de motivação válida."""
        # Act
        result = get_random_motivation()
        
        # Assert
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # Verifica se a mensagem contém emojis comuns de fitness
        common_fitness_emojis = ["💪", "🏋️", "🔥", "⚡", "💯", "🏆", "🚀", "⏱️", "💦", "🧠", "🔑", "🌟", "🏃", "🔄"]
        has_emoji = any(emoji in result for emoji in common_fitness_emojis)
        self.assertTrue(has_emoji, f"A mensagem '{result}' não contém emojis de fitness comuns")

if __name__ == "__main__":
    unittest.main() 