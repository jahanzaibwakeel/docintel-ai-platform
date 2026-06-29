@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0prod-config.ps1" %*
