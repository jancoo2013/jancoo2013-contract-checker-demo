[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptRoot "..")).Path
$MobileRoot = Join-Path $RepoRoot "mobile\pii-reviewer"
$AppJsonPath = Join-Path $MobileRoot "app.json"

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

function Stop-Restart {
    param(
        [Parameter(Mandatory = $true)][string]$Kind,
        [Parameter(Mandatory = $true)][string]$Message
    )
    Write-Host ("RESTART {0}: {1}" -f $Kind, $Message)
    exit 1
}

Write-Host "Android standalone application restart"
Write-Host ""

if (-not (Test-Path -LiteralPath $AppJsonPath -PathType Leaf)) {
    Stop-Restart "BLOCKED" "mobile app.json is missing."
}

try {
    $appConfig = Get-Content -LiteralPath $AppJsonPath -Raw | ConvertFrom-Json
    $packageName = [string]$appConfig.expo.android.package
}
catch {
    Stop-Restart "BLOCKED" "mobile app.json could not be parsed."
}
if (-not $packageName) {
    Stop-Restart "BLOCKED" "expo.android.package is missing."
}

$sdkPath = Find-AndroidSdk
$adbCommand = Get-Command adb -ErrorAction SilentlyContinue | Select-Object -First 1
$adbPath = if ($adbCommand) { $adbCommand.Definition } else { $null }
if (-not $adbPath -and $sdkPath) {
    $candidate = Join-Path $sdkPath "platform-tools\adb.exe"
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $adbPath = $candidate }
}
if (-not $adbPath) {
    Stop-Restart "BLOCKED" "adb was not found."
}

$deviceResult = Invoke-NativeCommand $adbPath @("devices", "-l")
if ($deviceResult.ExitCode -ne 0) {
    Stop-Restart "FAILED" "adb device query failed."
}
$deviceLines = @($deviceResult.Output -split "`r?`n" |
    Where-Object { $_ -match "^\S+\s+(device|offline|unauthorized)\b" })
$readyLines = @($deviceLines | Where-Object { $_ -match "^\S+\s+device\b" })
$blockedLines = @($deviceLines | Where-Object { $_ -match "^\S+\s+(offline|unauthorized)\b" })
if ($blockedLines.Count -gt 0) {
    Stop-Restart "BLOCKED" "$($blockedLines.Count) device(s) are offline or unauthorized; identifiers hidden."
}
if ($readyLines.Count -ne 1) {
    Stop-Restart "BLOCKED" "Expected exactly one ready device; found $($readyLines.Count); identifiers hidden."
}
$serial = ($readyLines[0] -split "\s+", 2)[0]

$installed = Invoke-NativeCommand $adbPath @("-s", $serial, "shell", "pm", "path", $packageName)
if ($installed.ExitCode -ne 0 -or $installed.Output -notmatch '(?m)^package:') {
    Stop-Restart "BLOCKED" "The current package is not installed. Run android-dev.ps1 run first."
}

Write-Host "[1/3] Stopping application..."
$forceStop = Invoke-NativeCommand $adbPath @("-s", $serial, "shell", "am", "force-stop", $packageName)
if ($forceStop.ExitCode -ne 0) {
    Stop-Restart "FAILED" "Could not stop the application process."
}
Start-Sleep -Milliseconds 750
$stopped = Invoke-NativeCommand $adbPath @("-s", $serial, "shell", "pidof", $packageName)
if (-not [string]::IsNullOrWhiteSpace($stopped.Output)) {
    Stop-Restart "FAILED" "Application process is still running after force-stop."
}
if ($stopped.ExitCode -notin @(0, 1)) {
    Stop-Restart "FAILED" "Application stop confirmation failed."
}

Write-Host "[2/3] Starting application..."
$launch = Invoke-NativeCommand $adbPath @(
    "-s", $serial, "shell", "monkey", "-p", $packageName,
    "-c", "android.intent.category.LAUNCHER", "1"
)
if ($launch.ExitCode -ne 0 -or $launch.Output -notmatch 'Events injected:\s*1') {
    Stop-Restart "FAILED" "Launcher activity did not start."
}

Write-Host "[3/3] Confirming application process..."
Start-Sleep -Seconds 2
$pidResult = Invoke-NativeCommand $adbPath @("-s", $serial, "shell", "pidof", $packageName)
$pidTokens = @($pidResult.Output.Trim() -split "\s+" | Where-Object { $_ -match '^\d+$' })
if ($pidResult.ExitCode -ne 0 -or $pidTokens.Count -eq 0) {
    Stop-Restart "FAILED" "Application process is not running after restart."
}

Write-Host ""
Write-Host "RESTART READY"
Write-Host "Package: $packageName"
Write-Host "Device: one ready device; identifier hidden."
exit 0
