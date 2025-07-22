import base58
from typing import Optional, Dict, Any, List
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solana.rpc.commitment import Commitment

from .debugger import Debugger
from lib.helius_client import HeliusClient


def get_wallet_for_telegram_chat(prisma, chat_id: str):
    """Returns the Solana wallet for a Telegram chat, or None if not found."""
    try:
        chat = prisma.telegramchat.find_unique(where={'chatId': chat_id})
        if not chat:
            return None
        return prisma.solanawallet.find_first(where={'telegramChatId': chat.id})
    except Exception as e:
        Debugger.getInstance().error(f"Error getting wallet for chat {chat_id}: {e}")
        return None


def create_wallet_for_telegram_chat(prisma, chat_id: str):
    """Creates and stores a Solana wallet for a Telegram chat if one does not exist."""
    try:
        chat = prisma.telegramchat.find_unique(where={'chatId': chat_id})
        if not chat:
            raise ValueError('TelegramChat not found')
        
        existing = prisma.solanawallet.find_first(where={'telegramChatId': chat.id})
        if existing:
            return existing
        
        keypair = Keypair()
        public_key = str(keypair.public_key)
        secret_key = base58.b58encode(keypair.secret_key).decode('utf-8')
        
        return prisma.solanawallet.create(data={
            'publicKey': public_key,
            'secretKey': secret_key,
            'telegramChatId': chat.id
        })
    except Exception as e:
        Debugger.getInstance().error(f"Error creating wallet for chat {chat_id}: {e}")
        raise


async def get_sol_balance_and_usd(public_key: str) -> Dict[str, float]:
    """Returns the SOL balance, USD value, and SOL price for a given public key."""
    try:
        helius = HeliusClient()
        balance_lamports = await helius.get_sol_balance(public_key)
        balance_in_sol = balance_lamports / 1e9
        
        # For now, we'll use a fixed SOL price. In a real implementation,
        # you'd fetch this from an API like CoinMarketCap
        sol_price = 100.0  # Placeholder price
        balance_usd = balance_in_sol * sol_price
        
        return {
            'balanceInSol': balance_in_sol,
            'balanceUsd': balance_usd,
            'solPrice': sol_price
        }
    except Exception as e:
        Debugger.getInstance().error(f"Error getting SOL balance for {public_key}: {e}")
        raise


async def send_sol(
    sender_wallet: Dict[str, str],
    to_address: str,
    amount_sol: float
) -> str:
    """Sends SOL from the sender's wallet to the specified address."""
    try:
        helius = HeliusClient()
        connection = helius.get_connection()
        
        sender_keypair = Keypair.from_secret_key(
            base58.b58decode(sender_wallet['secretKey'])
        )
        to_pubkey = PublicKey(to_address)
        
        transaction = Transaction().add(
            transfer(TransferParams(
                from_pubkey=sender_keypair.public_key,
                to_pubkey=to_pubkey,
                lamports=int(amount_sol * 1e9)
            ))
        )
        
        signature = await connection.send_transaction(
            transaction,
            sender_keypair,
            commitment=Commitment("confirmed")
        )
        
        return signature.value
    except Exception as e:
        Debugger.getInstance().error(f"Error sending SOL: {e}")
        raise


async def get_max_withdrawable_sol(public_key: str) -> float:
    """Returns the maximum amount of SOL that can be withdrawn from an account."""
    try:
        helius = HeliusClient()
        connection = helius.get_connection()
        
        balance_lamports = await connection.get_balance(PublicKey(public_key))
        rent_exempt_lamports = await connection.get_minimum_balance_for_rent_exemption(0)
        
        # Subtract a small fee (e.g., 5000 lamports)
        fee_lamports = 5000
        max_lamports = max(balance_lamports.value - rent_exempt_lamports - fee_lamports, 0)
        
        return max_lamports / 1e9
    except Exception as e:
        Debugger.getInstance().error(f"Error getting max withdrawable SOL for {public_key}: {e}")
        raise


async def get_token_balance_and_usd(public_key: str) -> List[Dict[str, Any]]:
    """Returns the token balances for a given public key."""
    try:
        helius = HeliusClient()
        token_balances = await helius.get_all_token_balances_for_wallet(public_key)
        
        result = []
        for token in token_balances:
            try:
                token_meta = await helius.get_token_details(token['mint'])
                symbol = token_meta.get('symbol', '')
                name = token_meta.get('name', '')
                
                # For now, we'll use placeholder values for price and USD value
                price = 0.0
                usd_value = 0.0
                
                result.append({
                    'name': name,
                    'address': token['mint'],
                    'symbol': symbol,
                    'amount': token['amount'],
                    'usdValue': usd_value,
                    'price': price
                })
            except Exception as e:
                Debugger.getInstance().error(f"Error processing token {token['mint']}: {e}")
                continue
        
        return result
    except Exception as e:
        Debugger.getInstance().error(f"Error getting token balances for {public_key}: {e}")
        raise


async def get_portfolio(public_key: str) -> Dict[str, Any]:
    """Returns the full portfolio for a given public key."""
    try:
        # Get SOL balance and USD value
        sol = await get_sol_balance_and_usd(public_key)
        sol_token = {
            'name': 'Solana',
            'symbol': 'SOL',
            'amount': sol['balanceInSol'],
            'usdValue': sol['balanceUsd'],
            'price': sol['solPrice'],
            'address': 'So11111111111111111111111111111111111111112'
        }
        
        # Get SPL tokens
        tokens = await get_token_balance_and_usd(public_key)
        
        # Combine and sort
        all_tokens = [sol_token] + tokens
        all_tokens.sort(key=lambda x: x.get('usdValue', 0), reverse=True)
        
        total_usd_value = sum(t.get('usdValue', 0) for t in all_tokens)
        
        return {
            'tokens': all_tokens,
            'totalUsdValue': total_usd_value
        }
    except Exception as e:
        Debugger.getInstance().error(f"Error getting portfolio for {public_key}: {e}")
        raise 