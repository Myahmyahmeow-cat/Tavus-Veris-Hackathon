"""
grader.py — Independent causal-completeness evaluator.

CRITICAL: this must NOT reuse prober_a's causal schema or extraction
prompt, or the evaluation is circular. Uses a different model prompt
that evaluates completeness holistically.

Input:  original utterance + (optional) probe + respondent's follow-up
Output: completeness score (1-5) + rationale
"""

import json
from dataclasses import dataclass
from typing import Optional
import anthropic
from dotenv import load_dotenv

load_dotenv()

@dataclass
class GradeResult:
    completeness: int        # 1-5 scale
    rationale: str
    has_cause: bool
    has_effect: bool
    has_explanation: bool    # deliberately vague — NOT "mechanism"
    has_boundaries: bool     # deliberately vague — NOT "condition"
    has_alternative: bool    # deliberately vague — NOT "counterfactual"


GRADER_PROMPT = """\
You are an independent evaluator for qualitative research interview responses.

Rate how COMPLETELY the respondent has explained a cause-and-effect relationship.
A complete explanation lets a reader fully understand WHY something happened.

EVALUATION CRITERIA (check each):
- has_cause: Did they identify what drove the outcome?
- has_effect: Did they identify what the outcome was?
- has_explanation: Did they explain the process or pathway connecting
  the two — not just assert the link, but describe what happened in between?
- has_boundaries: Did they indicate when, where, or for whom this
  relationship holds (or doesn't)?
- has_alternative: Did they address (explicitly or implicitly) what
  would have happened otherwise?

COMPLETENESS SCALE:
1 = bare assertion with no supporting detail
2 = cause and effect stated, but no explanation of how or when
3 = some explanation present, but significant gaps remain
4 = well-explained with minor gaps
5 = thorough — a reader could fully reconstruct the causal story

You will receive the respondent's FULL explanation (initial statement +
any follow-up they gave after being probed).

Respond with ONLY a JSON object. No markdown, no commentary.
{
  "completeness": <1-5>,
  "rationale": "<1-2 sentences>",
  "has_cause": true/false,
  "has_effect": true/false,
  "has_explanation": true/false,
  "has_boundaries": true/false,
  "has_alternative": true/false
}"""


def grade_response(
    initial_utterance: str,
    probe: Optional[str],
    follow_up: Optional[str],
) -> GradeResult:
    """Grade the causal completeness of a respondent's full explanation.

    Combines the initial utterance with any follow-up elicited by a probe.
    """
    # Build the full response text the grader sees
    if probe and follow_up:
        full_text = (
            f"Initial statement: {initial_utterance}\n"
            f"[Interviewer asked: {probe}]\n"
            f"Follow-up response: {follow_up}"
        )
    else:
        full_text = f"Statement: {initial_utterance}"

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=GRADER_PROMPT,
        messages=[{"role": "user", "content": full_text}],
    )
    raw = json.loads(response.content[0].text)
    return GradeResult(
        completeness=raw["completeness"],
        rationale=raw["rationale"],
        has_cause=raw.get("has_cause", False),
        has_effect=raw.get("has_effect", False),
        has_explanation=raw.get("has_explanation", False),
        has_boundaries=raw.get("has_boundaries", False),
        has_alternative=raw.get("has_alternative", False),
    )


# ── Test ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("GRADER — TEST RUN")
    print("=" * 60)

    # Test 1: bare assertion, no probe
    print("\n[bare assertion, no follow-up]")
    g1 = grade_response(
        "Remote work absolutely destroyed our culture.",
        probe=None,
        follow_up=None,
    )
    print(f"  Completeness: {g1.completeness}/5")
    print(f"  Rationale:    {g1.rationale}")
    print(f"  cause={g1.has_cause} effect={g1.has_effect} expl={g1.has_explanation} "
          f"bound={g1.has_boundaries} alt={g1.has_alternative}")

    # Test 2: bare assertion + targeted probe + good follow-up
    print("\n[bare assertion + targeted probe + mechanism follow-up]")
    g2 = grade_response(
        "Remote work absolutely destroyed our culture.",
        probe="What was it about working remotely that started pulling the culture apart?",
        follow_up=(
            "People stopped having those hallway conversations. New hires never "
            "built relationships with the team, so they felt isolated and left "
            "within six months. The informal knowledge transfer just disappeared."
        ),
    )
    print(f"  Completeness: {g2.completeness}/5")
    print(f"  Rationale:    {g2.rationale}")
    print(f"  cause={g2.has_cause} effect={g2.has_effect} expl={g2.has_explanation} "
          f"bound={g2.has_boundaries} alt={g2.has_alternative}")

    # Test 3: already-complete statement, no probe needed
    print("\n[complete statement, no probe]")
    g3 = grade_response(
        "The new onboarding flow reduced churn by 15% because it got users to "
        "their first value moment in under two minutes instead of five, and "
        "without it we'd still be losing half our trial signups.",
        probe=None,
        follow_up=None,
    )
    print(f"  Completeness: {g3.completeness}/5")
    print(f"  Rationale:    {g3.rationale}")
    print(f"  cause={g3.has_cause} effect={g3.has_effect} expl={g3.has_explanation} "
          f"bound={g3.has_boundaries} alt={g3.has_alternative}")

    print(f"\n{'=' * 60}")