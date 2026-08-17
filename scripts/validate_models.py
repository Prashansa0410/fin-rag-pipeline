import sys
import os

# Add parent dir to path so we can import backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from backend.llm.registry import registry
from config import settings

async def main():
    print("FinResearch Model Validation\n")
    
    if not settings.HF_TOKEN:
        print("WARNING: HF_TOKEN is not set in the environment.")
        
    for tier in ["economical", "standard", "advanced", "fallback"]:
        info = registry.get_model_info(tier)
        provider_name = info.get("provider")
        model_id = info.get("model_id")
        
        provider = registry.get_provider(provider_name)
        
        print(f"Checking {tier.capitalize()}: {model_id}")
        print(f"  Provider: {provider_name}")
        print(f"  Context Limit: {info.get('context_limit')}")
        print(f"  Input Cost: ${info.get('input_cost')} / 1k tokens")
        print(f"  Output Cost: ${info.get('output_cost')} / 1k tokens")
        
        # Ping health
        is_healthy = await provider.health_check(model_id)
        status_text = "Available" if is_healthy else "Unavailable"
        print(f"  Status: {status_text}")
        print("-" * 40)
        
        # Update registry
        registry.update_health(tier, is_healthy)
        
if __name__ == "__main__":
    asyncio.run(main())
