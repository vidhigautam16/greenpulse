#!/usr/bin/env python3
"""
GreenPulse — Startup Script
Supports local development and Replit deployment
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
os.chdir(ROOT)

print("""
╔═══════════════════════════════════════════════════════════╗
║  🌿  G R E E N P U L S E                                 ║
║      Real-Time Carbon Intelligence                        ║
║      Pathway · Langchain · WAQI · Gemini                 ║
╚═══════════════════════════════════════════════════════════╝
""")

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Check configuration
waqi = os.getenv("WAQI_TOKEN", "")
gemini = os.getenv("GOOGLE_API_KEY", "")

print(f"  📡  WAQI: {'✅ Set' if waqi and waqi != 'demo' else '⚠️  Demo token (limited)'}")
print(f"  🤖  Gemini: {'✅ Set' if gemini and gemini != 'your_key_here' else '⚠️  Not set (mock responses)'}")
print(f"  🌍  Cities: Delhi · Mumbai · Kolkata · Chennai · Prayagraj")
print(f"  🔧  Custom city search: Available")
print(f"\n  Starting server...\n")

try:
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=False,
    )
except KeyboardInterrupt:
    print("\n  🛑  Stopped\n")
except ImportError as e:
    print(f"\n  ❌  Missing: {e}")
    print("  Run: pip install -r requirements.txt\n")
    sys.exit(1)
