# OnChain Real Estate AI Platform API Documentation

This document provides comprehensive documentation for the OnChain Real Estate AI Platform API, which enables blockchain-powered AI analysis for real estate properties.

## Base URL

```
http://localhost:5001
```

## Authentication

Currently, the API does not require authentication. However, blockchain interactions require a valid wallet with sufficient ETH on the Arbitrum Sepolia testnet.

## Blockchain Configuration

- **Network**: Arbitrum Sepolia Testnet
- **Contract Address**: 0x6218F4B695c4b54F7eB02060d80A7Ee3649024e9
- **Current Wallet Address**: 0x053E848a6141867f66924cbc093A7e273ed4Ea04

## API Endpoints

### 1. Process Task

Creates a new real estate analysis task and submits it to the blockchain.

**Endpoint**: `/process_task`  
**Method**: POST  
**Content-Type**: application/json

#### Request Body

```json
{
  "task_id": 1,
  "property_address": "123 Main St, Springfield, IL",
  "task_type": "investment_analysis",
  "additional_details": {
    "extra_info": "Research on real estate trends"
  }
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| task_id | integer | Unique identifier for the task |
| property_address | string | Physical address of the property |
| task_type | string | Type of analysis (market_analysis, property_valuation, investment_analysis, neighborhood_insights) |
| additional_details | object | Optional additional information for the analysis |

#### Sample Request

```bash
curl -X 'POST' \
  'http://localhost:5001/process_task' \
  -H 'Content-Type: application/json' \
  -d '{
    "task_id": 1,
    "property_address": "123 Main St, Springfield, IL",
    "task_type": "investment_analysis",
    "additional_details": {
      "extra_info": "Research on real estate trends"
    }
  }'
