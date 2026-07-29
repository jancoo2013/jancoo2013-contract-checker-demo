[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("doctor", "build", "run")]
    [string]$Command = "doctor"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptRoot "..")).Path
$MobileRoot = Join-Path $RepoRoot "mobile\pii-reviewer"
$ArtifactRoot = Join-Path $MobileRoot "build-artifact"
$script:DoctorResults = New-Object "System.Collections.Generic.List[object]"

function Add-DoctorResult {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("PASS", "WARN", "FAIL", "INFO")]
        [string]$Status,
        [Parameter(Mandatory = $true)][string]$Check,
        [Parameter(Mandatory = $true)][string]$Detail
    )
    $script:DoctorResults.Add([pscustomobject]@{
        Status = $Status
        Check = $Check
        Detail = $Detail
    })
}

function Get-CommandPath {
    param([Parameter(Mandatory = $true)][string]$Name)
    $commandInfo = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $commandInfo) { return $null }
    return $commandInfo.Definition
}

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
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = ""
    )
    try {
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $FilePath
        $startInfo.Arguments = ConvertTo-NativeArguments -Arguments $Arguments
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.CreateNoWindow = $true
        if ($WorkingDirectory) { $startInfo.WorkingDirectory = $WorkingDirectory }

        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $startInfo
        if (-not $process.Start()) {
            return [pscustomobject]@{ ExitCode = -1; Output = "" }
        }

        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        $stdout = $stdoutTask.Result
        $stderr = $stderrTask.Result
        $exitCode = $process.ExitCode
        $process.Dispose()

        $parts = @($stdout.Trim(), $stderr.Trim()) | Where-Object { $_ }
        return [pscustomobject]@{
            ExitCode = $exitCode
            Output = ($parts -join [Environment]::NewLine)
        }
    }
    catch {
        return [pscustomobject]@{ ExitCode = -1; Output = "" }
    }
}

function Find-AndroidSdk {
    $candidates = New-Object "System.Collections.Generic.List[string]"
    foreach ($candidate in @(
        $env:ANDROID_HOME,
        $env:ANDROID_SDK_ROOT,
        $(if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "Android\Sdk" })
    )) {
        if ($candidate -and -not $candidates.Contains($candidate)) {
            $candidates.Add($candidate)
        }
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Container) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

function Test-ProjectFiles {
    param([switch]$RequireDependencies)
    if (-not (Test-Path -LiteralPath $MobileRoot -PathType Container)) {
        Add-DoctorResult "FAIL" "Mobile project" "mobile\pii-reviewer was not found."
        return
    }

    Add-DoctorResult "PASS" "Repository" "Repository root resolved."
    Add-DoctorResult "PASS" "Mobile project" "mobile\pii-reviewer found."

    $packageJson = Join-Path $MobileRoot "package.json"
    $appJson = Join-Path $MobileRoot "app.json"
    foreach ($requiredFile in @($packageJson, $appJson)) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            Add-DoctorResult "FAIL" "Project file" "A required mobile project file is missing."
        }
    }

    if (Test-Path -LiteralPath $appJson -PathType Leaf) {
        try {
            $appConfig = Get-Content -LiteralPath $appJson -Raw | ConvertFrom-Json
            $packageName = [string]$appConfig.expo.android.package
            if ($packageName) {
                Add-DoctorResult "PASS" "Android package" $packageName
            }
            else {
                Add-DoctorResult "FAIL" "Android package" "expo.android.package is missing."
            }
        }
        catch {
            Add-DoctorResult "FAIL" "app.json" "app.json could not be parsed."
        }
    }

    if (Test-Path (Join-Path $MobileRoot "node_modules\expo\package.json")) {
        Add-DoctorResult "PASS" "Dependencies" "node_modules contains Expo."
    }
    elseif ($RequireDependencies) {
        Add-DoctorResult "FAIL" "Dependencies" "Run npm install in mobile\pii-reviewer."
    }
    else {
        Add-DoctorResult "WARN" "Dependencies" "Run npm install in mobile\pii-reviewer."
    }

    if (Test-Path (Join-Path $MobileRoot "android\gradlew.bat")) {
        Add-DoctorResult "PASS" "Gradle wrapper" "Present."
    }
    else {
        Add-DoctorResult "INFO" "Gradle wrapper" "Expo prebuild will generate it."
    }
}

