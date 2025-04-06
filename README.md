# BRO BOT

Um bot para Telegram desenvolvido para a comunidade GYM NATION de academia e fitness. O bot dá boas-vindas aos novos membros, gerencia um sistema de check-in, responde a dúvidas sobre fitness, fornece mensagens motivacionais, e muito mais.

## Funcionalidades Principais

-   **Boas-vindas a Novos Membros:** Detecção automática e mensagens de boas-vindas personalizadas.
-   **Sistema de Check-in:** Permite aos administradores definir mensagens de check-in e aos membros registrarem presença. Inclui ranking de check-ins.
-   **Assistente de Dúvidas Fitness:** Responde a dúvidas sobre treino, nutrição, suplementação, etc., quando mencionado. Inclui feedback e modo especialista.
-   **Comandos Diversos:** Inclui comandos para motivação, cálculo de macros, regras do grupo, e mais.
-   **Gerenciamento de Usuários:** Sistema de administradores do bot e blacklist para usuários.
-   **Mensagens Recorrentes:** Permite configurar o envio periódico de mensagens.
-   **Integração:** Utiliza MongoDB para armazenamento de dados e API da Anthropic para IA.
-   **Implantação:** Suporte a Docker para fácil configuração.
-   **Controle de Acesso:** Restringe o uso da maioria dos comandos ao proprietário e administradores designados.

## Tecnologias Utilizadas

- **Python 3.8+**: Linguagem principal de desenvolvimento
- **python-telegram-bot 20.7+**: Framework para integração com a API do Telegram
- **MongoDB**: Banco de dados NoSQL para armazenamento de dados
  - **motor 3.7.0+**: Cliente MongoDB assíncrono para Python
  - **pymongo 4.11.1+**: Utilizado para tipos de exceção e operações específicas
- **Anthropic API**: Serviço de IA para geração de respostas para dúvidas fitness e mensagens motivacionais
- **Docker**: Containerização para facilitar a implantação
- **Testes**: Utiliza pytest, pytest-mock e pytest-asyncio para testes automatizados

## Arquitetura do Projeto

O projeto segue uma arquitetura modular organizada da seguinte forma:

```
bro-bot/
├── src/                      # Código fonte do bot
│   ├── main.py               # Ponto de entrada da aplicação
│   ├── bot/                  # Lógica específica do bot
│   │   ├── handlers.py       # Handlers gerais de comandos
│   │   ├── checkin_handlers.py # Sistema de check-in
│   │   ├── mention_handlers.py # Respostas a menções (QA Fitness)
│   │   ├── blacklist_handlers.py # Sistema de blacklist
│   │   ├── messages.py       # Mensagens de texto usadas pelo bot
│   │   ├── motivation.py     # Geração de mensagens motivacionais
│   │   └── fitness_qa.py     # Interação com API Anthropic para QA
│   └── utils/                # Utilitários e módulos de suporte
│       ├── config.py         # Carregamento de configurações (.env)
│       ├── filters.py        # Filtros de mensagem personalizados
│       ├── mongodb_client.py # Funções de interação com MongoDB
│       ├── mongodb_instance.py # Inicialização do cliente MongoDB
│       ├── anthropic_client.py # Cliente para a API da Anthropic
│       └── recurring_messages_manager.py # Gerenciador de mensagens recorrentes
├── tests/                    # Testes automatizados
├── scripts/                  # Scripts auxiliares
└── docs/                     # Documentação adicional
```

## Requisitos

