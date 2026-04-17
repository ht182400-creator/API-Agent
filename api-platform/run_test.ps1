$ErrorActionPreference = 'Continue'
Set-Location "d:/Work_Area/AI/API-Agent/api-platform"
python -m pytest tests/ -v --tb=short 2>&1 | Tee-Object -FilePath "test_output.txt" -Append
