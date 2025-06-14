#!/bin/bash
set -euo pipefail

# Ansible Custom EE Builder - Base Image Checker
# Check for updates to base container images

# デフォルト値
VERBOSE=false
OUTPUT_FORMAT="table"
CHECK_AUTH=true

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# ヘルプメッセージ
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Check for updates to Ansible EE base images.

Options:
    -v, --verbose           Enable verbose output
    -f, --format FORMAT     Output format (table|json|yaml) (default: table)
    --no-auth              Skip authentication checks
    -h, --help             Show this help message

Examples:
    $0                     # Basic check with table output
    $0 -v -f json         # Verbose output in JSON format
    $0 --no-auth          # Skip Red Hat registry authentication

Environment Variables:
    REDHAT_REGISTRY_USERNAME    Red Hat registry username
    REDHAT_REGISTRY_PASSWORD    Red Hat registry password
EOF
}

# パラメータ解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --no-auth)
            CHECK_AUTH=false
            shift
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

# 必要なツールのチェック
check_dependencies() {
    local missing_deps=()
    
    if ! command -v podman &> /dev/null && ! command -v docker &> /dev/null; then
        missing_deps+=("podman or docker")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
}

# コンテナランタイムの決定
get_container_runtime() {
    if command -v podman &> /dev/null; then
        echo "podman"
    elif command -v docker &> /dev/null; then
        echo "docker"
    else
        log_error "Neither podman nor docker found"
        exit 1
    fi
}

# Red Hatレジストリへの認証
authenticate_redhat() {
    if [ "$CHECK_AUTH" = false ]; then
        log_info "Skipping Red Hat registry authentication"
        return 0
    fi
    
    if [ -n "${REDHAT_REGISTRY_USERNAME:-}" ] && [ -n "${REDHAT_REGISTRY_PASSWORD:-}" ]; then
        log_info "Authenticating to Red Hat registry..."
        local runtime
        runtime=$(get_container_runtime)
        
        if echo "$REDHAT_REGISTRY_PASSWORD" | \
           $runtime login registry.redhat.io -u "$REDHAT_REGISTRY_USERNAME" --password-stdin; then
            log_success "Red Hat registry authentication successful"
            return 0
        else
            log_error "Red Hat registry authentication failed"
            return 1
        fi
    else
        log_warn "Red Hat registry credentials not provided"
        log_warn "Some image information may not be available"
        return 1
    fi
}

# イメージの最新情報を取得
get_image_info() {
    local image="$1"
    local runtime
    runtime=$(get_container_runtime)
    
    local digest=""
    local created=""
    local size=""
    
    if [ "$VERBOSE" = true ]; then
        log_info "Checking image: $image"
    fi
    
    # イメージのInspecion実行
    if image_info=$($runtime image inspect "$image" 2>/dev/null); then
        digest=$(echo "$image_info" | jq -r '.[0].Digest // "unknown"')
        created=$(echo "$image_info" | jq -r '.[0].Created // "unknown"')
        size=$(echo "$image_info" | jq -r '.[0].Size // 0')
        
        # サイズを人間が読める形式に変換
        if [ "$size" != "0" ] && [ "$size" != "unknown" ]; then
            size=$(numfmt --to=iec --suffix=B "$size" 2>/dev/null || echo "${size}B")
        fi
    else
        # ローカルにない場合はリモートから情報を取得を試行
        if $runtime image pull "$image" >/dev/null 2>&1; then
            if image_info=$($runtime image inspect "$image" 2>/dev/null); then
                digest=$(echo "$image_info" | jq -r '.[0].Digest // "unknown"')
                created=$(echo "$image_info" | jq -r '.[0].Created // "unknown"')
                size=$(echo "$image_info" | jq -r '.[0].Size // 0')
                
                if [ "$size" != "0" ] && [ "$size" != "unknown" ]; then
                    size=$(numfmt --to=iec --suffix=B "$size" 2>/dev/null || echo "${size}B")
                fi
            fi
        else
            digest="unavailable"
            created="unavailable"
            size="unavailable"
        fi
    fi
    
    # JSON形式で情報を返す
    jq -n \
        --arg image "$image" \
        --arg digest "$digest" \
        --arg created "$created" \
        --arg size "$size" \
        '{
            image: $image,
            digest: $digest,
            created: $created,
            size: $size
        }'
}

