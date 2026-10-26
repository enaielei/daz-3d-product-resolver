param([Parameter(Mandatory = $true)][string]$Installer)
# The test app is confined to a fresh workspace folder. /PORTABLETEST suppresses shortcuts
# and uninstall registration; the same payload and generated uninstaller are exercised.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$testDir = Join-Path $projectRoot ('work/installer-smoke-' + [guid]::NewGuid().ToString('N'))
$process = Start-Process -FilePath (Resolve-Path -LiteralPath $Installer) -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/PORTABLETEST=1', '/TASKS=""',
    "/DIR=`"$testDir`""
) -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Installation failed: $($process.ExitCode)" }
$app = Join-Path $testDir 'Daz3DProductResolver.exe'
$process = Start-Process -FilePath $app -ArgumentList '--smoke-test' -WindowStyle Hidden -PassThru
if (-not $process.WaitForExit(30000)) { $process.Kill(); throw 'Installed app timed out' }
if ($process.ExitCode -ne 0) { throw "Installed app failed: $($process.ExitCode)" }
# A content sentinel proves that application removal does not remove unrelated files.
$sentinel = Join-Path $testDir 'user-content-sentinel.txt'
Set-Content -LiteralPath $sentinel -Value 'preserve user content'
$process = Start-Process -FilePath (Join-Path $testDir 'unins000.exe') -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'
) -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Uninstall failed: $($process.ExitCode)" }
if (Test-Path -LiteralPath $app) { throw 'Uninstaller left the application executable' }
if (-not (Test-Path -LiteralPath $sentinel)) { throw 'Uninstaller removed unrelated content' }
Write-Output 'Installer, installed app, uninstaller and user-content preservation: PASS'
