import aiohttp
import json
from typing import Dict, Any, List, Optional
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey as PublicKey

from utils.debugger import Debugger
from utils.secrets import get_helius_api_key


class HeliusClient:
    def __init__(self):
        self.api_key = get_helius_api_key()
        self.base_url = 'https://mainnet.helius-rpc.com'
        self.debug = Debugger.getInstance()
    
    def get_connection(self) -> AsyncClient:
        """Returns a Solana RPC client using the Helius endpoint and API key."""
        return AsyncClient(f"{self.base_url}/?api-key={self.api_key}")
    
    async def get_transaction_details(self, signature: str) -> Dict[str, Any]:
        """Get transaction details from Helius API."""
        try:
            request_body = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    signature,
                    {
                        "encoding": "json",
                        "maxSupportedTransactionVersion": 0
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/?api-key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json=request_body
                ) as response:
                    if not response.ok:
                        raise Exception(f"Helius API Error: {response.status}")
                    
                    data = await response.json()
                    if "error" in data:
                        raise Exception(f"Helius API Error: {data['error']['message']}")
                    
                    return data.get("result", {})
        except Exception as e:
            self.debug.error(f"Error fetching transaction details: {e}")
            raise
    
    async def get_token_details(self, mint_address: str) -> Dict[str, Any]:
        """Get token metadata from Helius API."""
        try:
            request_body = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAsset",
                "params": {
                    "id": mint_address,
                    "displayOptions": {
                        "showFungible": True
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/?api-key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json=request_body
                ) as response:
                    if not response.ok:
                        raise Exception(f"Helius API Error: {response.status}")
                    
                    data = await response.json()
                    if "error" in data:
                        raise Exception(f"Helius API Error: {data['error']['message']}")
                    
                    result = data.get("result", {})
                    return {
                        "name": result.get("content", {}).get("metadata", {}).get("name", ""),
                        "symbol": result.get("content", {}).get("metadata", {}).get("symbol", ""),
                        "decimals": result.get("token_info", {}).get("decimals", 0),
                        "supply": result.get("token_info", {}).get("supply", 0),
                        "image": result.get("content", {}).get("links", {}).get("image", "")
                    }
        except Exception as e:
            self.debug.error(f"Error fetching token metadata: {e}")
            raise
    
    async def get_sol_balance(self, public_key: str) -> int:
        """Get SOL balance in lamports."""
        try:
            request_body = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [public_key]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/?api-key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json=request_body
                ) as response:
                    if not response.ok:
                        raise Exception(f"Helius API Error: {response.status}")
                    
                    data = await response.json()
                    if "error" in data:
                        raise Exception(f"Helius API Error: {data['error']['message']}")
                    
                    return data.get("result", {}).get("value", 0)
        except Exception as e:
            self.debug.error(f"Error fetching SOL balance: {e}")
            raise
    
    async def get_all_token_balances_for_wallet(self, public_key: str) -> List[Dict[str, Any]]:
        """Get all SPL token balances for a wallet."""
        try:
            # Get SPL token accounts
            spl_request_body = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    public_key,
                    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                    {"encoding": "jsonParsed"}
                ]
            }
            
            # Get Metaplex token accounts
            metaplex_request_body = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    public_key,
                    {"programId": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"},
                    {"encoding": "jsonParsed"}
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                # Get SPL token accounts
                async with session.post(
                    f"{self.base_url}/?api-key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json=spl_request_body
                ) as response:
                    if not response.ok:
                        raise Exception(f"Helius API Error: {response.status}")
                    
                    spl_data = await response.json()
                    spl_accounts = spl_data.get("result", {}).get("value", [])
                
                # Get Metaplex token accounts
                async with session.post(
                    f"{self.base_url}/?api-key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json=metaplex_request_body
                ) as response:
                    if not response.ok:
                        raise Exception(f"Helius API Error: {response.status}")
                    
                    metaplex_data = await response.json()
                    metaplex_accounts = metaplex_data.get("result", {}).get("value", [])
                
                # Combine all token accounts
                all_accounts = spl_accounts + metaplex_accounts
                
                # Get balances for each token account
                balances = []
                for account in all_accounts:
                    try:
                        token_account_address = account["pubkey"]
                        mint = account["account"]["data"]["parsed"]["info"]["mint"]
                        
                        # Get balance for this token account
                        balance_request_body = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "getTokenAccountBalance",
                            "params": [token_account_address]
                        }
                        
                        async with session.post(
                            f"{self.base_url}/?api-key={self.api_key}",
                            headers={"Content-Type": "application/json"},
                            json=balance_request_body
                        ) as balance_response:
                            if balance_response.ok:
                                balance_data = await balance_response.json()
                                amount = balance_data.get("result", {}).get("value", {}).get("uiAmount", 0)
                                decimals = balance_data.get("result", {}).get("value", {}).get("decimals", 0)
                                
                                balances.append({
                                    "mint": mint,
                                    "amount": amount,
                                    "decimals": decimals,
                                    "tokenAccount": token_account_address
                                })
                    except Exception as e:
                        self.debug.error(f"Error processing token account {account.get('pubkey', 'unknown')}: {e}")
                        continue
                
                return balances
        except Exception as e:
            self.debug.error(f"Error fetching token balances: {e}")
            raise 