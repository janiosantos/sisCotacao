# Build e deploy Docker
param([switch]$Prod)

$src = "C:\Users\jpsantos\Documents\Projetos\ecommerce_scraper"

if ($Prod) {
    Write-Host "=== BUILD PRODUÇÃO ==="
    docker compose -f "$src\docker-compose.prod.yml" up --build -d
    Write-Host "Frontend: http://localhost:80"
    Write-Host "Backend:  http://localhost:8000"
} else {
    Write-Host "=== BUILD DESENVOLVIMENTO ==="
    # Prepara contexto mínimo para o backend
    $tmp = "$env:TEMP\docker_build_backend"
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path "$tmp\catalog_server" -Force | Out-Null
    New-Item -ItemType Directory -Path "$tmp\app" -Force | Out-Null
    Copy-Item "$src\catalog_server\*" "$tmp\catalog_server\" -Recurse -Exclude "data"
    Copy-Item "$src\app\*" "$tmp\app\" -Recurse
    Copy-Item "$src\catalog_server\Dockerfile" "$tmp\"
    Write-Host "Contexto: $([math]::Round((Get-ChildItem -Recurse $tmp -File | Measure-Object Length -Sum).Sum / 1KB)) KB"
    docker build -t ecommerce_scraper-backend -f "$tmp\Dockerfile" $tmp
    docker compose -f "$src\docker-compose.yml" up -d --force-recreate backend
    Write-Host "Frontend: http://localhost:5173"
    Write-Host "Backend:  http://localhost:8000"
}
