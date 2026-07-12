param(
  [string]$DatabaseUrl
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
$backendEnvPath = Join-Path $backendDir ".env"

function Read-DotEnvValue {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Key
  )

  if (-not (Test-Path -LiteralPath $Path)) {
    return $null
  }

  foreach ($line in Get-Content -LiteralPath $Path) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) {
      continue
    }
    if ($trimmed -notmatch "^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$") {
      continue
    }
    if ($Matches[1] -ne $Key) {
      continue
    }
    $value = $Matches[2].Trim()
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
      $value = $value.Substring(1, $value.Length - 2)
    }
    return $value
  }

  return $null
}

function ConvertTo-MaskedDatabaseUrl {
  param([Parameter(Mandatory = $true)][string]$Url)

  try {
    $uri = [System.Uri]$Url
    $userinfo = $uri.UserInfo
    $maskedUserInfo = ""
    if ($userinfo) {
      $user = ($userinfo -split ":", 2)[0]
      $maskedUserInfo = "$user`:***@"
    }
    return "$($uri.Scheme)://$maskedUserInfo$($uri.Host):$($uri.Port)$($uri.AbsolutePath)"
  }
  catch {
    return "<invalid database url>"
  }
}

if (-not (Test-Path -LiteralPath $python)) {
  throw "Python virtualenv not found at $python. Create it and install backend requirements first."
}

$resolvedDatabaseUrl = $null
if ($PSBoundParameters.ContainsKey("DatabaseUrl") -and $DatabaseUrl) {
  $resolvedDatabaseUrl = $DatabaseUrl
}
elseif ($env:DATABASE_URL) {
  $resolvedDatabaseUrl = $env:DATABASE_URL
}
else {
  $resolvedDatabaseUrl = Read-DotEnvValue -Path $backendEnvPath -Key "DATABASE_URL"
}

if (-not $resolvedDatabaseUrl) {
  throw "DATABASE_URL is required. Use the local dev database URL for smoke metadata."
}

Write-Host "Using metadata database: $(ConvertTo-MaskedDatabaseUrl -Url $resolvedDatabaseUrl)"

Push-Location $backendDir
try {
  & $python "scripts\smoke_supabase_storage.py" "--database-url" $resolvedDatabaseUrl
  if ($LASTEXITCODE -ne 0) { throw "Supabase Storage smoke test failed." }
}
finally {
  Pop-Location
}
