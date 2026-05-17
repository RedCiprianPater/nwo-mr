"""
Example: Automated Trading Agent
Buys and sells virtual artifacts based on market analysis
"""

from nwo_mr import NWOMRClient
from nwo_mr.agent_economy import AgentEconomy
import time


def main():
    # Initialize
    client = NWOMRClient(
        api_url="https://nwo-mr.onrender.com",
        wallet_address="0x...",
        private_key="0x..."
    )
    
    economy = AgentEconomy(client)
    
    print("Starting automated trading agent...")
    
    while True:
        # Run trading strategy
        result = economy.auto_trade_strategy(strategy="value_arbitrage")
        
        print(f"Cycle complete:")
        print(f"  Actions evaluated: {result['actions_evaluated']}")
        print(f"  Actions executed: {result['actions_executed']}")
        
        # Check balance
        eth_balance = client.finance.get_balance("ETH")
        print(f"  ETH Balance: {eth_balance}")
        
        # Wait before next cycle
        time.sleep(300)  # 5 minutes


if __name__ == "__main__":
    main()
