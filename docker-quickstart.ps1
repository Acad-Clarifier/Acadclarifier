@echo off
REM AcadClarifier Docker Quick Start Script (Windows PowerShell version)
REM Usage: .\docker-quickstart.ps1 -Command up|down|logs|build|clean

param(
    [Parameter(Position=0)]
    [ValidateSet('up', 'down', 'logs', 'build', 'clean', 'health', 'status')]
    [string]$Command = 'up'
)

$ErrorActionPreference = "Stop"

$PROJECT_NAME = "acadclarifier"
$COMPOSE_FILE = "docker-compose.yml"
$ENV_FILE = ".env"
$ENV_EXAMPLE = ".env.example"

function Write-Header {
    param([string]$Message)
    Write-Host "=== $Message ===" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "WARNING: $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Check-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    try {
        $dockerVersion = docker --version
        Write-Success "Docker installed: $dockerVersion"
    } catch {
        Write-Error "Docker not found. Install from https://docs.docker.com/get-docker/"
        exit 1
    }
    
    try {
        $composeVersion = docker compose version
        Write-Success "Docker Compose installed: $composeVersion"
    } catch {
        Write-Error "Docker Compose not found. Install https://docs.docker.com/compose/install/"
        exit 1
    }
}

function Setup-Env {
    if (-not (Test-Path $ENV_FILE)) {
        if (-not (Test-Path $ENV_EXAMPLE)) {
            Write-Error ".env.example not found!"
            exit 1
        }
        
        Write-Warning ".env not found. Creating from .env.example..."
        Copy-Item $ENV_EXAMPLE $ENV_FILE
        Write-Warning "IMPORTANT: Edit .env with your configuration!"
        Write-Warning "Then run: .\docker-quickstart.ps1 -Command up"
        exit 0
    }
    Write-Success ".env file exists"
}

function Build-Image {
    Write-Header "Building Docker Image"
    docker compose -f $COMPOSE_FILE build
    Write-Success "Image built successfully"
}

function Start-Services {
    Write-Header "Starting Services"
    docker compose -f $COMPOSE_FILE up -d
    
    Write-Warning "Waiting for services to be healthy..."
    Start-Sleep -Seconds 15
    
    docker compose -f $COMPOSE_FILE ps
    
    Write-Host ""
    Write-Success "Services started!"
    Write-Host ""
    Write-Header "Access Your Application"
    Write-Host "  Backend API: http://localhost:5000"
    Write-Host "  Frontend:   http://localhost:8501"
    Write-Host "  Database:   localhost:5432"
    Write-Host ""
    Write-Host "View logs:     .\docker-quickstart.ps1 -Command logs"
    Write-Host "Stop services: .\docker-quickstart.ps1 -Command down"
}

function Initialize-Database {
    Write-Header "Initializing Database"
    
    Write-Host "Running migrations..."
    docker compose -f $COMPOSE_FILE exec -T backend flask db upgrade
    
    Write-Success "Database initialized"
}

function Stop-Services {
    Write-Header "Stopping Services"
    docker compose -f $COMPOSE_FILE down
    Write-Success "Services stopped"
}

function Show-Logs {
    docker compose -f $COMPOSE_FILE logs --tail 100 -f
}

function Clean-All {
    Write-Header "Cleaning Up (WARNING: Removes all data!)"
    Write-Warning "Press Ctrl+C within 5 seconds to cancel..."
    Start-Sleep -Seconds 5
    
    docker compose -f $COMPOSE_FILE down -v
    Write-Success "Cleaned up all services and volumes"
}

function Health-Check {
    Write-Header "Health Check"
    
    Write-Host "Checking Docker..."
    docker compose -f $COMPOSE_FILE ps
    
    Write-Host ""
    Write-Host "Checking backend health..."
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing -ErrorAction SilentlyContinue
        Write-Success "Backend is healthy"
    } catch {
        Write-Warning "Backend is not responding on :5000"
    }
}

# Main logic
switch ($Command) {
    'up' {
        Check-Prerequisites
        Setup-Env
        Build-Image
        Start-Services
        Initialize-Database
        Health-Check
    }
    'down' {
        Stop-Services
    }
    'logs' {
        Show-Logs
    }
    'build' {
        Check-Prerequisites
        Build-Image
    }
    'clean' {
        Clean-All
    }
    'health' {
        Health-Check
    }
    'status' {
        docker compose -f $COMPOSE_FILE ps
    }
}
