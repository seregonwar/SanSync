@echo off
powershell.exe -Command "Start-Process python -ArgumentList 'test_injection.py' -Verb RunAs -WorkingDirectory '%~dp0'"