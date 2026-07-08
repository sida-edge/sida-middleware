NETWORK_NAME=sida-edge-net

init-network:
	@docker network inspect $(NETWORK_NAME) > /dev/null 2>&1 || docker network create $(NETWORK_NAME)
	@echo "Network $(NETWORK_NAME) is ready."

up-infra: init-network
	docker compose -f infra/docker-compose.yml up -d

up-apps: up-infra
	docker compose -f middleware/docker-compose.yml up -d --build
	docker compose -f memory/docker-compose.yml up -d --build

start: up-apps
	@echo "SIDA services are up and running."

stop:
	docker compose -f middleware/docker-compose.yml down
	docker compose -f memory/docker-compose.yml down
	docker compose -f infra/docker-compose.yml down
	@echo "SIDA services have been stopped."
