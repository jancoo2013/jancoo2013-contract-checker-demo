[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("doctor")]
    [string]$Command = "doctor"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptRoot "..")).Path
$MobileRoot = Join-Path $RepoRoot "mobile\pii-reviewer"
$script:DoctorResults = New-Object "System.Collections.Generic.List[object]"

function Add-DoctorResult {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("PASS", "WARN", "FAIL", "INFO")]
        [string]$Status,
        [Parameter(Mandatory = $true)]
        [string]$Check,
        [Parameter(Mandatory = $true)]
        [string]$Detail
    )

    $script:DoctorResults.Add(
        [pscustomobject]@{
            Status = $Status
            Check  = $Check
            Detail = $Detail
        }
    )
}

function Get-CommandPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $commandInfo = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $commandInfo) {
        return $null
    }

    return $commandInfo.Definition
}

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    try {
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $FilePath
        $startInfo.Arguments = ($Arguments -join " ")
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.CreateNoWindow = $true

        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $startInfo
        if (-not $process.Start()) {
            return [pscustomobject]@{ ExitCode = -1; Output = "" }
        }

        $standardOutput = $process.StandardOutput.ReadToEnd()
        $standardError = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        $exitCode = $process.ExitCode
        $process.Dispose()

        $outputParts = @($standardOutput.Trim(), $standardError.Trim()) |
            Where-Object { $_ }

        return [pscustomobject]@{
            ExitCode = $exitCode
            Output   = ($outputParts -join [Environment]::NewLine)
        }
    }
    catch {
        return [pscustomobject]@{ ExitCode = -1; Output = "" }
    }
}

function Find-AndroidSdk {
    $candidates = New-Object "System.Collections.Generic.List[string]"

    if ($env:ANDROID_HOME) {
        $candidates.Add($env:ANDROID_HOME)
    }
    if ($env:ANDROID_SDK_ROOT -and $env:ANDROID_SDK_ROOT -ne $env:ANDROID_HOME) {
        $candidates.Add($env:ANDROID_SDK_ROOT)
    }
    if ($env:LOCALAPPDATA) {
        $defaultSdk = Join-Path $env:LOCALAPPDATA "Android\Sdk"
        if (-not $candidates.Contains($defaultSdk)) {
            $candidates.Add($defaultSdk)
        }
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Container)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    return $null
}

function Test-ProjectFiles {
    if (-not (Test-Path -LiteralPath $MobileRoot -PathType Container)) {
        Add-DoctorResult -Status "FAIL" -Check "Mobile project" -Detail "mobile\pii-reviewer was not found."
        return
    }

    Add-DoctorResult -Status "PASS" -Check "Repository" -Detail "Repository root resolved."
    Add-DoctorResult -Status "PASS" -Check "Mobile project" -Detail "mobile\pii-reviewer found."

    $packageJsonPath = Join-Path $MobileRoot "package.json"
    $appJsonPath = Join-Path $MobileRoot "app.json"

    foreach ($requiredFile in @($packageJsonPath, $appJsonPath)) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            Add-DoctorResult -Status "FAIL" -Check "Project file" -Detail "A required mobile project file is missing."
        }
    }

    if (Test-Path -LiteralPath $appJsonPath -PathType Leaf) {
        try {
            $appConfig = Get-Content -LiteralPath $appJsonPath -Raw | ConvertFrom-Json
            $packageName = [string]$appConfig.expo.android.package
            if ($packageName) {
                Add-DoctorResult -Status "PASS" -Check "Android package" -Detail $packageName
            }
            else {
                Add-DoctorResult -Status "FAIL" -Check "Android package" -Detail "expo.android.package is missing in app.json."
            }
        }
        catch {
            Add-DoctorResult -Status "FAIL" -Check "app.json" -Detail "app.json could not be parsed."
        }
    }

    $expoPackagePath = Join-Path $MobileRoot "node_modules\expo\package.json"
    if (Test-Path -LiteralPath $expoPackagePath -PathType Leaf) {
        Add-DoctorResult -Status "PASS" -Check "Dependencies" -Detail "node_modules contains Expo."
    }
    else {
        Add-DoctorResult -Status "WARN" -Check "Dependencies" -Detail "Expo dependencies are not installed. Run npm install in mobile\pii-reviewer."
    }

    $gradleWrapperPath = Join-Path $MobileRoot "android\gradlew.bat"
    if (Test-Path -LiteralPath $gradleWrapperPath -PathType Leaf) {
        Add-DoctorResult -Status "PASS" -Check "Gradle wrapper" -Detail "Present."
    }
    else {
        Add-DoctorResult -Status "INFO" -Check "Gradle wrapper" -Detail "Native android directory is absent; Expo can generate it."
    }
}

