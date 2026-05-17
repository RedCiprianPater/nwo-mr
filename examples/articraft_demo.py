"""
Example: ArtiCraft Integration with NWO MR
Generate articulated 3D assets for robot training and marketplace
"""

from nwo_mr import NWOMRClient
from nwo_mr.articraft import ArtiCraftIntegration, ArtiCraftConfig, ArticulationType


def basic_generation_example():
    """Basic example of generating an articulated asset."""
    
    # Initialize NWO MR
    client = NWOMRClient(
        api_url="https://nwo-mr.onrender.com",
        wallet_address="0x...",
        private_key="0x..."
    )
    
    # Configure ArtiCraft
    config = ArtiCraftConfig(
        api_url="https://api.articraft3d.ai",
        api_key="your_api_key",
        validate_physics=True,
        generate_urdf=True
    )
    
    # Initialize ArtiCraft
    articraft = ArtiCraftIntegration(config)
    
    print("=== ArtiCraft + NWO MR Demo ===\n")
    
    # Example 1: Generate a simple articulated object
    print("1. Generating cabinet with drawers...")
    cabinet = articraft.generate(
        description="office cabinet with 3 sliding drawers, metal handles, wooden material",
        articulation_type=ArticulationType.PRISMATIC,
        category="furniture",
        validate=True
    )
    
    print(f"   Generated: {cabinet.name}")
    print(f"   Parts: {len(cabinet.parts)}")
    print(f"   Joints: {len(cabinet.joints)}")
    print(f"   Quality: {cabinet.quality_score:.2f}")
    
    # Example 2: Import to NWO MR
    print("\n2. Importing to NWO MR...")
    result = articraft.import_to_nwo_mr(
        asset=cabinet,
        mr_client=client,
        price_eth=0.3
    )
    
    print(f"   Artifact ID: {result['artifact_id']}")
    print(f"   NFT ID: {result.get('nft_id', 'N/A')}")
    print(f"   Listed for: 0.3 ETH")
    
    # Example 3: Add to simulation
    print("\n3. Adding to simulation...")
    sim = client.simulation.create({
        'world': 'office_environment',
        'physics': 'mujoco'
    })
    
    spawn_result = articraft.add_to_simulation(
        asset=cabinet,
        simulation_id=sim['id'],
        mr_client=client,
        position={'x': 1.0, 'y': 0, 'z': 2.0}
    )
    
    print(f"   Spawned in simulation: {spawn_result['status']}")
    
    # Example 4: Test robot manipulation
    print("\n4. Testing robot manipulation...")
    test_result = client.simulation.run_task(
        simulation_id=sim['id'],
        task="open_all_drawers",
        iterations=20
    )
    
    print(f"   Success rate: {test_result['success_rate']}%")
    print(f"   Task completed: {test_result['success_rate'] > 80}")


def batch_generation_example():
    """Generate multiple assets for marketplace."""
    
    config = ArtiCraftConfig(api_key="...")
    articraft = ArtiCraftIntegration(config)
    
    client = NWOMRClient(...)
    
    # Generate variety of articulated objects
    descriptions = [
        "toolbox with hinged lid and removable tray",
        "laptop stand with adjustable height and angle",
        "kitchen faucet with rotating spout and pull-out spray",
        "exercise bike with adjustable seat and resistance knob",
        "3D printer with moving print bed and extruder"
    ]
    
    print("Batch generating assets...")
    assets = articraft.generate_batch(
        descriptions=descriptions,
        category="mechanical",
        max_workers=3
    )
    
    print(f"\nGenerated {len(assets)} assets")
    
    # Import all to marketplace
    for i, asset in enumerate(assets):
        print(f"\nImporting asset {i+1}/{len(assets)}: {asset.name}")
        
        result = articraft.import_to_nwo_mr(
            asset=asset,
            mr_client=client,
            price_eth=0.2 + (asset.quality_score * 0.3)  # Price based on quality
        )
        
        print(f"  Listed: {result.get('nft_id', 'N/A')}")


def dataset_search_example():
    """Search ArtiCraft-10K dataset for existing assets."""
    
    config = ArtiCraftConfig()
    articraft = ArtiCraftIntegration(config)
    
    # Search for grasping training objects
    print("Searching ArtiCraft-10K dataset...")
    
    graspable_objects = articraft.search_dataset(
        query="bottle with cap",
        category="containers",
        articulation_type=ArticulationType.REVOLUTE,
        min_quality=0.85
    )
    
    print(f"\nFound {len(graspable_objects)} matching objects")
    
    for obj in graspable_objects[:5]:
        print(f"  - {obj.name}: {obj.quality_score:.2f} quality")


def training_curriculum_example():
    """Create progressive training curriculum for robot."""
    
    config = ArtiCraftConfig()
    articraft = ArtiCraftIntegration(config)
    client = NWOMRClient(...)
    
    print("Creating training curriculum for 'opening' skill...")
    
    # Generate progressive difficulty levels
    curriculum = articraft.create_training_curriculum(
        skill="opening",
        difficulty_levels=5,
        assets_per_level=10
    )
    
    for level, assets in enumerate(curriculum):
        print(f"\nLevel {level + 1} ({len(assets)} assets):")
        
        # Create simulation for this level
        sim = client.simulation.create({
            'world': f'training_level_{level + 1}',
            'physics': 'mujoco'
        })
        
        # Add all assets
        for asset in assets:
            articraft.add_to_simulation(
                asset=asset,
                simulation_id=sim['id'],
                mr_client=client
            )
        
        print(f"  Simulation ready: {sim['id']}")


def agent_autonomous_example():
    """Agent autonomously creates and sells articulated assets."""
    
    from nwo_mr.agent_economy import AgentEconomy
    
    client = NWOMRClient(...)
    economy = AgentEconomy(client)
    
    config = ArtiCraftConfig(api_key="...")
    articraft = ArtiCraftIntegration(config)
    
    # Agent identifies market need
    trending_categories = economy.get_trending_categories()
    target_category = trending_categories[0] if trending_categories else "tools"
    
    print(f"Agent identified trending category: {target_category}")
    
    # Generate unique articulated asset
    asset = articraft.generate(
        description=f"innovative {target_category} with multiple articulation points",
        category=target_category,
        validate=True
    )
    
    # Test in simulation
    sim = client.simulation.create({'world': 'test_chamber'})
    articraft.add_to_simulation(asset, sim['id'], client)
    
    test_result = client.simulation.run_task(
        sim['id'],
        "test_articulation",
        iterations=10
    )
    
    # Price based on quality and test results
    base_price = 0.2
    quality_multiplier = asset.quality_score
    test_multiplier = test_result['success_rate'] / 100
    
    final_price = base_price * (1 + quality_multiplier + test_multiplier)
    
    # List on marketplace
    result = articraft.import_to_nwo_mr(
        asset=asset,
        mr_client=client,
        price_eth=final_price
    )
    
    print(f"\nAgent created and listed:")
    print(f"  Asset: {asset.name}")
    print(f"  Quality: {asset.quality_score:.2f}")
    print(f"  Test Success: {test_result['success_rate']:.1f}%")
    print(f"  Price: {final_price:.3f} ETH")
    print(f"  NFT: {result.get('nft_id', 'N/A')}")


if __name__ == "__main__":
    # Run examples
    # basic_generation_example()
    # batch_generation_example()
    # dataset_search_example()
    # training_curriculum_example()
    # agent_autonomous_example()
    pass
