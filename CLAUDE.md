# Ansible Custom EE Builder

Ansible-navigatorやAnsible Automation Platform用のカスタムExecution Environment (EE)を作成するためのツールです。

## プロジェクト概要

このプロジェクトは、GitHub ActionsとAnsible-builderを使用してカスタムEEを自動的にビルドし、各種コンテナレジストリにプッシュする機能を提供します。ローカル環境でもPodmanを使用して開発・テストが可能です。

## 主な機能

- GitHub Actionsによる自動ビルド・プッシュ
- 複数のコンテナレジストリ対応（Docker Hub、ECR、ACR、GCR）
- ローカル環境でのビルド・テスト
- ベースイメージの最新情報確認
- ansible-builder.ymlからansible-navigator.ymlの自動生成
- サンプル設定ファイルの提供

## プロジェクト構造

```
ansible-custom-ee-builder/
├── .github/
│   ├── workflows/
│   │   ├── build-ee.yml           # メインのビルドワークフロー
│   │   └── check-base-images.yml  # ベースイメージの更新確認
│   └── actions/
│       └── build-push/            # カスタムアクション
├── examples/                      # サンプル設定ファイル
│   ├── execution-environment.yml
│   └── ansible-navigator.yml
├── scripts/                       # ユーティリティスクリプト
│   ├── build-local.sh
│   ├── generate-navigator-config.py
│   └── check-base-images.sh
├── tests/                        # テストスクリプト
├── docs/                         # ドキュメント
├── Makefile
├── README.md
├── execution-environment.yml    # デフォルトEE設定
├── ansible.cfg                  # Ansible設定（Automation Hub対応）
└── .env.example                # 環境変数のサンプル

```

## 必要な環境

- Podman 4.0以上
- Python 3.9以上
- ansible-builder 3.0以上
- ansible-navigator 3.0以上（ローカルテスト用）
- Red Hatアカウント（Red Hat認定ベースイメージ使用時）

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/ansible-custom-ee-builder.git
cd ansible-custom-ee-builder
```

### 2. 必要なツールのインストール

```bash
# Pythonパッケージのインストール
pip install -r requirements-dev.txt

# または
make setup
```

### 3. Red Hatレジストリへの認証

Red Hat認定ベースイメージを使用する場合は、レジストリへの認証が必要です：

```bash
# Red Hatレジストリにログイン
podman login registry.redhat.io
Username: your-redhat-username
Password: your-redhat-password

# または、サービスアカウントトークンを使用
podman login registry.redhat.io -u='your-service-account' -p='your-token'
```

#### Red Hatサービスアカウントの作成（推奨）

1. [Red Hat Customer Portal](https://access.redhat.com/terms-based-registry/)にアクセス
2. "New Service Account"をクリック
3. アカウント名を入力して作成
4. 生成されたユーザー名とトークンを保存

### 4. GitHub Secretsの設定

以下のシークレットをGitHubリポジトリに設定してください：

#### Red Hatレジストリ
- `REDHAT_REGISTRY_USERNAME`: Red Hatサービスアカウントのユーザー名
- `REDHAT_REGISTRY_PASSWORD`: サービスアカウントのトークン

#### 認証トークン
- `ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN`: Red Hat Automation Hubのトークン
- `ANSIBLE_GALAXY_SERVER_GALAXY_TOKEN`: Ansible Galaxyのトークン（オプション）

#### Docker Hub
- `DOCKER_USERNAME`: Docker Hubのユーザー名
- `DOCKER_PASSWORD`: Docker Hubのパスワード

#### AWS ECR
- `AWS_ACCESS_KEY_ID`: AWSアクセスキー
- `AWS_SECRET_ACCESS_KEY`: AWSシークレットキー
- `AWS_REGION`: リージョン（例: ap-northeast-1）
- `ECR_REGISTRY`: ECRレジストリURL

#### Azure ACR
- `AZURE_CLIENT_ID`: AzureサービスプリンシパルのクライアントID
- `AZURE_CLIENT_SECRET`: クライアントシークレット
- `AZURE_TENANT_ID`: テナントID
- `ACR_REGISTRY`: ACRレジストリURL

#### Google GCR
- `GCP_SA_KEY`: サービスアカウントのJSONキー（Base64エンコード）
- `GCP_PROJECT_ID`: GCPプロジェクトID

## 使用方法

### ローカルでのビルド

```bash
# デフォルト設定でビルド
make build

# カスタム設定でビルド
make build EE_FILE=custom-execution-environment.yml

# 特定のタグでビルド
make build TAG=v1.0.0

