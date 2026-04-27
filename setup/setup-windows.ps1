# Shrimp Agent v5.0.0 - Windows Setup Script
# Architecture: Agent-based (backend_operator, virtual_human, shared)

Write-Host "Shrimp Agent v5.0.0 - Windows Setup" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "Docker: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Docker not found" -ForegroundColor Red
    Write-Host "Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
}

# Check docker-compose
try {
    $composeVersion = docker-compose --version 2>&1
    Write-Host "Compose: $composeVersion" -ForegroundColor Green
    $composeCmd = "docker-compose"
} catch {
    try {
        $composeVersion = docker compose version 2>&1
        Write-Host "Compose: $composeVersion" -ForegroundColor Green
        $composeCmd = "docker compose"
    } catch {
        Write-Host "Error: docker-compose not found" -ForegroundColor Red
        exit 1
    }
}

# Check .env file
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "Creating .env file..." -ForegroundColor Cyan
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env file" -ForegroundColor Green
        Write-Host ""
        Write-Host "IMPORTANT: Edit .env and add your API_KEY" -ForegroundColor Yellow
        Write-Host "Command: notepad .env" -ForegroundColor Cyan
        Write-Host ""
    } else {
        Write-Host "Warning: .env.example not found" -ForegroundColor Yellow
    }
} else {
    Write-Host ".env file exists" -ForegroundColor Green
}

# Create directories
Write-Host ""
Write-Host "Checking directories..." -ForegroundColor Cyan
if (-not (Test-Path "../workspace")) {
    New-Item -ItemType Directory -Path "../workspace" | Out-Null
    Write-Host "Created ../workspace/" -ForegroundColor Green
}
if (-not (Test-Path "../downloads")) {
    New-Item -ItemType Directory -Path "../downloads" | Out-Null
    Write-Host "Created ../downloads/" -ForegroundColor Green
}
if (-not (Test-Path "../knowledge")) {
    New-Item -ItemType Directory -Path "../knowledge" | Out-Null
    Write-Host "Created ../knowledge/" -ForegroundColor Green
    Write-Host "   Tip: Place your knowledge files in ../knowledge/{knowledge_id}/" -ForegroundColor Gray
}
Write-Host "Directories ready" -ForegroundColor Green

# Check agent files (CRITICAL - required for Docker to work)
Write-Host ""
Write-Host "Checking agent files..." -ForegroundColor Cyan

# New architecture files (v5.0.0)
$agentFiles = @(
    "../agent/backend_operator/api.py",
    "../agent/virtual_human/api.py",
    "../agent/shared/sse_events.py",
    "../session/session_store.py",
    "../frontend/templates/index.html",
    "../frontend/static/js/chat.js"
)
$missingFiles = @()

foreach ($file in $agentFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "ERROR: Agent files not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Missing files:" -ForegroundColor Yellow
    foreach ($file in $missingFiles) {
        Write-Host "  - $file" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Expected directory structure:" -ForegroundColor Cyan
    Write-Host "  agtshrimp/" -ForegroundColor Gray
    Write-Host "  ├── agent/" -ForegroundColor Gray
    Write-Host "  │   ├── backend_operator/  # Agent API" -ForegroundColor Gray
    Write-Host "  │   ├── virtual_human/     # VH Agent" -ForegroundColor Gray
    Write-Host "  │   └── shared/            # Shared modules" -ForegroundColor Gray
    Write-Host "  ├── session/               # Session management" -ForegroundColor Gray
    Write-Host "  ├── frontend/              # Web UI" -ForegroundColor Gray
    Write-Host "  ├── setup/                 # You are here" -ForegroundColor Gray
    Write-Host "  ├── workspace/             # Will be created" -ForegroundColor Gray
    Write-Host "  ├── downloads/             # Will be created" -ForegroundColor Gray
    Write-Host "  └── knowledge/             # Knowledge base" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Solution:" -ForegroundColor Cyan
    Write-Host "1. Use Git clone (recommended):" -ForegroundColor White
    Write-Host "   git clone https://github.com/srjiang/agtshrimp.git" -ForegroundColor White
    Write-Host "   cd agtshrimp" -ForegroundColor White
    Write-Host "   git checkout dev" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Or download ZIP from dev branch:" -ForegroundColor White
    Write-Host "   https://github.com/srjiang/agtshrimp/archive/refs/heads/dev.zip" -ForegroundColor White
    Write-Host ""
    
    exit 1
}

Write-Host "All agent files found" -ForegroundColor Green

# Done
Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env file (add your API_KEY)" -ForegroundColor Yellow
Write-Host "2. $composeCmd up -d --build" -ForegroundColor Yellow
Write-Host ""
Write-Host "Web UI: http://localhost:5000" -ForegroundColor Cyan
Write-Host "Agent API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
