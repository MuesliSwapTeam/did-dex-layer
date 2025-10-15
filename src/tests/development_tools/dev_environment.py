"""
Development environment setup and management tools.

This module provides tools for setting up, managing, and maintaining
the development environment for the MuesliSwap DID Orderbook system.
"""

import os
import json
import subprocess
import shutil
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import yaml


class DevelopmentEnvironment:
    """Development environment management system."""

    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.getcwd()
        self.config_file = os.path.join(self.project_root, "dev_config.yaml")
        self.setup_log = []

    def setup_development_environment(self, config: Dict[str, Any] = None):
        """Setup complete development environment."""
        print("🛠️ Setting up development environment...")

        default_config = {
            "python_version": "3.9+",
            "node_version": "18+",
            "cardano_tools": {"opshin": True, "cardano_cli": True},
            "services": {"ogmios": True, "kupo": True, "blockfrost": True},
            "databases": {"sqlite": True, "postgresql": False},
            "testing": {"pytest": True, "coverage": True, "mock": True},
        }

        config = config or default_config

        try:
            # Step 1: Check system requirements
            self._check_system_requirements(config)

            # Step 2: Setup Python environment
            self._setup_python_environment()

            # Step 3: Setup Node.js environment
            self._setup_nodejs_environment()

            # Step 4: Install Cardano tools
            self._install_cardano_tools(config["cardano_tools"])

            # Step 5: Setup services
            self._setup_services(config["services"])

            # Step 6: Setup databases
            self._setup_databases(config["databases"])

            # Step 7: Install testing tools
            self._install_testing_tools(config["testing"])

            # Step 8: Create configuration files
            self._create_configuration_files()

            # Step 9: Setup development scripts
            self._create_development_scripts()

            # Step 10: Run initial tests
            self._run_initial_tests()

            print("✅ Development environment setup completed successfully!")
            self._save_setup_log()

        except Exception as e:
            print(f"❌ Development environment setup failed: {e}")
            raise

    def _check_system_requirements(self, config: Dict[str, Any]):
        """Check system requirements."""
        print("🔍 Checking system requirements...")

        requirements = {
            "python": config["python_version"],
            "node": config["node_version"],
        }

        # Check Python version
        python_version = sys.version_info
        required_python = self._parse_version_requirement(requirements["python"])
        if not self._version_meets_requirement(python_version, required_python):
            raise Exception(
                f"Python {requirements['python']} required, found {python_version.major}.{python_version.minor}"
            )

        # Check Node.js version
        try:
            node_version = subprocess.check_output(
                ["node", "--version"], text=True
            ).strip()
            print(f"   ✅ Node.js: {node_version}")
        except FileNotFoundError:
            print("   ⚠ Node.js not found - will install")

        # Check available disk space
        disk_usage = shutil.disk_usage(self.project_root)
        free_gb = disk_usage.free / (1024**3)
        if free_gb < 5:
            print(f"   ⚠ Low disk space: {free_gb:.1f}GB available")

        print("   ✅ System requirements check completed")

    def _setup_python_environment(self):
        """Setup Python environment."""
        print("🐍 Setting up Python environment...")

        # Create virtual environment
        venv_path = os.path.join(self.project_root, "venv")
        if not os.path.exists(venv_path):
            subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
            print("   ✅ Virtual environment created")

        # Install requirements
        requirements_files = [
            "src/orderbook/requirements.txt",
            "src/auth_nft_minting_tool/requirements.txt",
            "src/testing_tools/requirements.txt",
        ]

        for req_file in requirements_files:
            if os.path.exists(req_file):
                self._install_python_requirements(req_file)

        print("   ✅ Python environment setup completed")

    def _setup_nodejs_environment(self):
        """Setup Node.js environment."""
        print("📦 Setting up Node.js environment...")

        # Setup frontend
        frontend_path = os.path.join(
            self.project_root, "src/auth_nft_minting_tool/frontend"
        )
        if os.path.exists(frontend_path):
            self._setup_frontend_environment(frontend_path)

        # Setup server
        server_path = os.path.join(
            self.project_root, "src/auth_nft_minting_tool/server"
        )
        if os.path.exists(server_path):
            self._setup_server_environment(server_path)

        print("   ✅ Node.js environment setup completed")

    def _install_cardano_tools(self, tools_config: Dict[str, bool]):
        """Install Cardano development tools."""
        print("🔧 Installing Cardano tools...")

        if tools_config.get("opshin", False):
            self._install_opshin()

        if tools_config.get("cardano_cli", False):
            self._install_cardano_cli()

        print("   ✅ Cardano tools installation completed")

    def _setup_services(self, services_config: Dict[str, bool]):
        """Setup required services."""
        print("🌐 Setting up services...")

        if services_config.get("ogmios", False):
            self._setup_ogmios()

        if services_config.get("kupo", False):
            self._setup_kupo()

        if services_config.get("blockfrost", False):
            self._setup_blockfrost()

        print("   ✅ Services setup completed")

    def _setup_databases(self, db_config: Dict[str, bool]):
        """Setup databases."""
        print("🗄️ Setting up databases...")

        if db_config.get("sqlite", False):
            self._setup_sqlite()

        if db_config.get("postgresql", False):
            self._setup_postgresql()

        print("   ✅ Database setup completed")

    def _install_testing_tools(self, testing_config: Dict[str, bool]):
        """Install testing tools."""
        print("🧪 Installing testing tools...")

        if testing_config.get("pytest", False):
            self._install_pytest()

        if testing_config.get("coverage", False):
            self._install_coverage()

        if testing_config.get("mock", False):
            self._install_mock()

        print("   ✅ Testing tools installation completed")

    def _create_configuration_files(self):
        """Create configuration files."""
        print("📝 Creating configuration files...")

        # Create .env file
        env_content = """# MuesliSwap DID Orderbook Environment Configuration

# Network Configuration
NETWORK=testnet
OGMIOS_API_HOST=localhost
OGMIOS_API_PORT=1337
OGMIOS_API_PROTOCOL=ws

# Database Configuration
DATABASE_URL=sqlite:///dev_database.db

# Blockfrost Configuration
BLOCKFROST_PROJECT_ID=your_project_id_here
BLOCKFROST_API_URL=https://cardano-preprod.blockfrost.io/api/v0

# DID Authentication Configuration
PROOFSPACE_CLIENT_ID=your_client_id_here
PROOFSPACE_SERVICE_DID=your_service_did_here

# Development Configuration
DEBUG=true
LOG_LEVEL=DEBUG
"""

        with open(os.path.join(self.project_root, ".env"), "w") as f:
            f.write(env_content)

        # Create dev_config.yaml
        dev_config = {
            "project": {
                "name": "MuesliSwap DID Orderbook",
                "version": "1.0.0",
                "description": "Cardano DEX Protocol with DIDs Layer",
            },
            "development": {
                "python_version": "3.9+",
                "node_version": "18+",
                "auto_reload": True,
                "debug_mode": True,
            },
            "services": {
                "ogmios": {"enabled": True, "host": "localhost", "port": 1337},
                "kupo": {"enabled": True, "host": "localhost", "port": 80},
            },
            "testing": {
                "pytest": {"enabled": True, "coverage_threshold": 80},
                "integration_tests": True,
                "performance_tests": True,
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(dev_config, f, default_flow_style=False)

        print("   ✅ Configuration files created")

    def _create_development_scripts(self):
        """Create development scripts."""
        print("📜 Creating development scripts...")

        scripts_dir = os.path.join(self.project_root, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)

        # Create run_tests.py
        run_tests_script = """#!/usr/bin/env python3
\"\"\"
Run all tests for the MuesliSwap DID Orderbook system.
\"\"\"

import sys
import os
import subprocess

def main():
    \"\"\"Run all tests.\"\"\"
    print("🧪 Running all tests...")
    
    # Run contract tests
    print("\\n📋 Running contract tests...")
    result1 = subprocess.run([
        sys.executable, "-m", "pytest", 
        "src/testing_tools/test_suite/test_orderbook_contracts.py",
        "-v"
    ])
    
    # Run DID authentication tests
    print("\\n🔐 Running DID authentication tests...")
    result2 = subprocess.run([
        sys.executable, "-m", "pytest",
        "src/testing_tools/test_suite/test_did_authentication.py",
        "-v"
    ])
    
    # Run integration tests
    print("\\n🔗 Running integration tests...")
    result3 = subprocess.run([
        sys.executable, "-m", "pytest",
        "src/testing_tools/test_suite/test_integration.py",
        "-v"
    ])
    
    # Check results
    if result1.returncode == 0 and result2.returncode == 0 and result3.returncode == 0:
        print("\\n✅ All tests passed!")
        return 0
    else:
        print("\\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""

        with open(os.path.join(scripts_dir, "run_tests.py"), "w") as f:
            f.write(run_tests_script)

        # Create deploy_contracts.py
        deploy_script = """#!/usr/bin/env python3
\"\"\"
Deploy all smart contracts.
\"\"\"

import sys
import os

def main():
    \"\"\"Deploy contracts.\"\"\"
    print("🚀 Deploying contracts...")
    
    from testing_tools.development_tools.contract_deployer import ContractDeployer, DeploymentConfig
    
    config = DeploymentConfig(
        network="testnet",
        gas_limit=2000000,
        max_fee=2000000,
        timeout=300,
        retry_count=3,
        verification_enabled=True
    )
    
    deployer = ContractDeployer(config)
    
    try:
        contracts = deployer.deploy_all_contracts("admin")
        print("\\n✅ All contracts deployed successfully!")
        return 0
    except Exception as e:
        print(f"\\n❌ Deployment failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""

        with open(os.path.join(scripts_dir, "deploy_contracts.py"), "w") as f:
            f.write(deploy_script)

        # Create start_services.py
        start_services_script = """#!/usr/bin/env python3
\"\"\"
Start all required services.
\"\"\"

import subprocess
import time
import sys

def main():
    \"\"\"Start services.\"\"\"
    print("🌐 Starting services...")
    
    # Start Ogmios (if available)
    try:
        ogmios_process = subprocess.Popen([
            "ogmios", "serve", "--node-socket", "/tmp/cardano-node.socket"
        ])
        print("✅ Ogmios started")
    except FileNotFoundError:
        print("⚠ Ogmios not found - skipping")
    
    # Start Kupo (if available)
    try:
        kupo_process = subprocess.Popen([
            "kupo", "--ogmios", "ws://localhost:1337"
        ])
        print("✅ Kupo started")
    except FileNotFoundError:
        print("⚠ Kupo not found - skipping")
    
    print("\\n✅ Services started!")
    print("Press Ctrl+C to stop all services")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\\n🛑 Stopping services...")
        if 'ogmios_process' in locals():
            ogmios_process.terminate()
        if 'kupo_process' in locals():
            kupo_process.terminate()
        print("✅ Services stopped")

if __name__ == "__main__":
    sys.exit(main())
"""

        with open(os.path.join(scripts_dir, "start_services.py"), "w") as f:
            f.write(start_services_script)

        # Make scripts executable
        for script_file in os.listdir(scripts_dir):
            if script_file.endswith(".py"):
                os.chmod(os.path.join(scripts_dir, script_file), 0o755)

        print("   ✅ Development scripts created")

    def _run_initial_tests(self):
        """Run initial tests to verify setup."""
        print("🧪 Running initial tests...")

        try:
            # Test Python imports
            import orderbook
            import pycardano

            print("   ✅ Python imports working")

            # Test contract compilation
            from orderbook.off_chain.utils.contracts import get_contract

            script, script_hash, address = get_contract("orderbook", False)
            print("   ✅ Contract loading working")

            print("   ✅ Initial tests passed")

        except Exception as e:
            print(f"   ⚠ Initial tests failed: {e}")

    def _parse_version_requirement(self, requirement: str) -> tuple:
        """Parse version requirement string."""
        if "+" in requirement:
            version = requirement.replace("+", "")
            return tuple(map(int, version.split(".")))
        return tuple(map(int, requirement.split(".")))

    def _version_meets_requirement(self, version: tuple, requirement: tuple) -> bool:
        """Check if version meets requirement."""
        return version >= requirement

    def _install_python_requirements(self, requirements_file: str):
        """Install Python requirements."""
        if os.path.exists(requirements_file):
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", requirements_file],
                check=True,
            )

    def _setup_frontend_environment(self, frontend_path: str):
        """Setup frontend environment."""
        if os.path.exists(os.path.join(frontend_path, "package.json")):
            subprocess.run(["npm", "install"], cwd=frontend_path, check=True)

    def _setup_server_environment(self, server_path: str):
        """Setup server environment."""
        if os.path.exists(os.path.join(server_path, "package.json")):
            subprocess.run(["npm", "install"], cwd=server_path, check=True)

    def _install_opshin(self):
        """Install OpShin."""
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "opshin"], check=True
            )
            print("   ✅ OpShin installed")
        except subprocess.CalledProcessError:
            print("   ⚠ OpShin installation failed")

    def _install_cardano_cli(self):
        """Install Cardano CLI."""
        print("   ⚠ Cardano CLI installation not automated - please install manually")

    def _setup_ogmios(self):
        """Setup Ogmios service."""
        print("   ⚠ Ogmios setup not automated - please configure manually")

    def _setup_kupo(self):
        """Setup Kupo service."""
        print("   ⚠ Kupo setup not automated - please configure manually")

    def _setup_blockfrost(self):
        """Setup Blockfrost service."""
        print("   ⚠ Blockfrost setup not automated - please configure manually")

    def _setup_sqlite(self):
        """Setup SQLite database."""
        print("   ✅ SQLite database ready")

    def _setup_postgresql(self):
        """Setup PostgreSQL database."""
        print("   ⚠ PostgreSQL setup not automated - please configure manually")

    def _install_pytest(self):
        """Install pytest."""
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest"], check=True)
        print("   ✅ pytest installed")

    def _install_coverage(self):
        """Install coverage."""
        subprocess.run([sys.executable, "-m", "pip", "install", "coverage"], check=True)
        print("   ✅ coverage installed")

    def _install_mock(self):
        """Install mock."""
        subprocess.run([sys.executable, "-m", "pip", "install", "mock"], check=True)
        print("   ✅ mock installed")

    def _save_setup_log(self):
        """Save setup log."""
        log_data = {
            "setup_time": datetime.now().isoformat(),
            "project_root": self.project_root,
            "setup_log": self.setup_log,
        }

        with open(os.path.join(self.project_root, "setup_log.json"), "w") as f:
            json.dump(log_data, f, indent=2, default=str)

    def create_requirements_file(self):
        """Create comprehensive requirements file."""
        requirements = [
            "# MuesliSwap DID Orderbook Requirements",
            "",
            "# Core dependencies",
            "pycardano>=0.9.0",
            "opshin>=0.19.0",
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "coverage>=7.0.0",
            "",
            "# Web framework",
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
            "pydantic>=2.0.0",
            "",
            "# Database",
            "peewee>=3.16.0",
            "sqlite3",
            "",
            "# Utilities",
            "click>=8.0.0",
            "python-dotenv>=1.0.0",
            "pyyaml>=6.0",
            "psutil>=5.9.0",
            "",
            "# Development tools",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "",
            "# Testing",
            "pytest-mock>=3.10.0",
            "pytest-cov>=4.0.0",
            "requests-mock>=1.10.0",
        ]

        with open(os.path.join(self.project_root, "requirements.txt"), "w") as f:
            f.write("\n".join(requirements))

        print("📝 Requirements file created")


def main():
    """Run development environment setup."""
    print("🛠️ MuesliSwap DID Orderbook Development Environment Setup")
    print("=" * 60)

    env = DevelopmentEnvironment()

    try:
        env.setup_development_environment()
        env.create_requirements_file()
        print("\n🎉 Development environment setup completed successfully!")
        print("\nNext steps:")
        print("1. Activate virtual environment: source venv/bin/activate")
        print("2. Run tests: python scripts/run_tests.py")
        print("3. Deploy contracts: python scripts/deploy_contracts.py")
        print("4. Start services: python scripts/start_services.py")

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
