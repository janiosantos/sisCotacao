param(
    [Parameter(Mandatory = $true)]
    [string]$Workspace
)

$ErrorActionPreference = "Stop"

docker compose `
    -f (Join-Path $Workspace "docker-compose.yml") `
    -f (Join-Path $Workspace "docker-compose.debug.yml") `
    up -d --build --no-deps backend

if ($LASTEXITCODE -ne 0) {
    throw "Nao foi possivel iniciar o backend com debugpy."
}

$deadline = (Get-Date).AddSeconds(60)
do {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connected = $client.ConnectAsync("127.0.0.1", 5678).Wait(1000)
        if ($connected -and $client.Connected) {
            Write-Host "debugpy pronto em 127.0.0.1:5678"
            exit 0
        }
    }
    catch {
        # O container ainda esta iniciando; tentar novamente ate o limite.
    }
    finally {
        $client.Dispose()
    }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)

throw "debugpy nao abriu a porta 5678 em 60 segundos. Consulte: docker compose logs backend"
