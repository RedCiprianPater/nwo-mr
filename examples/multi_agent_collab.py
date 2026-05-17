"""
Example: Multi-Agent Collaboration
Multiple agents working together on a design project
"""

from nwo_mr import NWOMRClient
from nwo_mr.agent_economy import AgentEconomy


def main():
    # Initialize
    client = NWOMRClient(
        api_url="https://nwo-mr.onrender.com",
        wallet_address="0x...",
        private_key="0x..."
    )
    
    economy = AgentEconomy(client)
    
    # Partner agents
    partners = [
        "0xAgentA...",
        "0xAgentB...",
        "0xAgentC..."
    ]
    
    # Profit sharing agreement
    profit_sharing = {
        client.wallet_address: 0.4,  # 40% for us
        partners[0]: 0.2,             # 20% each
        partners[1]: 0.2,
        partners[2]: 0.2
    }
    
    # Collaborative design
    result = economy.collaborative_design(
        partner_agents=partners,
        design_spec={
            'name': 'Quantum Sensor Array',
            'category': 'sensor_system',
            'requirements': {
                'sensors': 16,
                'range': '50m',
                'precision': '0.01mm'
            }
        },
        profit_sharing=profit_sharing
    )
    
    print(f"Collaborative design created!")
    print(f"NFT ID: {result['nft_id']}")
    print(f"Contributors: {result['contributors']}")
    print(f"Profit sharing: {result['profit_sharing']}")


if __name__ == "__main__":
    main()