function Test-Node {
    $nodePath = Get-CommandPath -Name "node"
    if (-not $nodePath) {
        Add-DoctorResult -Status "FAIL" -Check "Node.js" -Detail "node was not found in PATH."
        return
    }

    $nodeResult = Invoke-NativeCommand -FilePath $nodePath -Arguments @("--version")
    if ($nodeResult.ExitCode -ne 0) {
        Add-DoctorResult -Status "FAIL" -Check "Node.js" -Detail "node --version failed."
        return
    }

    $version = $nodeResult.Output
    if ($version -match "^v(?<major>\d+)") {
        $major = [int]$Matches.major
        if ($major -eq 22) {
            Add-DoctorResult -Status "PASS" -Check "Node.js" -Detail "$version (matches CI major version 22)."
        }
        elseif ($major -ge 20) {
            Add-DoctorResult -Status "WARN" -Check "Node.js" -Detail "$version is usable, but CI uses Node 22."
        }
        else {
            Add-DoctorResult -Status "FAIL" -Check "Node.js" -Detail "$version is too old; use Node 20 or newer, preferably 22."
        }
    }
    else {
        Add-DoctorResult -Status "WARN" -Check "Node.js" -Detail "Version output was not recognized."
    }

    foreach ($tool in @("npm", "npx")) {
        if (Get-CommandPath -Name $tool) {
            Add-DoctorResult -Status "PASS" -Check $tool -Detail "Available in PATH."
        }
        else {
            Add-DoctorResult -Status "FAIL" -Check $tool -Detail "$tool was not found in PATH."
        }
    }
}

function Test-Java {
    $javaPath = Get-CommandPath -Name "java"
    if (-not $javaPath) {
        Add-DoctorResult -Status "FAIL" -Check "Java" -Detail "java was not found in PATH; project CI uses JDK 17."
    }
    else {
        $javaResult = Invoke-NativeCommand -FilePath $javaPath -Arguments @("-version")
        if ($javaResult.ExitCode -ne 0) {
            Add-DoctorResult -Status "FAIL" -Check "Java" -Detail "java -version failed."
        }
        elseif ($javaResult.Output -match 'version\s+"(?<major>\d+)') {
            $major = [int]$Matches.major
            if ($major -eq 17) {
                Add-DoctorResult -Status "PASS" -Check "Java" -Detail "JDK 17 is available."
            }
            else {
                Add-DoctorResult -Status "FAIL" -Check "Java" -Detail "Detected Java $major; this project requires JDK 17."
            }
        }
        else {
            Add-DoctorResult -Status "WARN" -Check "Java" -Detail "java -version output was not recognized."
        }
    }

    if ($env:JAVA_HOME -and (Test-Path -LiteralPath $env:JAVA_HOME -PathType Container)) {
        Add-DoctorResult -Status "PASS" -Check "JAVA_HOME" -Detail "Set to an existing directory."
    }
    elseif ($env:JAVA_HOME) {
        Add-DoctorResult -Status "FAIL" -Check "JAVA_HOME" -Detail "Points to a missing directory."
    }
    else {
        Add-DoctorResult -Status "WARN" -Check "JAVA_HOME" -Detail "Not set."
    }
}

