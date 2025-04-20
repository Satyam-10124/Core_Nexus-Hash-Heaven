// Deployment script for Arbitrum Stylus AIAgent contract
const { ethers } = require("hardhat");
const path = require("path");
const fs = require("fs");

async function main() {
  console.log("Deploying AIAgent contract to Arbitrum Stylus...");

  // Get the network configuration
  const network = await ethers.provider.getNetwork();
  console.log(`Network: ${network.name} (${network.chainId})`);

  // Get the deployer account
  const [deployer] = await ethers.getSigners();
  console.log(`Deploying from account: ${deployer.address}`);
  
  // Check balance
  const balance = await deployer.getBalance();
  console.log(`Account balance: ${ethers.utils.formatEther(balance)} ETH`);

  try {
    // For Stylus, we need to use the compiled WASM file
    const wasmPath = path.join(__dirname, "../wasm-output/AIAgent.wasm");
    if (!fs.existsSync(wasmPath)) {
      console.error("WASM file not found. Please compile the Rust contract first.");
      console.error("Run: cargo stylus build --release");
      process.exit(1);
    }

    // Read the WASM file
    const wasmBinary = fs.readFileSync(wasmPath);
    console.log(`WASM binary size: ${wasmBinary.length} bytes`);

    // Deploy the contract using the Stylus factory
    const StylusDeployer = await ethers.getContractFactory("StylusDeployer");
    const deployer = await StylusDeployer.deploy();
    
    console.log("Deploying WASM contract...");
    const tx = await deployer.deployWasm(wasmBinary);
    const receipt = await tx.wait();
    
    // Get the deployed contract address from the event
    const deployEvent = receipt.events.find(e => e.event === "ContractDeployed");
    const contractAddress = deployEvent.args.contractAddress;
    
    console.log(`AIAgent contract deployed to: ${contractAddress}`);
    
    // Save the contract address to a file
    const deploymentInfo = {
      network: network.name,
      chainId: network.chainId.toString(),
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
        if (network.chainId === 421614) {
          envContent += `ARBITRUM_RPC_URL=https://sepolia-rollup.arbitrum.io/rpc\n`;
        } else if (network.chainId === 42161) {
          envContent += `ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc\n`;
        }
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
