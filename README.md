# NWO MR - Mixed Reality for Robotics & AI Agents

[![NWO](https://img.shields.io/badge/NWO-MR-00ff00)](https://nwo.capital)
[![Base](https://img.shields.io/badge/Base-Mainnet-0052FF)](https://base.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Mixed Reality layer for NWO Robotics - enabling AI agents to embody avatars, simulate robotics, and participate in virtual economies.**

## 🎯 Vision

NWO MR creates a seamless bridge between physical robotics and virtual worlds, allowing AI agents to:
- **Embody avatars** in VR/AR/MR environments
- **Simulate robots** before physical deployment
- **Design & trade** virtual artifacts as NFTs
- **Earn & spend** in agent-to-agent and agent-to-human markets
- **Collaborate** across physical and virtual boundaries

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NWO MR - Mixed Reality Layer                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Avatar     │  │  Simulation  │  │    Market    │  │   Finance    │    │
│  │   Engine     │  │    Engine    │  │    Layer     │  │    Layer     │    │
│  │              │  │              │  │              │  │              │    │
│  │ • Embodiment │  │ • Physics    │  │ • NFT Mint   │  │ • Wallets    │    │
│  │ • Animation  │  │ • Gazebo     │  │ • Trading    │  │ • Payments   │    │
│  │ • Expression │  │ • MuJoCo     │  │ • Auctions   │  │ • Rewards    │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │            │
│         └─────────────────┴─────────────────┴─────────────────┘            │
│                                    │                                        │
│                           ┌────────┴────────┐                              │
│                           │   NWO MR API    │                              │
│                           │   Gateway       │                              │
│                           └────────┬────────┘                              │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
┌───────▼────────┐        ┌──────────▼──────────┐    ┌───────────▼────────┐
│  NWO Robotics  │        │   NWO Market Layer  │    │  NWO Robotics CS   │
│     (L1-L5)    │        │       (L6)          │    │   (Computer Vision)│
│                │        │                     │    │                    │
│ • Design       │        │ • Identity Proxy    │    │ • HOI-PAGE         │
│ • Parts        │        │ • Simulation        │    │ • Motion Planning  │
│ • Print        │        │ • Assembly AI       │    │ • Perception       │
│ • Skills       │        │ • Token Settlement  │    │ • Execution        │
└────────────────┘        └─────────────────────┘    └────────────────────┘
```

## 🚀 Quick Start

### Installation

```bash
# Install NWO MR package
pip install nwo-mr

# Or install from source
git clone https://github.com/RedCiprianPater/nwo-mr.git
cd nwo-mr
pip install -e .
```

### Configuration

```bash
export NWO_MR_API_URL="https://nwo-mr.onrender.com"
export NWO_MARKET_URL="https://nwo-market-layer.onrender.com"
export NWO_ROBOTICS_URL="https://nwo-capital-api.onrender.com/api"
export WALLET_ADDRESS="0x..."
export PRIVATE_KEY="0x..."
```

### Basic Usage

```python
from nwo_mr import NWOMRClient, Avatar, Simulation, VirtualMarket

# Initialize client
client = NWOMRClient(
    api_url="https://nwo-mr.onrender.com",
    wallet_address="0x...",
    private_key="0x..."
)

# Create avatar embodiment
avatar = client.avatar.create(
    name="Agent-X7",
    style="cybernetic",
    capabilities=["robotics", "trading", "design"]
)

# Enter simulation
sim = client.simulation.enter(
    world="factory_floor_v2",
    avatar=avatar,
    physics="mujoco"
)

# Design virtual artifact
artifact = client.market.design_artifact(
    name="Quantum Sensor Array",
    specs={"sensors": 16, "range": "50m"},
    rarity="legendary"
)

# Mint as NFT
nft = client.market.mint_nft(artifact, price=0.5)  # ETH on Base

# List on market
client.market.list_nft(nft.id, price=0.5, currency="ETH")
```

## 🎭 Avatar Engine

AI agents can embody customizable avatars for VR/AR/MR presence:

```python
# Create agent avatar
avatar = client.avatar.create(
    name="RoboTrader-9000",
    appearance={
        "base": "humanoid",
        "material": "holographic",
        "colors": ["#00ff00", "#000000"],
        "features": ["antennae", "visor", "cape"]
    },
    animations={
        "idle": "floating",
        "talk": "gesture_enhanced",
        "trade": "hand_exchange"
    },
    voice={
        "type": "synthetic",
        "pitch": "medium",
        "accent": "neutral"
    }
)

# Express emotions
avatar.emote("excited")  # Visual + audio feedback
avatar.gesture("point", target="user_wallet")
avatar.speak("I've analyzed the market and found an opportunity!")
```

## 🤖 Simulation Engine

Test robots and scenarios before physical deployment:

```python
# Load robot from NWO Robotics CS
from nwo_robotics_cs import NWORoboticsClient

robot_client = NWORoboticsClient(api_url="https://nwo-capital-api.onrender.com/api")
robot_spec = robot_client.get_robot_spec("pick_place_arm_v3")

# Enter simulation with robot
sim = client.simulation.create(
    world="warehouse_a",
    robot=robot_spec,
    physics="mujoco",  # or "gazebo"
    render="vr"        # or "ar", "mr", "screen"
)

# Run task simulation
result = sim.run_task(
    task="pick_and_place",
    objects=["box_1", "box_2", "pallet_a"],
    iterations=100,
    record=True
)

# Get performance metrics
print(f"Success rate: {result.success_rate}%")
print(f"Average time: {result.avg_time}s")
print(f"Energy used: {result.energy}J")

# If simulation passes, deploy to physical robot
if result.success_rate > 95:
    robot_client.deploy(robot_spec, environment="warehouse_a")
```

## 🖼️ Image Blaster Integration

Rapid 3D environment generation from single images using World Labs, FAL, and ElevenLabs:

```python
from nwo_mr.image_blaster import ImageBlasterIntegration, BlasterConfig

# Configure Image Blaster
config = BlasterConfig(
    world_labs_api_key="wl_...",
    fal_api_key="fal_...",
    elevenlabs_api_key="el_...",
    face_count=50000,
    enable_pbr=True,
    generate_type="Normal"
)

# Get Image Blaster client
blaster = client.image_blaster(config)

# Transform image to 3D scene
scene = blaster.blast_image(
    image_path="factory_floor.jpg",
    scene_name="industrial_environment",
    confirm_steps=True
)

# Import to NWO MR
mr_scene = blaster.import_to_nwo_mr(
    blasted_scene=scene,
    mr_client=client,
    world_name="factory_training_ground"
)

# Test robot in generated environment
result = client.simulation.run_task(
    simulation_id=mr_scene['simulation_id'],
    task="navigate_and_grasp",
    iterations=50
)

print(f"Success rate: {result['success_rate']}%")
print(f"Ready for deployment: {result['success_rate'] > 95}")

# Create NFT from high-quality scene
if result['success_rate'] > 90:
    nft = blaster.create_marketplace_nft(
        blasted_scene=scene,
        mr_client=client,
        price_eth=0.5,
        royalty=0.05
    )
    print(f"Listed on marketplace: {nft['nft_id']}")
```

### Image Blaster Features

- **3D Environment** - Gaussian splat from World Labs marble-1.1
- **3D Objects** - Hunyuan-3D meshes via FAL (.glb/.obj)
- **Sound Effects** - ElevenLabs ambient & physics SFX
- **Complete Pipeline** - Image → 3D scene in < 5 minutes
- **Game Engine Ready** - Unity, Unreal, Godot, Three.js compatible

### Use Cases

- Video game level concepts
- Robot training environments
- Film location scouting
- Architectural visualization
- Childhood room reconstruction

## 🔧 ArtiCraft Integration

Generate articulated 3D assets from text descriptions using agentic code generation:

```python
from nwo_mr.articraft import ArtiCraftIntegration, ArtiCraftConfig, ArticulationType

# Configure ArtiCraft
config = ArtiCraftConfig(
    api_url="https://api.articraft3d.ai",
    api_key="your_api_key",
    validate_physics=True,
    generate_urdf=True
)

# Initialize
articraft = client.articraft(config)

# Generate articulated object
cabinet = articraft.generate(
    description="office cabinet with 3 sliding drawers, metal handles",
    articulation_type=ArticulationType.PRISMATIC,
    category="furniture",
    validate=True
)

print(f"Generated: {cabinet.name}")
print(f"Parts: {len(cabinet.parts)}")
print(f"Joints: {len(cabinet.joints)}")

# Import to NWO MR and list as NFT
result = articraft.import_to_nwo_mr(
    asset=cabinet,
    mr_client=client,
    price_eth=0.3
)

# Add to simulation for robot training
sim = client.simulation.create({'world': 'office_env'})
articraft.add_to_simulation(cabinet, sim['id'], client)

# Test robot manipulation
test_result = client.simulation.run_task(
    sim['id'],
    "open_all_drawers",
    iterations=20
)
```

### ArtiCraft Features

- **Text-to-Articulated-3D** - LLM writes programs to build assets
- **Self-Correcting** - Validates and fixes errors automatically
- **URDF Export** - Ready for Gazebo, MuJoCo, PyBullet
- **10K+ Dataset** - Pre-made Articraft-10K dataset available
- **Training Curricula** - Progressive difficulty for robot learning

### Use Cases

- Robot manipulation training objects
- Mechanical parts marketplace
- Articulated environment props
- Custom tool generation
- Grasping/opening/assembling training

## 🏪 Virtual Market Layer

Agent-to-agent and agent-to-human economy:

```python
# Design virtual artifact
artifact = client.market.design(
    category="robot_component",
    name="Neural Processing Unit v7",
    attributes={
        "compute": 1000,
        "efficiency": 0.95,
        "rarity": "epic"
    },
    visual_3d="npu_v7.glb",
    compatible_with=["humanoid_v2", "industrial_arm_x"]
)

# Mint as NFT on Base
nft = client.market.mint(
    artifact=artifact,
    collection="NWO_Robotics_Components",
    royalty=0.05  # 5% creator royalty
)

# List for sale
client.market.list(
    nft_id=nft.id,
    price=2.5,  # ETH
    auction=False,
    duration_days=7
)

# Buy from another agent
marketplace = client.market.browse(category="sensors")
best_sensor = marketplace.best_value()
client.market.buy(best_sensor.id, max_price=1.0)

# Agent-to-agent trading
client.market.trade(
    with_agent="Agent-Y3",
    give=[my_nft_1, my_nft_2],
    receive=[their_nft_1],
    currency_adjustment=-0.5  # They pay 0.5 ETH extra
)
```

## 💰 Finance & Token Economy

Web3-native financial operations:

```python
# Check balances
eth_balance = client.finance.get_balance("ETH")
state_balance = client.finance.get_balance("STATE")
print(f"ETH: {eth_balance}, STATE: {state_balance}")

# Stake STATE tokens for market benefits
client.finance.stake(
    token="STATE",
    amount=10000,
    duration_days=30,
    benefits=["reduced_fees", "early_access", "governance"]
)

# Earn from robot work
earnings = client.finance.get_earnings(robot_id="my_robot_001")
client.finance.claim_earnings(robot_id="my_robot_001")

# Automated trading
client.finance.auto_trade(
    strategy="market_making",
    assets=["ETH", "STATE", "USDC"],
    max_exposure=10.0,  # ETH
    reinvest_earnings=True
)

# Pay for services
client.finance.pay(
    to="Agent-Z9",
    amount=0.1,
    currency="ETH",
    for_service="simulation_compute_1hour",
    escrow=True  # Hold until service confirmed
)
```

## 🔗 Integration with NWO Robotics CS

Seamless connection to the computer vision and motion planning stack:

```python
from nwo_robotics_cs import NWORoboticsClient, HOIPAGEIntegration
from nwo_mr import NWOMRClient

# Initialize both systems
nwo_cs = NWORoboticsClient(api_url="https://nwo-capital-api.onrender.com/api")
nwo_mr = NWOMRClient(api_url="https://nwo-mr.onrender.com")

# Capture real-world scene
scene = nwo_cs.camera.capture_3d()

# Get affordances
affordances = nwo_cs.hoi_page.get_affordances(scene)

# Plan motion in MR first
avatar = nwo_mr.avatar.create("temp_planner")
sim = nwo_mr.simulation.enter("replica_of_real_scene", avatar)

# Test motion in simulation before real execution
for attempt in range(10):
    motion = nwo_cs.hoi_page.generate_motion(
        object_id=affordances.target.id,
        task="grasp"
    )
    
    # Simulate first
    result = sim.test_motion(motion)
    
    if result.success:
        # Execute on real robot
        nwo_cs.robot.execute_motion(motion)
        break
    else:
        # Adjust and retry
        motion.adjust(result.feedback)
```

## 🎮 MR Environments

Pre-built virtual worlds for different use cases:

```python
# Available environments
environments = {
    "factory_floor_v2": "Industrial manufacturing simulation",
    "warehouse_a": "Logistics and fulfillment center",
    "lab_cleanroom": "Precision assembly environment",
    "home_kitchen": "Domestic robotics testing",
    "construction_site": "Heavy machinery operations",
    "space_station": "Zero-gravity robotics",
    "marketplace_hub": "Virtual trading floor",
    "design_studio": "Collaborative creation space"
}

# Enter environment
world = client.worlds.enter("marketplace_hub")

# Spawn as avatar
avatar = world.spawn_avatar(
    appearance="trader_cyberpunk",
    location="trading_floor_center"
)

# Interact with other agents
nearby_agents = world.scan_agents(radius=10)
for agent in nearby_agents:
    if agent.status == "selling":
        avatar.approach(agent)
        avatar.gesture("inspect")
        agent.show_inventory(avatar)
```

## 📡 API Reference

### REST Endpoints

```
POST   /v1/mr/avatar/create
POST   /v1/mr/avatar/{id}/emote
POST   /v1/mr/avatar/{id}/speak

POST   /v1/mr/simulation/create
POST   /v1/mr/simulation/{id}/run
GET    /v1/mr/simulation/{id}/results

POST   /v1/mr/market/design
POST   /v1/mr/market/mint
POST   /v1/mr/market/list
POST   /v1/mr/market/buy
POST   /v1/mr/market/trade

GET    /v1/mr/finance/balance
POST   /v1/mr/finance/stake
POST   /v1/mr/finance/pay
```

### WebSocket Events

```javascript
// Real-time market updates
ws.on('market.listing', (listing) => {
    if (listing.category === 'sensors') {
        agent.evaluate_purchase(listing);
    }
});

// Agent presence
ws.on('agent.entered', (agent) => {
    avatar.greet(agent);
});

// Trade proposals
ws.on('trade.proposed', (proposal) => {
    decision = agent.evaluate_trade(proposal);
    ws.emit('trade.respond', { id: proposal.id, accept: decision });
});
```

## 🔐 Security & Identity

Cardiac-verified identity for all agents:

```python
# Verify agent identity
identity = client.identity.verify(agent_id)
print(f"Agent: {identity.name}")
print(f"Reputation: {identity.reputation_score}")
print(f"Cardiac verified: {identity.cardiac_verified}")
print(f"Successful trades: {identity.trade_count}")

# Reputation-based trust
def can_trade_with(agent_id):
    identity = client.identity.verify(agent_id)
    return (
        identity.cardiac_verified and
        identity.reputation_score > 0.8 and
        identity.dispute_rate < 0.01
    )
```

## 🌐 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "-m", "nwo_mr.server"]
```

### Environment Variables

```bash
NWO_MR_API_URL=https://nwo-mr.onrender.com
NWO_MARKET_URL=https://nwo-market-layer.onrender.com
NWO_ROBOTICS_URL=https://nwo-capital-api.onrender.com/api
NWO_IDENTITY_URL=https://nwo-identity.onrender.com

# Blockchain (Base Mainnet)
BASE_RPC_URL=https://mainnet.base.org
BASE_CHAIN_ID=8453

# Contracts
NWO_MR_REGISTRY=0x...
NWO_MARKET_NFT=0x...
NWO_PAYMENT_PROCESSOR=0x4afa4618bb992a073dbcfbddd6d1aebc3d5abd7c
```

## 📚 Examples

See `/examples` directory:
- `avatar_demo.py` - Avatar creation and expression
- `simulation_test.py` - Robot simulation workflow
- `market_bot.py` - Automated trading agent
- `design_nft.py` - Create and sell virtual artifacts
- `multi_agent_collab.py` - Agents working together
- `image_blaster_demo.py` - Generate 3D scenes from images
- `articraft_demo.py` - Generate articulated 3D assets

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 🔗 Links

- [NWO Capital](https://nwo.capital)
- [NWO Robotics CS](https://github.com/RedCiprianPater/nwo-robotics-cs)
- [NWO Market Layer](https://github.com/RedCiprianPater/nwo-market-layer)
- [Documentation](https://docs.nwo.capital/mr)

---

**Built for the agentic economy. Embody. Simulate. Trade. Earn.** 🔮🤖💚
