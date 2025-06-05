# Bro Bot - GYM NATION Telegram Bot

Um bot Telegram completo desenvolvido em Python para gerenciamento de comunidades de fitness. O bot oferece sistema de check-in gamificado, moderação inteligente com blacklist, respostas contextuais com IA (Anthropic Claude), mensagens recorrentes automáticas e controles administrativos avançados.

## 📋 Índice

- [Funcionalidades](#-funcionalidades)
- [Arquitetura](#-arquitetura)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Instalação e Configuração](#-instalação-e-configuração)
- [Uso e Comandos](#-uso-e-comandos)
- [Deployment](#-deployment)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Desenvolvimento](#-desenvolvimento)
- [API e Integrações](#-api-e-integrações)
- [Contribuição](#-contribuição)

## 🚀 Funcionalidades

### Sistema de Check-in Gamificado
- **Check-in Normal**: 1 ponto por check-in
- **Check-in PLUS**: 2+ pontos com respostas personalizadas da IA
- **Múltiplas Âncoras**: Suporte a múltiplos check-ins simultâneos por grupo
- **Ranking Dinâmico**: Sistema de pontuação e scoreboard em tempo real
- **Confirmação Manual**: Admins podem confirmar check-ins manualmente
- **Mensagens Contextuais**: Respostas diferenciadas por nível de experiência

### Moderação Inteligente
- **Blacklist Automática**: Sistema de lista negra para moderação
- **Notificações Inteligentes**: Aviso automático via DM para usuários adicionados
- **Fallback para Novos Usuários**: Mensagem no grupo quando DM não é possível
- **Banimento em Lote**: Comando para banir múltiplos usuários da blacklist
- **Paginação Automática**: Listas grandes divididas em múltiplas mensagens
- **Gestão por Links**: Remoção de itens via link da mensagem original

### IA Contextual (Anthropic Claude)
- **Respostas Especializadas**: Foco em fitness, nutrição e treino
- **Análise de Contexto**: Considera thread completa ao responder menções
- **Rate Limiting**: 2 perguntas por dia por usuário
- **Sistema de Feedback**: Usuários podem avaliar qualidade das respostas
- **Controle de Uso**: Métricas e limitações de API

### Correio Elegante 📬
- **Mensagens Anônimas**: Envio de mensagens anônimas entre membros do grupo
- **Sistema de Pagamento**: Revelação do remetente via Pix (R$ 2,00)
- **Publicação Automática**: Agendador publica correios no grupo a cada hora
- **Respostas Anônimas**: Destinatários podem responder anonimamente
- **Moderação Inteligente**: Sistema de denúncias e expiração automática (24h)
- **Filtros de Conteúdo**: Bloqueio automático de conteúdo ofensivo
- **Limite Diário**: 2 correios por usuário por dia
- **Validação de Membros**: Verifica se destinatário está no grupo

### Automação de Mensagens
- **Mensagens Recorrentes**: Agendamento flexível (horas/dias)
- **Edição em Tempo Real**: Modificação sem interrupção do serviço
- **Múltiplos Grupos**: Gestão de várias comunidades
- **Agendamento Inteligente**: Sistema de retry e recuperação

### Controles Administrativos
- **Hierarquia de Permissões**: Owner → Admins → Membros
- **Monitoramento de Grupos**: Tracking completo de atividades
- **Auditoria Completa**: Logs estruturados de todas as ações
- **Gestão de Admins**: Adicionar/remover administradores do bot

## 🏗️ Arquitetura

### Visão Geral
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram API  │    │   Bot Core      │    │  MongoDB Atlas  │
│                 │◄──►│                 │◄──►│                 │
│  - Messages     │    │  - Handlers     │    │  - User Data    │
│  - Commands     │    │  - Business     │    │  - Check-ins    │
│  - Callbacks    │    │  - Logic        │    │  - Blacklist    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Anthropic API  │
                       │                 │
                       │  - Claude AI    │
                       │  - Context      │
                       │  - Analysis     │
                       └─────────────────┘
```

### Componentes Principais

1. **Bot Core** (`src/main.py`)
   - Inicialização e configuração da aplicação
   - Gerenciamento de handlers e rotas
   - Sistema de retry e recuperação de erros
   - Configuração de comandos por escopo

2. **Handlers Modulares** (`src/bot/`)
   - `handlers.py`: Comandos gerais e administrativos
   - `checkin_handlers.py`: Sistema de check-in gamificado
   - `mention_handlers.py`: Respostas IA contextuais
   - `blacklist_handlers.py`: Moderação e blacklist
   - `messages.py`: Templates de mensagens
   - `motivation.py`: Sistema de motivação

3. **Utilitários** (`src/utils/`)
   - `mongodb_client.py`: Cliente MongoDB com operações CRUD
   - `anthropic_client.py`: Integração com Claude AI
   - `config.py`: Gerenciamento de configurações
   - `filters.py`: Filtros personalizados do Telegram
   - `recurring_messages_manager.py`: Automação de mensagens

4. **Scripts de Automação** (`scripts/`)
   - `migrate_to_atlas.py`: Migração de dados local → cloud
   - `deploy.py`: Automação de deployment

## 💻 Tecnologias Utilizadas

### Core Stack
- **Python 3.x**: Linguagem principal
- **python-telegram-bot 21.8**: Framework para Telegram Bot API
- **MongoDB Atlas**: Banco de dados cloud NoSQL
- **Motor + PyMongo**: Drivers assíncronos e síncronos para MongoDB
- **Anthropic API**: Integração com Claude AI

### Infrastructure & DevOps
- **Docker**: Containerização da aplicação
- **Docker Compose**: Orquestração de containers
- **Environment Variables**: Configuração segura via `.env`

### Development & Testing
- **pytest**: Framework de testes
- **pytest-asyncio**: Suporte a testes assíncronos
- **pytest-mock**: Mocking para testes
- **python-dotenv**: Carregamento de variáveis de ambiente

## 🛠️ Instalação e Configuração

### Pré-requisitos
- Python 3.8+
- Docker (opcional, para containerização)
- MongoDB Atlas account (ou MongoDB local)
- Anthropic API key
- Telegram Bot Token

### Configuração Inicial

1. **Clone o repositório**
   ```bash
   git clone https://github.com/seu-usuario/bro-bot.git
   cd bro-bot
   ```

2. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure as variáveis de ambiente**
   ```bash
   cp .env.example .env
   ```
   
   Edite o arquivo `.env` com suas configurações:
   ```env
   # Obrigatório: Token do Bot (BotFather)
   TELEGRAM_API_TOKEN=your_bot_token_here
   
   # Obrigatório: Seu ID do Telegram
   OWNER_ID=123456789
   
   # Obrigatório: Chave da API Anthropic
   ANTHROPIC_API_KEY=sk-ant-api03-your_key_here
   
   # Obrigatório: String de conexão MongoDB
   MONGODB_CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/
   
   # Opcional: Configurações adicionais
   BOT_USERNAME=Nations_bro_bot
   QA_DAILY_LIMIT=2
   LOG_LEVEL=INFO
   ```

### Obtenção de Credenciais

1. **Token do Telegram Bot**
   - Converse com [@BotFather](https://t.me/botfather)
   - Crie um novo bot com `/newbot`
   - Copie o token fornecido

2. **Seu ID do Telegram**
   - Envie uma mensagem para [@userinfobot](https://t.me/userinfobot)
   - Copie o ID numérico fornecido

3. **Chave da API Anthropic**
   - Acesse [console.anthropic.com](https://console.anthropic.com/)
   - Crie uma conta e gere uma API key

4. **MongoDB Atlas**
   - Crie uma conta em [mongodb.com](https://www.mongodb.com/atlas)
   - Configure um cluster gratuito
   - Obtenha a string de conexão

## 📋 Uso e Comandos

### Comandos Gerais (Proprietário/Admins)

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `/start` | Inicia o bot | `/start` |
| `/help` | Mostra ajuda | `/help` |
| `/motivacao` | Mensagem motivacional IA | `/motivacao` |
| `/macros` | Calcula macronutrientes | `/macros 100g peito frango` |
| `/regras` | Exibe regras do grupo | `/regras` |
| `/apresentacao` | Apresentação do bot | `/apresentacao` |

### Correio Elegante (Todos os Membros)

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `/correio` | Inicia envio de correio anônimo | `/correio` (apenas chat privado) |
| `/revelarcorreio` | Revela remetente via Pix | `/revelarcorreio ID_MENSAGEM` |
| `/respondercorreio` | Responde anonimamente | `/respondercorreio ID_MENSAGEM` |

### Sistema de Check-in

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `/checkin` | Define âncora check-in (1pt) | `/checkin` |
| `/checkinplus` | Define âncora check-in (2+pts) | `/checkinplus` |
| `/endcheckin` | Desativa check-in | `/endcheckin anchor_id` |
| `/checkinscore` | Mostra ranking | `/checkinscore` |
| `/confirmcheckin` | Confirma check-in manual | `/confirmcheckin @user anchor_id` |

### Moderação e Blacklist

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `/addblacklist` | Adiciona à blacklist | `/addblacklist` (reply) |
| `/blacklist` | Lista blacklist | `/blacklist grupo_name` |
| `/rmblacklist` | Remove da blacklist | `/rmblacklist item_id` |
| `/ban_blacklist` | Bane usuários em lote | `/ban_blacklist grupo_name` |

### Administração (Apenas Proprietário)

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `/setadmin` | Adiciona admin | `/setadmin` (reply ou forward) |
| `/deladmin` | Remove admin | `/deladmin user_id` |
| `/listadmins` | Lista admins | `/listadmins` |
| `/monitor` | Monitora grupo | `/monitor` |
| `/unmonitor` | Para monitoramento | `/unmonitor` |
| `/admincorreio` | Administra correio elegante | `/admincorreio status` |

### Mensagens Recorrentes

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `/sayrecurrent` | Cria mensagem recorrente | `/sayrecurrent` |
| `/listrecurrent` | Lista mensagens ativas | `/listrecurrent` |
| `/delrecurrent` | Remove mensagem | `/delrecurrent message_id` |

### Interação com IA

- **Menções**: Mencione o bot em qualquer mensagem para receber resposta contextual
- **Rate Limit**: 2 perguntas por dia por usuário
- **Feedback**: Reaja com 👍/👎 nas respostas para feedback

### Fluxo do Correio Elegante

1. **Envio**: Use `/correio` no chat privado com o bot
2. **Composição**: Digite sua mensagem (10-500 caracteres)
3. **Destinatário**: Informe o @ do destinatário (deve ser membro do grupo)
4. **Confirmação**: Revise e confirme o envio
5. **Publicação**: Mensagem é publicada automaticamente no grupo (até 1h)
6. **Interação**: Membros podem revelar remetente (R$2) ou responder anonimamente
7. **Expiração**: Correios expiram em 24h ou com 3+ denúncias

## 🚀 Deployment

### Desenvolvimento Local

```bash
# Execução direta
python -m src.main

# Com Docker (desenvolvimento)
docker-compose up -d
```

### Produção

1. **Usando Docker Compose (Recomendado)**
   ```bash
   # Configure .env para produção
   # Use docker-compose.prod.yml
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Deploy Automatizado**
   ```bash
   # Script de deploy completo
   python scripts/deploy.py
   ```

3. **Migração de Dados**
   ```bash
   # Migrar dados local → Atlas
   python scripts/migrate_to_atlas.py
   ```

### Monitoramento

```bash
# Logs em tempo real
docker logs gym-nation-bot-prod -f

# Status do container
docker ps | grep gym-nation

# Health check
docker exec gym-nation-bot-prod python -c "print('Bot healthy')"
```

## 📁 Estrutura do Projeto

```
bro-bot/
├── src/                          # Código fonte
│   ├── main.py                   # Entry point da aplicação
│   ├── bot/                      # Módulos do bot
│   │   ├── __init__.py
│   │   ├── handlers.py           # Handlers gerais
│   │   ├── checkin_handlers.py   # Sistema check-in
│   │   ├── mention_handlers.py   # Respostas IA
│   │   ├── blacklist_handlers.py # Moderação
│   │   ├── mail_handlers.py      # Correio elegante
│   │   ├── messages.py           # Templates mensagens
│   │   ├── motivation.py         # Sistema motivação
│   │   └── fitness_qa.py         # Q&A fitness
│   └── utils/                    # Utilitários
│       ├── __init__.py
│       ├── config.py             # Configurações
│       ├── filters.py            # Filtros customizados
│       ├── mongodb_client.py     # Cliente MongoDB
│       ├── mongodb_instance.py   # Instância MongoDB
│       ├── anthropic_client.py   # Cliente Anthropic
│       ├── mail_scheduler.py     # Agendador correio
│       └── recurring_messages_manager.py
├── tests/                        # Testes automatizados
│   ├── test_checkin_handlers.py
│   ├── test_blacklist_handlers.py
│   └── ...
├── scripts/                      # Scripts utilitários
│   ├── migrate_to_atlas.py       # Migração dados
│   └── deploy.py                 # Deploy automatizado
├── memory-bank/                  # Documentação Cursor
├── docs/                         # Documentação adicional
├── docker-compose.yml            # Config desenvolvimento
├── docker-compose.prod.yml       # Config produção
├── Dockerfile                    # Container config
├── requirements.txt              # Dependências Python
├── .env.example                  # Template configuração
├── .dockerignore                 # Exclusões Docker
├── .gitignore                    # Exclusões Git
├── DEPLOY.md                     # Guia deployment
└── README.md                     # Esta documentação
```

## 🔧 Desenvolvimento

### Configuração do Ambiente

1. **Ambiente Virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

2. **MongoDB Local (Desenvolvimento)**
   ```bash
   # Com Docker
   docker run -d -p 27017:27017 \
     -e MONGO_INITDB_ROOT_USERNAME=admin \
     -e MONGO_INITDB_ROOT_PASSWORD=password \
     mongo:latest
   ```

### Executando Testes

```bash
# Todos os testes
pytest

# Testes específicos
pytest tests/test_checkin_handlers.py

# Com coverage
pytest --cov=src tests/

# Testes assíncronos
pytest -v tests/test_async_handlers.py
```

### Desenvolvimento de Features

1. **Novo Handler**
   - Crie o handler em `src/bot/`
   - Registre em `src/main.py`
   - Adicione testes em `tests/`

2. **Nova Funcionalidade MongoDB**
   - Adicione métodos em `mongodb_client.py`
   - Implemente tratamento de erros
   - Crie testes unitários

3. **Integração IA**
   - Modifique `anthropic_client.py`
   - Ajuste prompts em `fitness_qa.py`
   - Teste com diferentes contextos

### Padrões de Código

- **Async/Await**: Use para operações MongoDB e API
- **Error Handling**: Try/catch em todas operações críticas
- **Logging**: Use logger estruturado
- **Type Hints**: Documente tipos quando possível
- **Docstrings**: Documente funções e classes

## 🔌 API e Integrações

### MongoDB Collections

- `user_checkins`: Check-ins dos usuários
- `checkin_anchors`: Âncoras de check-in ativas
- `blacklist`: Lista negra de mensagens
- `bot_admins`: Administradores do bot
- `recurring_messages`: Mensagens automáticas
- `monitored_chats`: Grupos monitorados
- `qa_interactions`: Interações com IA
- `qa_usage`: Uso diário da IA
- `correio_elegante`: Mensagens do correio elegante
- `pix_payments`: Pagamentos Pix para revelações

### Anthropic API

```python
# Exemplo de uso
from src.utils.anthropic_client import AnthropicClient

client = AnthropicClient(api_key="your_key")
response = await client.generate_response(
    prompt="Como melhorar resistência muscular?",
    context="Usuário iniciante, treina 3x/semana"
)
```

### Telegram Bot API

- **Polling**: Busca ativa por mensagens
- **Webhooks**: Não implementado (polling preferido)
- **Rate Limits**: Respeitados automaticamente
- **Error Recovery**: Sistema de retry implementado

## 🤝 Contribuição

### Como Contribuir

1. **Fork** o repositório
2. **Crie** uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. **Implemente** as mudanças com testes
4. **Commit** suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
5. **Push** para a branch (`git push origin feature/nova-funcionalidade`)
6. **Abra** um Pull Request

### Guidelines

- Mantenha o código bem documentado
- Adicione testes para novas funcionalidades
- Siga os padrões de código existentes
- Atualize a documentação quando necessário
- Teste localmente antes de submeter PR

### Reportando Issues

- Use templates de issue quando disponíveis
- Inclua logs relevantes
- Descreva passos para reproduzir
- Especifique ambiente (OS, Python version, etc.)

---

## 📝 Licença

Este projeto está sob licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 📞 Suporte

- **Issues**: [GitHub Issues](https://github.com/seu-usuario/bro-bot/issues)
- **Documentação**: [Wiki do projeto](https://github.com/seu-usuario/bro-bot/wiki)
- **Email**: seu-email@exemplo.com

---

*Desenvolvido com ❤️ para a comunidade GYM NATION* 