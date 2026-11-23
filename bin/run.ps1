# Usage: .\bin\run.ps1
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$env:BUDGET_HOST = "127.0.0.1"
$env:BUDGET_PORT = "80"
$env:BUDGET_PROXY_HEADERS = "false"

.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

$listener = Get-NetTCPConnection -LocalPort 80 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)"
    if ($process.CommandLine -notmatch '(?i)\s\.\s*$') {
        throw "Port 80 is used by another process (PID $($listener.OwningProcess))."
    }
    Stop-Process -Id $listener.OwningProcess
}

python .
