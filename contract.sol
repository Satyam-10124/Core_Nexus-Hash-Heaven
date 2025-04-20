// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title AIAgent
 * @dev Smart contract for storing AI-generated real estate analysis results on Arbitrum
 * @custom:security Access control implemented for task completion
 */
contract AIAgent {
    struct Task {
        uint256 id;
        string topic;      // Contains property address and task details (JSON)
        string result;     // Contains AI analysis results
        address requester; // Address that created the task
        bool completed;    // Flag to track if task has been completed
    }

    // State variables
    address public owner;
    uint256 public taskCounter;
    mapping(uint256 => Task) public tasks;
    uint256 public constant MAX_STRING_LENGTH = 8000; // Limit string size for gas efficiency

    // Events
    event TaskCreated(uint256 indexed id, string topic, address indexed requester);
    event TaskCompleted(uint256 indexed id, string result);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "AIAgent: caller is not the owner");
        _;
    }

    modifier taskExists(uint256 _id) {
        require(tasks[_id].id != 0, "AIAgent: task does not exist");
        _;
    }

    modifier taskNotCompleted(uint256 _id) {
        require(!tasks[_id].completed, "AIAgent: task already completed");
        _;
    }

    /**
     * @dev Sets the contract deployer as the initial owner
     */
    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    /**
     * @dev Transfers ownership of the contract to a new account
     * @param newOwner Address of the new owner
     */
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "AIAgent: new owner is the zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    /**
     * @dev Creates a new task with the given topic
     * @param _topic Task topic (JSON string with property details)
     * @return taskId The ID of the newly created task
     */
    function createTask(string memory _topic) public returns (uint256 taskId) {
        require(bytes(_topic).length <= MAX_STRING_LENGTH, "AIAgent: topic too long");
        
        taskCounter++;
        tasks[taskCounter] = Task({
            id: taskCounter,
            topic: _topic,
            result: "",
            requester: msg.sender,
            completed: false
        });
        
        emit TaskCreated(taskCounter, _topic, msg.sender);
        return taskCounter;
    }

    /**
     * @dev Completes a task by storing the result
     * @param _id Task ID
     * @param _result Task result (AI analysis)
     */
    function completeTask(uint256 _id, string memory _result) public onlyOwner taskExists(_id) taskNotCompleted(_id) {
        require(bytes(_result).length <= MAX_STRING_LENGTH, "AIAgent: result too long");
        
        tasks[_id].result = _result;
        tasks[_id].completed = true;
        
        emit TaskCompleted(_id, _result);
    }

    /**
     * @dev Retrieves a task by ID
     * @param _id Task ID
     * @return Task memory The task data
     */
    function getTask(uint256 _id) public view taskExists(_id) returns (Task memory) {
        return tasks[_id];
    }

    /**
     * @dev Checks if a task exists
     * @param _id Task ID
     * @return bool Whether the task exists
     */
    function taskExistsCheck(uint256 _id) public view returns (bool) {
        return tasks[_id].id != 0;
    }
}
