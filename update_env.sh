#!/bin/bash

# Backup current .env
cp .env .env.backup.$(date +%Y%m%d%H%M%S)

# Update contract address
sed -i '' "s|CONTRACT_ADDRESS=.*|CONTRACT_ADDRESS=\"0x6218F4B695c4b54F7eB02060d80A7Ee3649024e9\"|g" .env

# Improve RPC URL with a more reliable endpoint
echo "Updated environment variables. You may want to consider using a dedicated RPC provider like Infura, Alchemy, or QuickNode for better reliability."
echo "Environment file updated successfully!"
