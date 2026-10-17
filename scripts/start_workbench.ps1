[CmdletBinding()]
param(
    [string]$Store = 'var\primary\store',
    [string]$Models,
    [string]$Config,
    [string]$Python,
    [ValidateRange(1, 65535)][int]$Port = 8769,
    [switch]$InitializeStore,
    [switch]$AllowOperations,
    [switch]$NoBrowser,
    [ValidateSet('agent', 'human')][string]$ActorKind = 'human',
    [string]$ActorName = $env:USERNAME,
    [string[]]$Settings = @()
)

$ErrorActionPreference = 'Stop'
$masProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not [IO.Path]::IsPathRooted($Store)) { $Store = Join-Path $masProjectRoot $Store }
$Store = [IO.Path]::GetFullPath($Store)
$masStoreExists = Test-Path -LiteralPath (Join-Path $Store 'store.db') -PathType Leaf
if (-not $masStoreExists -and -not $InitializeStore) {
    throw "No store.db at $Store. For a new workspace add -InitializeStore, or pass -Store <existing directory>."
}
if (-not $Python) {
    $masLocalPython = Join-Path $masProjectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $masLocalPython) { $Python = $masLocalPython }
    else { $Python = (Get-Command python -ErrorAction Stop).Source }
}
elseif (-not [IO.Path]::IsPathRooted($Python) -and (Test-Path -LiteralPath (Join-Path $masProjectRoot $Python) -PathType Leaf)) {
    $Python = [IO.Path]::GetFullPath((Join-Path $masProjectRoot $Python))
}
foreach ($masPathOption in @('Models', 'Config')) {
    $masPathValue = Get-Variable -Name $masPathOption -ValueOnly
    if ($masPathValue -and -not [IO.Path]::IsPathRooted($masPathValue)) {
        Set-Variable -Name $masPathOption -Value ([IO.Path]::GetFullPath((Join-Path $masProjectRoot $masPathValue)))
    }
}
$masAssetDirectory = $env:MAS_WORKBENCH_ASSET_DIR
if (-not $masAssetDirectory) { $masAssetDirectory = Join-Path $masProjectRoot 'web\client\dist' }
elseif (-not [IO.Path]::IsPathRooted($masAssetDirectory)) { $masAssetDirectory = Join-Path $masProjectRoot $masAssetDirectory }
if ($AllowOperations -and -not (Test-Path -LiteralPath (Join-Path $masAssetDirectory 'index.html') -PathType Leaf)) {
    throw "Build the client first from $masProjectRoot : npm --prefix web/client ci; npm --prefix web/client run build"
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
Push-Location -LiteralPath $masProjectRoot
try {
    $env:PYTHONPATH = (Join-Path $masProjectRoot 'src') + [IO.Path]::PathSeparator + $masPreviousPythonPath
    $env:PYTHONUTF8 = '1'
    if (-not $masStoreExists) {
        & $Python -m mas.cli.main --store $Store init
        if ($LASTEXITCODE -ne 0) { throw "Could not initialize the workspace at $Store." }
    }
    $masLinkedReadCache = Join-Path (Split-Path -Parent $Store) 'workbench-linked-read.db'
    if (-not $env:MAS_WORKBENCH_READ_CACHE -and (Test-Path -LiteralPath $masLinkedReadCache -PathType Leaf)) {
        $env:MAS_WORKBENCH_READ_CACHE = $masLinkedReadCache
    }
    & $Python @masArguments
    $masExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
    $env:PYTHONPATH = $masPreviousPythonPath
    $env:PYTHONUTF8 = $masPreviousUtf8
    $env:MAS_WORKBENCH_READ_CACHE = $masPreviousReadCache
}
exit $masExitCode
