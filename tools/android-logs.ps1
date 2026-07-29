[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptRoot "..")).Path
$MobileRoot = Join-Path $RepoRoot "mobile\pii-reviewer"
$AppJsonPath = Join-Path $MobileRoot "app.json"
$MaxOutputLines = 120

function ConvertTo-NativeArguments {
    param([string[]]$Arguments = @())
    $quoted = foreach ($argument in $Arguments) {
        if ($argument -match '[\s"]') {
            '"' + ($argument -replace '"', '\"') + '"'
        }
        else {
            $argument
        }
    }
    return ($quoted -join " ")
}

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @()
    )
    try {
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $FilePath
        $startInfo.Arguments = ConvertTo-NativeArguments -Arguments $Arguments
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.CreateNoWindow = $true

        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $startInfo
        if (-not $process.Start()) {
            return [pscustomobject]@{ ExitCode = -1; Output = "" }
        }

        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        $parts = @($stdoutTask.Result.Trim(), $stderrTask.Result.Trim()) |
            Where-Object { $_ }
        $result = [pscustomobject]@{
            ExitCode = $process.ExitCode
            Output = ($parts -join [Environment]::NewLine)
        }
        $process.Dispose()
        return $result
    }
    catch {
        return [pscustomobject]@{ ExitCode = -1; Output = "" }
    }
}

function Find-AndroidSdk {
    foreach ($candidate in @(
        $env:ANDROID_HOME,
        $env:ANDROID_SDK_ROOT,
        $(if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "Android\Sdk" })
    )) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Container)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

function Stop-Logs {
    param(
        [Parameter(Mandatory = $true)][string]$Kind,
        [Parameter(Mandatory = $true)][string]$Message
    )
    Write-Host ("LOGS {0}: {1}" -f $Kind, $Message)
    exit 1
}

function Protect-LogLine {
    param([Parameter(Mandatory = $true)][string]$Line)

    $safe = $Line -replace '[\x00-\x08\x0B\x0C\x0E-\x1F]', ''
    $safe = $safe -replace 'https?://\S+', '<URL>'
    $safe = $safe -replace '(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '<EMAIL>'
    $safe = $safe -replace '(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '<UUID>'
    $safe = $safe -replace '(?:[A-Za-z]:\\|/)(?:[^\s:]+[\\/])+[^\s:]*', '<PATH>'
    $safe = $safe -replace '[\u0590-\u05FF]+', '<HEBREW_TEXT>'
    $safe = $safe -replace '(?<![A-Za-z0-9])[+]?\d[\d\s().-]{6,}\d(?![A-Za-z0-9])', '<NUMBER>'
    $safe = $safe -replace '(?i)\b[0-9a-f]{24,}\b', '<TOKEN>'
    $safe = $safe -replace '\(\s*\d+\s*\)', '(<PID>)'

    if ($safe.Length -gt 500) {
        $safe = $safe.Substring(0, 500) + '...<TRUNCATED>'
    }
    return $safe
}

Write-Host "Android process warning/error logs"
Write-Host ""

if (-not (Test-Path -LiteralPath $AppJsonPath -PathType Leaf)) {
    Stop-Logs "BLOCKED" "mobile app.json is missing."
}

try {
    $appConfig = Get-Content -LiteralPath $AppJsonPath -Raw | ConvertFrom-Json
    $packageName = [string]$appConfig.expo.android.package
}
catch {
    Stop-Logs "BLOCKED" "mobile app.json could not be parsed."
}
if (-not $packageName) {
    Stop-Logs "BLOCKED" "expo.android.package is missing."
}

$sdkPath = Find-AndroidSdk
$adbCommand = Get-Command adb -ErrorAction SilentlyContinue | Select-Object -First 1
$adbPath = if ($adbCommand) { $adbCommand.Definition } else { $null }
if (-not $adbPath -and $sdkPath) {
    $candidate = Join-Path $sdkPath "platform-tools\adb.exe"
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $adbPath = $candidate }
}
if (-not $adbPath) {
    Stop-Logs "BLOCKED" "adb was not found."
}

$deviceResult = Invoke-NativeCommand $adbPath @("devices", "-l")
if ($deviceResult.ExitCode -ne 0) {
    Stop-Logs "FAILED" "adb device query failed."
}
$deviceLines = @($deviceResult.Output -split "`r?`n" |
    Where-Object { $_ -match "^\S+\s+(device|offline|unauthorized)\b" })
$readyLines = @($deviceLines | Where-Object { $_ -match "^\S+\s+device\b" })
$blockedLines = @($deviceLines | Where-Object { $_ -match "^\S+\s+(offline|unauthorized)\b" })
if ($blockedLines.Count -gt 0) {
    Stop-Logs "BLOCKED" "$($blockedLines.Count) device(s) are offline or unauthorized; identifiers hidden."
}
if ($readyLines.Count -ne 1) {
    Stop-Logs "BLOCKED" "Expected exactly one ready device; found $($readyLines.Count); identifiers hidden."
}
$serial = ($readyLines[0] -split "\s+", 2)[0]

$pidResult = Invoke-NativeCommand $adbPath @("-s", $serial, "shell", "pidof", $packageName)
if ($pidResult.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($pidResult.Output)) {
    Stop-Logs "BLOCKED" "Application process is not running. Run android-dev.ps1 run first."
}
$pidTokens = @($pidResult.Output.Trim() -split "\s+" | Where-Object { $_ -match '^\d+$' })
if ($pidTokens.Count -eq 0) {
    Stop-Logs "FAILED" "Application process identifier could not be parsed."
}
$processId = $pidTokens[0]

$logResult = Invoke-NativeCommand $adbPath @(
    "-s", $serial, "logcat", "--pid=$processId", "-d",
    "-v", "tag", "-t", "200", "*:W"
)
if ($logResult.ExitCode -ne 0) {
    Stop-Logs "FAILED" "Process-scoped logcat query failed; raw output is hidden."
}

$lines = @($logResult.Output -split "`r?`n" |
    Where-Object { $_ -and $_ -notmatch '^--------- beginning of' } |
    Select-Object -Last $MaxOutputLines)

Write-Host "Scope: current package process only; warning/error; identifiers hidden."
Write-Host "Sanitization: paths, URLs, email, long numbers, Hebrew text and tokens are redacted."
Write-Host ""

if ($lines.Count -eq 0) {
    Write-Host "No warning/error lines were found in the recent process log."
}
else {
    foreach ($line in $lines) {
        Write-Host (Protect-LogLine $line)
    }
}

Write-Host ""
Write-Host "LOGS READY"
Write-Host "Package: $packageName"
Write-Host "Device: one ready device; identifier hidden."
exit 0
