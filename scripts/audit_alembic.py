import os, sys
from alembic.config import Config
from alembic.script import ScriptDirectory

print("=" * 60)
print("AUDITORIA BLOCO 2C-1 - CONFIGURAÇÃO ALEMBIC ASSÍNCRONO")
print("=" * 60)

errors = []

# 1. Verificar existência dos 4 arquivos obrigatórios
required_files = [
    "packages/db/alembic.ini",
    "packages/db/alembic/script.py.mako",
    "packages/db/alembic/env.py",
    "packages/db/alembic/versions/.gitkeep",
]

for f in required_files:
    if os.path.exists(f):
        print(f"  [OK] {f}")
    else:
        print(f"  [FALHA] Ausente: {f}")
        errors.append(f"Arquivo ausente: {f}")

# 2. Validar leitura do alembic.ini e diretório de scripts
if os.path.exists("packages/db/alembic.ini"):
    try:
        cfg = Config("packages/db/alembic.ini")
        cfg.set_main_option("script_location", os.path.abspath("packages/db/alembic"))
        script_dir = ScriptDirectory.from_config(cfg)
        print(f"  [OK] ScriptDirectory carregado: {script_dir.dir}")
    except Exception as e:
        errors.append(f"Erro ao carregar alembic.ini / ScriptDirectory: {e}")

# 3. Validar sintaxe e imports do env.py
if os.path.exists("packages/db/alembic/env.py"):
    try:
        with open("packages/db/alembic/env.py", "r", encoding="utf-8") as f:
            env_code = f.read()
        compile(env_code, "packages/db/alembic/env.py", "exec")
        for expected in ["Base", "target_metadata", "async_engine_from_config"]:
            if expected not in env_code:
                errors.append(f"env.py não contém referência obrigatória: {expected}")
        if not errors:
            print("  [OK] env.py compilado e estrutura assíncrona verificada.")
    except Exception as e:
        errors.append(f"Erro de sintaxe em env.py: {e}")

print("\n" + "=" * 60)
if errors:
    for err in errors:
        print(f"[FALHA] {err}")
    print("\nAUDITORIA_ALEMBIC_REPROVADA")
    sys.exit(1)
else:
    print("Configuração do Alembic validada com sucesso!")
    print("\nAUDITORIA_ALEMBIC_APROVADA")
    sys.exit(0)
