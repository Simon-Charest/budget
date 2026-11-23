# Usage: .\bin\deploy.ps1
# Commits and pushes every change, deploys it on the server, then replaces the local database with
# the production one. Asks no questions: the server's sudo password comes from BUDGET_DEPLOY_PASSWORD
# in .env and goes through SSH's input, never on a command line.
[CmdletBinding()]
param(
    [string]$CommitMessage = "Deploy budget app $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$EnvFile = Join-Path $ProjectRoot '.env'
$Git = (Get-Command git -ErrorAction Stop).Source
$Ssh = (Get-Command ssh -ErrorAction Stop).Source
$Scp = (Get-Command scp -ErrorAction Stop).Source
$TempEnv = $null
$RemoteEnvStage = $null
$RemoteDatabaseStage = $null
$LocalInitialBackup = $null
$LocalRemoteBackup = $null
$LocalOldBackup = $null
$RemoteTransfer = $null

function Invoke-Quietly {
    # Windows PowerShell 5.1 turns redirected native stderr into a terminating error under
    # $ErrorActionPreference = 'Stop'; callers inspect $LASTEXITCODE instead.
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $ErrorActionPreference = 'Continue'
    & $Executable @Arguments *> $null
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Operation,
        [switch]$Quiet
    )

    if ($Quiet) {
        Invoke-Quietly -Executable $Executable -Arguments $Arguments
    } else {
        & $Executable @Arguments
    }
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE."
    }
}

