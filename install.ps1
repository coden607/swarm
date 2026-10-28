# Swarm Detection - one-click installer for Windows (PowerShell 5.1+).
#   irm https://raw.githubusercontent.com/coden607/swarm/main/install.ps1 | iex
# Env: SWARM_HOME (default %USERPROFILE%\swarm)  SWARM_PORT (default 8000)  GEMINI_API_KEY
#      SWARM_REMOTE=1 (public https link via Cloudflare tunnel)  SWARM_NO_ICON=1
$ErrorActionPreference = 'Stop'
$Repo = 'coden607/swarm'; $Branch = 'main'
$Home_ = if ($env:SWARM_HOME) { $env:SWARM_HOME } else { Join-Path $env:USERPROFILE 'swarm' }
$Port  = if ($env:SWARM_PORT) { $env:SWARM_PORT } else { '8000' }
function Log($m)  { Write-Host "[+] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[!] $m" -ForegroundColor Yellow }

# 1. source
if (-not (Test-Path (Join-Path $Home_ 'app\main.py'))) {
  Log "Downloading Swarm to $Home_"
  $zip = Join-Path $env:TEMP 'swarm.zip'; $tmp = Join-Path $env:TEMP 'swarm-extract'
  Invoke-WebRequest "https://codeload.github.com/$Repo/zip/refs/heads/$Branch" -OutFile $zip
  if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
  Expand-Archive $zip $tmp -Force
  New-Item -ItemType Directory -Force $Home_ | Out-Null
  Copy-Item (Join-Path (Get-ChildItem $tmp | Select-Object -First 1).FullName '*') $Home_ -Recurse -Force
} else { Log "Using existing $Home_" }
Set-Location $Home_

# 2. python
function Find-Py {
  foreach ($c in @('py -3', 'python', 'python3')) {
    $exe = $c.Split(' ')[0]
    if (Get-Command $exe -ErrorAction SilentlyContinue) {
      try { & $exe $c.Split(' ')[1..9] -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>$null; if ($LASTEXITCODE -eq 0) { return $c } } catch {}
    }
  }
  return $null
}
$py = Find-Py
if (-not $py) {
  Log 'Installing Python 3.12 via winget'
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'winget not found. Install Python 3.9+ from python.org and re-run.' }
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
  $py = Find-Py
  if (-not $py) { throw 'Python installed but not on PATH yet. Open a new PowerShell window and re-run.' }
}
$pyExe = $py.Split(' ')[0]; $pyArgs = @($py.Split(' ')[1..9] | Where-Object { $_ })

# 3. venv + deps
$vpy = Join-Path $Home_ 'venv\Scripts\python.exe'
if (-not (Test-Path $vpy)) { Log 'Creating virtualenv'; & $pyExe @pyArgs -m venv venv }
Log 'Installing Python dependencies (first run takes a few minutes)'
& $vpy -m pip install -q --upgrade pip
& $vpy -m pip install -q -r requirements.txt
& $vpy -m pip install -q qrcode 2>$null

# 4. config
function Rand { & $vpy -c "import secrets; print(secrets.token_urlsafe(16))" }
$newPass = $null
if (-not (Test-Path .env)) {
  Log 'Creating .env'
  $key = $env:GEMINI_API_KEY
  if (-not $key) { $key = Read-Host 'Gemini API key (https://aistudio.google.com/apikey) - Enter to skip' }
  $newPass = Rand
  @("JWT_SECRET=$(Rand)$(Rand)", 'ADMIN_USER=admin', "ADMIN_PASS=$newPass", "GEMINI_API_KEY=$key",
    '# EMAIL_SMTP_SERVER=', '# EMAIL_SMTP_PORT=587', '# EMAIL_SMTP_USER=', '# EMAIL_SMTP_PASS=', '# EMAIL_FROM=') |
    Set-Content -Encoding ASCII .env
} else { Log 'Keeping existing .env' }

# 4b. optional public https link (Cloudflare tunnel); login is still required
$remote = $false
if ($env:SWARM_REMOTE -eq '1') {
  New-Item -ItemType Directory -Force bin | Out-Null
  if (-not (Test-Path 'bin\cloudflared.exe')) {
    try { Log 'Downloading cloudflared'; Invoke-WebRequest 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'bin\cloudflared.exe' } catch { Warn 'cloudflared download failed' }
  }
  $remote = Test-Path 'bin\cloudflared.exe'
}
$lines = @(Get-Content .env | Where-Object { $_ -notmatch '^SWARM_REMOTE=' })
if ($remote) { $lines += 'SWARM_REMOTE=1' }
Set-Content -Encoding ASCII .env $lines