function Test-AndroidSdk {
    $sdkPath = Find-AndroidSdk
    if (-not $sdkPath) {
        Add-DoctorResult -Status "FAIL" -Check "Android SDK" -Detail "No valid environment or default Android Studio SDK directory was found."
        Add-DoctorResult -Status "FAIL" -Check "adb" -Detail "Cannot locate adb without an Android SDK."
        return
    }

    if ($env:ANDROID_HOME -and (Test-Path -LiteralPath $env:ANDROID_HOME -PathType Container)) {
        Add-DoctorResult -Status "PASS" -Check "ANDROID_HOME" -Detail "Set to an existing SDK directory."
    }
    else {
        Add-DoctorResult -Status "WARN" -Check "ANDROID_HOME" -Detail "SDK detected, but ANDROID_HOME is not set to a valid directory."
    }

    $adbPath = Get-CommandPath -Name "adb"
    if (-not $adbPath) {
        $adbCandidate = Join-Path $sdkPath "platform-tools\adb.exe"
        if (Test-Path -LiteralPath $adbCandidate -PathType Leaf) {
            $adbPath = $adbCandidate
        }
    }

    if (-not $adbPath) {
        Add-DoctorResult -Status "FAIL" -Check "adb" -Detail "adb was not found in PATH or Android SDK platform-tools."
        return
    }

    $adbResult = Invoke-NativeCommand -FilePath $adbPath -Arguments @("devices", "-l")
    if ($adbResult.ExitCode -ne 0) {
        Add-DoctorResult -Status "FAIL" -Check "adb" -Detail "adb devices -l failed."
        return
    }

    $deviceLines = @(
        $adbResult.Output -split "`r?`n" |
            Where-Object { $_ -match "^\S+\s+(device|offline|unauthorized)\b" }
    )

    if ($deviceLines.Count -eq 0) {
        Add-DoctorResult -Status "WARN" -Check "Android device" -Detail "adb is available, but no emulator or phone is connected."
        return
    }

    $readyDevices = @($deviceLines | Where-Object { $_ -match "^\S+\s+device\b" })
    $blockedDevices = @($deviceLines | Where-Object { $_ -match "^\S+\s+(offline|unauthorized)\b" })

    if ($blockedDevices.Count -gt 0) {
        Add-DoctorResult -Status "FAIL" -Check "Android device" -Detail "$($blockedDevices.Count) device(s) are offline or unauthorized; identifiers are not printed."
    }
    if ($readyDevices.Count -gt 0) {
        Add-DoctorResult -Status "PASS" -Check "Android device" -Detail "$($readyDevices.Count) ready device(s); identifiers are not printed."
    }
}

function Show-DoctorResults {
    foreach ($result in $script:DoctorResults) {
        Write-Host ("[{0}] {1}: {2}" -f $result.Status, $result.Check, $result.Detail)
    }

    $failCount = @($script:DoctorResults | Where-Object { $_.Status -eq "FAIL" }).Count
    $warnCount = @($script:DoctorResults | Where-Object { $_.Status -eq "WARN" }).Count
    $passCount = @($script:DoctorResults | Where-Object { $_.Status -eq "PASS" }).Count

    Write-Host ""
    Write-Host ("Summary: {0} passed, {1} warning(s), {2} failure(s)." -f $passCount, $warnCount, $failCount)

    if ($failCount -gt 0) {
        return 1
    }

    return 0
}

function Invoke-Doctor {
    Write-Host "Android development environment doctor"
    Write-Host ""

    Test-ProjectFiles
    Test-Node
    Test-Java
    Test-AndroidSdk

    return Show-DoctorResults
}

switch ($Command) {
    "doctor" {
        $exitCode = Invoke-Doctor
        exit $exitCode
    }
}
