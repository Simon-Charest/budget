# Usage: .\bin\run.ps1
.\.venv\Scripts\activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:BUDGET_HOST = "127.0.0.1"
$env:BUDGET_PORT = "80"
$env:BUDGET_PROXY_HEADERS = "false"
python .
