import aiohttp
import base58
from typing import Dict, Any, Optional
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.commitment_config import CommitmentConfig

from utils.debugger import Debugger
from lib.helius_client import HeliusClient


class JupiterClient:
    def __init__(self):
        self.debug = Debugger.getInstance()
        self.helius_client = HeliusClient()
        self.connection = self.helius_client.get_connection()
        self.quote_url = 'https://lite-api.jup.ag/swap/v1/quote'
        self.swap_url = 'https://lite-api.jup.ag/swap/v1/swap'
    
    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: str,
        slippage_bps: int = 50
    ) -> Dict[str, Any]:
        """Get a quote from Jupiter API."""
        try:
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippageBps': str(slippage_bps),
                'restrictIntermediateTokens': 'true'
            }
            
            self.debug.info('Jupiter /quote request params:', params)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.quote_url, params=params) as response:
                    if not response.ok:
                        raise Exception(f"Jupiter API Error: {response.status}")
                    
                    data = await response.json()
                    return data
        except Exception as e:
            self.debug.error(f"Error getting Jupiter quote: {e}")
            raise
    
    async def get_swap_transaction(
        self,
        quote_response: Dict[str, Any],
        user_public_key: str
    ) -> Dict[str, Any]:
        """Get swap transaction from Jupiter API."""
        try:
            request_body = {
                'quoteResponse': quote_response,
                'userPublicKey': user_public_key,
                'wrapUnwrapSOL': True,
                'asLegacyTransaction': False,
                'dynamicComputeUnitLimit': True,
                'dynamicSlippage': True,
                'prioritizationFeeLamports': {
                    'priorityLevelWithMaxLamports': {
                        'maxLamports': 1000000,
                        'priorityLevel': 'veryHigh'
                    }
                }
            }
            
            self.debug.info('Jupiter /swap request payload:', request_body)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.swap_url,
                    headers={'Content-Type': 'application/json'},
                    json=request_body
                ) as response:
                    if not response.ok:
                        raise Exception(f"Jupiter API Error: {response.status}")
                    
                    data = await response.json()
                    return data
        except Exception as e:
            self.debug.error(f"Error getting Jupiter swap transaction: {e}")
            raise
    
    async def swap(
        self,
        wallet: Dict[str, str],
        input_mint: str,
        output_mint: str,
        amount: str,
        slippage_bps: int = 50
    ) -> Dict[str, Any]:
        """Swap tokens using Jupiter."""
        try:
            self.debug.info('Jupiter swap request', {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippageBps': slippage_bps
            })
            
            quote = await self.get_quote(input_mint, output_mint, amount, slippage_bps)
            
            self.debug.info('Quote received:', {
                'inputAmount': quote.get('inAmount'),
                'outputAmount': quote.get('outAmount'),
                'priceImpact': quote.get('priceImpactPct')
            })
            
            swap_response = await self.get_swap_transaction(quote, wallet['publicKey'])
            
            # Deserialize and sign transaction
            transaction_data = base58.b58decode(swap_response['swapTransaction'])
            transaction = Transaction.deserialize(transaction_data)
            
            keypair = Keypair.from_secret_key(base58.b58decode(wallet['secretKey']))
            transaction.sign(keypair)
            
            self.debug.info('Sending swap transaction...')
            
            signature = await self.connection.send_transaction(
                transaction,
                opts={
                    'skipPreflight': False,
                    'preflightCommitment': 'confirmed',
                    'maxRetries': 3
                }
            )
            
            self.debug.info('Swap transaction sent:', {'signature': signature.value})
            
            confirmation = await self.connection.confirm_transaction(
                signature.value,
                'confirmed'
            )
            
            if confirmation.value.err:
                raise Exception(f"Transaction failed: {confirmation.value.err}")
            
            self.debug.info('Swap transaction confirmed:', {'signature': signature.value})
            
            return {'signature': signature.value, 'quote': quote}
        except Exception as e:
            self.debug.error(f"Error in Jupiter swap: {e}")
            raise
    
    async def buy_token(
        self,
        wallet: Dict[str, str],
        token_mint: str,
        sol_amount: float,
        slippage_bps: int = 50
    ) -> Dict[str, Any]:
        """Buy a token using SOL as input."""
        sol_mint = 'So11111111111111111111111111111111111111112'
        amount_in_lamports = str(int(sol_amount * 1e9))
        
        # Execute the swap and get both signature and quote
        result = await self.swap(wallet, sol_mint, token_mint, amount_in_lamports, slippage_bps)
        
        return {
            'signature': result['signature'],
            'outputAmount': result['quote']['outAmount']
        }
    
    async def sell_token(
        self,
        wallet: Dict[str, str],
        token_mint: str,
        token_amount: float,
        slippage_bps: int = 50
    ) -> str:
        """Sell a token for SOL."""
        sol_mint = 'So11111111111111111111111111111111111111112'
        
        # Get decimals for the token
        token_meta = await self.helius_client.get_token_details(token_mint)
        amount_in_base_units = str(int(token_amount * (10 ** token_meta['decimals'])))
        
        result = await self.swap(wallet, token_mint, sol_mint, amount_in_base_units, slippage_bps)
        return result['signature']
    
    def get_connection(self):
        """Get the Solana connection."""
        return self.connection 