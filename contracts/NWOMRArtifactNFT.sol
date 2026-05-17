// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title NWO MR Artifact NFT
 * @notice NFT contract for virtual artifacts in NWO MR
 * @dev ERC721 with royalty support and marketplace integration
 */
contract NWOMRArtifactNFT is ERC721, ERC721Enumerable, Ownable, ReentrancyGuard {
    
    struct Artifact {
        uint256 templateId;
        address creator;
        uint256 mintedAt;
        uint256 royaltyBasisPoints; // 500 = 5%
        string metadataURI;
    }
    
    struct Listing {
        address seller;
        uint256 price;
        address currency; // ETH or token address
        bool active;
    }
    
    mapping(uint256 => Artifact) public artifacts;
    mapping(uint256 => Listing) public listings;
    mapping(address => bool) public approvedCurrencies;
    
    uint256 public tokenCounter;
    address public feeRecipient;
    uint256 public platformFeeBasisPoints = 200; // 2%
    
    // Template contract for artifact definitions
    address public templateRegistry;
    
    event ArtifactMinted(
        uint256 indexed tokenId,
        uint256 indexed templateId,
        address indexed creator,
        address owner
    );
    
    event Listed(
        uint256 indexed tokenId,
        address indexed seller,
        uint256 price,
        address currency
    );
    
    event Sold(
        uint256 indexed tokenId,
        address indexed seller,
        address indexed buyer,
        uint256 price
    );
    
    event Delisted(uint256 indexed tokenId);
    
    constructor(
        address _feeRecipient,
        address _templateRegistry
    ) ERC721("NWO MR Artifact", "NWOART") {
        feeRecipient = _feeRecipient;
        templateRegistry = _templateRegistry;
        approvedCurrencies[address(0)] = true; // ETH
    }
    
    /**
     * @notice Mint new artifact NFT
     */
    function mint(
        uint256 _templateId,
        string calldata _metadataURI,
        uint256 _royaltyBasisPoints
    ) external returns (uint256) {
        require(_royaltyBasisPoints <= 1000, "Royalty max 10%");
        
        tokenCounter++;
        uint256 tokenId = tokenCounter;
        
        artifacts[tokenId] = Artifact({
            templateId: _templateId,
            creator: msg.sender,
            mintedAt: block.timestamp,
            royaltyBasisPoints: _royaltyBasisPoints,
            metadataURI: _metadataURI
        });
        
        _safeMint(msg.sender, tokenId);
        
        emit ArtifactMinted(tokenId, _templateId, msg.sender, msg.sender);
        
        return tokenId;
    }
    
    /**
     * @notice List artifact for sale
     */
    function list(
        uint256 _tokenId,
        uint256 _price,
        address _currency
    ) external {
        require(ownerOf(_tokenId) == msg.sender, "Not owner");
        require(approvedCurrencies[_currency], "Currency not approved");
        require(_price > 0, "Price must be > 0");
        
        listings[_tokenId] = Listing({
            seller: msg.sender,
            price: _price,
            currency: _currency,
            active: true
        });
        
        emit Listed(_tokenId, msg.sender, _price, _currency);
    }
    
    /**
     * @notice Delist artifact
     */
    function delist(uint256 _tokenId) external {
        require(listings[_tokenId].seller == msg.sender, "Not seller");
        listings[_tokenId].active = false;
        emit Delisted(_tokenId);
    }
    
    /**
     * @notice Buy listed artifact
     */
    function buy(uint256 _tokenId) external payable nonReentrant {
        Listing memory listing = listings[_tokenId];
        require(listing.active, "Not listed");
        require(listing.currency == address(0), "Use token contract");
        require(msg.value >= listing.price, "Insufficient payment");
        
        _executeSale(_tokenId, listing, msg.value);
    }
    
    /**
     * @notice Internal sale execution
     */
    function _executeSale(
        uint256 _tokenId,
        Listing memory listing,
        uint256 payment
    ) internal {
        Artifact memory artifact = artifacts[_tokenId];
        
        // Calculate fees
        uint256 platformFee = (payment * platformFeeBasisPoints) / 10000;
        uint256 royaltyFee = (payment * artifact.royaltyBasisPoints) / 10000;
        uint256 sellerProceeds = payment - platformFee - royaltyFee;
        
        // Transfer NFT
        _transfer(listing.seller, msg.sender, _tokenId);
        
        // Distribute payments
        (bool platformSuccess, ) = payable(feeRecipient).call{value: platformFee}("");
        require(platformSuccess, "Platform fee failed");
        
        if (royaltyFee > 0) {
            (bool royaltySuccess, ) = payable(artifact.creator).call{value: royaltyFee}("");
            require(royaltySuccess, "Royalty payment failed");
        }
        
        (bool sellerSuccess, ) = payable(listing.seller).call{value: sellerProceeds}("");
        require(sellerSuccess, "Seller payment failed");
        
        // Clear listing
        listings[_tokenId].active = false;
        
        emit Sold(_tokenId, listing.seller, msg.sender, payment);
    }
    
    /**
     * @notice Get royalty info for token
     */
    function royaltyInfo(uint256 _tokenId, uint256 _salePrice) 
        external 
        view 
        returns (address receiver, uint256 royaltyAmount) 
    {
        Artifact memory artifact = artifacts[_tokenId];
        return (
            artifact.creator,
            (_salePrice * artifact.royaltyBasisPoints) / 10000
        );
    }
    
    /**
     * @notice Add approved currency
     */
    function addCurrency(address _currency) external onlyOwner {
        approvedCurrencies[_currency] = true;
    }
    
    /**
     * @notice Remove approved currency
     */
    function removeCurrency(address _currency) external onlyOwner {
        approvedCurrencies[_currency] = false;
    }
    
    /**
     * @notice Update platform fee
     */
    function updatePlatformFee(uint256 _newFee) external onlyOwner {
        require(_newFee <= 500, "Max 5%");
        platformFeeBasisPoints = _newFee;
    }
    
    /**
     * @notice Update fee recipient
     */
    function updateFeeRecipient(address _newRecipient) external onlyOwner {
        feeRecipient = _newRecipient;
    }
    
    /**
     * @notice Get token URI
     */
    function tokenURI(uint256 _tokenId) public view override returns (string memory) {
        require(_exists(_tokenId), "Token does not exist");
        return artifacts[_tokenId].metadataURI;
    }
    
    // Required overrides
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId,
        uint256 batchSize
    ) internal override(ERC721, ERC721Enumerable) {
        super._beforeTokenTransfer(from, to, tokenId, batchSize);
        
        // Delist if transferred
        if (listings[tokenId].active && from != address(0)) {
            listings[tokenId].active = false;
            emit Delisted(tokenId);
        }
    }
    
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721Enumerable)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
