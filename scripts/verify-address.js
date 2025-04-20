// Script to verify the address derived from a private key
const { ethers } = require('ethers');

function getAddressFromPrivateKey(privateKey) {
  try {
    // Remove '0x' prefix if present
    if (privateKey.startsWith('0x')) {
      privateKey = privateKey.substring(2);
    }
    
    // Create wallet from private key
    const wallet = new ethers.Wallet(privateKey);
    
    return {
      address: wallet.address,
      privateKey: privateKey
    };
  } catch (error) {
    console.error('Error deriving address:', error.message);
    return null;
  }
}

// Private key from command line or use default
const privateKey = process.argv[2] || "41726f1006abfe2d1fde5231731a0c02ec53cb3d237b961552bab114dab32301";

const result = getAddressFromPrivateKey(privateKey);

if (result) {
  console.log(`Private Key: ${result.privateKey}`);
  console.log(`Derived Address: ${result.address}`);
  
  // Check if this matches the expected address
  const expectedAddress = "0x4F440a019eEDaCDc3C6aa533d3d15F54a66eaF2b";
  console.log(`Expected Address: ${expectedAddress}`);
  console.log(`Matches expected address: ${result.address.toLowerCase() === expectedAddress.toLowerCase()}`);
} else {
  console.log('Failed to derive address from private key.');
}
