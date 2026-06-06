"""
prober_a.py — Targeted causal-slot prober (treatment arm).

Takes an utterance + its CausalFrame → generates ONE gentle follow-up
that targets the highest-value missing slot.

Slot priority: mechanism > condition > counterfactual.
"""

import json
from typing import Optional
import anthropic
from dotenv import load_dotenv
from causal_frame import CausalFrame, extract_causal_slots

load_dotenv()

PROBE_PROMPT = """\
You are an interviewer follow-up generator for qualitative research.

The respondent just said something containing a causal claim. Your job:
generate ONE short, gentle follow-up question that targets a SPECIFIC
missing piece of their explanation.

CONTEXT:
- Utterance: "{utterance}"
- Cause identified: {cause}
- Effect identified: {effect}
- Missing slot to probe: {slot}

SLOT DEFINITIONS:
- mechanism: HOW the cause led to the effect — the process, pathway, or
  intermediary step. Ask what happened BETWEEN cause and effect.
- condition: WHEN or under what circumstances this relationship holds.
  Ask about scope, boundaries, or qualifying factors.
- counterfactual: what would have happened WITHOUT the cause. Ask them
  to imagine the alternative scenario.

RULES:
- Ask exactly ONE question.
- Be conversational and gentle — this is a research interview, not a deposition.
- Reference what they actually said — show you were listening.
- Do NOT explain why you're asking or what slot you're targeting.
- Do NOT ask multiple questions or offer options.
- Keep it under 30 words.

Respond with ONLY the question. No quotes, no preamble."""


def generate_targeted_probe(utterance: str, frame: CausalFrame) -> Optional[str]:
    """Generate a probe targeting the highest-value missing causal slot.
    
    Returns None if:
    - No causal claim was found
    - The frame is already complete (nothing to probe)
    """
    if not frame.has_claim or frame.is_complete:
        return None

    slot = frame.highest_value_missing
    if slot is None:
        return None

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        system=PROBE_PROMPT.format(
            utterance=utterance,
            cause=frame.cause or "unclear",
            effect=frame.effect or "unclear",
            slot=slot,
        ),
        messages=[{"role": "user", "content": "Generate the follow-up question."}],
    )
    return response.content[0].text.strip()


# ── Test ───────────────────────────────────────────────────

TEST_UTTERANCES = [
    # Missing mechanism — should ask HOW
    "The rollout definitely caused the spike in churn. We saw it immediately after launch.",
    # Missing everything — should target mechanism first
    "Remote work absolutely destroyed our culture.",
    # Missing condition + counterfactual — should target condition
    "I think the price increase pushed enterprise clients away because they had already locked in competitor quotes.",
    # Complete — should return None
    "The new onboarding flow reduced churn by 15% because it got users to their first value moment in under two minutes instead of five, and without it we'd still be losing half our trial signups.",
    # No claim — should return None
    "Yeah, so we switched to the new platform in March. The team was pretty excited about it.",
]

if __name__ == "__main__":
    print("=" * 60)
    print("PROBER A (TARGETED) — TEST RUN")
    print("=" * 60)

    for text in TEST_UTTERANCES:
        print(f"\nUtterance: \"{text[:80]}{'...' if len(text) > 80 else ''}\"")
        frame = extract_causal_slots(text)
        print(f"  Missing: {frame.missing}")
        print(f"  Target:  {frame.highest_value_missing}")

        probe = generate_targeted_probe(text, frame)
        if probe:
            print(f"  Probe:   {probe}")
        else:
            print(f"  Probe:   [none — {'complete' if frame.is_complete else 'no claim'}]")

    print(f"\n{'=' * 60}")