# Automation Hubトークンを指定してビルド
ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN=your_token make build
```

### GitHub Actionsでのビルド

#### 手動実行

1. GitHubのActionsタブに移動
2. "Build Custom EE"ワークフローを選択
3. "Run workflow"をクリック
4. パラメータを設定して実行

#### タグによる自動実行

```bash
# タグを作成してプッシュ
git tag v1.0.0
git push origin v1.0.0
```

### Automation Hubトークンの取得

1. [Red Hat Customer Portal](https://console.redhat.com/)にログイン
2. Automation Hub → Collections → API token に移動
3. "Load token" をクリックしてトークンを取得
4. 環境変数またはGitHub Secretsに設定

### ansible-navigator.ymlの生成

```bash
# execution-environment.ymlから自動生成
python scripts/generate-navigator-config.py

# カスタムファイルから生成
python scripts/generate-navigator-config.py --ee-file custom-ee.yml
```

## 設定ファイル

### execution-environment.yml

全ての依存関係を統合した設定ファイルです：

```yaml
version: 3

# コンテナイメージの設定
images:
  base_image:
    # Red Hat認定イメージ（要認証）
    name: registry.redhat.io/ansible-automation-platform-24/ee-minimal-rhel9:latest
    
    # 代替オプション（認証不要）
    # name: quay.io/ansible/creator-ee:latest
    # name: quay.io/ansible/awx-ee:latest

# Ansible Collections（コミュニティ + Automation Hub）
dependencies:
  galaxy: |
    ---
    collections:
      # Red Hat認定コレクション（Automation Hub）
      - name: redhat.rhel_system_roles
        version: ">=1.0.0"
        source: https://console.redhat.com/api/automation-hub/
      - name: redhat.satellite
        version: ">=3.0.0"
        source: https://console.redhat.com/api/automation-hub/
      - name: redhat.insights
        version: ">=1.0.0"
        source: https://console.redhat.com/api/automation-hub/
      
      # コミュニティコレクション（Galaxy）
      - name: ansible.posix
        version: ">=1.5.0"
      - name: community.general
        version: ">=8.0.0"
      - name: kubernetes.core
        version: ">=3.0.0"
      - name: community.docker
        version: ">=3.0.0"
      - name: amazon.aws
        version: ">=7.0.0"
      - name: azure.azcollection
        version: ">=1.19.0"
      - name: google.cloud
        version: ">=1.3.0"

  # Python パッケージ
  python: |
    # 基本パッケージ
    jmespath>=1.0.0
    netaddr>=0.8.0
    
    # Kubernetes/OpenShift
    kubernetes>=28.0.0
    openshift>=0.13.0
    
    # クラウドプロバイダー
    boto3>=1.28.0
    botocore>=1.31.0
    azure-mgmt-compute>=30.0.0
    azure-mgmt-network>=25.0.0
    google-cloud-compute>=1.14.0
    
    # その他のユーティリティ
    pyvmomi>=8.0.0
    requests>=2.31.0
    urllib3>=2.0.0

  # システムパッケージ
  system: |
    # ビルドツール
    python39-devel [platform:rhel-9]
    gcc [platform:rpm]
    
    # 基本ツール
    git [platform:rpm]
    rsync [platform:rpm]
    openssh-clients [platform:rpm]
    
    # ネットワークツール
    bind-utils [platform:rpm]
    net-tools [platform:rpm]
    
    # その他
    jq [platform:rpm]
    vim-minimal [platform:rpm]

# ビルド時の設定
build_arg_defaults:
  ANSIBLE_GALAXY_CLI_COLLECTION_OPTS: "-v"
  ANSIBLE_GALAXY_CLI_ROLE_OPTS: "-v"

# 追加のビルドステップ
additional_build_steps:
  prepend: |
    # ansible.cfgをコピー
    COPY ansible.cfg /etc/ansible/ansible.cfg
    
    # 環境情報の出力
    RUN echo "=== Build Environment ===" && \
        cat /etc/os-release && \
        python3 --version && \
        ansible --version

  append:
    - RUN echo "=== Installed Collections ===" && ansible-galaxy collection list
    - RUN echo "=== Custom EE build completed ==="

# 環境変数の設定
options:
  container_init:
    package_pip: ansible-core>=2.15
  build_outputs_dir: ./context
```

### ansible.cfg

Automation Hubとコミュニティコレクションの両方を利用するための設定：

```ini
[defaults]
# 基本設定
host_key_checking = False
stdout_callback = yaml
interpreter_python = auto_silent
remote_tmp = /tmp
local_tmp = /tmp
retry_files_enabled = False

