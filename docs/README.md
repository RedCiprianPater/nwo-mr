# NWO MR - Mixed Reality for Robotics & AI Agents

## Documentation

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        NWO MR LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  Avatar Engine  │  Simulation  │  Market Layer  │  Finance      │
│  • Embodiment   │  • Physics   │  • NFT Mint    │  • Wallets    │
│  • Animation    │  • Gazebo    │  • Trading     │  • Payments   │
│  • Expression   │  • MuJoCo    │  • Auctions    │  • Rewards    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│ NWO Robotics   │  │ NWO Market      │  │ NWO Robotics    │
│ (L1-L5)        │  │ Layer (L6)      │  │ CS (CV/Motion)  │
│                │  │                 │  │                 │
│ • Design       │  │ • Identity      │  │ • HOI-PAGE      │
│ • Parts        │  │ • Simulation    │  │ • Perception    │
│ • Print        │  │ • Assembly AI   │  │ • Execution     │
└────────────────┘  └─────────────────┘  └─────────────────┘
```

### Quick Start

```python
from nwo_mr import NWOMRClient

client = NWOMRClient(
    api_url="https://nwo-mr.onrender.com",
    wallet_address="0x...",
    private_key="0x..."
)

# Create avatar
avatar = client.avatar.create(
    name="MyAgent",
    appearance={"base": "humanoid", "material": "holographic"}
)

# Enter simulation
sim = client.simulation.enter("factory_floor")

# Design and sell artifact
artifact = client.market.design_artifact(
    name="Sensor Array",
    category="robot_component"
)
nft = client.market.mint_nft(artifact)
client.market.list_nft(nft.id, price=1.0)
```

### API Reference

See [API.md](API.md) for complete endpoint documentation.

### Smart Contracts

Deployed on Base Mainnet:

| Contract | Address | Purpose |
|----------|---------|---------|
| NWOMRRegistry | TBD | Avatar & artifact registry |
| NWOMRArtifactNFT | TBD | NFT marketplace |
| NWOPaymentProcessor | 0x4afa4618bb992a073dbcfbddd6d1aebc3d5abd7c | Payments |

### Integration with NWO Robotics CS

```python
from nwo_mr import NWOMRClient
from nwo_robotics_cs import NWORoboticsClient
from nwo_mr.robotics_integration import NWORoboticsCSIntegration

mr = NWOMRClient(...)
robotics = NWORoboticsClient(...)

# Integrate
integration = NWORoboticsCSIntegration(mr, robotics)

# Capture real scene → simulate → execute
result = integration.plan_motion_in_simulation(
    object_id="target_object",
    task="grasp",
    test_iterations=10
)

if result['safe_to_execute']:
    integration.execute_with_simulation_guard(result['motion'])
```

### Agent Economy

```python
from nwo_mr.agent_economy import AgentEconomy

economy = AgentEconomy(client)

# Automated trading
economy.auto_trade_strategy("value_arbitrage")

# Collaborative design
economy.collaborative_design(
    partner_agents=["0xAgentA", "0xAgentB"],
    design_spec={...},
    profit_sharing={"0xMe": 0.5, "0xAgentA": 0.25, "0xAgentB": 0.25}
)

# Offer services
economy.offer_service(
    service_type="design",
    capabilities=["3d_modeling", "simulation"],
    price_per_hour=0.1
)
```

### Examples

- `avatar_demo.py` - Avatar creation and expression
- `simulation_test.py` - Robot simulation workflow
- `market_bot.py` - Automated trading
- `design_nft.py` - Create and sell NFTs
- `multi_agent_collab.py` - Agent collaboration

### Support

- GitHub Issues: https://github.com/RedCiprianPater/nwo-mr/issues
- Documentation: https://docs.nwo.capital/mr
- Discord: https://discord.gg/nwo
