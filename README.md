# Ansible Custom EE Builder

Ansible-navigatorやAnsible Automation Platform用のカスタムExecution Environment (EE)を作成するためのツールです。

## 概要

このプロジェクトは、GitHub ActionsとAnsible-builderを使用してカスタムEEを自動的にビルドし、各種コンテナレジストリにプッシュする機能を提供します。ローカル環境でもPodmanを使用して開発・テストが可能です。

## 主な機能

- ✅ GitHub Actionsによる自動ビルド・プッシュ
- ✅ 複数のコンテナレジストリ対応（Docker Hub、ECR、ACR、GCR）
- ✅ ローカル環境でのビルド・テスト
- ✅ ベースイメージの最新情報確認
- ✅ ansible-navigator.ymlの自動生成
- ✅ サンプル設定ファイルの提供

## セットアップ

### 必要な環境

- Podman 4.0以上 または Docker
- Python 3.9以上
- ansible-builder 3.0以上
- ansible-navigator 3.0以上（ローカルテスト用）
- Red Hatアカウント（Red Hat認定ベースイメージ使用時）

### インストール

1. **リポジトリのクローン**
   ```bash
   git clone https://github.com/your-org/ansible-custom-ee-builder.git
   cd ansible-custom-ee-builder
   ```

2. **開発環境のセットアップ**
   ```bash
   make setup
   ```

3. **環境変数の設定**
   ```bash
   cp .env.example .env
   # .envファイルを編集して認証情報を設定
   ```

4. **Red Hatレジストリへの認証**（オプション）
   ```bash
   podman login registry.redhat.io
   ```

## 使用方法

### ローカルでのビルド

```bash
# 基本的なビルド
make build

# カスタム設定でビルド
make build EE_FILE=custom-execution-environment.yml

# 特定のタグでビルド
make build TAG=v1.0.0

# レジストリへのプッシュ
make push REGISTRY=docker.io/myorg
```

### GitHub Actionsでのビルド

1. **手動実行**
   - GitHubのActionsタブに移動
   - "Build Custom EE"ワークフローを選択
   - "Run workflow"をクリックして実行

2. **タグによる自動実行**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

### ansible-navigatorでの実行

```bash
# 設定ファイルの生成
python scripts/generate-navigator-config.py

# Playbookの実行
ansible-navigator run site.yml
```

## 設定

### execution-environment.yml

メインの設定ファイルです：

```yaml
version: 3

images:
  base_image:
    name: registry.redhat.io/ansible-automation-platform-24/ee-minimal-rhel9:latest

dependencies:
  galaxy: |
    ---
    collections:
      - name: ansible.posix
        version: ">=1.5.0"
      - name: community.general
        version: ">=8.0.0"

  python: |
    jmespath>=1.0.0
    requests>=2.31.0
```

### 環境変数

主要な環境変数：

```bash
# Automation Hub認証
ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN=your_token

# Red Hat Registry認証
REDHAT_REGISTRY_USERNAME=your_username
REDHAT_REGISTRY_PASSWORD=your_password

# コンテナランタイム
CONTAINER_RUNTIME=podman
```

## テスト

```bash
# プロジェクト構造のテスト
python tests/test_build.py

# リリーステスト
python tests/test_release.py

# EEのビルドテスト
make test
```

## トラブルシューティング

### よくある問題

1. **ansible-builderが見つからない**
   ```bash
   pip install ansible-builder
   ```

2. **Red Hatレジストリ認証エラー**
   ```bash
   podman login registry.redhat.io
   ```

3. **ビルドが失敗する**
   ```bash
   make build VERBOSE=1
   ```

### ログの確認

```bash
# ビルドログ
cat ansible-navigator.log

# GitHub Actionsログ
# GitHubのActionsタブで確認
```

## 貢献

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## サポート

- [Issues](https://github.com/your-org/ansible-custom-ee-builder/issues)
- [Discussions](https://github.com/your-org/ansible-custom-ee-builder/discussions)
- [Documentation](docs/)