import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_secrets() -> Dict[str, Any]:
    """Get all secrets from environment variables"""
    return {
        'heliusApiKey': os.getenv('HELIUS_API_KEY'),
        'databaseUrl': os.getenv('DATABASE_URL'),
        'directUrl': os.getenv('DIRECT_URL'),
        'jupiterApiKey': os.getenv('JUPITER_API_KEY'),
    }


def get_helius_api_key() -> str:
    """Get Helius API key from environment"""
    api_key = os.getenv('HELIUS_API_KEY')
    if not api_key:
        raise ValueError("HELIUS_API_KEY environment variable is required")
    return api_key


def get_database_url() -> str:
    """Get database URL from environment"""
    url = os.getenv('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable is required")
    return url


def get_direct_url() -> str:
    """Get direct database URL from environment"""
    url = os.getenv('DIRECT_URL')
    if not url:
        raise ValueError("DIRECT_URL environment variable is required")
    return url 