function Invoke-RemoteScript {
    # Sends the sudo password, then the script, to bash on the server through SSH's input. In the script,
    # `s` runs a command with sudo and that password (and fails instead of prompting when none is set).
    param(
        [Parameter(Mandatory = $true)][string]$Script,
        [Parameter(Mandatory = $true)][string]$Operation
    )

    $payload = @(
        # Left empty: should a byte order mark still be sent, it lands here and the password is read correctly
        '',
        'IFS= read -r p || true',
        $SudoPassword,
        'p=${p%$''\r''}',
        's() { if [ -n "$p" ]; then printf ''%s\n'' "$p" | sudo -S -p '''' "$@"; else sudo -n "$@"; fi; }',
        # Parsed whole before it runs, with its own input closed: no command can read the rest of the script
        '{',
        $Script,
        '} < /dev/null',
        'exit $?',
        ''
    ) -join "`n"

    # Written as raw bytes: piping text to a native command in Windows PowerShell 5.1 adds a byte order
    # mark and CRLF line endings, which bash would read as part of the commands
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new($Ssh)
    $startInfo.Arguments = "-o BatchMode=yes $Remote `"bash -s`""
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardInput = $true
    # .NET Framework opens the child's input with the console's input encoding, and writes its byte order mark
    $previousInputEncoding = [Console]::InputEncoding
    try {
        [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
    } catch {
        $previousInputEncoding = $null
    }
    try {
        $process = [System.Diagnostics.Process]::Start($startInfo)
    } finally {
        if ($previousInputEncoding) {
            [Console]::InputEncoding = $previousInputEncoding
        }
    }
    try {
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($payload)
        $process.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
        $process.StandardInput.Close()
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) {
            throw "$Operation failed with exit code $($process.ExitCode)."
        }
    } finally {
        $process.Dispose()
    }
}

function Read-EnvSettings {
    param([Parameter(Mandatory = $true)][string]$Path)

    $settings = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') {
            $name = $matches[1]
            $value = $matches[2].Trim()
            if ($value.Length -ge 2 -and
                (($value.StartsWith('"') -and $value.EndsWith('"')) -or
                ($value.StartsWith("'") -and $value.EndsWith("'")))) {
                $value = $value.Substring(1, $value.Length - 2)
            } elseif ($value -match '^([^#]*?)\s+#.*$') {
                $value = $matches[1].TrimEnd()
            }
            $settings[$name] = $value
        }
    }
    return $settings
}

function Resolve-ConfiguredPath {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ([System.IO.Path]::IsPathRooted($Value)) {
        return [System.IO.Path]::GetFullPath($Value)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Value))
}

function Assert-NoLocalServer {
    param([Parameter(Mandatory = $true)][int]$Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $pending = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        if ($pending.AsyncWaitHandle.WaitOne(500)) {
            try {
                $client.EndConnect($pending)
            } catch [System.Net.Sockets.SocketException] {
                return
            }
        } else {
            return
        }
    } finally {
        $client.Dispose()
    }

    $request = [System.Net.HttpWebRequest]::Create("http://127.0.0.1:$Port/api/me")
    $request.Method = 'GET'
    $request.Timeout = 1500
    try {
        $response = $request.GetResponse()
        $server = $response.Headers['Server']
        $response.Close()
        if ($server -match 'uvicorn') {
            throw "The local app is running on port $Port. Stop it before deployment so the local database can be safely synchronized."
        }
    } catch [System.Net.WebException] {
        if ($_.Exception.Response) {
            $server = $_.Exception.Response.Headers['Server']
            $_.Exception.Response.Close()
            if ($server -match 'uvicorn') {
                throw "The local app is running on port $Port. Stop it before deployment so the local database can be safely synchronized."
            }
        }
    }
}

function New-ProductionEnvFile {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$DestinationPath,
        [Parameter(Mandatory = $true)][string]$RemoteRoot
    )

    $productionValues = [ordered]@{
        BUDGET_DATABASE = "$RemoteRoot/data/budget.sqlite3"
        BUDGET_HOST = '127.0.0.1'
        BUDGET_PORT = '8001'
        BUDGET_COOKIE_SECURE = 'true'
        BUDGET_PROXY_HEADERS = 'true'
        BUDGET_FORWARDED_ALLOW_IPS = '127.0.0.1'
    }
    $overrides = @{}
    foreach ($name in $productionValues.Keys) {
        $overrides[$name] = $true
    }
    $content = [System.Collections.Generic.List[string]]::new()
    foreach ($line in Get-Content -LiteralPath $SourcePath) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') {
            # Deployment settings, such as the sudo password, never go to the server
            if ($overrides.ContainsKey($matches[1]) -or $matches[1].StartsWith('BUDGET_DEPLOY_')) {
                continue
            }
        }
        $content.Add($line)
    }
    foreach ($entry in $productionValues.GetEnumerator()) {
        $content.Add("$($entry.Key)=$($entry.Value)")
    }
    [System.IO.File]::WriteAllLines(
        $DestinationPath,
        [string[]]$content,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Get-UtcStamp {
    return [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
}

try {
    if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
        throw "Missing $EnvFile. Copy .env.example to .env and configure it first."
    }
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "Missing project virtual environment. Create .venv and install requirements.txt first."
    }

    $settings = Read-EnvSettings -Path $EnvFile
    $Remote = [string]$settings['BUDGET_DEPLOY_REMOTE']
    $remoteRootSetting = [string]$settings['BUDGET_DEPLOY_REMOTE_ROOT']
    $Branch = [string]$settings['BUDGET_DEPLOY_BRANCH']
    if ($Remote -notmatch '^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+$') {
        throw 'Set BUDGET_DEPLOY_REMOTE in .env to a valid SSH user@host.'
    }
    if ($remoteRootSetting -notmatch '^(~/[A-Za-z0-9._/-]+|/[A-Za-z0-9._/-]+)$') {
        throw 'Set BUDGET_DEPLOY_REMOTE_ROOT in .env to a ~/path or absolute Linux path.'
    }
    if ($Branch -notmatch '^[A-Za-z0-9._/-]+$') {
        throw 'Set BUDGET_DEPLOY_BRANCH in .env to a valid branch name.'
    }

    Write-Output "Checking SSH access to $Remote..."
    Invoke-Checked -Executable $Ssh -Arguments @('-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', $Remote, 'true') -Operation 'SSH connection'
    $RemoteHome = (& $Ssh -n -o BatchMode=yes $Remote 'printf %s "$HOME"').Trim()
    if ($LASTEXITCODE -ne 0 -or $RemoteHome -notmatch '^/[A-Za-z0-9._/-]+$') {
        throw 'Could not safely resolve the remote home directory.'
    }
    if ($remoteRootSetting.StartsWith('~/')) {
        $RemoteRoot = $RemoteHome.TrimEnd('/') + $remoteRootSetting.Substring(1)
    } else {
        $RemoteRoot = $remoteRootSetting
    }
    $RemoteRoot = $RemoteRoot.TrimEnd('/')
    $SudoPassword = [string]$settings['BUDGET_DEPLOY_PASSWORD']

    $password = [string]$settings['BUDGET_DATABASE_PASSWORD']
    if ($password.Length -lt 16) {
        throw 'BUDGET_DATABASE_PASSWORD in .env must contain at least 16 characters before deployment.'
    }
    $port = 8000
    if ($settings.ContainsKey('BUDGET_PORT')) {
        $port = [int]$settings['BUDGET_PORT']
    }
    Assert-NoLocalServer -Port $port

    $databaseValue = if ($settings.ContainsKey('BUDGET_DATABASE')) {
        [string]$settings['BUDGET_DATABASE']
    } else {
        'data/budget.sqlite3'
    }
    $localDatabase = Resolve-ConfiguredPath -Value $databaseValue
    if (-not (Test-Path -LiteralPath $localDatabase -PathType Leaf)) {
        throw 'The configured local database is missing; import the Budget sheet before deploying.'
    }
    $stamp = Get-UtcStamp
    $localBackupDirectory = Join-Path $ProjectRoot 'data\backups'
    $LocalInitialBackup = Join-Path $localBackupDirectory "budget-initial-$stamp.sqlite3"
    $LocalRemoteBackup = Join-Path $localBackupDirectory "budget-production-$stamp.sqlite3"

    $origin = (& $Git -C $ProjectRoot remote get-url origin).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($origin)) {
        throw 'A Git remote named origin is required.'
    }
    $currentBranch = (& $Git -C $ProjectRoot branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or $currentBranch -ne $Branch) {
        throw "Deployment is configured for branch '$Branch'; current branch is '$currentBranch'."
    }
    if ((& $Git -C $ProjectRoot check-ignore '.env') -ne '.env') {
        throw '.env must be ignored by Git before deployment.'
    }
    & $Git -C $ProjectRoot diff --cached --quiet
    if ($LASTEXITCODE -eq 1) {
        throw 'There are already staged Git changes. Commit or unstage them before deploying.'
    } elseif ($LASTEXITCODE -ne 0) {
        throw 'Could not inspect staged Git changes.'
    }
    Invoke-Quietly -Executable $Git -Arguments @('-C', $ProjectRoot, 'ls-files', '--error-unmatch', '.env')
    if ($LASTEXITCODE -eq 0) {
        throw '.env is already tracked by Git. Remove it from tracking before deployment; do not publish secrets.'
    }
    Invoke-Quietly -Executable $Git -Arguments @('-C', $ProjectRoot, 'ls-files', '--error-unmatch', 'data/budget.sqlite3')
    if ($LASTEXITCODE -eq 0) {
        throw 'The local database is tracked by Git. Remove it from tracking before deployment.'
    }

    $remoteRepoCheck = "test -d '$RemoteRoot/.git' && test -x '$RemoteRoot/.venv/bin/python'"
    Invoke-Checked -Executable $Ssh -Arguments @('-n', $Remote, $remoteRepoCheck) -Operation 'Remote deployment directory check'

    # Before anything is committed, so a missing or wrong password changes nothing
    Write-Output 'Checking sudo on the server...'
    try {
        Invoke-RemoteScript -Script 's true' -Operation 'Remote sudo check'
    } catch {
        throw 'sudo failed on the server: set BUDGET_DEPLOY_PASSWORD in .env to the sudo password of the deploy account. Nothing was changed.'
    }

    New-Item -ItemType Directory -Force -Path $localBackupDirectory | Out-Null
    $remoteEnvPath = Join-Path ([System.IO.Path]::GetTempPath()) "budget-production-$([guid]::NewGuid().ToString('N')).env"
    $TempEnv = $remoteEnvPath
    $RemoteEnvStage = "$RemoteRoot/.budget-deploy-$stamp.env"
    New-ProductionEnvFile -SourcePath $EnvFile -DestinationPath $TempEnv -RemoteRoot $RemoteRoot
    Write-Output 'Verifying/encrypting the local database before deployment...'
    Invoke-Checked -Executable $Python -Arguments @('.', 'verify-database') -Operation 'Local database verification'
    Invoke-Checked -Executable $Python -Arguments @('.', 'backup-database', $LocalInitialBackup) -Operation 'Local encrypted database backup'

    Write-Output 'Staging and committing application files (ignored .env/database files are excluded)...'
    Invoke-Checked -Executable $Git -Arguments @('-C', $ProjectRoot, 'add', '--all') -Operation 'Git staging'
    & $Git -C $ProjectRoot diff --cached --quiet
    if ($LASTEXITCODE -eq 1) {
        Invoke-Checked -Executable $Git -Arguments @('-C', $ProjectRoot, 'commit', '-m', $CommitMessage) -Operation 'Git commit'
    } elseif ($LASTEXITCODE -ne 0) {
        throw 'Could not inspect staged changes.'
    } else {
        Write-Output 'No new source changes to commit.'
    }
    Invoke-Checked -Executable $Git -Arguments @('-C', $ProjectRoot, 'push', 'origin', $Branch) -Operation 'GitHub push'

    Write-Output 'Installing the production .env with HTTPS and server path overrides...'
    Invoke-Checked -Executable $Scp -Arguments @('-o', 'BatchMode=yes', $TempEnv, "${Remote}:$RemoteEnvStage") -Operation 'Upload production .env'
    $installEnv = "chmod 600 '$RemoteEnvStage' && install -m 600 '$RemoteEnvStage' '$RemoteRoot/.env' && rm -f '$RemoteEnvStage' && mkdir -m 700 -p '$RemoteRoot/data/backups'"
    Invoke-Checked -Executable $Ssh -Arguments @('-n', $Remote, $installEnv) -Operation 'Install production .env'

    $remoteDatabase = "$RemoteRoot/data/budget.sqlite3"
    $remoteHasDatabase = "test -f '$remoteDatabase'"
    Invoke-Quietly -Executable $Ssh -Arguments @('-n', $Remote, $remoteHasDatabase)
    if ($LASTEXITCODE -ne 0) {
        Write-Output 'Initializing the server database from the encrypted local database snapshot...'
        $RemoteDatabaseStage = "$RemoteRoot/.budget-initial-$stamp.sqlite3"
        Invoke-Checked -Executable $Scp -Arguments @('-o', 'BatchMode=yes', $LocalInitialBackup, "${Remote}:$RemoteDatabaseStage") -Operation 'Upload initial encrypted database'
        $installDatabase = "install -m 600 '$RemoteDatabaseStage' '$remoteDatabase' && rm -f '$RemoteDatabaseStage'"
        Invoke-Checked -Executable $Ssh -Arguments @('-n', $Remote, $installDatabase) -Operation 'Install initial database'
    }

    Write-Output 'Pulling the pushed commit and restarting the production service...'
    $remoteBackup = "$RemoteRoot/data/backups/budget-production-$stamp.sqlite3"
    $remoteTransfer = "/tmp/budget-production-$stamp.sqlite3"
    $deployCommand = @(
        "cd '$RemoteRoot'",
        "git pull --ff-only origin '$Branch'",
        '.venv/bin/python -m pip install -r requirements.txt',
        "s install -o root -g root -m 644 'deploy/budget.service' '/etc/systemd/system/budget.service'",
        's systemctl daemon-reload',
        's systemctl enable --quiet budget',
        's systemctl restart budget',
        # Uvicorn answers only after startup, which applies the database migrations, so the backup below includes them
        '{ up=0; for i in $(seq 1 30); do if curl -s -o /dev/null --max-time 2 http://127.0.0.1:8001/api/me; then up=1; break; fi; sleep 1; done; [ $up = 1 ] || { echo The budget service did not answer on 127.0.0.1:8001; s journalctl -u budget -n 30 --no-pager; false; }; }',
        'systemctl is-active --quiet budget',
        ".venv/bin/python . backup-database '$remoteBackup'",
        ".venv/bin/python . verify-database '$remoteBackup'",
        "chmod 600 '$remoteBackup'",
        "install -m 600 '$remoteBackup' '$remoteTransfer'"
    ) -join ' && '
    Invoke-RemoteScript -Script $deployCommand -Operation 'Production deployment and encrypted database backup'

    Write-Output 'Downloading the encrypted production database...'
    Invoke-Checked -Executable $Scp -Arguments @('-o', 'BatchMode=yes', "${Remote}:$remoteTransfer", $LocalRemoteBackup) -Operation 'Download production database backup'
    Invoke-Checked -Executable $Ssh -Arguments @('-n', $Remote, "rm -f '$remoteTransfer'") -Operation 'Remove temporary remote transfer copy'
    Invoke-Checked -Executable $Python -Arguments @('.', 'verify-database', $LocalRemoteBackup) -Operation 'Downloaded database verification'

    if (Test-Path -LiteralPath $localDatabase -PathType Leaf) {
        $LocalOldBackup = Join-Path $localBackupDirectory "budget-before-production-sync-$stamp.sqlite3"
        Invoke-Checked -Executable $Python -Arguments @('.', 'backup-database', $LocalOldBackup) -Operation 'Local pre-sync database backup'
    }
    $incomingDatabase = "$localDatabase.production-sync"
    Copy-Item -LiteralPath $LocalRemoteBackup -Destination $incomingDatabase
    try {
        foreach ($suffix in @('-wal', '-shm')) {
            $sidecar = "$localDatabase$suffix"
            if (Test-Path -LiteralPath $sidecar) {
                Remove-Item -LiteralPath $sidecar -Force
            }
        }
        Move-Item -LiteralPath $incomingDatabase -Destination $localDatabase -Force
    } finally {
        if (Test-Path -LiteralPath $incomingDatabase) {
            Remove-Item -LiteralPath $incomingDatabase -Force
        }
    }

    Write-Output "Deployment complete. Local development database synchronized with production."
    Write-Output "Encrypted production backup: $LocalRemoteBackup"
    if ($LocalOldBackup) {
        Write-Output "Encrypted pre-sync local backup: $LocalOldBackup"
    }
    Write-Output 'Restart the local app to use the synchronized database.'
} finally {
    if ($TempEnv -and (Test-Path -LiteralPath $TempEnv)) {
        Remove-Item -LiteralPath $TempEnv -Force
    }
    if ($RemoteTransfer) {
        Invoke-Quietly -Executable $Ssh -Arguments @('-n', '-o', 'BatchMode=yes', $Remote, "rm -f '$RemoteTransfer'")
    }
    if ($RemoteEnvStage) {
        Invoke-Quietly -Executable $Ssh -Arguments @('-n', '-o', 'BatchMode=yes', $Remote, "rm -f '$RemoteEnvStage'")
    }
    if ($RemoteDatabaseStage) {
        Invoke-Quietly -Executable $Ssh -Arguments @('-n', '-o', 'BatchMode=yes', $Remote, "rm -f '$RemoteDatabaseStage'")
    }
}