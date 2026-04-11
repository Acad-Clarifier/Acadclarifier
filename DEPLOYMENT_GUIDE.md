# AcadClarifier - Docker Deployment Guide

## Prerequisites

Ensure you have installed:

- **Docker** (version 20.10+) - [Install](https://docs.docker.com/get-docker/)
- **Docker Compose** (version 2.0+) - [Install](https://docs.docker.com/compose/install/)
- **Git** (to clone/pull the repository)

For Windows:

```powershell
# Verify installation
docker --version      # Docker version 20.10.0 or higher
docker compose version # Docker Compose version 2.0 or higher
```

---

## Quick Start (One Command)

```bash
# Navigate to project root
cd "d:\BE Project\Execution\test"

# Create .env file from example (IMPORTANT!)
cp .env.example .env
# Edit .env with your settings (passwords, API keys, etc.)

# Start everything
docker compose up -d

# Check status
docker compose ps
```

Done! Your app is running:

- **Backend API:** http://localhost:5000
- **Frontend:** http://localhost:8501 (if accessible)
- **Database:** localhost:5432

---

## Detailed Setup Instructions

### Step 1: Prepare Environment File

```bash
# Create .env from template
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Windows (PowerShell)
notepad .env

# Linux/macOS
nano .env
```

**Critical settings to update:**

```env
DB_PASSWORD=YourSecurePassword123!  # Change this!
GOOGLE_API_KEY=your_actual_key      # If using Google AI
TAVILY_API_KEY=your_actual_key      # If using web retrieval
FLASK_ENV=production                # Set to production
```

### Step 2: Build the Docker Image

```bash
# Option A: Build with docker-compose (recommended)
docker compose build

# Option B: Build manually
docker build -t acadclarifier:latest .

# Option B (show build progress):
docker build --progress=plain -t acadclarifier:latest .
```

**Build time estimates:**

- First build (initial dependencies): **3-5 minutes**
- Subsequent builds (cached layers): **10-30 seconds**

### Step 3: Start Services

```bash
# Start all services in background
docker compose up -d

# Check if services are running
docker compose ps

# View real-time logs
docker compose logs -f backend db

# Stop following logs
# Press Ctrl+C

# Stop services
docker compose down

# Stop and remove all data (WARNING: deletes database!)
docker compose down -v
```

### Step 4: Database Setup (First Run Only)

```bash
# Initialize database tables and run migrations
docker compose exec backend flask db upgrade

# Optional: Seed sample data
docker compose exec backend python -c "from apps.backend.seeds import seed_books; seed_books()"
```

---

## Testing the Deployment

### Health Checks

```bash
# Check if backend is responding
curl http://localhost:5000/health

# Check database connection
docker compose exec backend psql -U postgres -d acadclarifier -c "SELECT 1"
```

### API Testing

```powershell
# Windows PowerShell - Test backend API
$uri = "http://localhost:5000/api/books"
$response = Invoke-RestMethod -Uri $uri -UseBasicParsing
$response | ConvertTo-Json

# Or with curl (if installed)
curl http://localhost:5000/api/books
```

### View Logs

```bash
# Backend logs
docker compose logs backend

# Database logs
docker compose logs db

# Follow logs in real-time
docker compose logs -f

# Limit to last 50 lines
docker compose logs --tail 50
```

---

## Common Operations

### Restart Services

```bash
# Restart backend only
docker compose restart backend

# Restart all
docker compose restart

# Hard restart (stop + start)
docker compose down && docker compose up -d
```

### Access Database Directly

```bash
# Connect to PostgreSQL
docker compose exec db psql -U postgres -d acadclarifier

# Run SQL commands
docker compose exec db psql -U postgres -d acadclarifier -c "SELECT * FROM books LIMIT 5;"

# Exit psql
\q
```

### Access Application Shell

```bash
# Python shell with app context
docker compose exec backend python

# Flask shell (if available)
docker compose exec backend flask shell

# Bash in backend container
docker compose exec backend /bin/bash
```

### View Persistent Data

```bash
# List volumes
docker volume ls | grep acadclarifier

# Check ChromaDB data
docker compose exec backend ls -la /app/services/book-recommender/chroma_data/

# Check retrieval outputs
docker compose exec backend ls -la /app/services/retrieval-local/outputs/
```

---

## Troubleshooting

### Issue: "docker: command not found"

**Solution:** Docker is not installed or not in PATH.

```bash
# Install Docker Desktop (Windows/macOS)
# https://docs.docker.com/get-docker/

# Or install Docker Engine (Linux)
sudo apt-get install docker.io
sudo usermod -aG docker $USER
```

### Issue: Port Already in Use

**Error:** `bind: address already in use`

```bash
# Find process using port 5000
netstat -ano | findstr :5000  # Windows PowerShell

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or change ports in docker-compose.yml
# Modify: BACKEND_PORT=5000 -> BACKEND_PORT=5001
```

### Issue: Database Connection Failed

**Error:** `psycopg2.OperationalError`

```bash
# Check if database service is healthy
docker compose ps

# Verify DB environment variables
docker compose exec backend env | grep DB_

# Check database logs
docker compose logs db

# Restart database
docker compose restart db
docker compose exec backend flask db upgrade
```

### Issue: Out of Memory During Build

**Solution:** This is common with PyTorch and transformers

```bash
# Increase Docker memory in settings:
# Docker Desktop -> Preferences -> Resources -> Memory: 4GB or more

# Or build with reduced parallelism
docker compose build --build-arg PIP_ARGS="--no-cache"
```

### Issue: Changes Not Reflected

```bash
# Rebuild image with fresh layers
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Issue: Slow Inference / Model Loading

First run will be slow due to model caching:

- Sentence-transformers: ~500MB download
- ChromaDB: Initial vectorization
- IMPORTANT: This is expected! Subsequent requests are fast.

```bash
# Monitor progress
docker compose logs -f backend | grep -E "downloading|Loading"
```

---

## Environment Variables Reference

| Variable         | Default       | Purpose                            |
| ---------------- | ------------- | ---------------------------------- |
| `DB_USER`        | postgres      | Database username                  |
| `DB_PASSWORD`    | postgres      | **Change this!** Database password |
| `DB_NAME`        | acadclarifier | Database name                      |
| `DB_PORT`        | 5432          | PostgreSQL port                    |
| `FLASK_ENV`      | production    | Flask environment                  |
| `BACKEND_PORT`   | 5000          | Backend API port                   |
| `FRONTEND_PORT`  | 8501          | Frontend port (optional)           |
| `GOOGLE_API_KEY` | (empty)       | Google AI API key (optional)       |
| `TAVILY_API_KEY` | (empty)       | Tavily API key (optional)          |

---

## Production Checklist

- [ ] Changed `DB_PASSWORD` in `.env`
- [ ] Set `FLASK_ENV=production`
- [ ] Added `GOOGLE_API_KEY` and `TAVILY_API_KEY` if needed
- [ ] Tested database migrations: `docker compose exec backend flask db upgrade`
- [ ] Tested API endpoint: `curl http://localhost:5000/api/books`
- [ ] Verified logs: `docker compose logs -f`
- [ ] Set up log rotation in docker-compose.yml (already done!)
- [ ] Backed up `.env` file securely
- [ ] **DO NOT commit .env with secrets to Git**

---

## Cleanup & Decommissioning

```bash
# Stop services but keep data
docker compose down

# Stop and remove everything (WARNING: deletes database!)
docker compose down -v

# Remove unused images
docker image prune

# Remove all containers, images, networks (DANGER!)
docker system prune -a --volumes
```

---

## Next Steps

### Scaling

- Increase Gunicorn workers: Edit Dockerfile `--workers 4` → higher number
- Use external load balancer in front of Docker

### Monitoring

- Add Prometheus + Grafana for metrics
- Add ELK Stack for centralized logging

### Deployment Platforms

- **AWS ECS:** Push to ECR, deploy via ECS
- **Google Cloud Run:** `docker push` and deploy
- **Azure Container Instances:** Push to ACR
- **Kubernetes:** Use Helm charts (convert docker-compose first)

### CI/CD Integration

- GitHub Actions / GitLab CI to auto-build on push
- Deploy automatically to staging/production

---

## Support

For issues:

1. Check logs: `docker compose logs --tail 100`
2. Verify .env: `docker compose config`
3. Test connectivity: `docker compose exec backend python -c "import apps.backend.db; print('Database OK')"`
4. Check requirements.txt is compatible with Python 3.10

---

**Last Updated:** April 2026  
**Docker Version:** 20.10+  
**Docker Compose Version:** 2.0+
