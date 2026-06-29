@echo off
set "DOCKER_CONFIG=%~dp0..\.docker"
docker compose --profile test run --build --rm backend-tests
