param(
  [string]$DatabaseUrl = "postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev",
  [switch]$ResetSchema,
  [switch]$ResetVolume
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
  throw "Python virtualenv not found at $python. Create it and install backend requirements first."
}

$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
  throw "Docker is not available in PATH. Install/start Docker Desktop before running this script."
}

Write-Host "Validating local database target..."
Push-Location $backendDir
try {
  & $python -c "from scripts.dev_db_safety import assert_local_database_url; import sys; print(assert_local_database_url(sys.argv[1], purpose='dev db setup').display)" $DatabaseUrl
  if ($LASTEXITCODE -ne 0) { throw "Database URL safety validation failed." }
}
finally {
  Pop-Location
}

Write-Host "Starting local PostgreSQL service..."
Push-Location $repoRoot
try {
  if ($ResetVolume) {
    Write-Host "Removing only the local PostgreSQL Docker volume for a clean development database..."
    docker compose stop postgres
    if ($LASTEXITCODE -ne 0) { throw "docker compose stop postgres failed." }
    docker compose rm -f postgres
    if ($LASTEXITCODE -ne 0) { throw "docker compose rm postgres failed." }
    $projectName = if ($env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME } else { (Split-Path -Leaf $repoRoot).ToLowerInvariant() }
    $postgresVolume = "${projectName}_postgres_data"
    $existingVolume = docker volume ls --format "{{.Name}}" | Where-Object { $_ -eq $postgresVolume }
    if ($existingVolume) {
      docker volume rm $postgresVolume
      if ($LASTEXITCODE -ne 0) { throw "docker volume rm $postgresVolume failed." }
    }
  }

  docker compose up -d postgres
  if ($LASTEXITCODE -ne 0) { throw "docker compose up failed." }

  $containerId = docker compose ps -q postgres
  if (-not $containerId) { throw "PostgreSQL container was not created." }

  $deadline = (Get-Date).AddSeconds(90)
  do {
    $health = docker inspect --format "{{.State.Health.Status}}" $containerId 2>$null
    if ($health -eq "healthy") { break }
    Start-Sleep -Seconds 2
  } while ((Get-Date) -lt $deadline)

  if ($health -ne "healthy") {
    throw "PostgreSQL did not become healthy. Last health status: $health"
  }
}
finally {
  Pop-Location
}

Write-Host "Applying migrations..."
Push-Location $backendDir
try {
  $env:DATABASE_URL = $DatabaseUrl
  $args = @("scripts\apply_migrations.py", "--database-url", $DatabaseUrl)
  if ($ResetSchema) { $args += "--reset-schema" }
  & $python @args
  if ($LASTEXITCODE -ne 0) { throw "Migration command failed." }

  & $python "scripts\inspect_dev_schema.py" "--database-url" $DatabaseUrl
  if ($LASTEXITCODE -ne 0) { throw "Schema inspection failed." }
}
finally {
  Pop-Location
}

Write-Host "Local PostgreSQL development database is ready."
Write-Host "Use STORAGE_BACKEND=postgres and DATABASE_URL=$DatabaseUrl for backend validation."
