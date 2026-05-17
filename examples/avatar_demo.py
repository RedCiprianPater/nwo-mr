"""
Example: Avatar Creation and Expression Demo
"""

from nwo_mr import NWOMRClient, AvatarConfig


def main():
    # Initialize client
    client = NWOMRClient(
        api_url="https://nwo-mr.onrender.com",
        wallet_address="0xYourWalletAddress",
        private_key="0xYourPrivateKey"
    )
    
    # Create avatar
    config = AvatarConfig(
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
        },
        capabilities=["trading", "analysis", "communication"]
    )
    
    avatar = client.avatar.create(config)
    print(f"Avatar created: {avatar['id']}")
    
    # Express emotions
    client.avatar.emote(avatar['id'], "excited")
    client.avatar.speak(avatar['id'], "I've analyzed the market and found an opportunity!")
    client.avatar.gesture(avatar['id'], "point", target="market_chart")
    
    print("Avatar demo complete!")


if __name__ == "__main__":
    main()