# 5. launcher + autostart at logon
@"
@echo off
cd /d "$Home_"
set SWARM_PORT=$Port
set SWARM_SCHEME=http
"$vpy" -m uvicorn app.main:app --host 0.0.0.0 --port $Port
"@ | Set-Content -Encoding ASCII (Join-Path $Home_ 'swarm.cmd')

@"
@echo off
powershell -NoProfile -Command "try{Invoke-WebRequest http://127.0.0.1:$Port/health -UseBasicParsing -TimeoutSec 2 | Out-Null}catch{Start-ScheduledTask -TaskName 'Swarm Detection' -ErrorAction SilentlyContinue; Start-Sleep 8}"
start "" msedge --app=http://localhost:$Port 2>nul || start "" http://localhost:$Port
"@ | Set-Content -Encoding ASCII (Join-Path $Home_ 'swarm-open.cmd')

# 5b. Desktop + Start Menu icon
if ($env:SWARM_NO_ICON -ne '1') {
  try {
    $ws = New-Object -ComObject WScript.Shell
    foreach ($dir in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
      if (-not $dir -or -not (Test-Path $dir)) { continue }
      $lnk = $ws.CreateShortcut((Join-Path $dir 'Swarm Detection.lnk'))
      $lnk.TargetPath = Join-Path $Home_ 'swarm-open.cmd'
      $lnk.WorkingDirectory = $Home_
      $lnk.WindowStyle = 7
      $lnk.IconLocation = (Join-Path $Home_ 'ui\swarm.ico')
      $lnk.Description = 'Swarm Detection'
      $lnk.Save()
    }
    Log 'Icon added to Desktop and Start Menu'
  } catch { Warn "Could not create shortcut: $($_.Exception.Message)" }
}

try {
  $cmdArg = '/c ""' + "$Home_\swarm.cmd" + '" >> "' + "$Home_\swarm.log" + '" 2>&1"'
  $act = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument $cmdArg
  $trg = New-ScheduledTaskTrigger -AtLogOn
  $set = New-ScheduledTaskSettingsSet -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable
  Register-ScheduledTask -TaskName 'Swarm Detection' -Action $act -Trigger $trg -Settings $set -Force | Out-Null
  Stop-ScheduledTask -TaskName 'Swarm Detection' -ErrorAction SilentlyContinue
  Start-ScheduledTask -TaskName 'Swarm Detection'
  Log "Scheduled task 'Swarm Detection' registered (starts at logon, restarts on failure)"
} catch {
  Warn "Could not register scheduled task ($($_.Exception.Message)); starting in background instead."
  Start-Process -FilePath "$Home_\swarm.cmd" -WindowStyle Hidden -RedirectStandardOutput "$Home_\swarm.log" -RedirectStandardError "$Home_\swarm.err.log"
}

# 6. firewall (needs admin; best effort)
try { New-NetFirewallRule -DisplayName 'Swarm Detection' -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -ErrorAction Stop | Out-Null; Log "Firewall: allowed TCP $Port" }
catch { Warn "Firewall rule not added (run PowerShell as Administrator, or allow TCP $Port manually) to reach it from phones." }

# 7. verify + report
$up = $false
$fell = $false
for ($i = 0; $i -lt 40; $i++) {
  try { if ((Invoke-WebRequest "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { $up = $true; break } } catch {}
  if ($i -ge 12 -and -not $fell) {
    $fell = $true
    Warn 'Scheduled task has not started the server yet; starting it directly.'
    Start-Process -FilePath "$Home_\swarm.cmd" -WindowStyle Hidden -RedirectStandardOutput "$Home_\swarm.log" -RedirectStandardError "$Home_\swarm.err.log"
  }
  Start-Sleep 1
}
$ip = & $vpy -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('10.255.255.255',1)); print(s.getsockname()[0])" 2>$null
if (-not $ip) { $ip = '127.0.0.1' }
if (-not $up) { foreach ($lf in 'swarm.log','swarm.err.log') { if (Test-Path "$Home_\$lf") { Write-Host "--- $lf (last 40 lines) ---"; Get-Content "$Home_\$lf" -Tail 40 } }; throw "Installed but server did not answer on port $Port. See $Home_\swarm.log" }
Log "Swarm is running: http://${ip}:$Port   (this PC: http://127.0.0.1:$Port)"
if ($newPass) { Write-Host "`n  Login:    admin`n  Password: $newPass      (saved in $Home_\.env)`n" }
if ($remote) { Write-Host "  Remote link (anywhere, login required) appears in the app within ~20 s, or see $Home_\data\tunnel.log" }
Write-Host '  Phones: open the URL, then Share / menu -> Add to Home Screen (or Install app).'
Write-Host '  Works offline on your local network; the app caches the last alerts if the server is unreachable.'
