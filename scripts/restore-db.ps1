param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$env:DOCKER_CONFIG = Join-Path $repoRoot ".docker"
cmd /c "docker compose exec -T postgres psql -U docintel -d docintel < `"$BackupFile`""

