"""
causal_frame.py — Causal frame schema + structured-output extraction.

Slots:
  cause, effect        → almost always present when there's a claim
  mechanism            → HOW the cause produces the effect (most commonly missing)
  condition            → WHEN / under what scope the relationship holds
  counterfactual       → what would have happened WITHOUT the cause

Probe targets are mechanism, condition, counterfactual.
"""

import os
import json
from dataclasses import dataclass
from typing import Optional
import anthropic
from dotenv import load_dotenv

load_dotenv()

# ── Schema ─────────────────────────────────────────────────

@dataclass
class CausalFrame:
    has_claim: bool
    cause: Optional[str] = None
    effect: Optional[str] = None
    mechanism: Optional[str] = None
    condition: Optional[str] = None
    counterfactual: Optional[str] = None

    @property
    def missing(self) -> list[str]:
        """Probe-target slots that are absent."""
        if not self.has_claim:
            return []
        return [s for s in ("mechanism", "condition", "counterfactual")
                if not getattr(self, s)]

    @property
    def is_complete(self) -> bool:
        return self.has_claim and len(self.missing) == 0

    @property
    def highest_value_missing(self) -> Optional[str]:
        """Return the single best slot to probe (mechanism > condition > counterfactual)."""
        for slot in ("mechanism", "condition", "counterfactual"):
            if not getattr(self, slot):
                return slot
        return None


# ── Extraction prompt ──────────────────────────────────────

EXTRACTION_PROMPT = """\
You are a causal-frame extractor for qualitative research interviews.

Given a respondent utterance, determine:
1. Whether it contains a cause→effect claim.
2. If yes, extract whichever of the following slots are EXPLICITLY or CLEARLY
   IMPLICITLY present. Leave a slot null if the speaker did not address it.

SLOTS:
- cause: what the speaker identifies as the cause / driver.
- effect: the outcome or consequence they attribute to it.
- mechanism: HOW the cause produces the effect — the pathway, process, or
  intermediary. Must describe a step between cause and effect, not just
  restate the cause.
- condition: WHEN or under what circumstances the relationship holds —
  scope, boundary conditions, or qualifiers.
- counterfactual: what would have happened WITHOUT the cause — explicit
  or strongly implied.

Respond with ONLY a JSON object. No markdown fences, no commentary.
{
  "has_claim": true | false,
  "cause": "..." | null,
  "effect": "..." | null,
  "mechanism": "..." | null,
  "condition": "..." | null,
  "counterfactual": "..." | null
}

If there is no causal claim, return all slots as null."""


# ── Extraction function ───────────────────────────────────

def extract_causal_slots(utterance: str) -> CausalFrame:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": utterance}],
    )
    raw = json.loads(response.content[0].text)
    return CausalFrame(
        has_claim=raw.get("has_claim", False),
        cause=raw.get("cause"),
        effect=raw.get("effect"),
        mechanism=raw.get("mechanism"),
        condition=raw.get("condition"),
        counterfactual=raw.get("counterfactual"),
    )


# ── Test fixtures ──────────────────────────────────────────

TEST_CASES = [
    {
        "label": "complete",
        "text": (
            "The new onboarding flow reduced churn by 15% because it got users "
            "to their first value moment in under two minutes instead of five, "
            "and without it we'd still be losing half our trial signups."
        ),
        "expect_claim": True,
        "expect_missing": ["condition"],
    },
    {
        "label": "missing-mechanism",
        "text": "The rollout definitely caused the spike in churn. We saw it immediately after launch.",
        "expect_claim": True,
        "expect_missing": ["mechanism", "counterfactual"],
    },
    {
        "label": "bare-assertion",
        "text": "Remote work absolutely destroyed our culture.",
        "expect_claim": True,
        "expect_missing": ["mechanism", "condition", "counterfactual"],
    },
    {
        "label": "has-mechanism-missing-rest",
        "text": (
            "I think the price increase pushed enterprise clients away because "
            "they had already locked in competitor quotes."
        ),
        "expect_claim": True,
        "expect_missing": [],
    },
    {
        "label": "generic-no-scope",
        "text": "Better training leads to better retention.",
        "expect_claim": True,
        "expect_missing": ["mechanism", "condition", "counterfactual"],
    },
    {
        "label": "no-claim",
        "text": "Yeah, so we switched to the new platform in March. The team was pretty excited about it.",
        "expect_claim": False,
        "expect_missing": [],
    },
]


# ── Validation runner ──────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("CAUSAL FRAME EXTRACTION — VALIDATION RUN")
    print("=" * 60)

    passes, fails = 0, 0

    for case in TEST_CASES:
        print(f"\n[{case['label']}]")
        print(f"  \"{case['text'][:80]}{'...' if len(case['text']) > 80 else ''}\"")

        frame = extract_causal_slots(case["text"])

        claim_ok = frame.has_claim == case["expect_claim"]
        missing_ok = set(frame.missing) == set(case["expect_missing"])
        ok = claim_ok and missing_ok

        if ok:
            passes += 1
        else:
            fails += 1

        print(f"  has_claim: {frame.has_claim}  {'✓' if claim_ok else '✗  expected ' + str(case['expect_claim'])}")
        if frame.has_claim:
            print(f"  cause:          {frame.cause}")
            print(f"  effect:         {frame.effect}")
            print(f"  mechanism:      {frame.mechanism}")
            print(f"  condition:      {frame.condition}")
            print(f"  counterfactual: {frame.counterfactual}")
        print(f"  missing:   {frame.missing}  {'✓' if missing_ok else '✗  expected ' + str(case['expect_missing'])}")

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passes}/{passes + fails} passed")
    if fails:
        print(f"  {fails} mismatches — review extraction prompt or relabel fixtures.")
    print("=" * 60)