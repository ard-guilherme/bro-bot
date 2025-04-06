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
    git clone https://github.com/seu-usuario/gym-nation-bot.git
    cd gym-nation-bot
    ```

2.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

3.  Configure as variáveis de ambiente:
    -   Crie um arquivo `.env` na raiz do projeto baseado no `.env.example`.
    -   Preencha com suas chaves API, string de conexão do MongoDB e ID do proprietário:
        ```
        TELEGRAM_API_TOKEN=seu_token_aqui
        ANTHROPIC_API_KEY=sua_chave_anthropic_aqui
        MONGODB_CONNECTION_STRING=sua_string_de_conexao_mongodb
        OWNER_ID=seu_id_do_telegram # Importante para permissões
        BOT_USERNAME=Nations_bro_bot # Opcional, usado em algumas lógicas
        ```
    -   Para obter seu ID do Telegram, envie uma mensagem para [@userinfobot](https://t.me/userinfobot).

## Uso

### Método 1: Execução direta

Execute o bot a partir do diretório raiz:
```bash
python -m src.main
```

### Método 2: Usando Docker

1.  Certifique-se de que o Docker e o Docker Compose estejam instalados.
2.  Inicie o MongoDB e o bot com Docker Compose:
    ```bash
    docker-compose up -d
    ```
3.  Para parar os serviços:
    ```bash
    docker-compose down
    ```

## Controle de Acesso e Permissões

O bot opera com um sistema de permissões baseado em três níveis:

1.  **Proprietário do Bot:** Definido pela variável `OWNER_ID` no `.env`. Tem acesso total a todos os comandos e funcionalidades, incluindo o gerenciamento de administradores do bot.
2.  **Administradores do Bot:** Usuários adicionados pelo proprietário através do comando `/setadmin`. Podem usar a maioria dos comandos de interação e moderação em grupos onde o bot está presente e em chats privados com o bot.
3.  **Membros do Grupo:** Usuários regulares nos grupos onde o bot está. Podem interagir com o bot principalmente através do sistema de check-in e do assistente de dúvidas por menção. A maioria dos comandos diretos é ignorada.

**Importante:** Por padrão, o bot só responde a comandos enviados pelo Proprietário ou Administradores do Bot, tanto em chats privados quanto em grupos. Mensagens de outros usuários que tentam usar comandos são silenciosamente ignoradas. A exceção é o Assistente de Dúvidas Fitness, que pode ser ativado por qualquer membro ao mencionar o bot em resposta a uma pergunta.

## Comandos do Bot

### Comandos para Proprietário e Administradores do Bot

Estes comandos podem ser usados pelo proprietário e pelos administradores do bot em chats privados ou em grupos onde o bot está.

-   `/start` - Inicia a interação com o bot (em chat privado).
-   `/help` - Mostra a mensagem de ajuda com os comandos disponíveis.
-   `/motivacao` - Envia uma mensagem de motivação fitness gerada por IA.
-   `/fecho` - Envia uma tirada sarcástica e debochada com humor.
-   `/apresentacao` - Responde com uma apresentação personalizada do bot.
-   `/macros <descrição do alimento/refeição>` - Calcula macronutrientes estimados para o item descrito.
-   `/regras` - Mostra as regras do grupo GYM NATION (se configuradas).
-   `/checkin` - (Respondendo a uma mensagem) Define a mensagem respondida como a âncora de check-in ativa para o grupo.
-   `/endcheckin` - Desativa o check-in ativo no grupo.
-   `/checkinscore` - Mostra o ranking de check-ins dos usuários no grupo.
-   `/confirmcheckin <user_id ou reply>` - Confirma manualmente o check-in para um usuário específico no check-in ativo.
-   `/addblacklist` - (Respondendo a uma mensagem) Adiciona a mensagem respondida à blacklist do chat.
-   `/blacklist` - Lista as mensagens atualmente na blacklist do chat.
-   `/rmblacklist <id_da_mensagem_na_blacklist>` - Remove uma mensagem da blacklist usando seu ID único.
-   `/say <mensagem>` - Faz o bot enviar a mensagem especificada no chat atual.
-   `/sayrecurrent <intervalo> <mensagem>` - Configura uma mensagem recorrente. Intervalo (ex: `1d`, `2h30m`).
-   `/listrecurrent` - Lista as mensagens recorrentes configuradas para o chat.
-   `/delrecurrent <id_da_mensagem>` - Deleta uma mensagem recorrente pelo seu ID.

### Comandos Exclusivos do Proprietário do Bot

Estes comandos só podem ser usados pelo usuário definido como `OWNER_ID`.

-   `/setadmin <user_id ou reply> [Nome Opcional]` - Adiciona um usuário como administrador do bot. Pode ser usado respondendo a uma mensagem do usuário ou fornecendo o ID diretamente.
-   `/deladmin <user_id ou reply>` - Remove um usuário da lista de administradores do bot.
-   `/listadmins` - Lista todos os administradores atuais do bot.
-   `/monitor` - (Em um grupo) Começa a monitorar todas as mensagens enviadas no grupo (para fins de depuração ou análise).
-   `/unmonitor` - (Em um grupo) Para de monitorar as mensagens no grupo.

### Interações para Membros do Grupo

Membros regulares podem interagir com o bot das seguintes formas:

-   **Check-in:** Responder à mensagem âncora de check-in (definida por um admin/proprietário) para registrar presença.
-   **Assistente de Dúvidas Fitness:** Mencionar o bot (`@NomeDoBot`) em resposta a uma mensagem contendo uma dúvida sobre fitness para receber uma resposta gerada por IA.

## Funcionalidades Detalhadas

### Sistema de Check-in

1.  Um administrador ou proprietário usa `/checkin` respondendo a uma mensagem no grupo. Essa mensagem se torna a "âncora".
2.  Membros podem responder a essa mensagem âncora (com qualquer texto/emoji) para fazer check-in.
3.  O bot reage à resposta do membro para confirmar o check-in.
4.  `/checkinscore` mostra quem fez mais check-ins.
5.  `/endcheckin` desativa a âncora atual.
6.  `/confirmcheckin` permite adicionar manualmente um check-in para um usuário.

### Assistente de Dúvidas Fitness por Menção

1.  Um membro responde a uma mensagem com uma dúvida fitness mencionando o bot (ex: `@Nations_bro_bot`).
2.  O bot usa a API da Anthropic para analisar a pergunta e gerar uma resposta informativa.
3.  A resposta inclui botões de feedback (👍/👎) e um botão "Modo Especialista" para uma resposta mais detalhada via mensagem privada.
4.  Há um limite diário de consultas por usuário.

### Sistema de Blacklist

-   Permite que proprietário/admins adicionem mensagens específicas (usando `/addblacklist` em resposta) a uma lista negra para um chat.
-   Útil para marcar conteúdo inadequado ou spam recorrente.
-   `/blacklist` lista as mensagens marcadas e `/rmblacklist` remove uma entrada pelo seu ID.

### Mensagens Recorrentes

-   Proprietário/admins podem configurar mensagens para serem enviadas automaticamente em intervalos regulares (dias, horas, minutos) usando `/sayrecurrent`.
-   `/listrecurrent` mostra as mensagens agendadas e `/delrecurrent` permite removê-las.

## Testes

Execute os testes automatizados com:
```bash
pytest
```

## Estrutura do Projeto

```
bro-bot/
├── .env                      # Variáveis de ambiente (não versionado)
├── .env.example              # Exemplo de variáveis de ambiente
├── .gitignore                # Arquivos ignorados pelo Git
├── README.md                 # Este arquivo
├── requirements.txt          # Dependências Python
├── docker-compose.yml        # Configuração do Docker Compose
├── src/                      # Código fonte do bot
│   ├── __init__.py
│   ├── main.py               # Ponto de entrada da aplicação
│   ├── bot/                  # Lógica específica do bot (handlers, etc.)
│   │   ├── __init__.py
│   │   ├── handlers.py       # Handlers gerais de comandos
│   │   ├── checkin_handlers.py # Lógica do sistema de check-in
│   │   ├── mention_handlers.py # Lógica para responder a menções (QA Fitness)
│   │   ├── blacklist_handlers.py # Lógica do sistema de blacklist
│   │   ├── messages.py       # Mensagens de texto usadas pelo bot
│   │   ├── motivation.py     # Geração de mensagens motivacionais
│   │   └── fitness_qa.py     # Interação com API Anthropic para QA
│   └── utils/                # Utilitários e módulos de suporte
│       ├── __init__.py
│       ├── config.py         # Carregamento de configurações (.env)
│       ├── filters.py        # Filtros de mensagem personalizados (permissões)
│       ├── mongodb_client.py # Funções de interação com MongoDB
│       ├── mongodb_instance.py # Inicialização da instância do cliente MongoDB
│       ├── anthropic_client.py # Cliente para a API da Anthropic
│       └── recurring_messages_manager.py # Gerenciador de mensagens recorrentes
├── tests/                    # Testes automatizados (pytest)
│   ├── __init__.py
│   ├── test_*.py             # Arquivos de teste para diferentes módulos
│   └── .pytest_cache/        # Cache do pytest
├── scripts/                  # Scripts auxiliares (manutenção, etc.)
│   ├── check_recurring_messages.py
│   ├── clean_recurring_messages.py
│   ├── create_test_recurring_message.py
│   ├── fix_db.py
│   └── check_db.py
├── docs/                     # Documentação adicional (se houver)
├── .git/                     # Metadados do Git
└── venv/                     # Ambiente virtual Python (não versionado)
```

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir *issues* ou enviar *pull requests*. 