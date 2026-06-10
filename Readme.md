Causal Interview Agent
An A/B-tested framework for voice AI that treats emotion as a diagnostic signal, not a styling knob.
Built for the AI Tinkerers NYC "Emotionally Intelligent AI" Hackathon.
Stack: Tavus CVI (Raven-1 perception) · Anthropic Claude · Daily Python SDK · Docker

The problem
Emotion detection without structural analysis is just expensive empathy. Today's "emotionally intelligent" agents detect that you're frustrated and say "I hear you." They detect enthusiasm and match your energy. They never ask: did this person actually explain anything?
This project tests a different hypothesis: an interview agent that analyzes the causal structure of what a respondent says — and uses emotional perception to decide when to probe the gaps — elicits more complete explanations than a competent generic prober, without asking more questions.
The core idea: causal frames
Every causal claim a respondent makes is decomposed into five slots (causal_frame.py):
SlotWhat it capturesTypically present?causeWhat drove the outcomeAlmost alwayseffectWhat the outcome wasAlmost alwaysmechanismHow the cause produced the effectMost commonly missingconditionWhen/for whom the relationship holdsOften missingcounterfactualWhat would have happened without the causeOften missing
"The rollout definitely caused the spike in churn" has a cause and an effect — and nothing else. The agent's job is to notice which slots are empty and probe the highest-value gap (mechanism > condition > counterfactual), one gentle question at a time.
Experimental design
This is an A/B test, not a demo. The only difference between arms is the probe-selection module — base LLM, restraint policy (≤1 probe per boundary), simulated respondents, stimulus set, and grader are held identical.

Arm A (treatment) — prober_a.py: extracts the causal frame, targets the single highest-value missing slot.
Arm B (control) — prober_b.py: a competent generic adaptive prober, not a strawman. It asks a natural follow-up when an answer seems thin, and is allowed to decline (NO_PROBE) when an answer is already thorough.

Falsifiable win condition: A wins only if it achieves ≥ B on graded completeness and ≤ B on probe count. More questions buying more completeness would prove nothing.
Guarding against circular evaluation
The most common failure mode in LLM-graded experiments is the grader sharing the treatment's schema — then "A wins" just means A speaks the grader's language. The grader (grader.py) deliberately does not reuse the causal-frame schema or its vocabulary: it evaluates completeness holistically using intentionally vague criteria (has_explanation, not mechanism; has_boundaries, not condition; has_alternative, not counterfactual). The prober and grader cannot pattern-match each other's terms.
Results
From the live demo sessions (Demo & Findings), with both conditions running as Tavus CVI personas against identical stimuli:

Structural probing — 6/6 vs 0/6. Condition A asked a structural "why" question targeting the specific causal gap on every stimulus. Condition B asked temporal "what happened next" questions on every stimulus and never targeted the causal gap.
Emotion × structure interaction. A correctly handled the two key cases the framework predicts: a frustrated respondent giving a bare assertion (acknowledged the emotion, then probed for mechanism — where B empathized and asked about timeline) and an enthusiastic respondent saying nothing structural (saw through the energy and demanded the mechanism of change — where B matched the energy and accepted vagueness).
Perception sensitivity. A detected tentative delivery (verbal hedging) where B categorized everything as emotionally final, and A identified cases where a confident tone masked an incomplete explanation.

The offline harness (harness.py) reproduces the comparison with completeness grades (1–5 scale) and probe counts per arm, including the per-utterance breakdown and the win-condition check.
Honest limitations

The offline harness uses a simulated respondent (also Claude) being graded by Claude, with prompts written by me. The grader's vocabulary firewall mitigates schema circularity, but the simulated-respondent loop remains a confound: A could win partly because the probes and respondent share a model family's notion of a "good answer." The live Tavus path (conversation_bot.py) exists precisely to answer this — the architecture supports real human respondents; the hackathon timebox forced simulation for the quantitative arm.
n = 6 stimuli. This is a hackathon-scale signal, not a study. The result is directional.
Single-probe restraint policy keeps the comparison clean but understates what multi-turn probing could elicit.

Architecture
Participant speaks
   ├── Channel 1: Raven-1 perception (affect: confident/tentative, final/still-building)
   └── Channel 2: causal_frame.py (structured slot extraction)
            ↓
       Probe policy (affect × structure → action)
            ↓
   Targeted probe | acknowledge & advance | wait | gentle check-in
FileRolecausal_frame.pyCausal slot schema + extraction (with validation fixtures — run it directly)prober_a.pyTreatment arm: targeted slot probingprober_b.pyControl arm: generic adaptive probinggrader.pyIndependent completeness evaluator (vocabulary-firewalled)harness.pyOffline A/B harness: probe → simulated follow-up → grade → comparesetup_personas.pyCreates the two Tavus CVI personas (A and B)run_session.pyStarts live Tavus conversation sessions (python run_session.py both)conversation_bot.pyJoins the live room via Daily SDK; runs causal analysis on each user utterance in real timeconfig.pyKeys, persona IDs, shared interview questions
Running it
bashpip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY (and TAVUS_API_KEY for live sessions)

# Offline A/B evaluation (Anthropic key only)
python causal_frame.py    # validate extraction against fixtures
python harness.py         # full A/B run with summary table

# Live voice sessions (Tavus key required)
python setup_personas.py  # creates personas; put IDs in .env
python run_session.py both
python conversation_bot.py "<conversation_url>" "<conversation_id>"
requirements.txt:
anthropic
python-dotenv
requests
daily-python
Why this exists
The framework is grounded in a broader thesis: agent pipelines should be decomposed at boundaries native to how humans actually segment events and explanations (Event Segmentation Theory), not at boundaries convenient for engineers. Causal frames are one such natural joint — people reliably state causes and effects but omit mechanisms, and an agent that knows which slot is empty asks categorically better questions than one that only knows the answer "seems thin."
