#!/usr/bin/env python3
"""
Setup script for Alpha Hunter Strategy trading bot
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"  Error: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True


def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'prisma', 'solana', 'requests', 'python-dotenv', 
        'aiohttp', 'numpy', 'pandas'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"✗ Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✓ All required packages are installed")
    return True


def check_env_file():
    """Check if .env file exists"""
    env_file = Path('.env')
    if not env_file.exists():
        print("✗ .env file not found")
        print("Please create a .env file with the following variables:")
        print("DATABASE_URL=postgresql://username:password@localhost:5432/database_name")
        print("DIRECT_URL=postgresql://username:password@localhost:5432/database_name")
        print("HELIUS_API_KEY=your_helius_api_key_here")
        print("JUPITER_API_KEY=your_jupiter_api_key_here")
        return False
    
    print("✓ .env file found")
    return True


def generate_prisma_client():
    """Generate Prisma client"""
    return run_command("prisma generate", "Generate Prisma client")


def main():
    """Main setup function"""
    print("Alpha Hunter Strategy - Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment file
    if not check_env_file():
        sys.exit(1)
    
    # Generate Prisma client
    if not generate_prisma_client():
        print("Failed to generate Prisma client. Make sure Prisma CLI is installed.")
        print("Install with: npm install -g prisma")
        sys.exit(1)
    
    print("\n" + "=" * 40)
    print("✓ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Configure your database and run migrations if needed")
    print("2. Update the configuration in trade_executor.py")
    print("3. Run the bot: python trade_executor.py")


if __name__ == "__main__":
    main() 