#!/usr/bin/env python3
"""
Utility script to check if the current wallet is the owner of the contract
"""

import os
import json
import logging
from web3 import Web3
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(process)d - %(filename)s-%(module)s:%(lineno)d - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get blockchain configuration from environment
ARBITRUM_RPC_URL = os.getenv("ARBITRUM_RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Initialize Web3
web3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC_URL))
account = web3.eth.account.from_key(PRIVATE_KEY)

logger.info(f"Connected to Arbitrum Sepolia: {web3.is_connected()}")
logger.info(f"Current account address: {account.address}")

# Load contract ABI
try:
    with open("AIAgent.json", "r") as abi_file:
        contract_abi = json.load(abi_file)
    
    # Initialize contract
    contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)
    
    # Check if the contract has an owner function
    if 'owner' in [fn['name'] for fn in contract_abi if fn.get('type') == 'function']:
        try:
            contract_owner = contract.functions.owner().call()
            logger.info(f"Contract owner address: {contract_owner}")
            
            if contract_owner.lower() == account.address.lower():
                logger.info("✅ SUCCESS: Current account IS the contract owner")
            else:
                logger.warning(f"❌ WARNING: Current account is NOT the contract owner")
                logger.info(f"To fix this issue, either:")
                logger.info(f"1. Update your PRIVATE_KEY in .env to match the owner's private key")
                logger.info(f"2. Transfer ownership of the contract to your current account using transferOwnership()")
        except Exception as e:
            logger.error(f"Error calling owner(): {str(e)}")
    else:
        logger.error("Contract does not have an owner function")
except Exception as e:
    logger.error(f"Error initializing contract: {str(e)}")
