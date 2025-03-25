# GYM NATION Bot - Dev Guidelines

## Build & Test Commands
- Run app: `python -m src.main`
- Run all tests: `pytest`
- Run single test: `pytest tests/test_file.py::TestClass::test_method`
- Run by pattern: `pytest -k "pattern"`
- Deploy with Docker: `docker-compose up -d`

## Code Style Guidelines
- Use **snake_case** for functions and variables
- Use **CamelCase** for classes
- Use **UPPER_CASE** for constants
- Type annotations required for all function parameters and return values
- Organize imports: standard library → third-party → local modules
- Use Google-style docstrings with Args/Returns sections
- Document all public functions, classes, and methods
- Use structured try/except blocks with detailed error logging
- Keep file size manageable (max ~300 lines)
- Maintain clear separation between modules and responsibilities
- Use async/await consistently for asynchronous code
- Maintain handler registration in src/main.py
- Follow PEP 8 style guidelines