$repoRoot = Split-Path -Parent $PSScriptRoot
$env:DOCKER_CONFIG = Join-Path $repoRoot ".docker"
$backupDir = Join-Path $repoRoot "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $backupDir "docintel-$stamp.sql"
cmd /c "docker compose exec -T postgres pg_dump -U docintel -d docintel > `"$backupFile`""
Write-Output "Wrote $backupFile"

