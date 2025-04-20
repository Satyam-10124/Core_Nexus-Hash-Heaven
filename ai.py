import os
import json
import time
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv
from web3 import Web3
from web3.auto import w3
from eth_account import Account
from crewai import Agent, Task, Crew, LLM, Process
from crewai_tools import SerperDevTool
import uvicorn
import logging

# Initialize FastAPI app
app = FastAPI(title="OnChain Real Estate AI", description="API for processing real estate analysis tasks and storing results on the blockchain")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set Serper API key for internet search capability
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
if SERPER_API_KEY:
    os.environ["SERPER_API_KEY"] = SERPER_API_KEY
else:
    logger.warning("SERPER_API_KEY not found in environment. Internet search capability may be limited.")

# Arbitrum Stylus configuration
ARBITRUM_RPC_URL = os.getenv("ARBITRUM_RPC_URL", "https://sepolia-rollup.arbitrum.io/rpc")
# Use the deployed contract address
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x6218F4B695c4b54F7eB02060d80A7Ee3649024e9")

# Set up wallet and private key
try:
    # Use the wallet address with Sepolia ETH for transactions
    # This should be the address that deployed the contract (owner)
    WALLET_ADDRESS = "0x6218F4B695c4b54F7eB02060d80A7Ee3649024e9"  # Use the contract address as a fallback
    
    # Try to get private key from env var first
    PRIVATE_KEY = os.getenv("PRIVATE_KEY")
    if not PRIVATE_KEY:
        logger.warning("Private key not found in environment variables, trying .env file")
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    if line.strip().startswith("PRIVATE_KEY="):
                        PRIVATE_KEY = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                        logger.info("Private key loaded from .env file")
                        break
    
    if not PRIVATE_KEY:
        logger.error("No private key found in environment or .env file")
        raise ValueError("Private key not configured")
    
    # Create account from private key
    account = Account.from_key(PRIVATE_KEY)
    logger.info(f"Using wallet address: {account.address}")
    logger.info(f"Contract address: {CONTRACT_ADDRESS}")
    
    # Check if the account address matches the expected owner address
    EXPECTED_OWNER = os.getenv("CONTRACT_OWNER", account.address)
    if account.address.lower() != EXPECTED_OWNER.lower():
        logger.warning(f"Warning: The account address {account.address} may not be the contract owner {EXPECTED_OWNER}")
except Exception as e:
    logger.error(f"Error setting up wallet: {str(e)}")
    raise 

# For security, properly validate the private key format
# In a production environment, always use environment variables or secure key management
if PRIVATE_KEY:
    # Clean any quotes or whitespace
    PRIVATE_KEY = PRIVATE_KEY.strip().strip('"').strip("'")
    
    # Check if it's a valid private key (should be 64 hex characters or 0x + 64 hex characters)
    if PRIVATE_KEY.startswith("0x"):
        PRIVATE_KEY = PRIVATE_KEY[2:]
        
    if len(PRIVATE_KEY) == 64 and all(c in "0123456789abcdefABCDEF" for c in PRIVATE_KEY):
        logger.info("Valid private key format detected in .env file")
    else:
        logger.error("Invalid private key format in .env file")
        raise ValueError("Private key is not in the correct format. It should be 64 hex characters.")

# Check if private key is available
if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY could not be loaded from .env file")

# Check if contract address is valid
if not CONTRACT_ADDRESS:
    raise ValueError("CONTRACT_ADDRESS is not set in the .env file")
    
if not Web3.is_address(CONTRACT_ADDRESS):
    raise ValueError(f"Invalid CONTRACT_ADDRESS format: {CONTRACT_ADDRESS}")

# Initialize Web3 with Arbitrum
web3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC_URL))

# Validate connection to Arbitrum Sepolia
try:
    chain_id = web3.eth.chain_id
    if chain_id == 421614:  # Arbitrum Sepolia chain ID
        logger.info(f"Successfully connected to Arbitrum Sepolia (Chain ID: {chain_id})")
    else:
        logger.warning(f"Connected to unexpected chain ID: {chain_id} (Expected: 421614 for Arbitrum Sepolia)")
    
    # Check if we're connected
    if web3.is_connected():
        logger.info(f"Web3 connection successful: {ARBITRUM_RPC_URL}")
    else:
        logger.error(f"Web3 connection failed: {ARBITRUM_RPC_URL}")
        raise ConnectionError(f"Could not connect to Arbitrum Sepolia: {ARBITRUM_RPC_URL}")
        
except Exception as e:
    logger.error(f"Error validating Arbitrum connection: {str(e)}")
    raise

# Verify wallet address has funds
wallet_balance = web3.eth.get_balance(account.address)
wallet_balance_eth = web3.from_wei(wallet_balance, 'ether')
logger.info(f"Wallet address: {account.address}")
logger.info(f"Wallet balance: {wallet_balance_eth} ETH")

if wallet_balance == 0:
    logger.warning("Wallet has zero balance. Transactions will fail.")

# Load contract ABI (Application Binary Interface)
contract_abi = None

# Try to load ABI from multiple potential locations
ABI_PATHS = ["AIAgent.json", "contracts/AIAgent.json", "artifacts/contracts/AIAgent.sol/AIAgent.json"]

for path in ABI_PATHS:
    try:
        with open(path, "r") as abi_file:
            data = json.load(abi_file)
            if isinstance(data, list):
                contract_abi = data  # Direct ABI format
                logger.info(f"ABI loaded from {path} (list format)")
                break
            elif 'abi' in data:
                contract_abi = data['abi']  # Extract ABI from contract JSON
                logger.info(f"ABI loaded from {path} (contract JSON format)")
                break
    except Exception as e:
        logger.error(f"Error loading ABI from {path}: {str(e)}")

if contract_abi is None:
    raise FileNotFoundError(f"ABI file not found in any of the expected locations: {ABI_PATHS}")

contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

