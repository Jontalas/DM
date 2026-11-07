param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8181
)

# Local test database only. Existing listeners are never stopped or reused.
$ErrorActionPreference = 'Stop'
$testRoot = Split-Path -Parent $PSScriptRoot
$testRules = Join-Path $testRoot 'firestore.rules'
$testJar = Join-Path $testRoot '.deps/firebase-emulators/cloud-firestore-emulator-v1.21.0.jar'
$testJava = Join-Path $testRoot '.deps/java21/jdk-21.0.12.1+1-jre/bin/java.exe'
if (-not (Test-Path -LiteralPath $testJar)) {
    throw 'Falta el emulador local de Firestore en .deps/firebase-emulators.'
}
if (-not (Test-Path -LiteralPath $testJava)) {
    $testJava = (Get-Command java -ErrorAction Stop).Source
}
$testSocket = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
try {
    $testSocket.Start()
} catch {
    throw "El puerto local $Port no esta disponible. Usa otro puerto; este lanzador no detiene procesos."
} finally {
    $testSocket.Stop()
}
Write-Output "Emulador de pruebas con firestore.rules: 127.0.0.1:$Port (demo-cronicas-tests)."
& $testJava -jar $testJar --host=127.0.0.1 "--port=$Port" "--rules=$testRules" --project_id=demo-cronicas-tests --single_project_mode=true
exit $LASTEXITCODE
