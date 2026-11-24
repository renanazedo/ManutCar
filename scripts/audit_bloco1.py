#!/usr/bin/env python3
"""
Script de auditoria para o Bloco 1 (Estrutura do Monorepo) do ManutCar.
Verifica arquivos obrigatórios, ferramentas do ambiente e estado do Git.
"""

import os
import subprocess
import sys
import json
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Any


def run_command(cmd: List[str]) -> Tuple[int, str, str]:
    """Executa um comando e retorna (returncode, stdout, stderr)."""
    try:
        # No Windows, shutil.which resolve .cmd/.exe automaticamente
        resolved_cmd = [shutil.which(c) or c for c in cmd]
        if not resolved_cmd[0]:
            return -1, "", f"{cmd[0]} not found in PATH"
        
        result = subprocess.run(
            resolved_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return -1, "", "command not found"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def check_mandatory_files(base_path: Path) -> Dict[str, bool]:
    """Verifica se todos os arquivos obrigatórios existem."""
    mandatory_files = [
        "pnpm-workspace.yaml",
        "package.json",
        "turbo.json",
        ".gitignore",
        ".env.example",
        "lefthook.yml",
        "apps/api/pyproject.toml",
        "apps/api/app/main.py",
        "apps/api/Dockerfile",
        "apps/web/package.json",
        "apps/web/tsconfig.json",
        "render.yaml",
        ".github/workflows/ci.yml",
    ]

    results = {}
    for file_rel in mandatory_files:
        file_path = base_path / file_rel
        exists = file_path.exists()
        results[file_rel] = exists
        status = "[OK]" if exists else "[FALHA]"
        print(f"  {status} {file_rel}")

    return results


def check_environment_tools() -> Dict[str, str]:
    """Verifica se as ferramentas necessárias estão disponíveis."""
    tools = {
        "python": ["python", "--version"],
        "node": ["node", "--version"],
        "pnpm": ["pnpm", "--version"],
        "uv": ["uv", "--version"],
    }

    results = {}
    for name, cmd in tools.items():
        returncode, stdout, stderr = run_command(cmd)
        if returncode == 0:
            version = stdout.split('\n')[0] if stdout else "unknown"
            results[name] = version
            print(f"  [OK] {name}: {version}")
        else:
            results[name] = "MISSING"
            print(f"  [FALHA] {name}: MISSING")

    return results


def check_git_status(base_path: Path) -> List[str]:
    """Verifica o status do Git (arquivos não rastreados ou modificados)."""
    returncode, stdout, stderr = run_command(["git", "status", "--porcelain"])
    
    if returncode != 0:
        print(f"  [AVISO] Não foi possível executar 'git status': {stderr}")
        return []
    
    if not stdout:
        print("  [OK] Working tree clean")
        return []
    
    lines = stdout.strip().split('\n')
    print(f"  [INFO] {len(lines)} arquivo(s) com alterações:")
    for line in lines:
        print(f"    {line}")
    
    return lines


def main() -> int:
    """Função principal de auditoria."""
    base_path = Path(__file__).parent.parent
    os.chdir(base_path)
    
    print("=" * 60)
    print("AUDITORIA BLOCO 1 - ESTRUTURA DO MONOREPO MANUTCAR")
    print("=" * 60)
    print(f"Diretório base: {base_path}")
    print()

    # 1. Verificar arquivos obrigatórios
    print("1. VERIFICAÇÃO DE ARQUIVOS OBRIGATÓRIOS:")
    file_results = check_mandatory_files(base_path)
    print()

    # 2. Verificar ferramentas do ambiente
    print("2. VERIFICAÇÃO DE FERRAMENTAS DO AMBIENTE:")
    tool_results = check_environment_tools()
    print()

    # 3. Verificar estado do Git
    print("3. ESTADO DO GIT:")
    git_changes = check_git_status(base_path)
    print()

    # 4. Relatório final
    print("=" * 60)
    print("RELATÓRIO FINAL")
    print("=" * 60)

    # Verificar falhas críticas
    missing_files = [f for f, exists in file_results.items() if not exists]
    missing_tools = [t for t, v in tool_results.items() if v == "MISSING"]
    
    has_critical_failures = len(missing_files) > 0 or len(missing_tools) > 0
    
    if missing_files:
        print(f"Arquivos obrigatórios ausentes ({len(missing_files)}):")
        for f in missing_files:
            print(f"  - {f}")
    
    if missing_tools:
        print(f"Ferramentas críticas ausentes ({len(missing_tools)}):")
        for t in missing_tools:
            print(f"  - {t}")
    
    if not has_critical_failures:
        print("Todos os arquivos obrigatórios estão presentes.")
        print("Todas as ferramentas críticas estão disponíveis.")
        print()
        print("AUDITORIA_APROVADA")
        return 0
    else:
        print()
        print("AUDITORIA_REPROVADA")
        return 1


if __name__ == "__main__":
    sys.exit(main())
