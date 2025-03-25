"""
Mensagens de motivação fitness para o bot.
"""
import random
from typing import List

def get_random_motivation() -> str:
    """
    Retorna uma mensagem de motivação fitness aleatória.
    
    Returns:
        str: Mensagem de motivação.
    """
    motivational_quotes = [
        "💪 Não existe treino ruim, apenas dias bons e dias ótimos!",
        "🏋️ O único treino ruim é aquele que você não fez.",
        "🔥 Dor temporária, orgulho eterno.",
        "⚡ Seu corpo aguenta muito mais do que sua mente acredita.",
        "💯 Foco, força e fé. Um dia de cada vez.",
        "🏆 Não conte os dias, faça os dias contarem.",
        "🚀 O sucesso não acontece da noite para o dia. Nem o físico dos seus sonhos.",
        "💪 Não pare quando estiver cansado. Pare quando estiver pronto.",
        "🔄 💪 Transforme 'eu queria' em 'eu vou'.",
        "🏋️ Levante, treine, repita.",
        "⏱️ Uma hora de treino é apenas 4% do seu dia. Sem desculpas.",
        "💦 Suor é apenas gordura chorando.",
        "🧠 Sua mente desiste muito antes do seu corpo.",
        "🔑 Disciplina é escolher entre o que você quer agora e o que você quer mais.",
        "🌟 Seja mais forte que suas desculpas.",
        "🏃 Não importa o quão devagar você vá, desde que não pare.",
        "💯 Você não precisa ser extremo, apenas consistente.",
        "🔄 Progresso, não perfeição.",
        "🏋️ Treine como se você nunca tivesse vencido. Aja como se nunca tivesse falhado.",
        "💪 Você é mais forte do que pensa.",
        "💪 No GYM NATION, cada rep conta. Cada suor vale a pena.",
        "🏆 GYM NATION: onde os fracos não têm vez e os fortes se superam.",
        "🔥 Aqui no GYM NATION, transformamos suor em resultados.",
        "💯 GYM NATION: construindo corpos e fortalecendo mentes.",
        "⚡ No GYM NATION, não existem limites, apenas desafios.",
        "🚀 Faça parte da revolução fitness. GYM NATION!",
        "💪 GYM NATION: onde cada dia é dia de superar seus limites.",
        "🏋️ Seja a melhor versão de si mesmo. GYM NATION acredita em você!"
    ]
    
    return random.choice(motivational_quotes) 