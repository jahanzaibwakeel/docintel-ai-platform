$repoRoot = Split-Path -Parent $PSScriptRoot
$env:DOCKER_CONFIG = Join-Path $repoRoot ".docker"
docker compose --profile test run --build --rm backend-tests
