# ManutCar API

Backend FastAPI do projeto ManutCar.

## Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x assíncrono
- Pydantic v2
- uv para dependências e ambiente local

## Estrutura

- `app/api/v1/endpoints/`: rotas REST por domínio
- `app/services/`: serviços da aplicação
- `app/core/`: configuração, segurança e dependências
- `tests/`: testes pytest assíncronos

## Instalação e verificações

Na raiz do repositório:

```bash
cd apps/api
uv sync --locked
DATABASE_URL='sqlite+aiosqlite:///:memory:' uv run pytest
```

O SQLite em memória é suficiente para a suíte de testes e não exige um serviço
externo. Para iniciar a API, configure `DATABASE_URL` para um banco acessível
e execute:

```bash
uv run uvicorn app.main:app --reload
```

`GET /api/v1/health` verifica a conexão com o banco e retorna `503` quando ela
está indisponível. A documentação OpenAPI fica disponível em `/docs` fora do
ambiente de produção.

Ruff e MyPy estão configurados para o desenvolvimento local. As checagens
completas ainda encontram pendências existentes e não são gates do CI.