function Test-Node {
    $nodePath = Get-CommandPath "node"
    if (-not $nodePath) {
        Add-DoctorResult "FAIL" "Node.js" "node was not found in PATH."
        return
    }

    $nodeResult = Invoke-NativeCommand $nodePath @("--version")
    if ($nodeResult.ExitCode -ne 0) {
        Add-DoctorResult "FAIL" "Node.js" "node --version failed."
        return
    }

    if ($nodeResult.Output -match "^v(?<major>\d+)") {
        $major = [int]$Matches.major
        if ($major -eq 22) {
            Add-DoctorResult "PASS" "Node.js" "$($nodeResult.Output) matches CI."
        }
        elseif ($major -ge 20) {
            Add-DoctorResult "WARN" "Node.js" "$($nodeResult.Output) is usable; CI uses 22."
        }
        else {
            Add-DoctorResult "FAIL" "Node.js" "Use Node 20 or newer, preferably 22."
        }
    }
    else {
        Add-DoctorResult "WARN" "Node.js" "Version output was not recognized."
    }

    foreach ($tool in @("npm", "npx")) {
        if (Get-CommandPath $tool) {
            Add-DoctorResult "PASS" $tool "Available in PATH."
        }
        else {
            Add-DoctorResult "FAIL" $tool "$tool was not found in PATH."
        }
    }
}

function Test-Java {
    $javaPath = Get-CommandPath "java"
    if (-not $javaPath) {
        Add-DoctorResult "FAIL" "Java" "java was not found; project CI uses JDK 17."
    }
    else {
        $javaResult = Invoke-NativeCommand $javaPath @("-version")
        if ($javaResult.ExitCode -ne 0) {
            Add-DoctorResult "FAIL" "Java" "java -version failed."
        }
        elseif ($javaResult.Output -match 'version\s+"(?<major>\d+)') {
            $major = [int]$Matches.major
            if ($major -eq 17) {
                Add-DoctorResult "PASS" "Java" "JDK 17 is available."
            }
            else {
                Add-DoctorResult "FAIL" "Java" "Detected Java $major; this project requires JDK 17."
            }
        }
        else {
            Add-DoctorResult "WARN" "Java" "Version output was not recognized."
        }
    }

    if ($env:JAVA_HOME -and (Test-Path $env:JAVA_HOME -PathType Container)) {
        Add-DoctorResult "PASS" "JAVA_HOME" "Set to an existing directory."
    }
    elseif ($env:JAVA_HOME) {
        Add-DoctorResult "FAIL" "JAVA_HOME" "Points to a missing directory."
    }
    else {
        Add-DoctorResult "WARN" "JAVA_HOME" "Not set."
    }
}

function Test-AndroidSdk {
    param([switch]$CheckDevice)
    $sdkPath = Find-AndroidSdk
    if (-not $sdkPath) {
        Add-DoctorResult "FAIL" "Android SDK" "No valid SDK directory was found."
        return
    }

    if ($env:ANDROID_HOME -and (Test-Path $env:ANDROID_HOME -PathType Container)) {
        Add-DoctorResult "PASS" "ANDROID_HOME" "Set to an existing SDK directory."
    }
    else {
        Add-DoctorResult "WARN" "ANDROID_HOME" "SDK detected, but ANDROID_HOME is not valid."
    }

    if (-not $CheckDevice) { return }

    $adbPath = Get-CommandPath "adb"
    if (-not $adbPath) {
        $candidate = Join-Path $sdkPath "platform-tools\adb.exe"
        if (Test-Path $candidate -PathType Leaf) { $adbPath = $candidate }
    }
    if (-not $adbPath) {
        Add-DoctorResult "FAIL" "adb" "adb was not found."
        return
    }

    $adbResult = Invoke-NativeCommand $adbPath @("devices", "-l")
    if ($adbResult.ExitCode -ne 0) {
        Add-DoctorResult "FAIL" "adb" "adb devices failed."
        return
    }

    $lines = @($adbResult.Output -split "`r?`n" |
        Where-Object { $_ -match "^\S+\s+(device|offline|unauthorized)\b" })
    $ready = @($lines | Where-Object { $_ -match "^\S+\s+device\b" })
    $blocked = @($lines | Where-Object { $_ -match "^\S+\s+(offline|unauthorized)\b" })

    if ($blocked.Count -gt 0) {
        Add-DoctorResult "FAIL" "Android device" "$($blocked.Count) blocked device(s); identifiers hidden."
    }
    if ($ready.Count -gt 0) {
        Add-DoctorResult "PASS" "Android device" "$($ready.Count) ready device(s); identifiers hidden."
    }
    if ($lines.Count -eq 0) {
        Add-DoctorResult "WARN" "Android device" "No emulator or phone is connected."
    }
}

