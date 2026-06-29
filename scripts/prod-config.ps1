$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$env:DOCKER_CONFIG = Join-Path $repoRoot ".docker"
docker compose --env-file .env.production.example -f docker-compose.yml -f docker-compose.prod.yml config
