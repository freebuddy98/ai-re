.PHONY: build build-all push clean test

# 默认目标
all: build-all

# 构建所有服务
build-all:
	@echo "Building all services..."
	./scripts/build_docker.sh --all

# 构建特定服务
build:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Usage: make build SERVICE=service-name"; \
		exit 1; \
	fi
	./scripts/build_docker.sh --service $(SERVICE)

# 构建并推送
push:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Building and pushing all services..."; \
		./scripts/build_docker.sh --all --push; \
	else \
		echo "Building and pushing $(SERVICE)..."; \
		./scripts/build_docker.sh --service $(SERVICE) --push; \
	fi

# 清理Docker镜像
clean:
	@echo "Cleaning up Docker images..."
	docker image prune -f
	docker system prune -f

# 运行集成测试
test-integration:
	@echo "Running integration tests..."
	@if [ -f .env.test ]; then set -a && . ./.env.test && set +a; fi && ./scripts/run_tests.sh --integration

# 运行端到端测试
test-e2e:
	@echo "Running e2e tests..."
	@if [ -f .env.test ]; then set -a && . ./.env.test && set +a; fi && ./scripts/run_tests.sh --e2e

# 运行单元测试
test-unit:
	@echo "Running unit tests..."
	@if [ -f .env.test ]; then set -a && . ./.env.test && set +a; fi && ./scripts/run_tests.sh --unit

# 运行验收测试
test-acceptance:
	@echo "Running acceptance tests..."
	@echo "Ensuring Docker Compose services are running..."
	@docker compose up -d
	@sleep 10
	@echo "Running container acceptance tests..."
	@if [ -f .env.test ]; then set -a && . ./.env.test && set +a; fi && \
		export PATH=$$PATH:/home/yun/.local/bin && \
		pytest tests/acceptance/ -v --tb=short --color=yes \
		--junitxml=test-results/acceptance-test-results.xml \
		--cov-report=html:test-results/acceptance-coverage \
		--cov-report=term-missing || \
		(echo "Acceptance tests failed, cleaning up..."; docker compose down; exit 1)
	@echo "Acceptance tests completed successfully"
	@docker compose down

# 开发环境启动
dev-up:
	docker-compose up -d

# 开发环境停止
dev-down:
	docker-compose down

# 查看日志
logs:
	docker-compose logs -f $(SERVICE) 