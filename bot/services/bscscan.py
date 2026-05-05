import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "").lower()
REQUIRED_AMOUNT_USDT = float(os.getenv("PRICE_USDT", 10))
# USDT Contract address on BSC mainnet
USDT_CONTRACT_ADDRESS = "0x55d398326f99059fF775485246999027B3197955".lower()

async def verify_transaction(tx_hash: str) -> tuple[bool, str]:
    """
    Verifies a USDT (BEP20) transaction on BSC.
    Returns (success_boolean, message)
    """
    if not BSCSCAN_API_KEY or not WALLET_ADDRESS:
        return False, "BscScan API Key or Wallet Address is not configured."

    url = "https://api.bscscan.com/api"
    params = {
        "module": "account",
        "action": "tokentx",
        "contractaddress": USDT_CONTRACT_ADDRESS,
        "address": WALLET_ADDRESS,
        "page": 1,
        "offset": 100,
        "startblock": 0,
        "endblock": 999999999,
        "sort": "desc",
        "apikey": BSCSCAN_API_KEY
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return False, "Failed to connect to BscScan API."
                
                data = await response.json()
                
                if data["status"] != "1":
                    return False, f"BscScan Error: {data.get('message', 'Unknown error')}"

                transactions = data.get("result", [])
                
                for tx in transactions:
                    if tx["hash"].lower() == tx_hash.lower():
                        # Check if transaction was sent to our wallet
                        if tx["to"].lower() != WALLET_ADDRESS:
                            return False, "Transaction was not sent to the correct wallet address."
                        
                        # Calculate amount (USDT has 18 decimals on BSC)
                        decimals = int(tx["tokenDecimal"])
                        amount_sent = float(tx["value"]) / (10 ** decimals)
                        
                        if amount_sent >= REQUIRED_AMOUNT_USDT:
                            return True, f"Payment verified! Amount: {amount_sent} USDT."
                        else:
                            return False, f"Insufficient payment. Expected {REQUIRED_AMOUNT_USDT} USDT, but received {amount_sent} USDT."
                
                return False, "Transaction hash not found or not a valid USDT (BEP20) transfer to our wallet."
                
        except Exception as e:
            return False, f"Verification failed: {str(e)}"
