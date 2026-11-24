<#
.SYNOPSIS
    Script de verificação da integridade do Bloco 1 - ManutCar.
    Verifica ferramentas, estrutura de diretórios e arquivos obrigatórios.

.NOTES
    Execute na raiz do repositório:
    powershell -ExecutionPolicy Bypass -File scripts/verify_block1.ps1
#>

$ErrorActionPreference = "Stop"
$errors = 0

function Check-Command {
    param([string]$Name, [string]$Command, [string]$VersionFlag = "--version")
    Write-Host "Verificando comando: $Name ... " -NoNewline
    try {
        $result = & $Command $VersionFlag 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "OK" -ForegroundColor Green
            return $true
        } else {
            Write-Host "FALHOU (exit code $LASTEXITCODE)" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "NÃO ENCONTRADO" -ForegroundColor Red
        return $false
    }
}

function Check-Path {
    param([string]$Path, [string]$Type = "File")
    Write-Host "Verificando $Type: $Path ... " -NoNewline
    if ($Type -eq "Directory") {
        if (Test-Path -Path $Path -PathType Container) {
            Write-Host "OK" -ForegroundColor Green
            return $true
        } else {
            Write-Host "AUSENTE" -ForegroundColor Red
            return $false
        }
    } else {
        if (Test-Path -Path $Path -PathType Leaf) {
            Write-Host "OK" -ForegroundColor Green
            return $true
        } else {
            Write-Host "AUSENTE" -ForegroundColor Red
            return $false
        }
    }
}

Write-Host "===== VERIFICAÇÃO DE FERRAMENTAS ====="
$toolsOk = $true
$toolsOk = Check-Command "pnpm" "pnpm" -and $toolsOk
$toolsOk = Check-Command "uv" "uv" -and $toolsOk
# Fallback python -m pip se uv não estiver no PATH (embora uv seja o padrão do projeto)
if (-not (Check-Command "python" "python")) {
    $toolsOk = $false
}
if (-not $toolsOk) { $errors++ }

Write-Host "`n===== VERIFICAÇÃO DE DIRETÓRIOS OBRIGATÓRIOS ====="
$dirs = @(
    "apps/api",
    "apps/web",
    "packages/db",
    "packages/schemas",
    "packages/ui",
    "packages/config",
    "docs/adr"
)
foreach ($dir in $dirs) {
    if (-not (Check-Path $dir "Directory")) { $errors++ }
}

Write-Host "`n===== VERIFICAÇÃO DE ARQUIVOS OBRIGATÓRIOS (BLOCO 1) ====="
$files = @(
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
    ".github/workflows/ci.yml"
)
foreach ($file in $files) {
    if (-not (Check-Path $file "File")) { $errors++ }
}

Write-Host "`n===== RESULTADO FINAL ====="
if ($errors -gt 0) {
    Write-Host "FALHA_NA_AUDITORIA: $errors pendência(s) encontrada(s)." -ForegroundColor Red
    exit 1
} else {
    Write-Host "BLOCO_1_VALIDADO_COM_SUCESSO" -ForegroundColor Green
    exit 0
}
