// Simplified deployment script for Arbitrum
const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Deploying AIAgent contract to Arbitrum...");

  // Get the deployer account
  const [deployer] = await hre.ethers.getSigners();
  console.log(`Deploying from account: ${deployer.address}`);
  
  // Check balance
  const balance = await deployer.getBalance();
  console.log(`Account balance: ${hre.ethers.formatEther(balance)} ETH`);

  try {
    // Deploy the Solidity contract instead of Rust
    console.log("Compiling contract...");
    await hre.run("compile");
    
    console.log("Deploying contract...");
    const AIAgent = await hre.ethers.getContractFactory("AIAgent");
    const aiAgent = await AIAgent.deploy();
    
    await aiAgent.waitForDeployment();
    const contractAddress = await aiAgent.getAddress();
    
    console.log(`AIAgent contract deployed to: ${contractAddress}`);
    
    // Save the contract address to a file
    const deploymentInfo = {
      network: hre.network.name,
      chainId: hre.network.config.chainId.toString(),
      contractAddress,
      deploymentTime: new Date().toISOString(),
      deployer: deployer.address
    };
    
    fs.writeFileSync(
      path.join(__dirname, "../deployment-info.json"),
      JSON.stringify(deploymentInfo, null, 2)
    );
    
    console.log("Deployment information saved to deployment-info.json");
    
    // Update the .env file with the new contract address
    const envPath = path.join(__dirname, "../.env");
    let envContent = "";
    
    if (fs.existsSync(envPath)) {
      envContent = fs.readFileSync(envPath, "utf8");
      
      // Replace or add CONTRACT_ADDRESS
      if (envContent.includes("CONTRACT_ADDRESS=")) {
        envContent = envContent.replace(
          /CONTRACT_ADDRESS=.*/,
          `CONTRACT_ADDRESS=${contractAddress}`
        );
      } else {
        envContent += `\nCONTRACT_ADDRESS=${contractAddress}\n`;
      }
      
      // Add ARBITRUM_RPC_URL if it doesn't exist
      if (!envContent.includes("ARBITRUM_RPC_URL=")) {
        envContent += `ARBITRUM_RPC_URL=https://sepolia-rollup.arbitrum.io/rpc\n`;
      }
      
      fs.writeFileSync(envPath, envContent);
      console.log(".env file updated with new contract address");
    } else {
      console.warn(".env file not found. Please manually update your environment variables.");
    }
    
  } catch (error) {
    console.error("Deployment failed:", error);
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