function Show-DoctorResults {
    foreach ($result in $script:DoctorResults) {
        Write-Host ("[{0}] {1}: {2}" -f $result.Status, $result.Check, $result.Detail)
    }
    $fails = @($script:DoctorResults | Where-Object { $_.Status -eq "FAIL" }).Count
    $warns = @($script:DoctorResults | Where-Object { $_.Status -eq "WARN" }).Count
    $passes = @($script:DoctorResults | Where-Object { $_.Status -eq "PASS" }).Count
    Write-Host ""
    Write-Host ("Summary: {0} passed, {1} warning(s), {2} failure(s)." -f $passes, $warns, $fails)
    if ($fails -gt 0) { return 1 }
    return 0
}

function Invoke-Preflight {
    param([switch]$CheckDevice, [switch]$RequireDependencies)
    $script:DoctorResults.Clear()
    Test-ProjectFiles -RequireDependencies:$RequireDependencies
    Test-Node
    Test-Java
    Test-AndroidSdk -CheckDevice:$CheckDevice
    return Show-DoctorResults
}

function Invoke-Doctor {
    Write-Host "Android development environment doctor"
    Write-Host ""
    return Invoke-Preflight -CheckDevice
}

function Invoke-Build {
    Write-Host "Android standalone release build"
    Write-Host ""
    if ((Invoke-Preflight -RequireDependencies) -ne 0) {
        Write-Host ""
        Write-Host "BUILD BLOCKED: fix preflight failures first."
        return 1
    }

    $sdkPath = Find-AndroidSdk
    New-Item -ItemType Directory -Path $ArtifactRoot -Force | Out-Null
    $prebuildLog = Join-Path $ArtifactRoot "prebuild.log"
    $gradleLog = Join-Path $ArtifactRoot "gradle.log"
    $cmd = $env:ComSpec
    if (-not $cmd) {
        Write-Host "BUILD FAILED: Windows command processor was not found."
        return 1
    }

    Write-Host ""
    Write-Host "[1/2] Generating native Android project..."
    $prebuild = Invoke-NativeCommand $cmd @("/d", "/s", "/c", "npx expo prebuild --platform android --clean") $MobileRoot
    Set-Content -LiteralPath $prebuildLog -Value $prebuild.Output -Encoding UTF8
    if ($prebuild.ExitCode -ne 0) {
        Write-Host "BUILD FAILED: Expo prebuild returned exit code $($prebuild.ExitCode)."
        Write-Host "Local raw log: mobile\pii-reviewer\build-artifact\prebuild.log"
        Write-Host "The log may contain local paths; do not share it directly."
        return 1
    }

    $androidRoot = Join-Path $MobileRoot "android"
    $sdkValue = $sdkPath -replace '\\', '/'
    $localProperties = Join-Path $androidRoot "local.properties"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($localProperties, "sdk.dir=$sdkValue`r`n", $utf8NoBom)

    Write-Host "[2/2] Building release APK..."
    $gradle = Invoke-NativeCommand $cmd @("/d", "/s", "/c", "gradlew.bat --no-daemon --console=plain assembleRelease") $androidRoot
    Set-Content -LiteralPath $gradleLog -Value $gradle.Output -Encoding UTF8
    if ($gradle.ExitCode -ne 0) {
        Write-Host "BUILD FAILED: Gradle returned exit code $($gradle.ExitCode)."
        Write-Host "Local raw log: mobile\pii-reviewer\build-artifact\gradle.log"
        Write-Host "The log may contain local paths; do not share it directly."
        return 1
    }

    $sourceApk = Join-Path $androidRoot "app\build\outputs\apk\release\app-release.apk"
    if (-not (Test-Path $sourceApk -PathType Leaf)) {
        Write-Host "BUILD FAILED: Gradle finished without the expected release APK."
        return 1
    }

    $targetApk = Join-Path $ArtifactRoot "PII-Pilot-V2.apk"
    Copy-Item -LiteralPath $sourceApk -Destination $targetApk -Force
    Remove-Item $prebuildLog, $gradleLog -Force -ErrorAction SilentlyContinue
    $hash = (Get-FileHash -LiteralPath $targetApk -Algorithm SHA256).Hash.ToLowerInvariant()

    Write-Host ""
    Write-Host "BUILD READY"
    Write-Host "APK: mobile\pii-reviewer\build-artifact\PII-Pilot-V2.apk"
    Write-Host "SHA256: $hash"
    return 0
}

switch ($Command) {
    "doctor" { exit (Invoke-Doctor) }
    "build" { exit (Invoke-Build) }
    "run" { & (Join-Path $ScriptRoot "android-run.ps1"); exit $LASTEXITCODE }
}
