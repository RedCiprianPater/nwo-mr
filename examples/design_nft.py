"""
Example: Create and Sell Virtual Artifact as NFT
"""

from nwo_mr import NWOMRClient


def main():
    # Initialize
    client = NWOMRClient(
        api_url="https://nwo-mr.onrender.com",
        wallet_address="0x...",
        private_key="0x..."
    )
    
    # Design artifact
    artifact = client.market.design_artifact(
        category="robot_component",
        name="Neural Processing Unit v7",
        attributes={
            "compute": 1000,
            "efficiency": 0.95,
            "rarity": "epic",
            "power_consumption": "50W"
        },
        visual_3d="npu_v7.glb",
        compatible_with=["humanoid_v2", "industrial_arm_x"]
    )
    
    print(f"Artifact designed: {artifact.id}")
    
    # Mint as NFT
    nft = client.market.mint_nft(
        artifact=artifact,
        collection="NWO_Robotics_Components",
        royalty=0.05  # 5% creator royalty
    )
    
    print(f"NFT minted: {nft.id}")
    
    # List for sale
    listing = client.market.list_nft(
        nft_id=nft.id,
        price=2.5,  # ETH
        auction=False,
        duration_days=7
    )
    
    print(f"Listed for sale: 2.5 ETH")
    print(f"Listing ID: {listing['id']}")


if __name__ == "__main__":
    main()
