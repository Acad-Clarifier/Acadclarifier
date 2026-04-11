#!/bin/bash
# Quick status check for Docker setup

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   AcadClarifier Docker Setup - Generated Files Summary     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Docker Configuration Files:${NC}"
for file in Dockerfile docker-compose.yml .dockerignore .env.example; do
    if [ -f "$file" ]; then
        size=$(wc -l < "$file")
        echo "  ✓ $file ($size lines)"
    fi
done
echo ""

echo -e "${BLUE}Documentation Files:${NC}"
for file in START_HERE.md QUICK_COMMANDS.md DOCKER_SETUP_SUMMARY.md DEPLOYMENT_GUIDE.md DOCKER_SETUP_INDEX.md; do
    if [ -f "$file" ]; then
        size=$(wc -l < "$file")
        echo "  ✓ $file ($size lines)"
    fi
done
echo ""

echo -e "${BLUE}Automation Scripts:${NC}"
for file in docker-quickstart.ps1 docker-quickstart.sh verify_docker_setup.py; do
    if [ -f "$file" ]; then
        size=$(wc -l < "$file")
        echo "  ✓ $file ($size lines)"
    fi
done
echo ""

echo -e "${GREEN}✓ All files generated successfully!${NC}"
echo ""
echo "Next step: Open START_HERE.md for quick start instructions"
echo "Or run: cat START_HERE.md"
