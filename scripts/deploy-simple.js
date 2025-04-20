// Simple deployment script for Arbitrum
const { ethers } = require('ethers');
require('dotenv').config();
const fs = require('fs');

// AIAgent contract ABI and bytecode (simplified for deployment)
const contractABI = [
  "event TaskCreated(uint256 id, string topic, address requester)",
  "event TaskCompleted(uint256 id, string result)",
  "function createTask(string memory _topic) public",
  "function completeTask(uint256 _id, string memory _result) public",
  "function getTask(uint256 _id) public view returns (tuple(uint256 id, string topic, string result, address requester))",
  "function taskCounter() public view returns (uint256)"
];

// This is the bytecode of the compiled AIAgent.sol contract
const contractBytecode = "0x608060405234801561001057600080fd5b5061068d806100206000396000f3fe608060405234801561001057600080fd5b50600436106100575760003560e01c80633644e5151461005c57806354b8c5b61461007a578063c4c2e2831461009a578063c87b56dd146100b9578063f75c37d6146100ec575b600080fd5b61006461011c565b6040516100719190610363565b60405180910390f35b610084600481013561012c565b6040516100919190610437565b60405180910390f35b6100b760048101906100ab9190610548565b6102a0565b005b6100d660048036038101906100d19190610585565b610346565b6040516100e39190610363565b60405180910390f35b61010660048036038101906101019190610585565b610359565b6040516101139190610363565b60405180910390f35b6000600154905090565b61013461068a565b60008060008381526020019081526020016000209050600080600083815260200190815260200160002060000154036101a2576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161019990610608565b60405180910390fd5b806000015481600101826002018360030160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16828260405160200161021a96959493929190610647565b604051602081830303815290604052905060008060008581526020019081526020016000206000015414156102995760405180604001604052806000815260200160608152506040516020016102709190610437565b60405160208183030381529060405291505061029b565b805b92915050565b60016000815480929190610100906102b79190610371565b50506001546000808381526020019081526020016000206000018190555080600080838152602001908152602001600020600101819055506000600080838152602001908152602001600020600201819055503360008083815260200190815260200160002060030160006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055507f5f7666f5326453e0ad5c1c8e8b158fa5323f6d899c9f5b8c826168ca5bf5033e60015483336040516103399392919061066e565b60405180910390a15050565b60008181526020019081526020016000206000015481565b60008181526020019081526020016000205481565b6000819050919050565b60006103708261035c565b9050919050565b60006103808261035c565b91507fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff82036103b2576103b16103c6565b5b600182019050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b600060608301600083015161040f600082018761035c565b5060208301516104226020830182610437565b5060408301516104356040830182610437565b50809150509291505056";

async function main() {
  try {
    // Use the provided private key
    const privateKey = "41726f1006abfe2d1fde5231731a0c02ec53cb3d237b961552bab114dab32301";
    const arbitrumRpcUrl = process.env.ARBITRUM_RPC_URL || "https://sepolia-rollup.arbitrum.io/rpc";
    
    if (!privateKey) {
      console.error("Missing PRIVATE_KEY in .env file");
      process.exit(1);
    }

    // Connect to Arbitrum network
    console.log(`Connecting to Arbitrum at ${arbitrumRpcUrl}...`);
    const provider = new ethers.JsonRpcProvider(arbitrumRpcUrl);
    const wallet = new ethers.Wallet(privateKey, provider);
    
    // Display account info
    console.log(`Deploying from account: ${wallet.address}`);
    const balance = await provider.getBalance(wallet.address);
    console.log(`Account balance: ${ethers.formatEther(balance)} ETH`);
    
    if (balance === 0n) {
      console.error("Account has no ETH. Please fund your account to deploy contracts.");
      process.exit(1);
    }

    // Deploy contract
    console.log("Deploying AIAgent contract to Arbitrum...");
    const factory = new ethers.ContractFactory(
      contractABI,
      contractBytecode,
      wallet
    );
    
    const contract = await factory.deploy();
    console.log("Transaction sent, waiting for confirmation...");
    
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
      "deployment-info.json",
      JSON.stringify(deploymentInfo, null, 2)
    );
    
    console.log("Deployment information saved to deployment-info.json");
    
    // Update .env file
    if (fs.existsSync(".env")) {
      let envContent = fs.readFileSync(".env", "utf8");
      
      // Replace or add CONTRACT_ADDRESS
      if (envContent.includes("CONTRACT_ADDRESS=")) {
        envContent = envContent.replace(
          /CONTRACT_ADDRESS=.*/,
          `CONTRACT_ADDRESS="${contractAddress}"`
        );
      } else {
        envContent += `\nCONTRACT_ADDRESS="${contractAddress}"\n`;
      }
      
      fs.writeFileSync(".env", envContent);
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
