#!/usr/bin/env python3
"""
Wallet Configuration Update Script for OnChain Real Estate AI

This script helps update the wallet configuration to use a funded wallet address
for blockchain transactions. It creates a backup of your existing .env file
and adds the funded wallet's private key.

Usage:
    python update_wallet.py

Note: You will need to manually enter your private key when prompted.
"""

import os
import shutil
import getpass
from datetime import datetime

# Funded wallet address from memory
FUNDED_WALLET_ADDRESS = "0x4F440a019eEDaCDc3C6aa533d3d15F54a66eaF2b"

def main():
    # Path to .env file
    env_path = ".env"
    
    # Create backup of existing .env file
    if os.path.exists(env_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = f".env.backup.{timestamp}"
        shutil.copy2(env_path, backup_path)
        print(f"Created backup of .env file at {backup_path}")
    
    # Get private key from user (securely)
    print("\n===== Wallet Configuration Update =====")
    print(f"Target wallet address: {FUNDED_WALLET_ADDRESS}")
    print("This wallet has 0.148 Sepolia ETH for blockchain transactions.")
    print("\nPlease enter the private key for this wallet address.")
    print("WARNING: Never share your private key with anyone!")
    private_key = getpass.getpass("Private key (input will be hidden): ")
    
    # Validate private key format (basic check)
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key
    
    if len(private_key) != 66 and len(private_key) != 64:  # With or without 0x prefix
        print("Warning: Private key length doesn't look right. It should be 64 characters (without 0x prefix).")
        confirm = input("Continue anyway? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
    
    # Read existing .env content
    env_content = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_content[key.strip()] = value.strip()
    
    # Update or add the private key
    if private_key.startswith("0x"):
        private_key = private_key[2:]  # Remove 0x prefix if present
    env_content["PRIVATE_KEY"] = private_key
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        for key, value in env_content.items():
            f.write(f"{key}={value}\n")
    
    print("\n✅ Wallet configuration updated successfully!")
    print(f"The application will now use the wallet address {FUNDED_WALLET_ADDRESS} for blockchain transactions.")
    print("Restart your application for changes to take effect.")

if __name__ == "__main__":
    main()
