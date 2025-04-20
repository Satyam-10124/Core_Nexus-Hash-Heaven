# OnChain Real Estate AI with Arbitrum Stylus

This project combines AI-powered real estate analysis with blockchain storage using Arbitrum Stylus. It leverages Rust for smart contracts and Python for the AI backend.

## Features

- AI-powered real estate market analysis
- Property valuation and investment analysis
- Neighborhood insights and development potential assessment
- Immutable blockchain storage of all analyses using Arbitrum Stylus
- FastAPI backend with CrewAI for sophisticated multi-agent analysis

## Prerequisites

- Node.js and npm
- Rust and Cargo
- Python 3.9+
- Cargo Stylus (`cargo install cargo-stylus`)

## Environment Setup

Create a `.env` file with the following variables:

```
ARBITRUM_RPC_URL=https://sepolia-rollup.arbitrum.io/rpc
PRIVATE_KEY=your_private_key
CONTRACT_ADDRESS=deployed_contract_address
GEMINI_API_KEY=your_gemini_api_key
ARBISCAN_API_KEY=your_arbiscan_api_key
```

## Installation

1. Install JavaScript dependencies:

```shell
npm install
```

2. Install Python dependencies:

```shell
pip install -r requirements.txt
```

## Deploying the Stylus Contract

1. Build the Rust contract for Stylus:

```shell
npm run build:stylus
```

2. Deploy to Arbitrum Sepolia testnet:

```shell
npm run deploy:stylus
```

## Running the AI Server

Start the FastAPI server:

```shell
python ai.py
```

The server will be available at http://localhost:5001

## API Usage

### Process a Real Estate Analysis Task

```shell
curl -X POST http://localhost:5001/process_task \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": 1,
    "property_address": "123 Main St, San Francisco, CA 94105",
    "task_type": "market_analysis",
    "additional_details": {
      "property_details": {
        "property_type": "Single Family Home",
        "bedrooms": 3,
        "bathrooms": 2,
        "square_footage": 1800
      }
    }
  }'
```

### Get Available Analysis Types

```shell
curl http://localhost:5001/analysis_types
```

### Get Property Types

```shell
curl http://localhost:5001/property_types
```

### Retrieve a Task Result

```shell
curl http://localhost:5001/task_result/1
```

## Arbitrum Stylus Benefits

- **Performance**: Rust contracts are more gas-efficient than Solidity
- **Security**: Rust's memory safety features reduce smart contract vulnerabilities
- **Scalability**: Arbitrum's Layer 2 solution provides faster transactions at lower costs
- **Interoperability**: Full compatibility with the Ethereum ecosystem
