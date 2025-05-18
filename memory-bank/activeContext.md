# Active Context

## Current Focus
- Readequação das faixas de pontuação do sistema de check-in para uma escala máxima de 34 pontos.
- Escrever e executar testes automatizados para o novo comando `/ban_blacklist`.
- Documentar a adição do comando `/ban_blacklist` (concluído).
- Planejar próximos passos (corrigir testes existentes ou nova feature).

## Recent Changes
- **Nova Melhoria:** Readequação das faixas de pontuação para as mensagens de check-in ajustando para escala máxima de 34 pontos (considerando reset periódico a cada 30 dias). Foram ajustadas as faixas de pontuação de: [1-3, 4-7, 8-15, 16-25, 26-40, 41-60, 61+] para [1-3, 4-7, 8-12, 13-18, 19-25, 26-30, 31+].
- **Nova Feature:** Adicionado o comando `/ban_blacklist <group_name>` para administradores. Este comando bane usuários da blacklist de um grupo específico e remove as entradas correspondentes (apenas dos usuários banidos com sucesso). (Implementado em `src/utils/mongodb_client.py` e `src/bot/blacklist_handlers.py`, registrado em `src/main.py`).
- **Correção de Bug/Melhoria (Blacklist):** Implementada paginação na listagem da blacklist (`/blacklist` command) para evitar o erro "Message is too long". A lista agora é dividida em mensagens de até 4000 caracteres, enviadas sequencialmente. O ID do item foi adicionado à listagem para facilitar a remoção via `/rmblacklist`. Os botões inline de remoção foram removidos da listagem. (Implementado em `src/bot/blacklist_handlers.py` usando MongoDB).
- **Correção DB:** Confirmado o uso de MongoDB para a funcionalidade de blacklist nos documentos do Memory Bank.
- **Correção de Bug (Mensagens Editadas):** Corrigido bug onde editar uma mensagem de check-in causava erro.
- **Melhoria Mensagens Check-in:** Substituída a lista de respostas estáticas para check-in padrão.

## Next Steps
1.  **Testar Comando `/ban_blacklist`:** Escrever e executar testes unitários/integração para `ban_blacklist_command` e as novas funções do MongoDB client.
2.  **Testar Paginação:** Realizar testes unitários e manuais para a funcionalidade de paginação da blacklist (se ainda não foram feitos ou passaram).
3.  **Decidir Prioridade:** Avaliar se o próximo foco será corrigir os testes automatizados restantes em `tests/test_checkin_handlers.py` ou iniciar outra tarefa/feature.
4.  Se focar nos testes, investigar as falhas de `IndexError` e `KeyError`.
5.  Se focar em nova tarefa, definir e planejar.

## Active Decisions
1. Using SQLite for main database (TBC)
2. Using MongoDB for Blacklist feature
3. Implementing pytest for testing
4. Following modular architecture
5. Using Docker for containerization
6. Implementing comprehensive logging

## Current Considerations
- Cobertura de testes para as novas faixas de pontuação de check-in.
- Cobertura de testes para `/ban_blacklist`.
- Clarificar uso do SQLite para outras features.
- Estratégia de testes para a paginação da blacklist (`/blacklist`).
- Refinamento da interface de paginação (se necessário após testes).
- Error handling approach
- Logging system setup
- Deployment configuration (including MongoDB)

## Pending Tasks
1. Testes para as novas faixas de pontuação de check-in.
2. Testes para `/ban_blacklist`.
3. Testes para paginação do `/blacklist`.
4. Correção dos testes em `test_checkin_handlers.py`.
5. Database setup/confirmation (SQLite for core?)
6. Testing framework configuration.
7. Core functionality implementation (outros comandos).
8. Documentation completion
9. Deployment pipeline setup

## Active Issues
- **Testes Automatizados Falhando:** 4 testes em `test_checkin_handlers.py` estão falhando.
- **Falta de Testes:** Funcionalidade de paginação da blacklist (`/blacklist`) e o novo comando `/ban_blacklist` ainda não testados.
- **DB Pendente:** Confirmação do uso de SQLite para funcionalidades core.

## Recent Updates
- Readequação das faixas de pontuação para as mensagens de check-in (escala máxima de 34 pontos).
- Implementado comando `/ban_blacklist`.
- Implementada paginação para o comando `/blacklist` (MongoDB).
- Corrigido bug de processamento de mensagens de check-in editadas.
- Melhoria nas mensagens estáticas de check-in padrão.
- Atualização dos testes relacionados.
- Memory Bank initialization
- Project documentation setup
- Technical context establishment
- System patterns documentation 