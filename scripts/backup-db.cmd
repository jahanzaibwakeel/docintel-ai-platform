@echo off
setlocal
set "DOCKER_CONFIG=%~dp0..\.docker"
set "BACKUP_DIR=%~dp0..\backups"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set "TODAY=%%d%%b%%c"
for /f "tokens=1-3 delims=:." %%a in ("%time%") do set "NOW=%%a%%b%%c"
set "BACKUP_FILE=%BACKUP_DIR%\docintel-%TODAY%-%NOW%.sql"
docker compose exec -T postgres pg_dump -U docintel -d docintel > "%BACKUP_FILE%"
echo Wrote %BACKUP_FILE%

