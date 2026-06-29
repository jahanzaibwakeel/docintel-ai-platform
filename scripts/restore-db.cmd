@echo off
setlocal
if "%~1"=="" (
  echo Usage: scripts\restore-db.cmd backups\docintel.sql
  exit /b 1
)
set "DOCKER_CONFIG=%~dp0..\.docker"
docker compose exec -T postgres psql -U docintel -d docintel < "%~1"

