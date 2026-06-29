@echo off
set "DOCKER_CONFIG=%~dp0..\.docker"
docker compose %*

