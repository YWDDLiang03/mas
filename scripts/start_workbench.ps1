[CmdletBinding()]
param(
    [string]$Store = 'var\primary\store',
    [string]$Models,
    [string]$Config,
    [string]$Python,
    [ValidateRange(1, 65535)][int]$Port = 8769,
    [switch]$AllowOperations,
    [switch]$NoBrowser,
    [ValidateSet('agent', 'human')][string]$ActorKind = 'agent',
    [string]$ActorName = 'codex',
    [string[]]$Settings = @()
)

$ErrorActionPreference = 'Stop'
$masProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not [IO.Path]::IsPathRooted($Store)) { $Store = Join-Path $masProjectRoot $Store }
$Store = [IO.Path]::GetFullPath($Store)
if (-not (Test-Path -LiteralPath (Join-Path $Store 'store.db') -PathType Leaf)) {
    throw "No inherited store.db at $Store. Restore the existing store first, or pass -Store <directory>."
}
if (-not $Python) {
    $masLocalPython = Join-Path $masProjectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $masLocalPython) { $Python = $masLocalPython }
    else { $Python = (Get-Command python -ErrorAction Stop).Source }
}
$masArguments = @('-m', 'mas.cli.main', '--store', $Store)
if ($Models) { $masArguments += @('--models', $Models) }
if ($Config) { $masArguments += @('--config', $Config) }
foreach ($masSetting in $Settings) { $masArguments += @('--set', $masSetting) }
$masArguments += @('ui', 'serve', '--host', '127.0.0.1', '--port', "$Port")
if ($AllowOperations) {
    $masArguments += @('--allow-operations', '--operation-actor-kind', $ActorKind, '--operation-actor-name', $ActorName)
}
if (-not $NoBrowser) { $masArguments += '--open-browser' }
$masPreviousPythonPath = $env:PYTHONPATH
$masPreviousUtf8 = $env:PYTHONUTF8
$masPreviousReadCache = $env:MAS_WORKBENCH_READ_CACHE
try {
    $env:PYTHONPATH = (Join-Path $masProjectRoot 'src') + [IO.Path]::PathSeparator + $masPreviousPythonPath
    $env:PYTHONUTF8 = '1'
    $masLinkedReadCache = Join-Path (Split-Path -Parent $Store) 'workbench-linked-read.db'
    if (-not $env:MAS_WORKBENCH_READ_CACHE -and (Test-Path -LiteralPath $masLinkedReadCache -PathType Leaf)) {
        $env:MAS_WORKBENCH_READ_CACHE = $masLinkedReadCache
    }
    & $Python @masArguments
    $masExitCode = $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $masPreviousPythonPath
    $env:PYTHONUTF8 = $masPreviousUtf8
    $env:MAS_WORKBENCH_READ_CACHE = $masPreviousReadCache
}
exit $masExitCode