```

#### Successful Response

```json
{
  "task_id": 1,
  "local_result": "{\"roi\": \"28% cash-on-cash return based on $30,000 down payment.\", \"cap_rate\": \"5.6% cap rate based on $150,000 property value.\", \"cash_flow\": \"$700 monthly positive cash flow after all expenses.\", \"appreciation\": \"Expected 3.2% annual appreciation based on neighborhood trends.\", \"risk_assessment\": \"Medium risk investment with strong rental demand in the area.\", \"recommendations\": \"Consider value-add opportunities through minor renovations to increase rent by 15%.\"}",
  "transaction_hash": "0x8f7d7e8c5f5a4e3d2c1b0a9e6d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9e8d7c6b5",
  "transaction_status": "Pending",
  "on_chain_result": null
}
```

#### Failed Response

```json
{
  "error": "Transaction failed or was rejected",
  "task_id": 1,
  "transaction_hash": "0x8f7d7e8c5f5a4e3d2c1b0a9e6d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9e8d7c6b5",
  "transaction_status": "Failed",
  "local_result": "{\"roi\": \"28% cash-on-cash return based on $30,000 down payment.\", \"cap_rate\": \"5.6% cap rate based on $150,000 property value.\"...}"
}
```

### 2. Get Task

Retrieves a specific task from the blockchain by its ID.

**Endpoint**: `/get_task/{task_id}`  
**Method**: GET  
**Path Parameter**: task_id (integer)

#### Sample Request

```bash
curl -X 'GET' 'http://localhost:5001/get_task/1'
```

#### Successful Response

```json
{
  "id": 1,
  "topic": "{\"property_address\":\"123 Main St, Springfield, IL\",\"task_type\":\"investment_analysis\",\"additional_details\":{\"extra_info\":\"Research on real estate trends\"}}",
  "result": "{\"roi\":\"28%\",\"cap_rate\":\"5.6%\",\"cash_flow\":\"$700/month\",\"appreciation\":\"3.2%\"}",
  "requester": "0x053E848a6141867f66924cbc093A7e273ed4Ea04",
  "completed": true
}
```

#### Failed Response

```json
{
  "error": "Task 1 does not exist on the blockchain"
}
```

### 3. Task by Transaction Hash

Retrieves a task using its blockchain transaction hash instead of task ID. This is useful when you have the transaction hash from the blockchain but don't know the corresponding task ID.

**Endpoint**: `/task_by_hash/{tx_hash}`  
**Method**: GET  
**Path Parameter**: tx_hash (string) - The blockchain transaction hash

#### Sample Request

```bash
curl -X 'GET' 'http://localhost:5001/task_by_hash/0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
```

#### Successful Response

```json
{
  "id": 1,
  "topic": "{\"property_address\":\"123 Main St, Springfield, IL\",\"task_type\":\"investment_analysis\",\"additional_details\":{\"extra_info\":\"Research on real estate trends\"}}",
  "result": "{\"roi\":\"28%\",\"cap_rate\":\"5.6%\",\"cash_flow\":\"$700/month\",\"appreciation\":\"3.2%\"}",
  "requester": "0x053E848a6141867f66924cbc093A7e273ed4Ea04",
  "completed": true,
  "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
}
```

#### Failed Response

```json
{
  "error": "Transaction not found or no task associated with this transaction hash"
}
```

### 4. Task Result

Fetches the final on-chain content for a specific task, focusing only on the stored result.

**Endpoint**: `/task_result/{task_id}`  
**Method**: GET  
**Path Parameter**: task_id (integer)

#### Sample Request

```bash
curl -X 'GET' 'http://localhost:5001/task_result/1'
```

#### Successful Response

```json
{
  "task_id": 1,
  "topic": "{\"property_address\":\"123 Main St, Springfield, IL\",\"task_type\":\"investment_analysis\",\"additional_details\":{\"extra_info\":\"Research on real estate trends\"}}",
  "result": "{\"roi\":\"28%\",\"cap_rate\":\"5.6%\",\"cash_flow\":\"$700/month\",\"appreciation\":\"3.2%\"}",
  "requester": "0x053E848a6141867f66924cbc093A7e273ed4Ea04"
}
```

#### Failed Response

```json
{
  "error": "Task 1 does not exist on the blockchain"
}
```

### 4. Recent Tasks

Retrieves a list of the most recent tasks from the blockchain.

**Endpoint**: `/recent_tasks`  
**Method**: GET  
**Query Parameter**: count (integer, default=10) - Number of recent tasks to fetch

#### Sample Request

```bash
curl -X 'GET' 'http://localhost:5001/recent_tasks?count=5'
```

#### Successful Response

```json
[
  {
    "id": 10,
    "topic": "{\"property_address\":\"456 Oak Ave, Chicago, IL\",\"task_type\":\"market_analysis\"}",
    "result": "{\"market_trends\":\"Upward\",\"comparable_sales\":\"$350k-$400k\"}",
    "requester": "0x053E848a6141867f66924cbc093A7e273ed4Ea04",
    "completed": true
  },
  {
    "id": 9,
    "topic": "{\"property_address\":\"789 Pine St, Boston, MA\",\"task_type\":\"property_valuation\"}",
    "result": "{\"estimated_value\":\"$425,000\",\"confidence\":\"high\"}",
    "requester": "0x053E848a6141867f66924cbc093A7e273ed4Ea04",
    "completed": true
  }
]
```

#### Failed Response

```json
{
  "error": "Error getting task counter: ('execution reverted', 'no data')"
}
```

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of requests:

- **200 OK**: The request was successful
- **400 Bad Request**: The request was malformed or invalid
- **404 Not Found**: The requested resource was not found
- **500 Internal Server Error**: An error occurred on the server

Error responses include a JSON object with an `error` field containing a description of the error.

## Blockchain Interaction Notes

1. **Transaction Status**: When a task is submitted to the blockchain, the transaction may be in a "Pending" state initially. You should check the task status later using the `/get_task/{task_id}` endpoint.

2. **Transaction Hash Lookup**: Every blockchain transaction has a unique transaction hash. You can use the `/task_by_hash/{tx_hash}` endpoint to retrieve task details using this hash instead of the task ID. This is particularly useful when you have the transaction hash from a blockchain explorer but don't know the corresponding task ID.

3. **Local Caching**: The system maintains a local cache of tasks that failed to be stored on the blockchain. These tasks can still be retrieved using their task ID or transaction hash.

4. **Owner Privileges**: Some blockchain operations (like completing tasks) require owner privileges. If your wallet is not the contract owner, these operations will fail with appropriate error messages.

5. **Gas Fees**: All blockchain transactions require gas fees in Sepolia ETH. Ensure your wallet has sufficient funds.

6. **Transaction Failures**: If a blockchain transaction fails, the API will still return a transaction hash that can be used to look up the failed transaction on a blockchain explorer.

## Sample Workflow

1. Submit a new real estate analysis task:
   ```bash
   curl -X 'POST' 'http://localhost:5001/process_task' -H 'Content-Type: application/json' -d '{"task_id": 1, "property_address": "123 Main St, Springfield, IL", "task_type": "investment_analysis", "additional_details": {"extra_info": "Research on real estate trends"}}'
   ```

2. Check the task status on the blockchain:
   ```bash
   curl -X 'GET' 'http://localhost:5001/get_task/1'
   ```

3. Retrieve a task by transaction hash:
   ```bash
   curl -X 'GET' 'http://localhost:5001/task_by_hash/0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
   ```

4. Retrieve just the analysis result:
   ```bash
   curl -X 'GET' 'http://localhost:5001/task_result/1'
   ```

5. View recent tasks:
   ```bash
   curl -X 'GET' 'http://localhost:5001/recent_tasks'
   ```
