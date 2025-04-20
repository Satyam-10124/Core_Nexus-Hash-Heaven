// Direct deployment script using ethers.js
const { ethers } = require('ethers');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

async function main() {
  console.log("Deploying AIAgent contract to Arbitrum...");

  // Load environment variables
  const privateKey = process.env.PRIVATE_KEY;
  const arbitrumRpcUrl = process.env.ARBITRUM_RPC_URL || "https://sepolia-rollup.arbitrum.io/rpc";
  
  if (!privateKey) {
    console.error("Missing PRIVATE_KEY in .env file");
    process.exit(1);
  }

  // Connect to Arbitrum network
  const provider = new ethers.JsonRpcProvider(arbitrumRpcUrl);
  const wallet = new ethers.Wallet(privateKey, provider);
  
  // Load contract ABI and bytecode
  const contractPath = path.join(__dirname, '../artifacts/contracts/AIAgent.sol/AIAgent.json');
  if (!fs.existsSync(contractPath)) {
    console.error("Contract artifact not found. Please compile the contract first.");
    process.exit(1);
  }
  
  const contractArtifact = JSON.parse(fs.readFileSync(contractPath, 'utf8'));
  
  // Display account info
  console.log(`Deploying from account: ${wallet.address}`);
  const balance = await provider.getBalance(wallet.address);
  console.log(`Account balance: ${ethers.formatEther(balance)} ETH`);
  
  if (balance === 0n) {
    console.error("Account has no ETH. Please fund your account to deploy contracts.");
    process.exit(1);
  }

  try {
    // Deploy contract
    console.log("Deploying contract...");
    const factory = new ethers.ContractFactory(
      contractArtifact.abi,
      contractArtifact.bytecode,
      wallet
    );
    
    const contract = await factory.deploy();
    await contract.waitForDeployment();
    
    const contractAddress = await contract.getAddress();
    console.log(`AIAgent contract deployed to: ${contractAddress}`);
    
    // Save deployment info
    const network = await provider.getNetwork();
    const deploymentInfo = {
      network: network.name,
      chainId: network.chainId.toString(),
      contractAddress,
      deploymentTime: new Date().toISOString(),
      deployer: wallet.address
    };
    
    fs.writeFileSync(
      path.join(__dirname, "../deployment-info.json"),
      JSON.stringify(deploymentInfo, null, 2)
    );
    
    console.log("Deployment information saved to deployment-info.json");
    
    // Update .env file
    const envPath = path.join(__dirname, "../.env");
    if (fs.existsSync(envPath)) {
      let envContent = fs.readFileSync(envPath, "utf8");
      
      // Replace or add CONTRACT_ADDRESS
      if (envContent.includes("CONTRACT_ADDRESS=")) {
        envContent = envContent.replace(
          /CONTRACT_ADDRESS=.*/,
          `CONTRACT_ADDRESS="${contractAddress}"`
        );
      } else {
        envContent += `\nCONTRACT_ADDRESS="${contractAddress}"\n`;
      }
      
      fs.writeFileSync(envPath, envContent);
      console.log(".env file updated with new contract address");
    }
    
  } catch (error) {
    console.error("Deployment failed:", error);
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch(error => {
    console.error(error);
    process.exit(1);
  });
