# Ansible Custom EE Builder Makefile

# デフォルト設定
EE_FILE ?= execution-environment.yml
TAG ?= latest
REGISTRY ?= localhost
IMAGE_NAME ?= ansible-custom-ee
CONTAINER_RUNTIME ?= podman

# 環境変数
VERBOSE ?= 0
PUSH ?= 0

# カラー定義
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
BOLD = \033[1m
NC = \033[0m

# ヘルプターゲット
.PHONY: help
help: ## このヘルプメッセージを表示
	@echo "$(BOLD)Ansible Custom EE Builder$(NC)"
	@echo ""
	@echo "使用可能なターゲット:"
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(BLUE)%-15s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BOLD)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(BOLD)使用例:$(NC)"
	@echo "  make build                    # 基本的なビルド"
	@echo "  make build EE_FILE=custom.yml # カスタムEEファイルでビルド"
	@echo "  make build TAG=v1.0.0         # 特定のタグでビルド"
	@echo "  make test                     # テストの実行"
	@echo "  make push REGISTRY=docker.io  # レジストリへのプッシュ"
	@echo ""
	@echo "$(BOLD)環境変数:$(NC)"
	@echo "  EE_FILE=$(EE_FILE)"
	@echo "  TAG=$(TAG)"
	@echo "  REGISTRY=$(REGISTRY)"
	@echo "  IMAGE_NAME=$(IMAGE_NAME)"
	@echo "  CONTAINER_RUNTIME=$(CONTAINER_RUNTIME)"

##@ セットアップ
.PHONY: setup
setup: ## 開発環境のセットアップ
	@echo "$(BLUE)[INFO]$(NC) Setting up development environment..."
	@python -m pip install --upgrade pip
	@pip install -r requirements-dev.txt
	@echo "$(GREEN)[SUCCESS]$(NC) Development environment setup completed"

.PHONY: check-deps
check-deps: ## 依存関係のチェック
	@echo "$(BLUE)[INFO]$(NC) Checking dependencies..."
	@command -v $(CONTAINER_RUNTIME) >/dev/null 2>&1 || { echo "$(RED)[ERROR]$(NC) $(CONTAINER_RUNTIME) not found"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "$(RED)[ERROR]$(NC) python3 not found"; exit 1; }
	@if command -v ansible-builder >/dev/null 2>&1; then \
		echo "$(GREEN)[INFO]$(NC) ansible-builder found"; \
	else \
		echo "$(YELLOW)[WARN]$(NC) ansible-builder not found (install with: pip install ansible-builder)"; \
	fi
	@echo "$(GREEN)[SUCCESS]$(NC) Core dependencies available"

##@ ビルド
.PHONY: build
build: check-deps ## EEのビルド
	@echo "$(BLUE)[INFO]$(NC) Building Execution Environment..."
	@echo "  EE File: $(EE_FILE)"
	@echo "  Tag: $(REGISTRY)/$(IMAGE_NAME):$(TAG)"
	@echo "  Runtime: $(CONTAINER_RUNTIME)"
	@./scripts/build-local.sh \
		--file "$(EE_FILE)" \
		--tag "$(TAG)" \
		--registry "$(REGISTRY)" \
		--runtime "$(CONTAINER_RUNTIME)" \
		$(if $(filter 1,$(VERBOSE)),--verbose) \
		$(if $(filter 1,$(PUSH)),--push)

.PHONY: build-all
build-all: ## 複数のベースイメージでビルド
	@echo "$(BLUE)[INFO]$(NC) Building with multiple base images..."
	@$(MAKE) build EE_FILE=execution-environment.yml TAG=rhel9-$(TAG)
	@sed 's|registry.redhat.io/ansible-automation-platform-24/ee-minimal-rhel9:latest|quay.io/ansible/creator-ee:latest|' execution-environment.yml > ee-creator.yml
	@$(MAKE) build EE_FILE=ee-creator.yml TAG=creator-$(TAG)
	@rm -f ee-creator.yml

##@ テスト
.PHONY: test
test: ## ビルドされたEEのテスト
	@echo "$(BLUE)[INFO]$(NC) Testing built EE..."
	@$(CONTAINER_RUNTIME) run --rm "$(REGISTRY)/$(IMAGE_NAME):$(TAG)" ansible --version
	@$(CONTAINER_RUNTIME) run --rm "$(REGISTRY)/$(IMAGE_NAME):$(TAG)" ansible-galaxy collection list
	@$(CONTAINER_RUNTIME) run --rm "$(REGISTRY)/$(IMAGE_NAME):$(TAG)" python3 -c "import sys; print(f'Python {sys.version}')"
	@echo "$(GREEN)[SUCCESS]$(NC) EE tests passed"

.PHONY: test-collections
test-collections: ## インストールされたコレクションのテスト
	@echo "$(BLUE)[INFO]$(NC) Testing installed collections..."
	@$(CONTAINER_RUNTIME) run --rm "$(REGISTRY)/$(IMAGE_NAME):$(TAG)" \
		ansible-doc -l ansible.posix 2>/dev/null | head -5 || echo "ansible.posix collection not available"
	@$(CONTAINER_RUNTIME) run --rm "$(REGISTRY)/$(IMAGE_NAME):$(TAG)" \
		ansible-doc -l community.general 2>/dev/null | head -5 || echo "community.general collection not available"

##@ プッシュ
.PHONY: push
push: ## レジストリへのプッシュ
	@echo "$(BLUE)[INFO]$(NC) Pushing to registry: $(REGISTRY)"
	@$(CONTAINER_RUNTIME) push "$(REGISTRY)/$(IMAGE_NAME):$(TAG)"
	@echo "$(GREEN)[SUCCESS]$(NC) Push completed"

.PHONY: push-all
push-all: ## 全てのタグをプッシュ
	@echo "$(BLUE)[INFO]$(NC) Pushing all tags to registry..."
	@$(CONTAINER_RUNTIME) push "$(REGISTRY)/$(IMAGE_NAME):$(TAG)"
	@$(CONTAINER_RUNTIME) push "$(REGISTRY)/$(IMAGE_NAME):latest"
	@echo "$(GREEN)[SUCCESS]$(NC) All tags pushed"

##@ ユーティリティ
.PHONY: clean
clean: ## ビルドアーティファクトのクリーンアップ
	@echo "$(BLUE)[INFO]$(NC) Cleaning up build artifacts..."
	@rm -rf context/
	@rm -rf artifacts/
	@rm -f navigator.log
	@rm -f ee-*.yml
	@echo "$(GREEN)[SUCCESS]$(NC) Cleanup completed"

.PHONY: clean-images
clean-images: ## ローカルのEEイメージを削除
	@echo "$(BLUE)[INFO]$(NC) Removing local EE images..."
	@$(CONTAINER_RUNTIME) images --format "{{.Repository}}:{{.Tag}}" | \
		grep "$(IMAGE_NAME)" | \
		xargs -r $(CONTAINER_RUNTIME) rmi -f || true
	@echo "$(GREEN)[SUCCESS]$(NC) Local images removed"

.PHONY: check-base
check-base: ## ベースイメージの更新確認
	@echo "$(BLUE)[INFO]$(NC) Checking base image updates..."
	@./scripts/check-base-images.sh --verbose

.PHONY: generate-config
generate-config: ## ansible-navigator.ymlの生成
	@echo "$(BLUE)[INFO]$(NC) Generating ansible-navigator.yml..."
	@python scripts/generate-navigator-config.py \
		--ee-file "$(EE_FILE)" \
		--image "$(REGISTRY)/$(IMAGE_NAME):$(TAG)" \
		--create-samples
	@echo "$(GREEN)[SUCCESS]$(NC) Configuration files generated"

##@ 開発
.PHONY: dev-setup
dev-setup: setup generate-config ## 開発環境の完全セットアップ
	@echo "$(BLUE)[INFO]$(NC) Complete development setup..."
	@cp .env.example .env 2>/dev/null || true
	@echo "$(GREEN)[SUCCESS]$(NC) Development environment ready"
	@echo "$(YELLOW)[INFO]$(NC) Please edit .env file with your credentials"

.PHONY: lint
lint: ## コードの静的解析
	@echo "$(BLUE)[INFO]$(NC) Running code linting..."
	@python -m flake8 scripts/
	@python -m black --check scripts/
	@python -m mypy scripts/ || true
	@echo "$(GREEN)[SUCCESS]$(NC) Linting completed"

.PHONY: security-scan
security-scan: ## セキュリティスキャン
	@echo "$(BLUE)[INFO]$(NC) Running security scan..."
	@safety check -r requirements-dev.txt || true
	@bandit -r scripts/ || true
	@echo "$(GREEN)[SUCCESS]$(NC) Security scan completed"

##@ 情報
.PHONY: info
info: ## プロジェクト情報の表示
	@echo "$(BOLD)Project Information$(NC)"
	@echo "  Project: Ansible Custom EE Builder"
	@echo "  EE File: $(EE_FILE)"
	@echo "  Image: $(REGISTRY)/$(IMAGE_NAME):$(TAG)"
	@echo "  Runtime: $(CONTAINER_RUNTIME)"
	@echo ""
	@echo "$(BOLD)Available Images:$(NC)"
	@$(CONTAINER_RUNTIME) images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}" | \
		grep -E "(REPOSITORY|$(IMAGE_NAME))" || echo "  No local EE images found"

.PHONY: version
version: ## バージョン情報の表示
	@echo "$(BOLD)Version Information$(NC)"
	@echo "  Make: $(shell make --version | head -1)"
	@echo "  Python: $(shell python --version 2>&1)"
	@echo "  Ansible Core: $(shell ansible --version 2>/dev/null | head -1 || echo 'Not installed')"
	@echo "  Ansible Builder: $(shell ansible-builder --version 2>/dev/null || echo 'Not installed')"
	@echo "  Container Runtime: $(shell $(CONTAINER_RUNTIME) --version 2>/dev/null | head -1 || echo 'Not installed')"

# デフォルトターゲット
.DEFAULT_GOAL := help