# Makefile for Docker-based Django deployment
.PHONY: help build up down restart logs shell migrate collectstatic createsuperuser backup restore clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs (all services)"
	@echo "  make logs-backend   - View backend logs"
	@echo "  make logs-nginx     - View nginx logs"
	@echo "  make logs-db        - View database logs"
	@echo "  make shell          - Access Django shell"
	@echo "  make bash           - Access backend container bash"
	@echo "  make migrate        - Run database migrations"
	@echo "  make collectstatic  - Collect static files"
	@echo "  make createsuperuser - Create Django superuser"
	@echo "  make backup         - Backup database"
	@echo "  make restore        - Restore database from backup"
	@echo "  make clean          - Remove containers and volumes"
	@echo "  make rebuild        - Rebuild and restart services"

# Build Docker images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# Restart all services
restart:
	docker-compose restart

# View logs
logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-nginx:
	docker-compose logs -f nginx

logs-db:
	docker-compose logs -f db

# Access Django shell
shell:
	docker-compose exec backend python manage.py shell

# Access backend container
bash:
	docker-compose exec backend bash

# Access database
dbshell:
	docker-compose exec db psql -U sensor_user -d sensor_db

# Run migrations
migrate:
	docker-compose exec backend python manage.py migrate

# Create migrations
makemigrations:
	docker-compose exec backend python manage.py makemigrations

# Collect static files
collectstatic:
	docker-compose exec backend python manage.py collectstatic --noinput

# Create superuser
createsuperuser:
	docker-compose exec backend python manage.py createsuperuser

# Backup database
backup:
	@mkdir -p backups
	docker-compose exec db pg_dump -U sensor_user sensor_db > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in backups/ directory"

# Restore database (usage: make restore FILE=backups/backup_20231201_120000.sql)
restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make restore FILE=backups/backup_file.sql"; \
		exit 1; \
	fi
	docker-compose exec -T db psql -U sensor_user sensor_db < $(FILE)
	@echo "Database restored from $(FILE)"

# Clean up containers and volumes
clean:
	docker-compose down -v
	@echo "All containers and volumes removed"

# Rebuild everything
rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "Services rebuilt and started"

# First time setup
setup:
	@echo "Setting up project for first time..."
	cp .env.example .env
	@echo "Created .env file - please update with your configuration"
	docker-compose build
	docker-compose up -d
	@echo "Waiting for database to be ready..."
	sleep 10
	docker-compose exec backend python manage.py migrate
	docker-compose exec backend python manage.py collectstatic --noinput
	@echo "Setup complete! Create a superuser with: make createsuperuser"

# Run tests
test:
	docker-compose exec backend python manage.py test

# Check deployment readiness
check:
	docker-compose exec backend python manage.py check --deploy

# Show container status
ps:
	docker-compose ps

# Show container stats
stats:
	docker stats

# Update application (pull code, rebuild, migrate)
update:
	git pull origin main
	docker-compose up -d --build
	docker-compose exec backend python manage.py migrate
	docker-compose exec backend python manage.py collectstatic --noinput
	@echo "Application updated successfully"
