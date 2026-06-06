"""
prober_b.py — Generic adaptive prober (control arm).

Same interface as prober_a, but with NO causal schema. If the answer
seems thin or underspecified, asks ONE natural follow-up. This is the
matched baseline — a competent generic prober, NOT a strawman.

The ONLY difference from prober_a is the probe-selection module.
"""

from typing import Optional
import anthropic
from dotenv import load_dotenv
from causal_frame import CausalFrame, extract_causal_slots

load_dotenv()

GENERIC_PROBE_PROMPT = """\
You are an interviewer follow-up generator for qualitative research.

The respondent just said something. If their answer seems thin,
underspecified, or could benefit from elaboration, generate ONE short,
gentle follow-up question to draw out more detail.

Utterance: "{utterance}"

RULES:
- Ask exactly ONE question.
- Be conversational and gentle — this is a research interview.
- Reference what they said — show you were listening.
- Ask for more detail, clarification, or elaboration naturally.
- Do NOT use any causal analysis framework or schema.
- Do NOT ask about specific analytical categories like "mechanism" or "conditions."
- Do NOT ask multiple questions or offer options.
- Keep it under 30 words.
- If the answer already seems thorough and complete, respond with exactly: NO_PROBE

Respond with ONLY the question (or NO_PROBE). No quotes, no preamble."""


def generate_generic_probe(utterance: str, frame: CausalFrame) -> Optional[str]:
    """Generate a generic follow-up if the answer seems thin.

    Takes a CausalFrame for interface compatibility with prober_a,
    but does NOT use its slot structure for probe selection.

    Returns None if:
    - No causal claim (nothing to follow up on)
    - The model judges the answer as already thorough
    """
    if not frame.has_claim:
        return None

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        system=GENERIC_PROBE_PROMPT.format(utterance=utterance),
        messages=[{"role": "user", "content": "Generate the follow-up question."}],
    )
    result = response.content[0].text.strip()

    if result == "NO_PROBE":
        return None
    return result


# ── Test ───────────────────────────────────────────────────

TEST_UTTERANCES = [
    "The rollout definitely caused the spike in churn. We saw it immediately after launch.",
    "Remote work absolutely destroyed our culture.",
    "I think the price increase pushed enterprise clients away because they had already locked in competitor quotes.",
    "The new onboarding flow reduced churn by 15% because it got users to their first value moment in under two minutes instead of five, and without it we'd still be losing half our trial signups.",
    "Yeah, so we switched to the new platform in March. The team was pretty excited about it.",
]

if __name__ == "__main__":
    print("=" * 60)
    print("PROBER B (GENERIC) — TEST RUN")
    print("=" * 60)

    for text in TEST_UTTERANCES:
        print(f"\nUtterance: \"{text[:80]}{'...' if len(text) > 80 else ''}\"")
        frame = extract_causal_slots(text)

        probe = generate_generic_probe(text, frame)
        if probe:
            print(f"  Probe: {probe}")
        else:
            print(f"  Probe: [none — {'no claim' if not frame.has_claim else 'judged complete'}]")

    print(f"\n{'=' * 60}")