# Validate contract is deployed and accessible
contract_validated = False
try:
    # Try different ways to validate the contract is deployed
    available_functions = [fn['name'] for fn in contract.abi if fn['type'] == 'function']
    logger.info(f"Available contract functions: {available_functions}")
    
    # Check if basic functions exist
    if 'taskCounter' in available_functions:
        try:
            # Try with a higher gas limit to avoid execution reverted errors
            task_counter = contract.functions.taskCounter().call({'gas': 2000000})
            logger.info(f"Contract deployed at {CONTRACT_ADDRESS} with {task_counter} tasks")
            contract_validated = True
        except Exception as tc_error:
            logger.error(f"Error accessing taskCounter: {str(tc_error)}")
            # Don't fail validation just because of taskCounter error
            # We'll handle this more gracefully later
            contract_validated = True
    
    # Try getTask as an alternative validation
    elif 'getTask' in available_functions:
        try:
            # Just check if the function exists, don't need to actually call it successfully
            contract_validated = True
            logger.info(f"Contract validated through getTask function availability")
        except Exception as gt_error:
            logger.error(f"Error with getTask: {str(gt_error)}")
    
    # Try checking tasks mapping
    elif 'tasks' in available_functions:
        try:
            # Try to access task 1 (may not exist but confirms contract is there)
            contract.functions.tasks(1).call()
            contract_validated = True
            logger.info(f"Contract validated through tasks mapping access")
        except Exception as t_error:
            if "not found" in str(t_error).lower():
                # This is likely because task 1 doesn't exist, but contract is fine
                contract_validated = True
                logger.info(f"Contract validated but task 1 does not exist")
            else:
                logger.error(f"Error accessing tasks: {str(t_error)}")
    
    # If we couldn't validate through standard functions, just try to detect if it's a contract
    if not contract_validated:
        code = web3.eth.get_code(CONTRACT_ADDRESS)
        if code and code != '0x':
            logger.info(f"Contract exists at {CONTRACT_ADDRESS} but has unexpected interface")
            contract_validated = True
        else:
            logger.error(f"No contract code found at {CONTRACT_ADDRESS}")
    
    # If contract is validated, try to determine ownership if possible
    if contract_validated:
        # Try different ways to determine if our account has owner privileges
        try:
            # Check if the contract has an owner function
            if 'owner' in available_functions:
                try:
                    contract_owner = contract.functions.owner().call()
                    logger.info(f"Contract owner: {contract_owner}")
                    
                    if contract_owner.lower() == account.address.lower():
                        logger.info("Account is the contract owner - can complete tasks")
                    else:
                        logger.warning("Account is NOT the contract owner - cannot complete tasks")
                except Exception as o_error:
                    logger.error(f"Error calling owner(): {str(o_error)}")
            
            # If no owner function but complete task exists, try that for permission check
            elif 'completeTask' in available_functions:
                # Try to get gas estimate for a completion call (will fail if not owner)
                # We don't actually execute this, just estimate gas
                try:
                    gas_estimate = contract.functions.completeTask(999, "Test").estimate_gas({
                        "from": account.address
                    })
                    logger.info("Account appears to have owner privileges (can complete tasks)")
                except Exception as perm_error:
                    if "revert" in str(perm_error).lower():
                        logger.warning("Account does NOT have owner privileges")
                    else:
                        # This is likely another error, not a permissions issue
                        logger.error(f"Error testing owner privileges: {str(perm_error)}")
            else:
                logger.warning("Cannot determine ownership status - no suitable functions found")
        except Exception as own_error:
            logger.warning(f"Could not determine ownership status: {str(own_error)}")
        
except Exception as e:
    logger.error(f"Error validating contract deployment: {str(e)}")
    logger.warning("Contract may not be deployed at the specified address, or there's an ABI mismatch")
    # We'll continue anyway, as some functions might still work

# Initialize LLM
try:
    # Try to get Gemini API key directly from .env file if needed
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        with open(".env", "r") as env_file:
            for line in env_file:
                if line.startswith("GEMINI_API_KEY="):
                    gemini_api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    
    logger.info(f"Using Gemini API key: {gemini_api_key[:5]}..." if gemini_api_key else "No Gemini API key found")
    
    llm = LLM(
        model="gemini/gemini-2.0-flash",  # Gemini model
        api_key=gemini_api_key,
        temperature=0.7
    )
    
    # Initialize SerperDevTool for internet search capabilities
    search_tool = SerperDevTool()
except Exception as e:
    logger.error(f"Error initializing LLM: {str(e)}")
    # Fallback to a default LLM if available
    llm = LLM()
    search_tool = None

# Define Pydantic models for request/response validation
class RealEstateTaskRequest(BaseModel):
    task_id: int
    property_address: str
    task_type: str  # market_analysis, property_valuation, investment_analysis, neighborhood_insights, etc.
    additional_details: Optional[Dict[str, Any]] = None

class RealEstateAnalysisOutput(BaseModel):
    roi: str
    cap_rate: str
    cash_flow: str
    appreciation: str
    risk_assessment: str
    recommendations: str
    summary: str

class TaskResponse(BaseModel):
    task_id: int
    local_result: str
    output_json: Optional[Dict[str, Any]] = None
    transaction_hash: Optional[str] = None
    transaction_status: str
    on_chain_result: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    error: str
    task_id: Optional[int] = None
    transaction_hash: Optional[str] = None
    transaction_status: Optional[str] = None
    local_result: Optional[str] = None

class BlockchainTask(BaseModel):
    id: int
    topic: str  # Will contain serialized property info
    result: str
    requester: str

class PropertyDetails(BaseModel):
    address: str
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_footage: Optional[int] = None
    lot_size: Optional[float] = None
    year_built: Optional[int] = None
    price: Optional[float] = None
    features: Optional[List[str]] = None
    location_data: Optional[Dict[str, Any]] = None

# Global task cache to store tasks that fail to be stored on blockchain
task_cache = {}

# Map of transaction hash to task ID for lookup
tx_hash_to_task_id = {}

# Helper function to make objects JSON serializable
def make_json_serializable(obj, max_depth=10, current_depth=0, processed=None):
    # Initialize processed objects tracking on first call
    if processed is None:
        processed = set()
    
    # Return a simple string if max depth reached
    if current_depth >= max_depth:
        return "<max depth reached>"
    
    # Handle simple types directly
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    
    # Check for circular references using object id
    obj_id = id(obj)
    if obj_id in processed:
        return "<circular reference>"
    
    # Add this object to processed set
    processed.add(obj_id)
    
    try:
        if hasattr(obj, '__dict__'):
            # Convert object to dictionary
            return {key: make_json_serializable(value, max_depth, current_depth + 1, processed) 
                    for key, value in obj.__dict__.items()}
        elif isinstance(obj, dict):
            # Recursively convert dictionary values
            return {str(key): make_json_serializable(value, max_depth, current_depth + 1, processed) 
                    for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            # Recursively convert list items
            return [make_json_serializable(item, max_depth, current_depth + 1, processed) 
                    for item in obj]
        elif hasattr(obj, '__str__'):
            # Convert any object with string representation
            return str(obj)
        else:
            # Default fallback
            return "<non-serializable object>"
    finally:
        # Remove this object from processed set when done with this branch
        processed.remove(obj_id)

# Function to save CrewAI agent outputs directly to JSON files
def save_crew_output(crew_result, property_address=None, task_type=None, task_id=None, transaction_hash=None):
    """
    Save the raw output from CrewAI agents to a JSON file
    
    Args:
        crew_result: The result object from crew.kickoff()
        property_address: Optional property address for context
        task_type: Optional task type for context
        task_id: Optional task ID (will be generated if not provided)
        transaction_hash: Optional blockchain transaction hash
        
    Returns:
        The filename where the output was saved
    """
    try:
        # Create results directory if it doesn't exist
        results_dir = os.path.join(os.getcwd(), 'results')
        agents_dir = os.path.join(results_dir, 'agents')
        os.makedirs(agents_dir, exist_ok=True)
        
        # Generate a task ID if not provided
        if task_id is None:
            task_id = int(time.time())
            
        # Generate a unique filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(agents_dir, f"crew_output_{task_id}_{timestamp}.json")
        
        # Make the crew result serializable
        serializable_result = make_json_serializable(crew_result, max_depth=20)
        
        # Prepare the output data structure
        output_data = {
            "task_id": task_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "property_address": property_address,
            "task_type": task_type,
            "transaction_hash": transaction_hash,
            "crew_output": serializable_result
        }
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)
            
        logger.info(f"CrewAI output saved to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error saving CrewAI output: {str(e)}")
        return None

