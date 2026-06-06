"""
config.py — Central configuration for the Causal Interview Agent.

All API keys, persona IDs, and settings in one place.
After running setup_personas.py, update PERSONA_A_ID and PERSONA_B_ID.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ───────────────────────────────────────────────
TAVUS_API_KEY = os.getenv("TAVUS_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")  # optional — for custom TTS

# ── Tavus Settings ─────────────────────────────────────────
TAVUS_BASE_URL = "https://tavusapi.com/v2"

# Stock replica — Phoenix-4 Pro (used in Tavus quickstart examples)
# Replace with your own replica_id if you have one
DEFAULT_REPLICA_ID = "r90bbd427f71"

# LLM model hosted by Tavus (Claude Haiku for grounded reasoning)
TAVUS_LLM_MODEL = "tavus-claude-haiku-4.5"

# ── Persona IDs (populated after running setup_personas.py) ──
PERSONA_A_ID = os.getenv("PERSONA_A_ID", "")  # Condition A: targeted causal prober
PERSONA_B_ID = os.getenv("PERSONA_B_ID", "")  # Condition B: generic adaptive prober

# ── Interview Questions (shared across both conditions) ────
INTERVIEW_QUESTIONS = [
    "What problem were you trying to solve when you started looking for this product, and how has it actually changed the way your team works?",
    "Can you walk me through a time the product really helped — or really let you down — and what happened as a result?",
    "If you had to explain to a colleague why they should or shouldn't adopt this product, what would you tell them?",
]

# ── Callback URL for Tavus webhooks (optional) ─────────────
# Set this to your ngrok/public URL if running callback_server.py
CALLBACK_URL = os.getenv("CALLBACK_URL", "")