# チェック対象イメージのリスト
declare -a IMAGES=(
    # Red Hat認定イメージ（要認証）
    "registry.redhat.io/ansible-automation-platform-24/ee-minimal-rhel9:latest"
    "registry.redhat.io/ansible-automation-platform-24/ee-supported-rhel9:latest"
    "registry.redhat.io/ansible-automation-platform-23/ee-minimal-rhel8:latest"
    
    # コミュニティイメージ（認証不要）
    "quay.io/ansible/creator-ee:latest"
    "quay.io/ansible/awx-ee:latest"
    "quay.io/ansible/ansible-runner:latest"
)

# メイン処理
main() {
    log_info "Checking Ansible EE base images..."
    
    check_dependencies
    authenticate_redhat
    
    local results=()
    local failed_images=()
    
    # 各イメージをチェック
    for image in "${IMAGES[@]}"; do
        if image_info=$(get_image_info "$image"); then
            results+=("$image_info")
        else
            failed_images+=("$image")
        fi
    done
    
    # 結果の出力
    case "$OUTPUT_FORMAT" in
        "json")
            echo "["
            for i in "${!results[@]}"; do
                echo "${results[$i]}"
                if [ $i -lt $((${#results[@]} - 1)) ]; then
                    echo ","
                fi
            done
            echo "]"
            ;;
        "yaml")
            echo "images:"
            for result in "${results[@]}"; do
                echo "$result" | jq -r '
                    "  - image: \"" + .image + "\"",
                    "    digest: \"" + .digest + "\"",
                    "    created: \"" + .created + "\"",
                    "    size: \"" + .size + "\""
                '
            done
            ;;
        "table"|*)
            printf "${BOLD}%-60s %-20s %-25s %-10s${NC}\n" "IMAGE" "SIZE" "CREATED" "STATUS"
            printf "%-60s %-20s %-25s %-10s\n" "$(printf -- '-%.0s' {1..60})" "$(printf -- '-%.0s' {1..20})" "$(printf -- '-%.0s' {1..25})" "$(printf -- '-%.0s' {1..10})"
            
            for result in "${results[@]}"; do
                local image created size status
                image=$(echo "$result" | jq -r '.image')
                created=$(echo "$result" | jq -r '.created')
                size=$(echo "$result" | jq -r '.size')
                
                if [ "$created" = "unavailable" ]; then
                    status="${RED}ERROR${NC}"
                    created="${RED}N/A${NC}"
                    size="${RED}N/A${NC}"
                else
                    status="${GREEN}OK${NC}"
                    # 日付の短縮表示
                    if [ "$created" != "unknown" ]; then
                        created=$(date -d "$created" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "$created")
                    fi
                fi
                
                printf "%-60s %-20s %-25s %-10s\n" "$image" "$size" "$created" "$status"
            done
            ;;
    esac
    
    # 失敗したイメージがある場合の警告
    if [ ${#failed_images[@]} -gt 0 ]; then
        echo
        log_warn "Failed to check the following images:"
        for image in "${failed_images[@]}"; do
            log_warn "  - $image"
        done
        
        # GitHub Actionsの場合は環境変数を設定
        if [ -n "${GITHUB_ACTIONS:-}" ]; then
            echo "IMAGES_UPDATED=true" >> "${GITHUB_ENV:-/dev/null}" 2>/dev/null || true
            echo "UPDATE_DETAILS=Some base images failed to check: ${failed_images[*]}" >> "${GITHUB_ENV:-/dev/null}" 2>/dev/null || true
        fi
    fi
    
    log_success "Base image check completed"
    
    # 使用方法のヒント
    if [ "$OUTPUT_FORMAT" = "table" ] && [ "$VERBOSE" = true ]; then
        echo
        log_info "To use these images in your execution-environment.yml:"
        echo "images:"
        echo "  base_image:"
        echo "    name: <image_name_from_above>"
    fi
}

# メイン処理実行
main "$@"