"""
setup_personas.py — Create Condition A and B personas via Tavus API.

Run once. Prints persona IDs to add to your .env file.

Usage:
    python setup_personas.py
"""

import requests
import json
import sys
from config import (
    TAVUS_API_KEY, TAVUS_BASE_URL, DEFAULT_REPLICA_ID,
    TAVUS_LLM_MODEL, ELEVENLABS_API_KEY,
)
from prompts import SYSTEM_PROMPT_A, SYSTEM_PROMPT_B


def create_persona(name: str, system_prompt: str) -> dict:
    """Create a Tavus persona with full CVI pipeline."""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": TAVUS_API_KEY,
    }

    # ── Perception layer (identical across conditions) ─────
    perception = {
        "perception_model": "raven-1",
        "audio_awareness_queries": [
            "Does the speaker sound emotionally final and confident in what they just said, or tentative and still constructing their thought? Respond: FINAL or TENTATIVE, plus a brief reason.",
            "Rate the speaker's certainty about their statement on a scale: very_certain, somewhat_certain, neutral, somewhat_uncertain, very_uncertain.",
        ],
        "visual_awareness_queries": [
            "Does the user appear confident and settled (nodding, steady gaze, relaxed posture) or uncertain and still thinking (looking away, furrowed brow, fidgeting)?",
        ],
        "perception_analysis_queries": [
            "Across the full conversation, how many times did the respondent sound emotionally final vs tentative when making causal claims?",
            "Were there moments where the respondent's emotional tone contradicted the completeness of their explanation?",
        ],
    }

    # ── Conversational flow (identical across conditions) ──
    conversational_flow = {
        "turn_detection_model": "sparrow-1",
        "turn_taking_patience": "high",       # interview = let them think
        "replica_interruptibility": "medium",
    }

    # ── LLM layer ─────────────────────────────────────────
    llm = {
        "model": TAVUS_LLM_MODEL,
        "speculative_inference": True,
        "extra_body": {
            "temperature": 0.7,
        },
    }

    # ── TTS layer (optional ElevenLabs override) ──────────
    tts = {}
    if ELEVENLABS_API_KEY:
        tts = {
            "tts_engine": "elevenlabs",
            "api_key": ELEVENLABS_API_KEY,
            # voice_id can be set here if you have a specific ElevenLabs voice
            # "voice_id": "your_elevenlabs_voice_id",
        }

    # ── Assemble persona payload ──────────────────────────
    payload = {
        "persona_name": name,
        "system_prompt": system_prompt,
        "pipeline_mode": "full",
        "context": (
            "You are conducting a qualitative product feedback interview about "
            "a SaaS product the participant uses. The participant has consented "
            "to be interviewed and recorded. Be warm, professional, and "
            "genuinely curious about their experience with the product."
        ),
        "default_replica_id": DEFAULT_REPLICA_ID,
        "layers": {
            "perception": perception,
            "conversational_flow": conversational_flow,
            "llm": llm,
        },
    }

    # Only add TTS layer if configured
    if tts:
        payload["layers"]["tts"] = tts

    response = requests.post(
        f"{TAVUS_BASE_URL}/personas",
        headers=headers,
        json=payload,
    )

    if response.status_code not in (200, 201):
        print(f"ERROR creating persona '{name}':")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        return {}

    return response.json()


def main():
    if not TAVUS_API_KEY:
        print("ERROR: TAVUS_API_KEY not set in .env")
        sys.exit(1)

    print("=" * 60)
    print("CREATING TAVUS PERSONAS")
    print("=" * 60)

    # ── Condition A: Targeted Causal-Slot Prober ──────────
    print("\n[1/2] Creating Condition A (targeted causal prober)...")
    result_a = create_persona(
        name="Causal Interview Agent - Condition A (Targeted)",
        system_prompt=SYSTEM_PROMPT_A,
    )

    persona_a_id = result_a.get("persona_id", "")
    if persona_a_id:
        print(f"  ✓ Persona A created: {persona_a_id}")
    else:
        print("  ✗ Failed to create Persona A")

    # ── Condition B: Generic Adaptive Prober ──────────────
    print("\n[2/2] Creating Condition B (generic adaptive prober)...")
    result_b = create_persona(
        name="Causal Interview Agent - Condition B (Generic)",
        system_prompt=SYSTEM_PROMPT_B,
    )

    persona_b_id = result_b.get("persona_id", "")
    if persona_b_id:
        print(f"  ✓ Persona B created: {persona_b_id}")
    else:
        print("  ✗ Failed to create Persona B")

    # ── Output ────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("ADD THESE TO YOUR .env FILE:")
    print(f"{'=' * 60}")
    print(f"PERSONA_A_ID={persona_a_id}")
    print(f"PERSONA_B_ID={persona_b_id}")
    print(f"{'=' * 60}")

    # Also dump full responses for debugging
    print("\nFull Persona A response:")
    print(json.dumps(result_a, indent=2))
    print("\nFull Persona B response:")
    print(json.dumps(result_b, indent=2))


if __name__ == "__main__":
    main()