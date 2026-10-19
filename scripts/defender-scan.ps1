param(
    [Parameter(Mandatory)][string]$SourcePath,
    [Parameter(Mandatory)][string]$ReportPath
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$PSNativeCommandUseErrorActionPreference = $false
New-Item -ItemType Directory -Force $ReportPath | Out-Null
$report = [ordered]@{ result = 'failed'; startedUtc = [DateTime]::UtcNow.ToString('o') }
try {
    $root = (Resolve-Path $SourcePath).Path
    $installer = Join-Path $root 'dist/installer.exe'
    if (!(Test-Path $installer) -or (Get-Item $installer).Length -eq 0) { throw 'Missing installer to scan' }
    $before = (Get-FileHash $installer -Algorithm SHA256).Hash
    $report.installerSha256 = $before
    $service = Get-Service WinDefend
    if ($service.Status -ne 'Running') {
        Set-Service WinDefend -StartupType Manual
        Start-Service WinDefend
    }
    Update-MpSignature -ErrorAction Stop
    $status = Get-MpComputerStatus
    if (!$status.AMServiceEnabled -or !$status.AntivirusEnabled) { throw 'Defender antivirus is not enabled' }
    if ($status.AntivirusSignatureLastUpdated -lt (Get-Date).AddDays(-2)) { throw 'Defender signatures are older than 48 hours' }
    $report.engineVersion = $status.AMEngineVersion
    $report.signatureVersion = $status.AntivirusSignatureVersion
    $report.signatureUpdated = $status.AntivirusSignatureLastUpdated.ToUniversalTime().ToString('o')
    $candidates = @(Get-ChildItem "$env:ProgramData/Microsoft/Windows Defender/Platform/*/MpCmdRun.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending)
    $scanner = if ($candidates.Count) { $candidates[0].FullName } else { "$env:ProgramFiles/Windows Defender/MpCmdRun.exe" }
    if (!(Test-Path $scanner)) { throw 'MpCmdRun.exe is unavailable' }
    # Scan the whole build tree, including unpacked plugin binaries and final installer.
    # DisableRemediation ignores exclusions, scans archives and prevents a repaired
    # detection from being reported as a successful (exit 0) scan.
    & $scanner -Scan -ScanType 3 -File $root -DisableRemediation 2>&1 | Tee-Object -FilePath (Join-Path $ReportPath 'scan.log')
    $scanExit = $LASTEXITCODE
    $report.scanExitCode = $scanExit
    if ($scanExit -ne 0) { throw "Defender found a threat or could not complete the scan (exit $scanExit)" }
    if ((Get-FileHash $installer -Algorithm SHA256).Hash -ne $before) { throw 'Installer changed during scanning' }
    $report.result = 'clean'
} catch {
    $report.error = $_.Exception.Message
    throw
} finally {
    $report.finishedUtc = [DateTime]::UtcNow.ToString('o')
    $report | ConvertTo-Json | Set-Content (Join-Path $ReportPath 'result.json')
    if ($env:GITHUB_STEP_SUMMARY) {
        "Defender scan: **$($report.result)**. See the defender report artifact for signature version, installer SHA-256 and scan output." | Add-Content $env:GITHUB_STEP_SUMMARY
    }
}
