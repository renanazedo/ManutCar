# ManutCar API

Backend FastAPI do projeto ManutCar.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.x (async)
- Pydantic v2
- uv (gerenciador de dependências)

## Estrutura

- `app/api/v1/endpoints/` — rotas REST por domínio (`fleet`, `operations`, `maintenance`, ...)
- `app/services/` — regras de negócio por domínio
- `app/core/` — configuração, segurança, dependências
- `tests/` — testes pytest assíncronos

## Como rodar os testes

```bash
cd apps/api
$env:DATABASE_URL="sqlite+aiosqlite:///:memory:"
uv run pytest -v
