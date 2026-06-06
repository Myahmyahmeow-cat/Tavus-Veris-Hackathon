"""
harness.py — A/B evaluation harness.

Runs both prober arms (A=targeted, B=generic) on identical utterances,
simulates respondent follow-ups, grades independently, and compares.

The ONLY difference between arms is the probe-selection module.
Held identical: base LLM, simulated respondents, grader, restraint
policy (≤1 probe per boundary), and utterance set.
"""

import json
from dataclasses import dataclass, asdict
from typing import Optional
import anthropic
from dotenv import load_dotenv

from causal_frame import extract_causal_slots, CausalFrame
from prober_a import generate_targeted_probe
from prober_b import generate_generic_probe
from grader import grade_response, GradeResult

load_dotenv()

# ── Simulated respondent ──────────────────────────────────

RESPONDENT_PROMPT = """\
You are a simulated research interview respondent. You are a mid-level
manager reflecting on your work experience. You just said something,
and the interviewer asked a follow-up question.

Your original statement: "{utterance}"
Interviewer's question: "{probe}"

RESPOND NATURALLY:
- Answer in 2-4 sentences, conversational tone.
- Add SOME useful detail but don't be perfectly comprehensive.
- You may be slightly vague or leave minor gaps — you're a real person,
  not an encyclopedia.
- Stay consistent with your original statement.
- Do NOT use jargon like "mechanism" or "causal pathway."

Respond with ONLY your answer. No quotes, no meta-commentary."""


def simulate_follow_up(utterance: str, probe: str) -> str:
    """Simulate a respondent's answer to a probe."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=RESPONDENT_PROMPT.format(utterance=utterance, probe=probe),
        messages=[{"role": "user", "content": "Please respond to the interviewer's question."}],
    )
    return response.content[0].text.strip()


# ── Single-arm runner ─────────────────────────────────────

@dataclass
class ArmResult:
    arm: str                        # "A" or "B"
    utterance: str
    probe: Optional[str]
    follow_up: Optional[str]
    grade: GradeResult
    probe_count: int                # 0 or 1


def run_arm(
    arm_label: str,
    utterance: str,
    frame: CausalFrame,
    probe_fn,
) -> ArmResult:
    """Run one arm: probe → simulate follow-up → grade."""
    probe = probe_fn(utterance, frame)
    follow_up = None
    probe_count = 0

    if probe:
        probe_count = 1
        follow_up = simulate_follow_up(utterance, probe)

    grade = grade_response(utterance, probe, follow_up)

    return ArmResult(
        arm=arm_label,
        utterance=utterance,
        probe=probe,
        follow_up=follow_up,
        grade=grade,
        probe_count=probe_count,
    )


# ── Test utterance set ────────────────────────────────────

UTTERANCES = [
    "The rollout definitely caused the spike in churn. We saw it immediately after launch.",
    "Remote work absolutely destroyed our culture.",
    "Better training leads to better retention.",
    "Switching to agile cut our release cycle in half. The team was shipping faster almost overnight.",
    "Our biggest client left because of the pricing change.",
    "The rebrand confused everyone. Sales tanked for two quarters.",
]


# ── Main harness ──────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("A/B EVALUATION HARNESS")
    print("A = targeted causal-slot prober  |  B = generic adaptive prober")
    print("=" * 70)

    results_a = []
    results_b = []

    for i, utterance in enumerate(UTTERANCES):
        print(f"\n{'─' * 70}")
        print(f"UTTERANCE {i+1}: \"{utterance[:75]}{'...' if len(utterance) > 75 else ''}\"")
        print(f"{'─' * 70}")

        # Extract frame ONCE — shared across arms
        frame = extract_causal_slots(utterance)
        print(f"  Frame: cause={frame.cause} | effect={frame.effect}")
        print(f"  Missing: {frame.missing}")

        # Run both arms
        a = run_arm("A", utterance, frame, generate_targeted_probe)
        b = run_arm("B", utterance, frame, generate_generic_probe)

        results_a.append(a)
        results_b.append(b)

        # Display per-utterance comparison
        for r in (a, b):
            print(f"\n  [{r.arm}] Probe: {r.probe or '[none]'}")
            if r.follow_up:
                print(f"      Follow-up: {r.follow_up[:100]}{'...' if r.follow_up and len(r.follow_up) > 100 else ''}")
            print(f"      Grade: {r.grade.completeness}/5 | probes used: {r.probe_count}")
            print(f"      Rationale: {r.grade.rationale}")

    # ── Summary ────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    a_scores = [r.grade.completeness for r in results_a]
    b_scores = [r.grade.completeness for r in results_b]
    a_probes = sum(r.probe_count for r in results_a)
    b_probes = sum(r.probe_count for r in results_b)

    avg_a = sum(a_scores) / len(a_scores)
    avg_b = sum(b_scores) / len(b_scores)

    print(f"\n  Arm A (targeted):  avg completeness = {avg_a:.2f}/5  |  total probes = {a_probes}")
    print(f"  Arm B (generic):   avg completeness = {avg_b:.2f}/5  |  total probes = {b_probes}")
    print(f"  Delta (A - B):     {avg_a - avg_b:+.2f}")

    # Win condition check
    print(f"\n  WIN CONDITION: A >= B on completeness AND A <= B on probe count")
    completeness_win = avg_a >= avg_b
    probe_win = a_probes <= b_probes
    print(f"  Completeness: A {'≥' if completeness_win else '<'} B  {'✓' if completeness_win else '✗'}")
    print(f"  Probe count:  A {'≤' if probe_win else '>'} B  {'✓' if probe_win else '✗'}")
    print(f"  RESULT: {'WIN — targeted probing outperforms generic' if completeness_win and probe_win else 'NO WIN — see breakdown above'}")

    # Per-utterance detail
    print(f"\n  Per-utterance scores:")
    print(f"  {'Utterance':<50} {'A':>3} {'B':>3} {'Δ':>4}")
    print(f"  {'─' * 60}")
    for i, (a, b) in enumerate(zip(results_a, results_b)):
        delta = a.grade.completeness - b.grade.completeness
        label = a.utterance[:48] + (".." if len(a.utterance) > 48 else "")
        print(f"  {label:<50} {a.grade.completeness:>3} {b.grade.completeness:>3} {delta:>+4}")

    print(f"\n{'=' * 70}")