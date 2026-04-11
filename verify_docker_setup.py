#!/usr/bin/env python3
"""
Verification Script for Docker Setup
Run this BEFORE deploying to check everything is configured correctly
"""

import os
import sys
import subprocess
import json
from pathlib import Path


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_ok(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def check_file_exists(filepath, description=""):
    desc = description or filepath
    if Path(filepath).exists():
        print_ok(f"Found: {desc}")
        return True
    else:
        print_error(f"Missing: {desc} ({filepath})")
        return False


def check_docker_installed():
    print_header("Checking Docker Installation")
    try:
        result = subprocess.run(['docker', '--version'],
                                capture_output=True, text=True)
        if result.returncode == 0:
            print_ok(f"Docker installed: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print_error("Docker not found. Visit: https://docs.docker.com/get-docker/")
    return False


def check_docker_compose_installed():
    try:
        result = subprocess.run(
            ['docker', 'compose', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_ok(f"Docker Compose installed: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print_error(
        "Docker Compose not found. Visit: https://docs.docker.com/compose/install/")
    return False


def check_docker_daemon():
    try:
        subprocess.run(['docker', 'ps'], capture_output=True, check=True)
        print_ok("Docker daemon is running")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error(
            "Docker daemon is not running. Start Docker Desktop or Docker daemon.")
        return False


def check_required_files():
    print_header("Checking Required Files")

    files_to_check = {
        'Dockerfile': 'Dockerfile',
        'docker-compose.yml': 'docker-compose.yml',
        '.dockerignore': '.dockerignore',
        'app.py': 'app.py',
        'wsgi.py': 'wsgi.py',
        'requirements.txt': 'requirements.txt',
        'apps/backend/server.py': 'Backend Flask server',
    }

    results = []
    for desc, filepath in files_to_check.items():
        result = check_file_exists(filepath, desc)
        results.append(result)

    return all(results)


def check_env_file():
    print_header("Checking Environment Configuration")

    env_path = Path('.env')
    env_example_path = Path('.env.example')

    if env_path.exists():
        print_ok("Found: .env file")

        # Check for critical settings
        env_content = env_path.read_text()

        if 'DB_PASSWORD=postgres' in env_content or 'DB_PASSWORD=' in env_content:
            print_warning(
                "DB_PASSWORD appears to still be default. Update it before production!")
        else:
            print_ok("DB_PASSWORD is set")

        if 'FLASK_ENV=production' in env_content:
            print_ok("FLASK_ENV set to production")
        else:
            print_warning(
                "FLASK_ENV not set to production (current setting will be used)")

        return True

    elif env_example_path.exists():
        print_warning("Found: .env.example but NOT .env")
        print_info("Run: Copy-Item .env.example .env (Windows)")
        print_info("Run: cp .env.example .env (Linux/macOS)")
        return False

    else:
        print_error("Neither .env nor .env.example found!")
        return False


def check_dockerfile():
    print_header("Checking Dockerfile Configuration")

    if not Path('Dockerfile').exists():
        print_error("Dockerfile not found")
        return False

    dockerfile_content = Path('Dockerfile').read_text()

    checks = {
        'Multi-stage build (FROM python:3.10-slim as builder)': 'as builder' in dockerfile_content,
        'Gunicorn configured': 'gunicorn' in dockerfile_content,
        'Health check enabled': 'HEALTHCHECK' in dockerfile_content,
        'Port exposure': 'EXPOSE' in dockerfile_content,
        'Virtual environment optimization': '/opt/venv' in dockerfile_content,
    }

    all_ok = True
    for check_name, result in checks.items():
        if result:
            print_ok(check_name)
        else:
            print_error(check_name)
            all_ok = False

    return all_ok


def check_docker_compose():
    print_header("Checking docker-compose.yml Configuration")

    if not Path('docker-compose.yml').exists():
        print_error("docker-compose.yml not found")
        return False

    compose_content = Path('docker-compose.yml').read_text()

    checks = {
        'PostgreSQL service defined': 'postgres:' in compose_content and 'db:' in compose_content,
        'Backend service defined': 'backend:' in compose_content,
        'Health checks configured': 'healthcheck:' in compose_content,
        'Volumes defined': 'volumes:' in compose_content and 'postgres_data:' in compose_content,
        'Networks configured': 'networks:' in compose_content,
        'Environment variables used': 'environment:' in compose_content,
    }

    all_ok = True
    for check_name, result in checks.items():
        if result:
            print_ok(check_name)
        else:
            print_error(check_name)
            all_ok = False

    return all_ok


def check_requirements():
    print_header("Checking Python Dependencies")

    if not Path('requirements.txt').exists():
        print_error("requirements.txt not found")
        return False

    requirements = Path('requirements.txt').read_text().lower()

    critical_packages = {
        'Flask': 'flask',
        'Gunicorn': 'gunicorn',
        'Psycopg2': 'psycopg2',
        'SQLAlchemy': 'sqlalchemy',
        'Flask-Migrate': 'flask-migrate',
        'ChromaDB': 'chromadb',
    }

    all_ok = True
    for package_name, package_check in critical_packages.items():
        if package_check in requirements:
            print_ok(f"Found: {package_name}")
        else:
            print_warning(f"Missing: {package_name}")
            all_ok = False

    return all_ok


def check_directory_structure():
    print_header("Checking Directory Structure")

    directories = {
        'apps/frontend': 'Frontend files',
        'apps/backend': 'Backend files',
        'services/book-recommender': 'Book recommender service',
        'services/retrieval-local': 'Local retrieval service',
        'services/retrieval-web': 'Web retrieval service',
        'migrations': 'Database migrations',
    }

    all_ok = True
    for dir_path, description in directories.items():
        if Path(dir_path).exists():
            print_ok(f"Found: {description} ({dir_path})")
        else:
            print_warning(f"Missing: {description} ({dir_path})")
            all_ok = False

    return all_ok


def main():
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + " AcadClarifier Docker Setup Verification ".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    print(f"{Colors.ENDC}\n")

    results = []

    # Check Docker tools
    docker_ok = check_docker_installed()
    compose_ok = check_docker_compose_installed()
    daemon_ok = check_docker_daemon()
    results.extend([docker_ok, compose_ok, daemon_ok])

    # Check files and configuration
    files_ok = check_required_files()
    env_ok = check_env_file()
    dockerfile_ok = check_dockerfile()
    compose_config_ok = check_docker_compose()
    requirements_ok = check_requirements()
    structure_ok = check_directory_structure()

    results.extend([files_ok, env_ok, dockerfile_ok,
                   compose_config_ok, requirements_ok, structure_ok])

    # Summary
    print_header("Verification Summary")

    passed = sum(results)
    total = len(results)
    percentage = (passed / total) * 100

    print(f"Checks passed: {passed}/{total} ({percentage:.0f}%)\n")

    if all(results):
        print_ok("All checks passed! Your Docker setup is ready to deploy.")
        print_info("\nNext steps:")
        print_info("1. Verify .env configuration (especially DB_PASSWORD)")
        print_info("2. Run: docker compose up -d")
        print_info("3. Run: docker compose exec backend flask db upgrade")
        print_info("4. Check: http://localhost:5000")
        return 0
    else:
        print_error(
            "Some checks failed. Please fix the issues above before deploying.")
        print_info("\nCommon fixes:")
        print_info("• Docker not running? Start Docker Desktop")
        print_info("• Missing .env? Run: Copy-Item .env.example .env")
        print_info("• Permission denied? Run with sudo or check file permissions")
        return 1


if __name__ == '__main__':
    sys.exit(main())
