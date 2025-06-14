#!/bin/bash
set -euo pipefail

# Ansible Custom EE Builder - Local Build Script
# Usage: ./scripts/build-local.sh [OPTIONS]

# デフォルト値
EE_FILE="execution-environment.yml"
TAG="latest"
REGISTRY="localhost"
PUSH=false
VERBOSE=false
CONTAINER_RUNTIME="podman"
BUILD_CONTEXT="./context"

# ヘルプメッセージ
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -f, --file FILE         Execution Environment file (default: execution-environment.yml)
    -t, --tag TAG          Container image tag (default: latest)
    -r, --registry REGISTRY Registry to push to (default: localhost)
    -p, --push             Push image to registry after build
    -v, --verbose          Enable verbose output
    --runtime RUNTIME      Container runtime (podman/docker, default: podman)
    --context DIR          Build context directory (default: ./context)
    -h, --help             Show this help message

Examples:
    $0                                          # Basic build
    $0 -f custom-ee.yml -t v1.0.0              # Custom EE file and tag
    $0 -t dev -p -r docker.io/myorg           # Build and push to registry
    $0 --verbose --runtime docker              # Use Docker runtime with verbose output

Environment Variables:
    ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN   Automation Hub token
    ANSIBLE_GALAXY_SERVER_GALAXY_TOKEN          Galaxy token
    REDHAT_REGISTRY_USERNAME                    Red Hat registry username
    REDHAT_REGISTRY_PASSWORD                    Red Hat registry password
EOF
}

# パラメータ解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            EE_FILE="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --runtime)
            CONTAINER_RUNTIME="$2"
            shift 2
            ;;
        --context)
            BUILD_CONTEXT="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            show_help
            exit 1
            ;;
    esac
done

# 色付きログ出力
log_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

log_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1" >&2
}

log_warn() {
    echo -e "\033[1;33m[WARN]\033[0m $1"
}

# 必要なツールのチェック
check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v ansible-builder &> /dev/null; then
        missing_deps+=("ansible-builder")
    fi
    
    if ! command -v "$CONTAINER_RUNTIME" &> /dev/null; then
        missing_deps+=("$CONTAINER_RUNTIME")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_error "Please install them using: pip install ansible-builder"
        exit 1
    fi
    
    log_success "All dependencies are available"
}

# EEファイルの存在確認
check_ee_file() {
    if [ ! -f "$EE_FILE" ]; then
        log_error "Execution Environment file not found: $EE_FILE"
        exit 1
    fi
    log_info "Using EE file: $EE_FILE"
}

# Red Hatレジストリへの認証
authenticate_redhat() {
    if [ -n "${REDHAT_REGISTRY_USERNAME:-}" ] && [ -n "${REDHAT_REGISTRY_PASSWORD:-}" ]; then
        log_info "Authenticating to Red Hat registry..."
        echo "$REDHAT_REGISTRY_PASSWORD" | \
            $CONTAINER_RUNTIME login registry.redhat.io -u "$REDHAT_REGISTRY_USERNAME" --password-stdin
        log_success "Red Hat registry authentication successful"
    else
        log_warn "Red Hat registry credentials not provided"
        log_warn "Set REDHAT_REGISTRY_USERNAME and REDHAT_REGISTRY_PASSWORD if using Red Hat base images"
    fi
}

# EEのビルド
build_ee() {
    log_info "Building Execution Environment..."
    
    local image_name="${REGISTRY}/ansible-custom-ee:${TAG}"
    local build_args=()
    
    build_args+=(--file "$EE_FILE")
    build_args+=(--tag "$image_name")
    build_args+=(--container-runtime "$CONTAINER_RUNTIME")
    build_args+=(--build-outputs-dir "$BUILD_CONTEXT")
    
    if [ "$VERBOSE" = true ]; then
        build_args+=(--verbosity 2)
    fi
    
    # ビルド実行
    if ! ansible-builder build "${build_args[@]}"; then
        log_error "Build failed"
        exit 1
    fi
    
    log_success "Build completed: $image_name"
    echo "IMAGE_NAME=$image_name" >> "${GITHUB_OUTPUT:-/dev/null}" 2>/dev/null || true
}

# EEのテスト
test_ee() {
    log_info "Testing built EE..."
    
    local image_name="${REGISTRY}/ansible-custom-ee:${TAG}"
    
    # 基本的な動作確認
    log_info "Testing Ansible version..."
    if ! $CONTAINER_RUNTIME run --rm "$image_name" ansible --version; then
        log_error "Ansible version test failed"
        exit 1
    fi
    
    log_info "Testing installed collections..."
    if ! $CONTAINER_RUNTIME run --rm "$image_name" ansible-galaxy collection list; then
        log_error "Collection list test failed"
        exit 1
    fi
    
    # Python環境の確認
    log_info "Testing Python environment..."
    if ! $CONTAINER_RUNTIME run --rm "$image_name" python3 -c "import sys; print(f'Python {sys.version}')"; then
        log_error "Python environment test failed"
        exit 1
    fi
    
    log_success "All tests passed"
}

# レジストリへのプッシュ
push_to_registry() {
    if [ "$PUSH" = true ]; then
        log_info "Pushing to registry..."
        
        local image_name="${REGISTRY}/ansible-custom-ee:${TAG}"
        
        if ! $CONTAINER_RUNTIME push "$image_name"; then
            log_error "Push failed"
            exit 1
        fi
        
        log_success "Push completed: $image_name"
    else
        log_info "Skipping push (use -p/--push to enable)"
    fi
}

# クリーンアップ
cleanup() {
    if [ -d "$BUILD_CONTEXT" ]; then
        log_info "Cleaning up build context..."
        rm -rf "$BUILD_CONTEXT"
    fi
}

# メイン処理
main() {
    log_info "Starting Ansible Custom EE build process..."
    log_info "EE File: $EE_FILE"
    log_info "Tag: $TAG"
    log_info "Registry: $REGISTRY"
    log_info "Container Runtime: $CONTAINER_RUNTIME"
    
    check_dependencies
    check_ee_file
    authenticate_redhat
    build_ee
    test_ee
    push_to_registry
    
    log_success "Build process completed successfully!"
    
    # 使用方法の表示
    if [ "$PUSH" = false ]; then
        log_info "To run the built EE:"
        log_info "  $CONTAINER_RUNTIME run -it --rm ${REGISTRY}/ansible-custom-ee:${TAG}"
    fi
}

# エラーハンドリング
trap cleanup EXIT
trap 'log_error "Script interrupted"; exit 1' INT TERM

# メイン処理実行
main "$@"