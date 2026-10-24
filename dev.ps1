$SeedOnly = $false
if ($args -contains '-SeedOnly') { $SeedOnly = $true }
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$envFile = Join-Path $root '.env'

if (-not (Test-Path $envFile)) {
    throw 'Create .env from .env.example and set a random EA_SECRET_KEY and unique administrator credentials first.'
}

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw 'Create .venv and install backend requirements first; see README.md.'
}
$env:PYTHONPATH = Join-Path $root 'backend'
Push-Location $root
try {
    & $python -m alembic -c backend\alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
    & $python -m app.seed
    if ($LASTEXITCODE -ne 0) { throw 'Administrator bootstrap failed; check .env.' }
} finally {
    Pop-Location
}

if ($SeedOnly) {
    Write-Output 'Database migrations and role seed are complete.'
    exit 0
}

foreach ($port in @(8000, 5173)) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        throw "Port $port is already in use. Stop the existing process before running this launcher."
    }
}

$vite = Join-Path $root 'frontend\node_modules\vite\bin\vite.js'
if (-not (Test-Path $vite)) {
    throw 'Install frontend dependencies with npm.cmd install from the frontend directory first.'
}
$node = (Get-Command node.exe -ErrorAction Stop).Source

$apiLog = Join-Path $root 'backend\dev-api.log'
$webLog = Join-Path $root 'frontend\dev-web.log'
Start-Process -FilePath $python -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend', '--port', '8000') -WorkingDirectory $root -RedirectStandardOutput $apiLog -RedirectStandardError ($apiLog + '.err')
Start-Process -FilePath $node -ArgumentList @($vite, '--host', '127.0.0.1') -WorkingDirectory (Join-Path $root 'frontend') -RedirectStandardOutput $webLog -RedirectStandardError ($webLog + '.err')
Write-Output 'EA Workbench is starting at http://127.0.0.1:5173'