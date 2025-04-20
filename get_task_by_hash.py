from fastapi import FastAPI, HTTPException, Query, Depends, Body, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
import json
import logging
import time
import os
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Web3 with Arbitrum Sepolia
ARBITRUM_RPC_URL = os.getenv("ARBITRUM_RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Global task cache to store tasks that fail to be stored on blockchain
task_cache = {}

# Transaction hash to task ID mapping for quick lookups
tx_hash_to_task_id = {}

# Initialize Web3 and contract
try:
    web3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC_URL))
    
    # Check connection
    if not web3.is_connected():
        logger.error(f"Failed to connect to Arbitrum Sepolia at {ARBITRUM_RPC_URL}")
    else:
        logger.info(f"Connected to Arbitrum Sepolia: {web3.client_version}")
        
    # Load contract ABI
    with open("AIAgent.json", "r") as f:
        contract_data = json.load(f)
    
    # Create contract instance
    contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_data["abi"])
    
    # Create account from private key
    account = web3.eth.account.from_key(PRIVATE_KEY)
    logger.info(f"Using account: {account.address}")
    
except Exception as e:
    logger.error(f"Error initializing Web3: {str(e)}")
    web3 = None
    contract = None
    account = None

# Function to get task by transaction hash
def get_task_by_transaction_hash(tx_hash):
    """
    Retrieves a task using its transaction hash
    
    Args:
        tx_hash: The transaction hash to look up
        
    Returns:
        Task data or error message
    """
    try:
        logger.info(f"Looking up task with transaction hash: {tx_hash}")
        
        # First check if we have this transaction hash in our local mapping
        if tx_hash in tx_hash_to_task_id:
            task_id = tx_hash_to_task_id[tx_hash]
            logger.info(f"Found task ID {task_id} for transaction hash {tx_hash} in local mapping")
            
            # Check if the task is in our local cache
            if task_id in task_cache:
                logger.info(f"Found task {task_id} in local cache")
                return task_cache[task_id]
            
            # Try to get the task from the blockchain
            try:
                # Call the getTask function on the smart contract
                task_data = contract.functions.getTask(task_id).call()
                
                # Format the task data
                task = {
                    "id": task_data[0],
                    "topic": task_data[1],
                    "result": task_data[2],
                    "requester": task_data[3],
                    "completed": task_data[4],
                    "transaction_hash": tx_hash
                }
                
                return task
            except Exception as contract_error:
                logger.error(f"Error getting task from blockchain: {str(contract_error)}")
                return {"error": f"Error retrieving task: {str(contract_error)}"}
        
        # If not in our mapping, try to get the transaction receipt from the blockchain
        try:
            # Convert string hash to bytes if needed
            if isinstance(tx_hash, str) and tx_hash.startswith("0x"):
                tx_hash_bytes = Web3.to_bytes(hexstr=tx_hash)
            else:
                tx_hash_bytes = tx_hash
                
            # Get transaction receipt
            receipt = web3.eth.get_transaction_receipt(tx_hash_bytes)
            
            if receipt:
                # Parse logs to find the task ID
                for log in receipt.logs:
                    # Check if this log is from our contract
                    if log['address'].lower() == CONTRACT_ADDRESS.lower():
                        # Try to decode the log
                        try:
                            # Look for TaskCreated or TaskCompleted events
                            task_created_event = contract.events.TaskCreated().process_log(log)
                            if task_created_event:
                                task_id = task_created_event['args']['id']
                                logger.info(f"Found TaskCreated event with task ID: {task_id}")
                                
                                # Store in our mapping for future lookups
                                tx_hash_to_task_id[tx_hash] = task_id
                                
                                # Get the task data
                                return get_task_from_blockchain(task_id)
                        except Exception as decode_error:
                            try:
                                # Try TaskCompleted event
                                task_completed_event = contract.events.TaskCompleted().process_log(log)
                                if task_completed_event:
                                    task_id = task_completed_event['args']['id']
                                    logger.info(f"Found TaskCompleted event with task ID: {task_id}")
                                    
                                    # Store in our mapping for future lookups
                                    tx_hash_to_task_id[tx_hash] = task_id
                                    
                                    # Get the task data
                                    return get_task_from_blockchain(task_id)
                            except Exception:
                                # Not a task event or couldn't decode
                                continue
                
                # If we got here, we couldn't find a task ID in the logs
                logger.warning(f"Transaction {tx_hash} found, but no task events detected")
                return {"error": "Transaction found, but no task events detected"}
            else:
                logger.warning(f"No transaction receipt found for hash {tx_hash}")
                return {"error": "Transaction not found"}
                
        except Exception as tx_error:
            logger.error(f"Error retrieving transaction: {str(tx_error)}")
            
            # Check if this is a locally generated hash for a failed transaction
            for task_id, task in task_cache.items():
                if "transaction_hash" in task and task["transaction_hash"] == tx_hash:
                    logger.info(f"Found cached task for generated hash {tx_hash}")
                    return task
            
            return {"error": f"Error retrieving transaction: {str(tx_error)}"}
    
    except Exception as e:
        logger.error(f"Unexpected error in get_task_by_transaction_hash: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}

# Function to get task from blockchain (needed by get_task_by_transaction_hash)
def get_task_from_blockchain(task_id):
    """
    Retrieves task data from the blockchain
    
    Args:
        task_id: The ID of the task to retrieve
        
    Returns:
        Task data or error message
    """
    try:
        # Check if contract is initialized
        if not contract:
            logger.error("Contract not initialized")
            return {"error": "Contract not initialized"}
            
        # First check if the task is in our local cache
        if task_id in task_cache:
            logger.info(f"Found task {task_id} in local cache")
            return task_cache[task_id]
        
        # Check if the task exists on the blockchain
        try:
            exists = contract.functions.taskExistsCheck(task_id).call()
            if not exists:
                logger.warning(f"Task {task_id} does not exist on blockchain")
                return {"error": f"Task {task_id} does not exist"}
        except Exception as exists_error:
            logger.error(f"Error checking if task exists: {str(exists_error)}")
            # Continue anyway, as the getTask call will fail if the task doesn't exist
        
        # Call the getTask function on the smart contract
        task_data = contract.functions.getTask(task_id).call()
        
        # Format the task data
        task = {
            "id": task_data[0],
            "topic": task_data[1],
            "result": task_data[2],
            "requester": task_data[3],
            "completed": task_data[4]
        }
        
        return task
    except Exception as e:
        logger.error(f"Error retrieving task {task_id}: {str(e)}")
        return {"error": f"Error retrieving task {task_id}: {str(e)}"}