# コレクション設定
collections_path = /usr/share/ansible/collections:/opt/ansible/collections

# タイムアウト設定
timeout = 30
gather_timeout = 30

[galaxy]
# Galaxy サーバーの優先順位（Automation Hub → Galaxy）
server_list = automation_hub, galaxy

[galaxy_server.automation_hub]
# Red Hat Automation Hub
url = https://console.redhat.com/api/automation-hub/
auth_url = https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token

# トークンは環境変数から取得
token = ${ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN}

# SSL検証（本番環境では True を推奨）
validate_certs = True

[galaxy_server.galaxy]
# Ansible Galaxy（コミュニティ）
url = https://galaxy.ansible.com/
token = ${ANSIBLE_GALAXY_SERVER_GALAXY_TOKEN}
```

### 環境変数の設定（.env.example）

```bash
# Automation Hub認証トークン（Red Hat Customer Portal から取得）
ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN=your_automation_hub_token_here

# Galaxy認証トークン（オプション）
ANSIBLE_GALAXY_SERVER_GALAXY_TOKEN=your_galaxy_token_here

# Red Hatレジストリ認証（サービスアカウント推奨）
REDHAT_REGISTRY_USERNAME=your_service_account_username
REDHAT_REGISTRY_PASSWORD=your_service_account_token

# コンテナレジストリ認証
REGISTRY_AUTH_FILE=$HOME/.config/containers/auth.json
```

## Makefile ターゲット

- `make setup`: 開発環境のセットアップ
- `make build`: EEのビルド
- `make push`: レジストリへのプッシュ
- `make test`: ローカルテストの実行
- `make clean`: ビルドアーティファクトのクリーンアップ
- `make check-base`: ベースイメージの更新確認
- `make generate-config`: ansible-navigator.ymlの生成

## ベースイメージの確認

利用可能なベースイメージの最新情報を確認：

```bash
# Red Hat公式イメージの確認（要認証）
make check-base

# または直接スクリプトを実行
./scripts/check-base-images.sh
```

### 利用可能なベースイメージ

#### Red Hat認定イメージ（要認証）
- `registry.redhat.io/ansible-automation-platform-24/ee-minimal-rhel9:latest`
- `registry.redhat.io/ansible-automation-platform-24/ee-supported-rhel9:latest`
- `registry.redhat.io/ansible-automation-platform-23/ee-minimal-rhel8:latest`

#### コミュニティイメージ（認証不要）
- `quay.io/ansible/creator-ee:latest` - 開発向け軽量イメージ
- `quay.io/ansible/awx-ee:latest` - AWX用イメージ
- `quay.io/ansible/ansible-runner:latest` - 基本的なランナーイメージ

## トラブルシューティング

### ビルドが失敗する場合

1. Podmanが正しくインストールされているか確認
   ```bash
   podman --version
   ```

2. Red Hatレジストリへの認証を確認
   ```bash
   podman login registry.redhat.io
   
   # 認証情報の確認
   cat ${XDG_RUNTIME_DIR}/containers/auth.json
   ```

3. ベースイメージの取得を確認
   ```bash
   podman pull registry.redhat.io/ansible-automation-platform-24/ee-minimal-rhel9:latest
   ```

4. ビルドログを確認
   ```bash
   make build VERBOSE=1
   ```

### プッシュが失敗する場合

1. レジストリの認証情報を確認
2. ネットワーク接続を確認
3. レジストリのクォータを確認

## ベストプラクティス

### タグ付け戦略

1. **セマンティックバージョニング**: `v1.0.0`, `v1.0.1`
2. **ブランチ名**: `main`, `develop`
3. **日付ベース**: `2024.01.15`
4. **latest**: 最新の安定版

推奨される組み合わせ：
- プロダクション: `v1.0.0`, `latest`
- 開発: `develop`, `dev-YYYYMMDD`

### EE最適化のヒント

1. **レイヤーキャッシュの活用**
   - 変更頻度の低い依存関係を先にインストール
   - requirements.txtを分割して管理

2. **マルチステージビルド**
   - ビルド時のみ必要なパッケージを分離
   - 最終イメージサイズの削減

3. **セキュリティ**
   - 定期的なベースイメージの更新
   - 脆弱性スキャンの実施

## 貢献方法

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 今後の機能追加予定

- [ ] マルチアーキテクチャビルド対応（arm64）
- [ ] ビルドキャッシュの最適化
- [ ] セキュリティスキャンの統合
- [ ] Web UIでの設定管理
- [ ] ビルド履歴の可視化