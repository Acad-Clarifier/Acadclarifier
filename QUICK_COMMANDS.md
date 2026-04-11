# ⚡ QUICK REFERENCE - Copy & Paste Commands

## 🚀 START HERE (Windows PowerShell)

```powershell
# 1. Navigate to project
cd "d:\BE Project\Execution\test"

# 2. Create .env file from template
Copy-Item .env.example .env

# 3. Open and edit .env (change DB_PASSWORD!)
notepad .env

# 4. Start everything
.\docker-quickstart.ps1 -Command up

# ✅ Done! Visit: http://localhost:5000
```

---

## 🔄 Common Commands

```powershell
# View status
docker compose ps

# View logs (live)
docker compose logs -f backend

# Stop everything
docker compose down

# Restart backend
docker compose restart backend

# Initialize database (first time only)
docker compose exec backend flask db upgrade

# Access database shell
docker compose exec db psql -U postgres -d acadclarifier

# Full rebuild (if changes to requirements.txt)
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## 🐧 START HERE (Linux/macOS)

```bash
# 1. Navigate to project
cd /path/to/BE\ Project/Execution/test

# 2. Create .env file from template
cp .env.example .env

# 3. Edit .env (change DB_PASSWORD!)
nano .env

# 4. Start everything
bash docker-quickstart.sh up

# ✅ Done! Visit: http://localhost:5000
```

---

## 🔍 Monitoring & Debugging

```powershell
# Full service logs
docker compose logs --tail 100

# Backend logs only
docker compose logs backend

# Database logs
docker compose logs db

# Follow logs live
docker compose logs -f

# Check specific service
docker compose exec backend echo "Backend is running"

# Test API
$response = Invoke-RestMethod -Uri "http://localhost:5000/api/books" -UseBasicParsing
$response | ConvertTo-Json
```

---

## 🛠️ Database Operations

```powershell
# Run migrations
docker compose exec backend flask db upgrade

# Seed sample data
docker compose exec backend python -c "from apps.backend.seeds import seed_books; seed_books()"

# Access PostgreSQL CLI
docker compose exec db psql -U postgres -d acadclarifier

# Run SQL query
docker compose exec db psql -U postgres -d acadclarifier -c "SELECT * FROM books LIMIT 5;"

# Backup database
docker compose exec db pg_dump -U postgres -d acadclarifier > backup.sql

# Restore from backup
docker compose exec -T db psql -U postgres -d acadclarifier < backup.sql
```

---

## 🐳 Docker Image Operations

```powershell
# Build only
docker compose build

# Build without cache (for clean rebuild)
docker compose build --no-cache

# View image size
docker images acadclarifier

# Show build layers
docker history acadclarifier:latest

# Inspect image
docker inspect acadclarifier:latest
```

---

## 🧹 Cleanup

```powershell
# Stop services but keep data
docker compose down

# Stop and remove all data (CAREFUL!)
docker compose down -v

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Full cleanup (NUCLEAR OPTION)
docker system prune -a --volumes
```

---

## 🐛 Troubleshooting

```powershell
# Show all services
docker compose ps

# Show detailed config
docker compose config

# Check environment variables in container
docker compose exec backend env | findstr DB_

# View container file system
docker compose exec backend ls -la /app

# Port conflict? Find process
netstat -ano | findstr :5000

# Kill process (replace PID)
taskkill /PID <PID> /F

# Verify Docker daemon running
docker ps

# Check Docker version
docker --version
docker compose version
```

---

## 📊 Health Checks

```powershell
# API health check
curl http://localhost:5000/health

# Database connection
docker compose exec backend psql -U postgres -d acadclarifier -c "SELECT 1"

# Check all services
docker compose ps

# View service logs for errors
docker compose logs --tail 50 | findstr ERROR

# Memory usage
docker stats

# Network connectivity
docker network ls
docker network inspect acadclarifier_acadclarifier_network
```

---

## 📝 File Reference

| File                      | Created | Purpose                  |
| ------------------------- | ------- | ------------------------ |
| `Dockerfile`              | ✅      | Multi-stage Python image |
| `docker-compose.yml`      | ✅      | Service orchestration    |
| `.dockerignore`           | ✅      | Build exclusions         |
| `.env.example`            | ✅      | Config template          |
| `docker-quickstart.sh`    | ✅      | Linux/macOS script       |
| `docker-quickstart.ps1`   | ✅      | Windows script           |
| `DEPLOYMENT_GUIDE.md`     | ✅      | Full documentation       |
| `DOCKER_SETUP_SUMMARY.md` | ✅      | Architecture overview    |

---

## 🎯 Typical Workflow

```powershell
# Day 1: Initial setup
Copy-Item .env.example .env
notepad .env                                    # Update DB_PASSWORD
.\docker-quickstart.ps1 -Command up
docker compose exec backend flask db upgrade

# Day 2-N: Development
# Play with code, then:
docker compose restart backend

# Editing requirements.txt?
docker compose build
docker compose up -d


# Deploying?
docker compose ps
docker compose logs -f backend
# Verify everything works, then push to registry
```

---

## 🚨 Emergency Commands

```powershell
# Something broke? Factory reset
docker compose down -v
docker compose build --no-cache
docker compose up -d
docker compose exec backend flask db upgrade

# Database locked?
docker compose restart db

# Image corrupted?
docker compose down
docker image rm acadclarifier:latest
docker compose build
docker compose up -d

# Port stuck?
Get-NetTCPConnection -LocalPort 5000
Stop-Process -Id <PID> -Force
```

---

## 🎓 Learning Resources

- Full guide: Read `DEPLOYMENT_GUIDE.md`
- Architecture: Read `DOCKER_SETUP_SUMMARY.md`
- Docker docs: https://docs.docker.com/
- Troubleshooting: `docker compose logs -f` (usually shows problems)

---

**Most common issues solved by:**

```powershell
docker compose down
docker compose up -d
docker compose logs -f backend  # Then wait 30 seconds for model loading
```

---

**Questions?** Check the logs! → `docker compose logs -f`

**Files created:** 12 ✅ | Ready for production: Yes ✅ | Copy-paste ready: Yes ✅