# Function to save AI outputs locally with improved organization
def save_ai_output(task_id, tx_hash, structured_output, result_str, property_address=None, task_type=None):
    try:
        # Create results directory if it doesn't exist
        results_dir = os.path.join(os.getcwd(), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        # Make structured_output serializable first
        serializable_output = make_json_serializable(structured_output)
        
        # Create a dictionary with all the information
        output_data = {
            "task_id": task_id,
            "transaction_hash": tx_hash,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "property_address": property_address,
            "task_type": task_type,
            "structured_output": serializable_output,
            "raw_result": result_str
        }
        
        # Save to a file named with transaction hash
        filename = os.path.join(results_dir, f"task_{task_id}_{tx_hash[:10]}.json")
        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        # Also save to an index file that tracks all tasks
        index_file = os.path.join(results_dir, "task_index.json")
        task_index = []
        
        # Load existing index if it exists
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r') as f:
                    task_index = json.load(f)
            except Exception as idx_error:
                logger.error(f"Error loading task index: {str(idx_error)}")
                task_index = []
        
        # Add this task to the index
        task_summary = {
            "task_id": task_id,
            "transaction_hash": tx_hash,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "property_address": property_address,
            "task_type": task_type,
            "result_file": os.path.basename(filename)
        }
        
        # Update or add to the index
        updated = False
        for i, entry in enumerate(task_index):
            if entry.get("task_id") == task_id:
                task_index[i] = task_summary
                updated = True
                break
        
        if not updated:
            task_index.append(task_summary)
        
        # Save the updated index
        with open(index_file, 'w') as f:
            json.dump(task_index, f, indent=2)
        
        logger.info(f"AI output saved to {filename} and indexed")
        return filename
    except Exception as e:
        logger.error(f"Error saving AI output: {str(e)}")
        return None

# Function to get local task results
def get_local_task_results(task_id=None, tx_hash=None):
    """
    Retrieves task results from local storage
    
    Args:
        task_id: Optional task ID to retrieve
        tx_hash: Optional transaction hash to retrieve
        
    Returns:
        A dictionary containing task data or a list of tasks
    """
    try:
        results_dir = os.path.join(os.getcwd(), 'results')
        
        # If no specific task is requested, return the index of all tasks
        if task_id is None and tx_hash is None:
            index_file = os.path.join(results_dir, "task_index.json")
            if os.path.exists(index_file):
                with open(index_file, 'r') as f:
                    return json.load(f)
            return []
        
        # If task_id is specified, look for files matching that task_id
        if task_id is not None:
            # First check the index
            index_file = os.path.join(results_dir, "task_index.json")
            if os.path.exists(index_file):
                with open(index_file, 'r') as f:
                    task_index = json.load(f)
                    for entry in task_index:
                        if entry.get("task_id") == task_id:
                            result_file = os.path.join(results_dir, entry.get("result_file"))
                            if os.path.exists(result_file):
                                with open(result_file, 'r') as f:
                                    return json.load(f)
            
            # If not found in index or index doesn't exist, search for files directly
            for filename in os.listdir(results_dir):
                if filename.startswith(f"task_{task_id}_") and filename.endswith(".json"):
                    with open(os.path.join(results_dir, filename), 'r') as f:
                        return json.load(f)
        
        # If tx_hash is specified, look for files containing that hash
        if tx_hash is not None:
            tx_hash_prefix = tx_hash[:10]  # We only use first 10 chars in filename
            for filename in os.listdir(results_dir):
                if tx_hash_prefix in filename and filename.endswith(".json"):
                    with open(os.path.join(results_dir, filename), 'r') as f:
                        return json.load(f)
        
        # If we get here, no matching task was found
        return {"error": "Task not found in local storage"}
    
    except Exception as e:
        logger.error(f"Error retrieving local task results: {str(e)}")
        return {"error": f"Error retrieving local task results: {str(e)}"}

# Function to get task data from blockchain
def get_task_from_blockchain(task_id):
    """
    Retrieves task data from the blockchain
    
    Args:
        task_id: The ID of the task to retrieve
        
    Returns:
        A dictionary containing task data or an error message
    """
    try:
        # Check if contract is initialized
        if not contract:
            logger.error("Contract not initialized")
            return {"error": "Contract not initialized"}
            
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
        logger.error(f"Error getting task from blockchain: {str(e)}")
        return {"error": f"Error retrieving task: {str(e)}"}

# Function to get task data by transaction hash
def get_task_by_tx_hash(tx_hash):
    """
    Retrieves task data by transaction hash
    
    Args:
        tx_hash: The transaction hash to look up
        
    Returns:
        A dictionary containing task data or an error message
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
        logger.error(f"Unexpected error in get_task_by_tx_hash: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}

# Function to get recent tasks from blockchain
def get_recent_tasks(count=10):
    """
    Retrieves the most recent tasks from the blockchain
    
    Args:
        count: Number of recent tasks to retrieve
        
    Returns:
        A list of task dictionaries or an error message
    """
    try:
        # Check if contract is initialized
        if not contract:
            logger.error("Contract not initialized")
            return {"error": "Contract not initialized"}
            
        # Get the current task counter
        task_counter = 0
        try:
            # Try with higher gas limit
            task_counter = contract.functions.taskCounter().call({'gas': 2000000})
            logger.info(f"Current task counter: {task_counter}")
        except Exception as counter_error:
            logger.warning(f"Error getting task counter from blockchain: {str(counter_error)}")
            # Fallback: Check local files to estimate task counter
            try:
                # Get all task files from the results directory
                results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
                task_files = [f for f in os.listdir(results_dir) if f.startswith('task_') and f.endswith('.json')]
                
                # Extract task IDs from filenames
                task_ids = []
                for filename in task_files:
                    try:
                        # Extract task ID from filename (format: task_ID_hash.json)
                        parts = filename.split('_')
                        if len(parts) >= 2 and parts[1].isdigit():
                            task_ids.append(int(parts[1]))
                    except:
                        continue
                
                # Use the highest task ID as our counter
                if task_ids:
                    task_counter = max(task_ids)
                    logger.info(f"Using local file-based task counter: {task_counter}")
                else:
                    task_counter = 0
                    logger.info("No local tasks found, using default task counter: 0")
            except Exception as fallback_error:
                logger.error(f"Error in fallback task counter logic: {str(fallback_error)}")
                task_counter = 0
        
        # Determine the range of tasks to retrieve
        start_id = max(1, task_counter - count + 1)
        end_id = task_counter
        
        # Retrieve each task
        tasks = []
        for task_id in range(end_id, start_id - 1, -1):
            task = get_task_from_blockchain(task_id)
            if "error" not in task:
                tasks.append(task)
        
        return tasks
    except Exception as e:
        logger.error(f"Unexpected error retrieving recent tasks: {str(e)}")
        return {"error": f"Unexpected error retrieving recent tasks: {str(e)}"}

# Function to send transaction to blockchain
def send_transaction(function_call, wallet_credentials=None):
    try:
        # Validate function call
        if function_call is None:
            logger.error("Function call is None")
            return None
            
        # Get nonce for sending address
        nonce = web3.eth.get_transaction_count(account.address)
        logger.info(f"Current nonce: {nonce}")
        
        # Check if the function is callable
        if not hasattr(function_call, 'estimate_gas') or not callable(function_call.estimate_gas):
            logger.error(f"Invalid function call object: {type(function_call)}")
            return None
        
        # Estimate gas required for the transaction - use a higher default for Arbitrum Sepolia
        try:
            # First check if the function exists on the contract
            function_name = getattr(function_call, '_function_name', 'unknown')
            logger.info(f"Attempting to call function: {function_name}")
            
            # Try to estimate gas (web3.py versions may vary in parameter support)
            try:
                # First try with timeout parameter (newer web3.py versions)
                gas_estimate = function_call.estimate_gas({'from': account.address}, timeout=60)
            except TypeError:
                # Fallback to standard estimation without timeout for older web3.py versions
                logger.info("Timeout parameter not supported, using standard gas estimation")
                gas_estimate = function_call.estimate_gas({'from': account.address})
            logger.info(f"Estimated gas: {gas_estimate}")
            # Add 100% safety margin for Arbitrum Sepolia which is known to have varying gas requirements
            gas_estimate = int(gas_estimate * 2.0)
            logger.info(f"Adjusted gas estimate with safety margin: {gas_estimate}")
        except Exception as e:
            logger.warning(f"Gas estimation failed: {str(e)}. Using conservative default gas limit.")
            # Check if this is a 'revert' error, which indicates the function will fail
            if 'revert' in str(e).lower():
                logger.error(f"Transaction would revert: {str(e)}")
                # Try to get more details about the revert reason
            
            # Check if this is a revert error
            if "execution reverted" in str(e).lower():
                # Check if it's a permission issue
                if "caller is not the owner" in str(e).lower():
                    logger.error("Transaction failed: Account is not the contract owner")
                    return None
                # Check if it's a size issue
                elif "result too long" in str(e).lower() or "topic too long" in str(e).lower():
                    logger.error("Transaction failed: Data exceeds contract size limits")
                    return None
                else:
                    logger.error(f"Transaction would revert: {str(e)}")
                    # We'll still try to send it with higher gas, as sometimes estimation fails but tx succeeds
            
        # Build transaction with higher gas limit to be safe
        tx_params = {
            'from': account.address,
            'gas': int(gas_estimate * 1.5),  # Add 50% buffer to gas estimate
            'gasPrice': web3.eth.gas_price,
            'nonce': nonce,
            'maxFeePerGas': web3.eth.gas_price * 2,  # Double the current gas price as max fee
            'maxPriorityFeePerGas': web3.eth.gas_price  # Set priority fee to current gas price
        }
        
        # Remove EIP-1559 specific parameters if not supported
        try:
            web3.eth.get_block('latest')['baseFeePerGas']
        except (KeyError, AttributeError):
            # EIP-1559 not supported, remove those fields
            tx_params.pop('maxFeePerGas', None)
            tx_params.pop('maxPriorityFeePerGas', None)
        
        # Build the raw transaction
        raw_tx = function_call.build_transaction(tx_params)
        
        # Sign the transaction
        signed_tx = web3.eth.account.sign_transaction(raw_tx, private_key=PRIVATE_KEY)
        
        # Get the raw transaction data
        if isinstance(signed_tx, dict) and 'rawTransaction' in signed_tx:
            raw_tx_data = signed_tx['rawTransaction']
        elif hasattr(signed_tx, 'rawTransaction'):
            raw_tx_data = signed_tx.rawTransaction
        elif hasattr(signed_tx, 'raw_transaction'):
            raw_tx_data = signed_tx.raw_transaction
        else:
            raise AttributeError("Cannot find raw transaction data in signed transaction object")
            
        # Send the raw transaction with retry logic
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                tx_hash = web3.eth.send_raw_transaction(raw_tx_data)
                logger.info(f"Transaction sent successfully on attempt {attempt+1}")
                
                # Wait for transaction receipt to confirm it was mined
                try:
                    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
                    if receipt.status == 1:
                        logger.info(f"Transaction confirmed successfully: {tx_hash.hex()}")
                    else:
                        logger.error(f"Transaction reverted on-chain: {tx_hash.hex()}")
                        # Return the hash anyway so we can track the failed tx
                except Exception as receipt_error:
                    logger.warning(f"Could not get receipt, but tx was submitted: {str(receipt_error)}")
                
                return tx_hash.hex()
            except Exception as e:
                logger.warning(f"Transaction attempt {attempt+1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    # Increment nonce for next attempt
                    nonce = web3.eth.get_transaction_count(account.address)
                    tx_params['nonce'] = nonce
                    raw_tx = function_call.build_transaction(tx_params)
                    signed_tx = web3.eth.account.sign_transaction(raw_tx, private_key=PRIVATE_KEY)
                    # Get the updated raw tx data
                    if hasattr(signed_tx, 'rawTransaction'):
                        raw_tx_data = signed_tx.rawTransaction
                    elif hasattr(signed_tx, 'raw_transaction'):
                        raw_tx_data = signed_tx.raw_transaction
                else:
                    logger.error(f"Transaction failed after {max_retries} attempts: {str(e)}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error in send_transaction: {str(e)}")
        return None

@app.post("/process_task", response_model=Union[TaskResponse, ErrorResponse])
async def process_task(task_data: RealEstateTaskRequest):
    # Main try-except block for the entire function
    try:
        task_id = task_data.task_id
        property_address = task_data.property_address
        task_type = task_data.task_type
        additional_details = task_data.additional_details or {}
        
        # Initialize structured_output with default values in case of errors
        structured_output = {
            "summary": "Analysis pending",
            "roi": "Not available",
            "cap_rate": "Not available",
            "cash_flow": "Not available",
            "appreciation": "Not available",
            "risk_assessment": "Not available",
            "recommendations": "Not available"
        }
        
        # Create a structured topic for blockchain storage
        topic_data = {
            "property_address": property_address,
            "task_type": task_type,
            "additional_details": additional_details
        }
        
        # Convert to JSON string for blockchain storage
        blockchain_topic = json.dumps(topic_data)
        
        # Log the incoming request
        logger.info(f"Processing task {task_id} for property: {property_address}")
        
        # Create the AI agents specialized for real estate with enhanced locality focus and data-driven approach
        real_estate_analyst = Agent(
            role='Senior Real Estate Market Analyst',
            goal='Deliver authoritative, data-driven market analyses with actionable insights using real-time internet data',
            backstory="""You are a highly respected real estate analyst with 15+ years of experience analyzing property markets.
                       You have a reputation for delivering precise, data-driven analyses that cut through the noise to identify
                       the most significant market factors. You consistently use specific numbers, percentages, and metrics in your
                       analyses rather than vague generalizations. You're known for your ability to synthesize complex market data
                       into clear, actionable insights that help clients make confident decisions. Your reports always include
                       specific price points, growth rates, and comparative metrics. You focus on hyperlocal market dynamics at the
                       neighborhood level and always provide context by comparing local metrics to broader market averages.
                       You structure your analyses with clear bullet points and headers for maximum clarity and impact.
                       You leverage internet search to find the most current market data, trends, and comparable properties.""",
            llm=llm,
            tools=[search_tool],
            verbose=True
        )
        
        property_appraiser = Agent(
            role='Senior Property Appraiser & Valuation Expert',
            goal='Deliver precise property valuations with specific value drivers and comparative metrics using real-time internet data',
            backstory="""You are a highly respected property appraiser with 15+ years of experience and multiple advanced certifications.
                       You're known for delivering valuations with specific dollar amounts, value ranges, and confidence levels rather than
                       vague estimates. Your reports always identify the exact features that drive a property's value with specific dollar
                       or percentage impacts for each feature. You consistently use comparative metrics like price per square foot, value
                       percentile ranking, and neighborhood premium/discount percentages. You have extensive experience with both automated
                       valuation models and traditional appraisal methods. You're skilled at identifying unique property attributes that
                       automated systems miss. You structure your valuations with clear bullet points and headers for maximum clarity and impact.
                       You always provide specific, actionable insights rather than general observations.
                       You leverage internet search to find the most current property values, comparable sales, and market trends.""",
            llm=llm,
            tools=[search_tool],
            verbose=True
        )
        
        investment_advisor = Agent(
            role='Elite Real Estate Investment Strategist',
            goal='Deliver precise investment analyses with specific returns, risks, and growth projections',
            backstory="""You are an elite investment advisor with 15+ years of experience and a track record of identifying
                       high-performing real estate investments. You're known for providing specific ROI projections, cap rates,
                       cash-on-cash returns, and IRR calculations rather than vague potential. Your analyses always include
                       detailed cash flow projections with specific income and expense figures. You quantify investment risks
                       with probability estimates and provide specific mitigation strategies. You have deep expertise in value-add
                       opportunities and can estimate renovation ROIs with remarkable accuracy. You consistently provide comparative
                       metrics showing how an investment performs against market averages. You structure your analyses with clear
                       bullet points and headers for maximum clarity and impact. You always provide specific, actionable insights
                       rather than general observations.""",
            llm=llm,
            tools=[search_tool],
            verbose=True
        )
        
        location_intelligence_specialist = Agent(
            role='Advanced Location Intelligence & Neighborhood Analytics Expert',
            goal='Deliver precise neighborhood analyses with specific metrics, amenities, and livability factors',
            backstory="""You are a renowned location intelligence expert with 15+ years of experience analyzing neighborhoods
                       at a micro level. You're known for providing specific demographic statistics, income levels, and
                       homeownership rates rather than vague descriptions. Your reports always include specific school ratings,
                       test scores, and student-teacher ratios for each nearby school. You quantify crime rates with specific
                       statistics compared to city averages and track safety trends over time. You identify specific amenities
                       with exact walking distances and quality ratings. You provide precise transit scores, commute times, and
                       transportation options. You're skilled at identifying neighborhood transition indicators and gentrification
                       patterns with specific metrics. You structure your analyses with clear bullet points and headers for maximum
                       clarity and impact. You always provide specific, actionable insights rather than general observations.""",
            llm=llm,
            tools=[search_tool],
            verbose=True
        )
        
        # Process the task with our AI agent
        try:
            # Initialize the real estate analyst agent
            real_estate_analyst = Agent(
                role="Real Estate Investment Analyst",
                goal="Provide comprehensive real estate investment analysis",
                backstory="""You are a seasoned real estate investment analyst with 15+ years of experience analyzing properties
                       across various markets. You have deep expertise in ROI calculations, market trend analysis, risk assessment,
                       and investment strategy. You're known for your data-driven approach and ability to identify hidden value and
                       potential pitfalls in real estate investments. Your analyses are thorough, balanced, and actionable, helping
                       investors make informed decisions. You have a particular talent for translating complex market data into clear,
                       strategic recommendations.
                       
                       You're especially skilled at evaluating properties based on cash flow potential, appreciation prospects,
                       tax advantages, and overall return metrics. You can assess both residential and commercial properties
                       with equal expertise. You always consider both macro market trends and micro neighborhood factors in your
                       analysis.
                       
                       When analyzing investment properties, you always include:
                       - Estimated ROI and cap rate calculations
                       - Cash flow projections
                       - Appreciation potential
                       - Risk assessment with probability estimates
                       - Specific recommendations for maximizing returns
                       
                       You present your findings in a clear, structured format that highlights the most important metrics and insights.
                       You're not afraid to recommend against an investment if the numbers don't make sense.""",
                verbose=True,
                llm=llm,
                tools=[search_tool] if search_tool else []
            )
            
            # Create a crew of agents
            crew = Crew(
                agents=[real_estate_analyst],
                tasks=[
                    Task(
                        description=f"""Analyze the investment potential of the property at {property_address}. 
                        Task type: {task_type}.
                        Additional details: {json.dumps(additional_details, indent=2)}
                        
                        Provide a comprehensive analysis including:
                        1. Estimated ROI and cap rate
                        2. Cash flow projections
                        3. Appreciation potential
                        4. Risk assessment
                        5. Specific recommendations
                        
                        You MUST format your response as a JSON object with the following EXACT keys:
                        - roi: Return on investment metrics and calculations
                        - cap_rate: Capitalization rate and related metrics
                        - cash_flow: Cash flow projections and analysis
                        - appreciation: Expected property appreciation over time
                        - risk_assessment: Analysis of investment risks
                        - recommendations: Specific investment recommendations
                        - summary: Brief overview of overall assessment
                        
                        Keep your total response under 2000 characters for blockchain storage efficiency.
                        """,
                        expected_output="A JSON object containing the real estate analysis results",
                        agent=real_estate_analyst,
                        output_json=RealEstateAnalysisOutput
                    )
                ],
                verbose=True,
                process=Process.sequential
            )
            
            # Run the analysis
            result = crew.kickoff()
            logger.info(f"Analysis completed for task {task_id}")
            
            # Save the raw CrewAI output to a JSON file
            crew_output_file = save_crew_output(
                crew_result=result,
                property_address=property_address,
                task_type=task_type,
                task_id=task_id
            )
            logger.info(f"Raw CrewAI output saved to {crew_output_file}")
            
            # The result should now be a dictionary with the RealEstateAnalysisOutput structure
            logger.info(f"AI Analysis result structure: {type(result)}")
            
            # Format the result for blockchain storage and frontend display
            try:
                # Check if we're dealing with CrewOutput type from newer CrewAI versions
                if 'crewai' in str(type(result)):
                    logger.info(f"Detected CrewAI output type: {type(result)}")
                    
                    # Check for TaskOutput
                    if 'TaskOutput' in str(type(result)):
                        logger.info("Processing TaskOutput object")
                        # Extract data from TaskOutput
                        # TaskOutput objects typically contain the result in a specific attribute
                        if hasattr(result, 'output'):
                            crew_data = result.output
                        elif hasattr(result, 'raw'):
                            crew_data = result.raw
                        else:
                            # Convert to serializable format
                            crew_data = make_json_serializable(result)
                    # Check for CrewOutput
                    elif 'CrewOutput' in str(type(result)):
                        logger.info("Processing CrewOutput object")
                        # Extract data from CrewOutput
                        if hasattr(result, 'raw_output'):
                            crew_data = result.raw_output
                        elif hasattr(result, 'final_output'):
                            crew_data = result.final_output
                        else:
                            # Convert to serializable format
                            crew_data = make_json_serializable(result)
                    else:
                        # Generic handling for other crewai output types
                        crew_data = make_json_serializable(result)
                    
                    logger.info(f"Extracted data type: {type(crew_data)}")
                    
                    # Now process the extracted data
                    if isinstance(crew_data, dict):
                        structured_output = crew_data
                        try:
                            result_str = json.dumps(crew_data, indent=2)
                        except TypeError:
                            # If JSON serialization fails, convert to serializable first
                            serializable_data = make_json_serializable(crew_data)
                            structured_output = serializable_data
                            result_str = json.dumps(serializable_data, indent=2)
                    elif isinstance(crew_data, str):
                        try:
                            # Try to parse as JSON
                            structured_output = json.loads(crew_data)
                            result_str = crew_data
                        except json.JSONDecodeError:
                            # If not valid JSON, use the string directly
                            structured_output = {
                                "summary": crew_data[:200] + "...",
                                "roi": "Extracted from result",
                                "cap_rate": "Extracted from result",
                                "cash_flow": "Extracted from result",
                                "appreciation": "Extracted from result",
                                "risk_assessment": "Extracted from result",
                                "recommendations": "Extracted from result"
                            }
                            result_str = json.dumps({"raw_result": crew_data})
                    else:
                        # Convert to serializable format
                        serializable_data = make_json_serializable(crew_data)
                        structured_output = {
                            "summary": str(serializable_data)[:200] + "...",
                            "roi": "Extracted from result",
                            "cap_rate": "Extracted from result",
                            "cash_flow": "Extracted from result",
                            "appreciation": "Extracted from result",
                            "risk_assessment": "Extracted from result",
                            "recommendations": "Extracted from result"
                        }
                        result_str = json.dumps({"raw_result": serializable_data})
                
                # If it's already a dictionary (expected with output_json)
                elif isinstance(result, dict):
                    # Store the structured result for frontend display
                    structured_output = result
                    # Convert to JSON string for blockchain
                    result_str = json.dumps(result, indent=2)
                    logger.info("Successfully processed structured JSON output")
                # Fallback for string results
                elif isinstance(result, str):
                    try:
                        # Try to parse as JSON
                        structured_output = json.loads(result)
                        result_str = result
                        logger.info("Parsed string result into JSON")
                    except json.JSONDecodeError:
                        # If it's not valid JSON, create a basic structure
                        logger.warning("Result is not valid JSON, creating basic structure")
                        structured_output = {
                            "summary": result[:200] + "...",
                            "roi": "Not available",
                            "cap_rate": "Not available",
                            "cash_flow": "Not available",
                            "appreciation": "Not available",
                            "risk_assessment": "Not available",
                            "recommendations": "Not available"
                        }
                        result_str = result
                else:
                    # Unexpected type
                    logger.warning(f"Unexpected result type: {type(result)}")
                    structured_output = {
                        "summary": str(result)[:200] + "...",
                        "roi": "Not available",
                        "cap_rate": "Not available",
                        "cash_flow": "Not available",
                        "appreciation": "Not available",
                        "risk_assessment": "Not available",
                        "recommendations": "Not available"
                    }
                    result_str = json.dumps({"raw_result": str(result)})
            except Exception as format_error:
                logger.error(f"Error formatting result for blockchain: {str(format_error)}")
                # Fallback to a very simple string if all else fails
                result_str = json.dumps({"analysis": "Analysis completed. Error formatting for blockchain."})
                structured_output = {
                    "summary": "Analysis completed with formatting error",
                    "roi": "Not available",
                    "cap_rate": "Not available",
                    "cash_flow": "Not available",
                    "appreciation": "Not available",
                    "risk_assessment": "Not available",
                    "recommendations": "Not available"
                }
            
            # Ensure result is not too long for blockchain storage
            try:
                MAX_BLOCKCHAIN_LENGTH = 7500  # Leave some margin below the 8000 limit
                if len(result_str) > MAX_BLOCKCHAIN_LENGTH:
                    logger.warning(f"Result too long ({len(result_str)} chars), truncating for blockchain storage")
                    # Create a simplified version instead of hard truncating
                    simple_result = {
                        "summary": structured_output.get("summary", "Analysis completed"),
                        "note": "Full analysis available in local storage"
                    }
                    result_str = json.dumps(simple_result)
            except Exception as length_error:
                logger.error(f"Error checking result length: {str(length_error)}")
                # Fallback to a very simple string if all else fails
                result_str = json.dumps({"analysis": "Analysis completed. Error formatting for blockchain."})
        
            # Now handle the blockchain interactions
            # Step 1: Create the blockchain task
            blockchain_task_created = False
            tx_hash = None
            transaction_status = "pending"
            result_tx_hash = None
            
            try:
                # Check if topic is too long for blockchain storage
                MAX_BLOCKCHAIN_TOPIC_LENGTH = 7500  # Slightly less than contract's 8000 limit to be safe
                
                # Truncate topic if needed
                if len(blockchain_topic) > MAX_BLOCKCHAIN_TOPIC_LENGTH:
                    logger.warning(f"Topic too long ({len(blockchain_topic)} chars), truncating for blockchain storage")
                    # Truncate and add indicator
                    blockchain_topic = blockchain_topic[:MAX_BLOCKCHAIN_TOPIC_LENGTH-30] + "... [truncated]"
                
                logger.info(f"Creating blockchain task with topic: {blockchain_topic[:100]}...")
                create_task_function = contract.functions.createTask(blockchain_topic)
                tx_hash = send_transaction(create_task_function)
                
                if tx_hash:
                    logger.info(f"Task {task_id} created on blockchain with tx hash: {tx_hash}")
                    blockchain_task_created = True
                else:
                    logger.warning(f"Failed to create task {task_id} on blockchain")
                    blockchain_task_created = False
            except Exception as e:
                logger.error(f"Error creating blockchain task: {str(e)}")
                blockchain_task_created = False
            
            # Step 2: Store the result on blockchain if task was created successfully
            blockchain_result_stored = False
            
            if blockchain_task_created:
                try:
                    # Check if we're the contract owner before attempting to complete the task
                    try:
                        contract_owner = contract.functions.owner().call()
                        if contract_owner.lower() != account.address.lower():
                            logger.error(f"Account {account.address} is not the contract owner {contract_owner}")
                            logger.error("Cannot complete task - only the contract owner can complete tasks")
                            blockchain_result_stored = False
                            transaction_status = "error_not_owner"
                        else:
                            logger.info(f"Account {account.address} is the contract owner - proceeding with task completion")
                    except Exception as owner_error:
                        logger.warning(f"Could not verify ownership: {str(owner_error)}")
                        # Continue anyway, the transaction will fail if we're not the owner
                    
                    # Only attempt to complete the task if we didn't detect an ownership issue
                    if transaction_status != "error_not_owner":
                        # Attempt to complete the task on blockchain
                        logger.info(f"Completing task {task_id} on blockchain with result: {result_str[:100]}...")
                        complete_task_function = contract.functions.completeTask(task_id, result_str)
                        result_tx_hash = send_transaction(complete_task_function)
                        
                        if result_tx_hash:
                            logger.info(f"Task {task_id} completed on blockchain with tx hash: {result_tx_hash}")
                            blockchain_result_stored = True
                            transaction_status = "completed"
                        else:
                            logger.error(f"Failed to store task {task_id} on blockchain")
                            blockchain_result_stored = False
                            transaction_status = "failed"
                except Exception as e:
                    logger.error(f"Error storing result on blockchain: {str(e)}")
                    blockchain_result_stored = False
                    transaction_status = "error"
        
            # Save the raw CrewAI output to a separate file
            crew_output_file = save_crew_output(
                crew_result=result,
                property_address=property_address,
                task_type=task_type,
                task_id=task_id,
                transaction_hash=result_tx_hash if result_tx_hash else tx_hash
            )
            logger.info(f"CrewAI output saved to {crew_output_file}")
            
            # Save the AI output locally regardless of blockchain status
            saved_file = save_ai_output(
                task_id=task_id, 
                tx_hash=result_tx_hash if result_tx_hash else tx_hash, 
                structured_output=structured_output, 
                result_str=result_str,
                property_address=property_address,
                task_type=task_type
            )
            logger.info(f"AI output saved to {saved_file}")
            
            # Try to get the updated task from blockchain if it was stored successfully
            on_chain_result = None
            if blockchain_result_stored:
                try:
                    on_chain_result = get_task_from_blockchain(task_id)
                except Exception as fetch_error:
                    logger.warning(f"Could not fetch on-chain result after completion: {str(fetch_error)}")
                    on_chain_result = {"id": task_id, "completed": True}
            
            # Return the result with appropriate status
            return TaskResponse(
                task_id=task_id,
                local_result=result_str,
                output_json=structured_output,
                transaction_hash=result_tx_hash if result_tx_hash else tx_hash,
                transaction_status=transaction_status,
                on_chain_result=on_chain_result
            )
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
            # Generate a transaction hash for error response
            error_tx_hash = web3.keccak(text=f"error_{task_id}_{int(time.time())}").hex()
            
            # Try to save whatever output we have
            try:
                # Create a basic structured output for the error case
                error_output = {
                    "summary": f"Error processing task: {str(e)}",
                    "roi": "Not available",
                    "cap_rate": "Not available",
                    "cash_flow": "Not available",
                    "appreciation": "Not available",
                    "risk_assessment": "Not available",
                    "recommendations": "Not available"
                }
                
                # Save the error output locally
                save_ai_output(
                    task_id=task_id,
                    tx_hash=error_tx_hash,
                    structured_output=error_output,
                    result_str=json.dumps({"error": str(e)}),
                    property_address=property_address,
                    task_type=task_type
                )
            except Exception as save_error:
                logger.error(f"Failed to save error output: {str(save_error)}")
            
            # Return error response
            return ErrorResponse(
                error=f"Error processing task: {str(e)}",
                task_id=task_id,
                transaction_hash=error_tx_hash,
                transaction_status="Error"
            )
    
    except Exception as e:
        logger.error(f"Unexpected code path in process_task for task {task_id}")
        
        # Store the task in our local cache so we can still retrieve it later
        try:
            # Check if we have result_str in scope
            if 'result_str' not in locals():
                result_str = json.dumps({"error": f"Failed to process task: {str(e)}"})
                
            # Check if structured_output is defined
            if 'structured_output' not in locals():
                structured_output = {
                    "summary": f"Error: {str(e)[:200]}...",
                    "roi": "Error occurred",
                    "cap_rate": "Error occurred",
                    "cash_flow": "Error occurred",
                    "appreciation": "Error occurred",
                    "risk_assessment": "Error occurred",
                    "recommendations": "Error occurred"
                }
                
            # Create a cached task entry
            cached_task = {
                "id": task_id,
                "topic": json.dumps({
                    "property_address": property_address,
                    "task_type": task_type,
                    "additional_details": additional_details
                }),
                "result": result_str,
                "requester": account.address,
                "completed": True,
                "transaction_hash": tx_hash if 'tx_hash' in locals() else None,
                "transaction_status": "Error",
                "error": f"Failed to process task: {str(e)}"
            }
            task_cache[task_id] = cached_task
            logger.info(f"Stored task {task_id} in local cache due to processing error")
            
            return ErrorResponse(
                error=f"Failed to process task: {str(e)}",
                task_id=task_id,
                transaction_hash=tx_hash if 'tx_hash' in locals() else None,
                transaction_status="Error",
                local_result=result_str
            )
        except Exception as cache_error:
            logger.error(f"Error storing task in cache: {str(cache_error)}")
            
            # If we couldn't store in cache or don't have a result
            return ErrorResponse(
                error=f"Failed to process task: {str(e)}",
                task_id=task_id,
                transaction_hash=tx_hash if 'tx_hash' in locals() else None,
                transaction_status="Error"
            )
        except Exception as final_error:
            # Last resort error handling
            logger.error(f"Critical error in error handling: {str(final_error)}")
            return ErrorResponse(
                error="Critical system error",
                task_id=task_id if 'task_id' in locals() else 0,
                transaction_status="Error"
            )

@app.get("/get_task/{task_id}", response_model=Union[BlockchainTask, ErrorResponse])
async def get_task(task_id: int):
    try:
        logger.info(f"Fetching task {task_id} from blockchain")
        task = get_task_from_blockchain(task_id)
        
        # Check if we got an error or if result is empty
        if "error" in task:
            logger.warning(f"Error fetching task {task_id}: {task['error']}")
            return JSONResponse(status_code=404, content={"error": task["error"]})
        
        if not task["result"]:
            logger.info(f"Task {task_id} exists but has no result yet")
        
        # Always return the on-chain data
        return task
        
    except Exception as e:
        logger.error(f"Exception fetching task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Use the local function to get tasks by transaction hash

@app.get("/task_by_hash/{tx_hash}", response_model=Union[BlockchainTask, ErrorResponse])
async def get_task_by_hash(tx_hash: str = Path(..., description="Transaction hash of the task")):
    try:
        logger.info(f"Fetching task with transaction hash {tx_hash}")
        task = get_task_by_tx_hash(tx_hash)
        
        # Check if we got an error
        if "error" in task:
            logger.warning(f"Error fetching task with hash {tx_hash}: {task['error']}")
            return JSONResponse(status_code=404, content={"error": task["error"]})
        
        # Always return the task data
        return task
        
    except Exception as e:
        logger.error(f"Exception fetching task with hash {tx_hash}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recent_tasks")
async def recent_tasks(count: int = Query(10, description="Number of recent tasks to fetch")):
    try:
        logger.info(f"Fetching {count} recent tasks")
        tasks = get_recent_tasks(count)
        return tasks
    except Exception as e:
        logger.error(f"Error fetching recent tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint for API documentation info
@app.get("/")
async def root():
    return {
        "message": "Welcome to OnChain Real Estate AI API", 
        "description": "This API provides AI-powered real estate analysis with blockchain storage",
        "endpoints": [
            "/process_task - Submit a real estate analysis task",
            "/get_task/{task_id} - Retrieve a specific task from blockchain",
            "/recent_tasks - Get recent tasks from blockchain",
            "/task_result/{task_id} - Get the final result of a task from blockchain",
            "/local_task/{task_id} - Get the complete local result for a task",
            "/local_tasks - Get all locally stored tasks",
            "/local_result/{tx_hash} - Get local result by transaction hash"
        ],
        "documentation": "/docs"
    }

# Endpoint to fetch final on-chain content for a task
@app.get("/task_result/{task_id}")
async def task_result(task_id: int):
    """
    Fetches the final on-chain content for a specific task.
    This endpoint focuses only on retrieving the stored result.
    """
    try:
        logger.info(f"Fetching final result for task {task_id}")
        task = get_task_from_blockchain(task_id)
        
        if "error" in task:
            return JSONResponse(status_code=404, content={"error": task["error"]})
            
        # Return just the result from the on-chain task
        return {
            "task_id": task["id"],
            "topic": task["topic"],
            "result": task["result"],
            "requester": task["requester"]
        }
    except Exception as e:
        logger.error(f"Error fetching task result {task_id}: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/property_types")
async def property_types():
    """Return a list of supported property types for analysis"""
    return {
        "property_types": [
            "Single Family Home",
            "Condominium",
            "Townhouse",
            "Multi-Family",
            "Commercial",
            "Land",
            "Industrial",
            "Mixed-Use"
        ]
    }

@app.get("/analysis_types")
async def analysis_types():
    """Return a list of supported analysis types"""
    return {
        "analysis_types": [
            {"id": "market_analysis", "name": "Market Analysis", "description": "Comprehensive analysis of the local real estate market conditions"},
            {"id": "property_valuation", "name": "Property Valuation", "description": "Detailed valuation of a specific property"},
            {"id": "investment_analysis", "name": "Investment Analysis", "description": "ROI and financial projections for property investments"},
            {"id": "neighborhood_insights", "name": "Neighborhood Insights", "description": "Analysis of neighborhood characteristics and livability"},
            {"id": "rental_analysis", "name": "Rental Analysis", "description": "Rental market analysis and potential rental income"},
            {"id": "development_potential", "name": "Development Potential", "description": "Assessment of property development or improvement potential"}
        ]
    }

@app.get("/local_tasks")
async def get_local_tasks():
    """Retrieve all locally stored task results"""
    try:
        logger.info("Fetching all locally stored tasks")
        tasks = get_local_task_results()
        return tasks
    except Exception as e:
        logger.error(f"Error fetching local tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/local_task/{task_id}")
async def get_local_task(task_id: int):
    """Retrieve a specific task from local storage"""
    try:
        logger.info(f"Fetching local task {task_id}")
        task = get_local_task_results(task_id=task_id)
        
        if "error" in task:
            return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found in local storage"})
        
        return task
    except Exception as e:
        logger.error(f"Error fetching local task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/local_result/{tx_hash}")
async def get_local_result_by_hash(tx_hash: str):
    """Retrieve a task result by transaction hash from local storage"""
    try:
        logger.info(f"Fetching local result for transaction {tx_hash}")
        result = get_local_task_results(tx_hash=tx_hash)
        
        if "error" in result:
            return JSONResponse(status_code=404, content={"error": f"Result for transaction {tx_hash} not found in local storage"})
        
        return result
    except Exception as e:
        logger.error(f"Error fetching local result for transaction {tx_hash}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info(f"Starting OnChain Real Estate AI API server on port 5001")
    uvicorn.run("ai:app", host="0.0.0.0", port=5001, reload=True)
