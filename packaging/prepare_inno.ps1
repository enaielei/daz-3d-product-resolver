# Pinned compiler in portable mode: no registry registration or global tool changes.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$toolsDir = Join-Path $projectRoot 'work/tools'
$compilerDir = Join-Path $toolsDir 'inno'
$download = Join-Path $toolsDir 'innosetup-6.7.3.exe'
New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
Invoke-WebRequest 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe' -OutFile $download
$expected = '9C73C3BAE7ED48D44112A0F48E66742C00090BDB5BEF71D9D3C056C66E97B732'
if ((Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash -ne $expected) {
    throw 'Inno Setup compiler checksum mismatch'
}
$process = Start-Process -FilePath $download -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER',
    '/PORTABLE=1', '/NOICONS', '/TASKS=""', "/DIR=`"$compilerDir`""
) -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Compiler extraction failed: $($process.ExitCode)" }
Write-Output (Join-Path $compilerDir 'ISCC.exe')
