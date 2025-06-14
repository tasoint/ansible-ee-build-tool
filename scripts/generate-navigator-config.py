#!/usr/bin/env python3
"""
Ansible Navigator Configuration Generator

This script generates ansible-navigator.yml configuration from execution-environment.yml
"""

import argparse
import sys
import os
from pathlib import Path
import yaml
from typing import Dict, Any, Optional


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load YAML file and return its contents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def save_yaml(data: Dict[str, Any], file_path: Path) -> None:
    """Save data to YAML file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
    except IOError as e:
        print(f"Error: Cannot write to {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def extract_base_image(ee_config: Dict[str, Any]) -> str:
    """Extract base image name from EE configuration."""
    images = ee_config.get('images', {})
    base_image = images.get('base_image', {})
    
    if isinstance(base_image, dict):
        return base_image.get('name', 'quay.io/ansible/creator-ee:latest')
    elif isinstance(base_image, str):
        return base_image
    else:
        return 'quay.io/ansible/creator-ee:latest'


def extract_collections(ee_config: Dict[str, Any]) -> Optional[str]:
    """Extract collections requirements from EE configuration."""
    dependencies = ee_config.get('dependencies', {})
    galaxy_content = dependencies.get('galaxy')
    
    if isinstance(galaxy_content, str):
        return galaxy_content.strip()
    elif isinstance(galaxy_content, dict):
        return yaml.dump(galaxy_content, default_flow_style=False)
    
    return None


def generate_navigator_config(ee_config: Dict[str, Any], image_name: str) -> Dict[str, Any]:
    """Generate ansible-navigator configuration from EE config."""
    
    base_image = extract_base_image(ee_config)
    
    config = {
        'ansible-navigator': {
            'ansible': {
                'inventories': ['inventory.yml'],
                'playbook': 'site.yml'
            },
            'execution-environment': {
                'enabled': True,
                'image': image_name or base_image,
                'pull-policy': 'missing',
                'container-engine': 'auto'
            },
            'logging': {
                'level': 'debug',
                'append': True,
                'file': './navigator.log'
            },
            'playbook-artifact': {
                'enable': True,
                'replay': './artifacts',
                'save-as': './artifacts/{playbook_name}-{time_stamp}.json'
            },
            'runner': {
                'artifact-dir': './artifacts',
                'rotate-artifacts-count': 10,
                'timeout': 300
            },
            'settings': {
                'effective-settings-file': './ansible-navigator-settings.json',
                'schema-cache-path': '~/.ansible-navigator/schema_cache'
            }
        }
    }
    
    # 環境変数の設定
    env_vars = {
        'ANSIBLE_HOST_KEY_CHECKING': 'false',
        'ANSIBLE_STDOUT_CALLBACK': 'yaml',
        'ANSIBLE_TIMEOUT': '30'
    }
    
    # Automation Hubトークンが設定されている場合は追加
    if 'ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN' in os.environ:
        env_vars['ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN'] = os.environ['ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN']
    
    if 'ANSIBLE_GALAXY_SERVER_GALAXY_TOKEN' in os.environ:
        env_vars['ANSIBLE_GALAXY_SERVER_GALAXY_TOKEN'] = os.environ['ANSIBLE_GALAXY_SERVER_GALAXY_TOKEN']
    
    config['ansible-navigator']['execution-environment']['environment-variables'] = {
        'set': env_vars
    }
    
    # ボリュームマウントの設定
    volumes = [
        '${HOME}/.ssh:/home/runner/.ssh:Z',
        '${PWD}:/runner/project:Z'
    ]
    
    # ansible.cfgがある場合はマウント
    if os.path.exists('ansible.cfg'):
        volumes.append('${PWD}/ansible.cfg:/etc/ansible/ansible.cfg:Z')
    
    config['ansible-navigator']['execution-environment']['volume-mounts'] = volumes
    
    return config


def create_sample_files(navigator_config: Dict[str, Any]) -> None:
    """Create sample inventory and playbook files."""
    
    # サンプルインベントリ
    inventory_content = {
        'all': {
            'hosts': {
                'localhost': {
                    'ansible_connection': 'local'
                }
            },
            'vars': {
                'ansible_python_interpreter': '{{ ansible_playbook_python }}'
            }
        }
    }
    
    if not os.path.exists('inventory.yml'):
        save_yaml(inventory_content, Path('inventory.yml'))
        print("Created sample inventory.yml")
    
    # サンプルプレイブック
    playbook_content = [
        {
            'name': 'Sample Playbook',
            'hosts': 'localhost',
            'gather_facts': True,
            'tasks': [
                {
                    'name': 'Display Ansible version',
                    'debug': {
                        'var': 'ansible_version'
                    }
                },
                {
                    'name': 'Display available collections',
                    'shell': 'ansible-galaxy collection list',
                    'register': 'collections_result'
                },
                {
                    'name': 'Show collections',
                    'debug': {
                        'var': 'collections_result.stdout_lines'
                    }
                }
            ]
        }
    ]
    
    if not os.path.exists('site.yml'):
        save_yaml(playbook_content, Path('site.yml'))
        print("Created sample site.yml")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Generate ansible-navigator.yml from execution-environment.yml',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use default execution-environment.yml
  %(prog)s -e custom-ee.yml                  # Use custom EE file
  %(prog)s -o custom-navigator.yml           # Custom output file
  %(prog)s -i my-custom-ee:latest            # Specify custom image name
  %(prog)s --create-samples                  # Create sample inventory and playbook
        """
    )
    
    parser.add_argument(
        '-e', '--ee-file',
        type=Path,
        default=Path('execution-environment.yml'),
        help='Execution Environment YAML file (default: execution-environment.yml)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=Path('ansible-navigator.yml'),
        help='Output ansible-navigator.yml file (default: ansible-navigator.yml)'
    )
    
    parser.add_argument(
        '-i', '--image',
        type=str,
        help='Override container image name'
    )
    
    parser.add_argument(
        '--create-samples',
        action='store_true',
        help='Create sample inventory.yml and site.yml files'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing files'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # EEファイルの存在確認
    if not args.ee_file.exists():
        print(f"Error: Execution Environment file not found: {args.ee_file}", file=sys.stderr)
        sys.exit(1)
    
    # 出力ファイルの存在確認
    if args.output.exists() and not args.force:
        print(f"Error: Output file already exists: {args.output}")
        print("Use --force to overwrite")
        sys.exit(1)
    
    if args.verbose:
        print(f"Loading EE configuration from: {args.ee_file}")
    
    # EE設定の読み込み
    ee_config = load_yaml(args.ee_file)
    
    # Navigator設定の生成
    navigator_config = generate_navigator_config(ee_config, args.image)
    
    # ファイルの保存
    save_yaml(navigator_config, args.output)
    print(f"Generated: {args.output}")
    
    # サンプルファイルの作成
    if args.create_samples:
        create_sample_files(navigator_config)
    
    if args.verbose:
        print("\nGenerated configuration:")
        print(yaml.dump(navigator_config, default_flow_style=False, indent=2))
        
        print("\nUsage:")
        print(f"  ansible-navigator run site.yml -i inventory.yml --eei {args.image or extract_base_image(ee_config)}")


if __name__ == '__main__':
    main()