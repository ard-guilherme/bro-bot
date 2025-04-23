# Technical Context

## Technologies Used
- **Programming Language**: Python 3.x
- **Telegram Integration**: python-telegram-bot
- **Database**: 
    - SQLite (Principal, para agendamentos, etc. - a confirmar)
    - MongoDB (Para Blacklist)
- **Testing**: pytest
- **Containerization**: Docker
- **Version Control**: Git

## Development Setup
1. Python virtual environment
2. Required packages from requirements.txt
3. Environment variables from .env
4. Docker for containerization
5. Git for version control

## Dependencies
```python
python-telegram-bot
pytest
python-dotenv
SQLite3 # Se usado para outras partes
pmongo # Para MongoDB (blacklist)
```
(Nota: Verificar se pymongo está no requirements.txt)

## Technical Constraints
1. Telegram API limitations
2. Database performance considerations (SQLite e MongoDB)
3. Message scheduling accuracy
4. Error handling requirements
5. Testing coverage requirements

## Development Environment
- Python 3.x
- Virtual environment
- Docker
- Git
- IDE/Editor of choice

## Deployment Requirements
1. Environment variables configuration (incluindo MongoDB connection string)
2. Database setup (SQLite e MongoDB)
3. Bot token configuration
4. Docker container setup
5. Logging configuration

## Testing Requirements
1. Unit tests
2. Integration tests
3. End-to-end tests
4. Performance tests
5. Error scenario tests

## Security Considerations
1. Bot token security
2. Database security (SQLite e MongoDB)
3. Environment variable protection
4. Input validation
5. Error handling security 