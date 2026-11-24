import os, json

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# 1. Workspace YAML
with open("pnpm-workspace.yaml", "w", encoding="utf-8") as f:
    f.write("packages:\n  - 'apps/*'\n  - 'packages/*'\n")

# 2. Pacotes compartilhados do Monorepo
for pkg in ["ui", "schemas", "config", "db"]:
    write_json(f"packages/{pkg}/package.json", {
        "name": f"@manutcar/{pkg}",
        "version": "0.1.0",
        "private": True,
        "main": "./index.ts",
        "types": "./index.ts"
    })
    with open(f"packages/{pkg}/index.ts", "w", encoding="utf-8") as f:
        f.write(f'export const {pkg.upper()}_VERSION = "0.1.0";\n')

# 3. App Web (Next.js 14.2.35 sem vulnerabilidade)
write_json("apps/web/package.json", {
    "name": "@manutcar/web",
    "version": "0.1.0",
    "private": True,
    "scripts": {
        "dev": "next dev",
        "build": "next build",
        "start": "next start",
        "lint": "next lint",
        "typecheck": "tsc --noEmit"
    },
    "dependencies": {
        "@clerk/nextjs": "^5.7.0",
        "@manutcar/ui": "workspace:*",
        "@manutcar/schemas": "workspace:*",
        "next": "14.2.35",
        "react": "^18.3.1",
        "react-dom": "^18.3.1"
    },
    "devDependencies": {
        "@types/node": "^22.0.0",
        "@types/react": "^18.3.0",
        "@types/react-dom": "^18.3.0",
        "eslint": "^9.0.0",
        "eslint-config-next": "14.2.35",
        "typescript": "^5.6.0"
    }
})

print("WORKSPACE_CRIADO_COM_SUCESSO")
