# Copy to ci/package-windows.ps1; adapt targets, build layout and installer script.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
cmake -S . -B build/ci -A x64
if ($LASTEXITCODE -ne 0) { throw 'Configure failed' }
cmake --build build/ci --config Release --target PluginName_VST3 PluginName_Standalone --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
# The project's installer script must consume the artefacts built above.
./package-windows.ps1 -Profile licensed
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
New-Item -ItemType Directory -Force dist | Out-Null
Copy-Item build/ci/installer/PluginName-Setup.exe dist/installer.exe
