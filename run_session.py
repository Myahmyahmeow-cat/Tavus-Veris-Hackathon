"""
run_session.py — Start and manage Tavus CVI conversation sessions.

Creates a live conversation from a persona, returns the URL to join.
Can run both conditions for A/B comparison.

Usage:
    python run_session.py              # interactive — choose A or B
    python run_session.py a            # start Condition A session
    python run_session.py b            # start Condition B session
    python run_session.py both         # start both, print URLs side by side
"""

import requests
import json
import sys
from config import (
    TAVUS_API_KEY, TAVUS_BASE_URL,
    PERSONA_A_ID, PERSONA_B_ID, CALLBACK_URL,
)


def start_conversation(persona_id: str, name: str) -> dict:
    """Create a new Tavus CVI conversation and return the response."""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": TAVUS_API_KEY,
    }

    payload = {
        "persona_id": persona_id,
        "conversation_name": name,
    }

    # If callback URL is configured, include it for webhook events
    if CALLBACK_URL:
        payload["callback_url"] = CALLBACK_URL

    response = requests.post(
        f"{TAVUS_BASE_URL}/conversations",
        headers=headers,
        json=payload,
    )

    if response.status_code not in (200, 201):
        print(f"ERROR starting conversation:")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        return {}

    return response.json()


def end_conversation(conversation_id: str) -> bool:
    """End an active conversation."""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": TAVUS_API_KEY,
    }

    response = requests.post(
        f"{TAVUS_BASE_URL}/conversations/{conversation_id}/end",
        headers=headers,
    )

    return response.status_code in (200, 204)


def get_conversation(conversation_id: str) -> dict:
    """Get conversation details including status and recording."""

    headers = {
        "x-api-key": TAVUS_API_KEY,
    }

    response = requests.get(
        f"{TAVUS_BASE_URL}/conversations/{conversation_id}",
        headers=headers,
    )

    if response.status_code == 200:
        return response.json()
    return {}


def main():
    if not TAVUS_API_KEY:
        print("ERROR: TAVUS_API_KEY not set in .env")
        sys.exit(1)

    # Determine which condition to run
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""

    if not arg:
        print("Which condition?")
        print("  a    — Condition A (targeted causal prober)")
        print("  b    — Condition B (generic adaptive prober)")
        print("  both — Start both sessions")
        arg = input("> ").strip().lower()

    conditions = []
    if arg in ("a", "both"):
        if not PERSONA_A_ID:
            print("ERROR: PERSONA_A_ID not set. Run setup_personas.py first.")
            sys.exit(1)
        conditions.append(("A", PERSONA_A_ID))
    if arg in ("b", "both"):
        if not PERSONA_B_ID:
            print("ERROR: PERSONA_B_ID not set. Run setup_personas.py first.")
            sys.exit(1)
        conditions.append(("B", PERSONA_B_ID))

    if not conditions:
        print("Invalid option. Use 'a', 'b', or 'both'.")
        sys.exit(1)

    print("=" * 60)
    print("STARTING CONVERSATION SESSION(S)")
    print("=" * 60)

    sessions = []
    for label, persona_id in conditions:
        print(f"\n[Condition {label}] Starting conversation...")
        result = start_conversation(
            persona_id=persona_id,
            name=f"Interview Session - Condition {label}",
        )

        conv_id = result.get("conversation_id", "")
        conv_url = result.get("conversation_url", "")

        if conv_url:
            print(f"  ✓ Conversation ID: {conv_id}")
            print(f"  ✓ JOIN URL: {conv_url}")
            sessions.append({"label": label, "id": conv_id, "url": conv_url})
        else:
            print(f"  ✗ Failed to start conversation")
            print(f"    Response: {json.dumps(result, indent=2)}")

    if sessions:
        print(f"\n{'=' * 60}")
        print("OPEN THESE URLS IN YOUR BROWSER TO JOIN:")
        print(f"{'=' * 60}")
        for s in sessions:
            print(f"  Condition {s['label']}: {s['url']}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()