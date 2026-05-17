// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title NWO MR Registry
 * @notice Registry for avatars, simulations, and virtual artifacts
 * @dev Part of NWO Mixed Reality layer on Base Mainnet
 */
contract NWOMRRegistry {
    
    struct Avatar {
        address owner;
        string name;
        string metadataURI;
        uint256 createdAt;
        bool active;
    }
    
    struct VirtualArtifact {
        address creator;
        string name;
        string category;
        string metadataURI;
        uint256 createdAt;
        uint256 totalSupply;
        uint256 minted;
    }
    
    struct Simulation {
        address creator;
        string worldName;
        string physicsEngine;
        uint256 createdAt;
        uint256 expiresAt;
        bool active;
    }
    
    mapping(uint256 => Avatar) public avatars;
    mapping(uint256 => VirtualArtifact) public artifacts;
    mapping(uint256 => Simulation) public simulations;
    mapping(address => uint256[]) public userAvatars;
    mapping(address => uint256[]) public userArtifacts;
    mapping(address => uint256[]) public userSimulations;
    
    uint256 public avatarCounter;
    uint256 public artifactCounter;
    uint256 public simulationCounter;
    
    address public owner;
    address public feeRecipient;
    
    uint256 public constant AVATAR_FEE = 0.001 ether;
    uint256 public constant ARTIFACT_FEE = 0.005 ether;
    uint256 public constant SIMULATION_FEE = 0.01 ether;
    
    event AvatarCreated(uint256 indexed avatarId, address indexed owner, string name);
    event ArtifactCreated(uint256 indexed artifactId, address indexed creator, string name);
    event SimulationCreated(uint256 indexed simId, address indexed creator, string worldName);
    event AvatarActivated(uint256 indexed avatarId);
    event AvatarDeactivated(uint256 indexed avatarId);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    constructor(address _feeRecipient) {
        owner = msg.sender;
        feeRecipient = _feeRecipient;
    }
    
    /**
     * @notice Create a new avatar
     */
    function createAvatar(
        string calldata _name,
        string calldata _metadataURI
    ) external payable returns (uint256) {
        require(msg.value >= AVATAR_FEE, "Insufficient fee");
        
        avatarCounter++;
        uint256 avatarId = avatarCounter;
        
        avatars[avatarId] = Avatar({
            owner: msg.sender,
            name: _name,
            metadataURI: _metadataURI,
            createdAt: block.timestamp,
            active: true
        });
        
        userAvatars[msg.sender].push(avatarId);
        
        // Send fee
        (bool success, ) = payable(feeRecipient).call{value: msg.value}("");
        require(success, "Fee transfer failed");
        
        emit AvatarCreated(avatarId, msg.sender, _name);
        
        return avatarId;
    }
    
    /**
     * @notice Create a virtual artifact template
     */
    function createArtifact(
        string calldata _name,
        string calldata _category,
        string calldata _metadataURI,
        uint256 _totalSupply
    ) external payable returns (uint256) {
        require(msg.value >= ARTIFACT_FEE, "Insufficient fee");
        
        artifactCounter++;
        uint256 artifactId = artifactCounter;
        
        artifacts[artifactId] = VirtualArtifact({
            creator: msg.sender,
            name: _name,
            category: _category,
            metadataURI: _metadataURI,
            createdAt: block.timestamp,
            totalSupply: _totalSupply,
            minted: 0
        });
        
        userArtifacts[msg.sender].push(artifactId);
        
        // Send fee
        (bool success, ) = payable(feeRecipient).call{value: msg.value}("");
        require(success, "Fee transfer failed");
        
        emit ArtifactCreated(artifactId, msg.sender, _name);
        
        return artifactId;
    }
    
    /**
     * @notice Create a simulation instance
     */
    function createSimulation(
        string calldata _worldName,
        string calldata _physicsEngine,
        uint256 _durationHours
    ) external payable returns (uint256) {
        require(msg.value >= SIMULATION_FEE, "Insufficient fee");
        
        simulationCounter++;
        uint256 simId = simulationCounter;
        
        simulations[simId] = Simulation({
            creator: msg.sender,
            worldName: _worldName,
            physicsEngine: _physicsEngine,
            createdAt: block.timestamp,
            expiresAt: block.timestamp + (_durationHours * 1 hours),
            active: true
        });
        
        userSimulations[msg.sender].push(simId);
        
        // Send fee
        (bool success, ) = payable(feeRecipient).call{value: msg.value}("");
        require(success, "Fee transfer failed");
        
        emit SimulationCreated(simId, msg.sender, _worldName);
        
        return simId;
    }
    
    /**
     * @notice Deactivate avatar
     */
    function deactivateAvatar(uint256 _avatarId) external {
        require(avatars[_avatarId].owner == msg.sender, "Not owner");
        avatars[_avatarId].active = false;
        emit AvatarDeactivated(_avatarId);
    }
    
    /**
     * @notice Reactivate avatar
     */
    function activateAvatar(uint256 _avatarId) external {
        require(avatars[_avatarId].owner == msg.sender, "Not owner");
        avatars[_avatarId].active = true;
        emit AvatarActivated(_avatarId);
    }
    
    /**
     * @notice Get user's avatars
     */
    function getUserAvatars(address _user) external view returns (uint256[] memory) {
        return userAvatars[_user];
    }
    
    /**
     * @notice Get user's artifacts
     */
    function getUserArtifacts(address _user) external view returns (uint256[] memory) {
        return userArtifacts[_user];
    }
    
    /**
     * @notice Get user's simulations
     */
    function getUserSimulations(address _user) external view returns (uint256[] memory) {
        return userSimulations[_user];
    }
    
    /**
     * @notice Update fees
     */
    function updateFees(
        uint256 _avatarFee,
        uint256 _artifactFee,
        uint256 _simulationFee
    ) external onlyOwner {
        // Note: In production, use a timelock
        // AVATAR_FEE = _avatarFee;
        // ARTIFACT_FEE = _artifactFee;
        // SIMULATION_FEE = _simulationFee;
    }
    
    /**
     * @notice Update fee recipient
     */
    function updateFeeRecipient(address _newRecipient) external onlyOwner {
        feeRecipient = _newRecipient;
    }
}