-   Python 3.8+
-   [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 20.7+
-   [python-dotenv](https://github.com/theskumar/python-dotenv) 1.0.0+
-   [motor](https://motor.readthedocs.io/en/stable/) 3.7.0+ (Cliente MongoDB assíncrono)
-   [pymongo](https://pymongo.readthedocs.io/en/stable/) 4.11.1+ (Usado para tipos de exceção)
-   [anthropic](https://github.com/anthropics/anthropic-sdk-python) (SDK da Anthropic)
-   MongoDB (Local ou remoto)
-   Chave API da Anthropic
-   Token do Bot do Telegram

**Para desenvolvimento e testes:**

-   [pytest](https://docs.pytest.org/en/latest/) 8.3.4+
-   [pytest-mock](https://github.com/pytest-dev/pytest-mock/) 3.11.1+
-   [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) 0.25.3+

## Instalação

1.  Clone o repositório:
    ```bash
    git clone https://github.com/seu-usuario/bro-bot.git
    cd bro-bot
    ```

2.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

3.  Configure as variáveis de ambiente:
    -   Crie um arquivo `.env` na raiz do projeto baseado no `.env.example`.
    -   Preencha com suas chaves API, string de conexão do MongoDB e ID do proprietário.

## Execução

### Método 1: Execução direta

Execute o bot a partir do diretório raiz:
```bash
python -m src.main
```

### Método 2: Usando Docker

1.  Inicie o MongoDB e o bot com Docker Compose:
    ```bash
    docker-compose up -d
    ```
2.  Para parar os serviços:
    ```bash
    docker-compose down
    ```

## Funcionalidades Detalhadas

### Sistema de Check-in

O sistema de check-in permite que administradores definam "âncoras" de check-in em mensagens específicas. Os membros podem responder a essas mensagens para registrar sua presença, acumulando pontos que são exibidos em um ranking.

- Check-in normal: Vale 1 ponto
- Check-in PLUS: Vale 2 pontos e pode gerar respostas personalizadas da IA

### Assistente de Dúvidas Fitness

Quando mencionado em resposta a uma mensagem contendo uma dúvida sobre fitness, o bot utiliza a API da Anthropic para gerar uma resposta informativa. Os usuários podem fornecer feedback sobre a qualidade da resposta.

### Sistema de Blacklist

Permite que administradores adicionem mensagens específicas a uma lista negra para monitoramento e moderação do chat.

### Mensagens Recorrentes

Permite configurar mensagens para serem enviadas automaticamente em intervalos regulares no chat.

## Testes

Execute os testes automatizados com:
```bash
pytest
```

## Controle de Acesso e Permissões

O bot opera com um sistema de permissões baseado em três níveis:

1.  **Proprietário do Bot:** Definido pela variável `OWNER_ID` no `.env`. Tem acesso total a todos os comandos.
2.  **Administradores do Bot:** Usuários adicionados pelo proprietário através do comando `/setadmin`. Podem usar a maioria dos comandos.
3.  **Membros do Grupo:** Usuários regulares nos grupos onde o bot está. Acesso limitado às funcionalidades básicas como check-in e perguntas via menção.

## Comandos do Bot

### Comandos para Proprietário e Administradores

- `/start` - Inicia a interação com o bot
- `/help` - Mostra a mensagem de ajuda
- `/motivacao` - Envia uma mensagem de motivação fitness
- `/fecho` - Envia uma tirada sarcástica e debochada
- `/apresentacao` - Responde com uma apresentação do bot
- `/macros <descrição>` - Calcula macronutrientes
- `/regras` - Mostra as regras do grupo
- `/checkin` - Define âncora de check-in normal (1 ponto)
- `/checkinplus` - Define âncora de check-in PLUS (2 pontos)
- `/endcheckin` - Desativa o check-in ativo
- `/checkinscore` - Mostra o ranking de check-ins
- `/confirmcheckin` - Confirma manualmente o check-in de um usuário
- `/addblacklist` - Adiciona uma mensagem à blacklist
- `/blacklist` - Lista mensagens na blacklist
- `/rmblacklist` - Remove uma mensagem da blacklist
- `/say` - Faz o bot enviar uma mensagem
- `/sayrecurrent` - Configura uma mensagem recorrente
- `/listrecurrent` - Lista mensagens recorrentes configuradas
- `/delrecurrent` - Deleta uma mensagem recorrente

### Comandos Exclusivos do Proprietário

- `/setadmin` - Adiciona um usuário como administrador do bot
- `/deladmin` - Remove um usuário da lista de administradores
- `/listadmins` - Lista todos os administradores do bot
- `/monitor` - Começa a monitorar mensagens em um grupo
- `/unmonitor` - Para de monitorar mensagens no grupo

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir *issues* ou enviar *pull requests*.

## Próximos Passos e Melhorias

Algumas sugestões para futuras melhorias no projeto:

1. **Otimização de Desempenho**:
   - Implementar cache para consultas frequentes ao MongoDB
   - Otimizar consultas ao banco de dados para aumentar a eficiência
   - Considerar a implementação de um sistema de fila para operações assíncronas

2. **Melhorias na IA**:
   - Atualizar para modelos mais recentes da Anthropic (Claude 3.5 Sonnet)
   - Implementar mecanismos de aprendizado contínuo com base no feedback dos usuários
   - Adicionar capacidade de processamento de imagens para análise de fotos de treino

3. **Novas Funcionalidades**:
   - Sistema de lembretes personalizados para treinos
   - Integração com aplicativos de fitness populares
   - Implementação de desafios e competições entre membros
   - Análise de métricas de progresso dos usuários
   - Suporte para criação e compartilhamento de treinos personalizados

4. **Segurança e Estabilidade**:
   - Implementar testes de integração mais abrangentes
   - Melhorar o sistema de log para facilitar a detecção de problemas
   - Adicionar monitoramento de saúde do bot e alertas automáticos

5. **Documentação e Usabilidade**:
   - Melhorar a documentação para desenvolvedores
   - Adicionar guias de uso para administradores e usuários finais
   - Implementar um painel administrativo web para gerenciamento do bot

6. **Escalabilidade**:
   - Preparar a infraestrutura para suportar maior número de grupos e usuários
   - Implementar sharding do MongoDB para maior escalabilidade
   - Otimizar o consumo de recursos para reduzir custos operacionais 