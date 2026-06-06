"""
conversation_bot.py — Analysis bot that sits in the Tavus conversation room.

Joins the conversation via Daily Python SDK. On each user utterance:
1. Extracts transcript + audio analysis from the event
2. Runs causal_frame.py for structured slot extraction
3. Appends the analysis result back into the conversation context
4. The LLM (Haiku) sees this context and uses it for probe decisions

This is the "code in the loop" — your causal_frame.py running live
during the conversation, feeding structured analysis to the agent.

Prerequisites:
    pip install daily-python

Usage:
    python conversation_bot.py <conversation_url> <conversation_id>

    # Or after starting a session via run_session.py:
    python conversation_bot.py "https://tavus.daily.co/xxxxx" "c477c9dd7aa6e4fe"
"""

import sys
import json
import time
import threading
from daily import Daily, EventHandler, CallClient
from causal_frame import extract_causal_slots, CausalFrame
from dotenv import load_dotenv

load_dotenv()


class AnalysisBot(EventHandler):
    """Bot that joins a Tavus CVI room and provides real-time causal analysis."""

    def __init__(self, conversation_id: str):
        super().__init__()
        self.conversation_id = conversation_id
        self.call_client = None
        self.turn_history = []  # track analysis per turn
        self.running = True

    def on_joined(self, data, error):
        if error:
            print(f"  ✗ Failed to join: {error}")
            self.running = False
        else:
            print(f"  ✓ Bot joined conversation room")

    def on_left(self, error):
        print(f"  Bot left room")
        self.running = False

    def on_app_message(self, message, sender: str):
        """Handle all conversation events from Tavus."""
        if not isinstance(message, dict):
            return

        event_type = message.get("event_type", "")

        # ── Handle user utterances ─────────────────────
        if event_type == "conversation.utterance":
            props = message.get("properties", {})
            speaker = props.get("speaker", "")

            # Only analyze USER utterances, not agent
            if speaker == "user":
                self._handle_user_utterance(message)

        # ── Handle tool calls (if persona has tools defined) ──
        elif event_type == "conversation.tool_call":
            self._handle_tool_call(message)

        # ── Log other events for debugging ─────────────
        elif event_type in (
            "conversation.user_started_speaking",
            "conversation.user_stopped_speaking",
            "conversation.replica_started_speaking",
            "conversation.replica_stopped_speaking",
        ):
            pass  # silently ignore speaking state events
        else:
            print(f"  📨 Event: {event_type}")

    def _handle_user_utterance(self, message):
        """Analyze a user utterance and append causal frame context."""
        props = message.get("properties", {})
        transcript = props.get("text", "")
        audio_analysis = props.get("user_audio_analysis", "")
        visual_analysis = props.get("user_visual_analysis", "")
        turn_idx = message.get("turn_idx", "?")

        if not transcript or len(transcript.strip()) < 10:
            return  # skip very short utterances

        print(f"\n  👤 User (turn {turn_idx}): {transcript[:80]}...")
        if audio_analysis:
            print(f"     🎙️  Affect: {audio_analysis}")

        # ── Run causal frame extraction ────────────────
        try:
            print(f"     🔍 Analyzing causal frame...")
            frame = extract_causal_slots(transcript)

            analysis = {
                "turn_idx": turn_idx,
                "has_claim": frame.has_claim,
                "cause": frame.cause,
                "effect": frame.effect,
                "missing_slots": frame.missing,
                "highest_priority_missing": frame.highest_value_missing,
                "is_complete": frame.is_complete,
                "audio_affect": audio_analysis,
            }

            self.turn_history.append(analysis)

            if frame.has_claim:
                print(f"     ✓ Claim detected: {frame.cause} → {frame.effect}")
                print(f"     ✓ Missing: {frame.missing}")
                print(f"     ✓ Priority target: {frame.highest_value_missing}")
            else:
                print(f"     ○ No causal claim detected")

            # ── Append analysis to conversation context ──
            self._append_context(analysis)

        except Exception as e:
            print(f"     ✗ Analysis error: {e}")

    def _append_context(self, analysis: dict):
        """Send causal frame analysis back into the conversation."""
        if not analysis["has_claim"]:
            context_text = (
                "[CAUSAL ANALYSIS: No cause-effect claim detected in this "
                "utterance. Continue the interview normally.]"
            )
        elif analysis["is_complete"]:
            context_text = (
                f"[CAUSAL ANALYSIS: Complete causal explanation detected. "
                f"Cause: {analysis['cause']}. Effect: {analysis['effect']}. "
                f"All key slots filled. Acknowledge and advance to the next "
                f"question.]"
            )
        else:
            context_text = (
                f"[CAUSAL ANALYSIS: Incomplete causal explanation. "
                f"Cause: {analysis['cause']}. Effect: {analysis['effect']}. "
                f"Missing slots: {', '.join(analysis['missing_slots'])}. "
                f"Highest priority target: {analysis['highest_priority_missing']}. "
                f"Speaker affect: {analysis['audio_affect'] or 'unknown'}. "
                f"Apply probe policy based on affect × completeness.]"
            )

        interaction = {
            "message_type": "conversation",
            "event_type": "conversation.append_context",
            "conversation_id": self.conversation_id,
            "properties": {
                "context": context_text,
            },
        }

        try:
            self.call_client.send_app_message(interaction, "*")
            print(f"     📤 Context appended: {context_text[:80]}...")
        except Exception as e:
            print(f"     ✗ Failed to append context: {e}")

    def _handle_tool_call(self, message):
        """Handle LLM tool calls (if tools are defined in persona)."""
        props = message.get("properties", {})
        tool_name = props.get("name", "")
        tool_args = props.get("arguments", {})
        tool_call_id = props.get("tool_call_id", "")

        print(f"\n  🔧 Tool call: {tool_name}({json.dumps(tool_args)[:80]})")

        if tool_name == "analyze_causal_frame":
            utterance = tool_args.get("utterance", "")
            if utterance:
                try:
                    frame = extract_causal_slots(utterance)
                    result = {
                        "has_claim": frame.has_claim,
                        "cause": frame.cause,
                        "effect": frame.effect,
                        "missing_slots": frame.missing,
                        "target_slot": frame.highest_value_missing,
                        "is_complete": frame.is_complete,
                    }
                    print(f"     ✓ Result: {json.dumps(result)[:80]}")

                    # Append as context (tool result return mechanism
                    # may vary — append context is the reliable fallback)
                    self._append_context({
                        "has_claim": frame.has_claim,
                        "cause": frame.cause,
                        "effect": frame.effect,
                        "missing_slots": frame.missing,
                        "highest_priority_missing": frame.highest_value_missing,
                        "is_complete": frame.is_complete,
                        "audio_affect": "",
                    })
                except Exception as e:
                    print(f"     ✗ Tool error: {e}")

    def print_summary(self):
        """Print analysis summary after conversation ends."""
        print(f"\n{'=' * 60}")
        print("SESSION ANALYSIS SUMMARY")
        print(f"{'=' * 60}")
        print(f"  Total turns analyzed: {len(self.turn_history)}")

        claims = [t for t in self.turn_history if t["has_claim"]]
        complete = [t for t in claims if t["is_complete"]]
        incomplete = [t for t in claims if not t["is_complete"]]

        print(f"  Causal claims found: {len(claims)}")
        print(f"  Complete: {len(complete)}")
        print(f"  Incomplete: {len(incomplete)}")

        if incomplete:
            print(f"\n  Missing slot frequency:")
            from collections import Counter
            all_missing = []
            for t in incomplete:
                all_missing.extend(t["missing_slots"])
            for slot, count in Counter(all_missing).most_common():
                print(f"    {slot}: {count}")

        print(f"{'=' * 60}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python conversation_bot.py <conversation_url> <conversation_id>")
        print("\nGet these from run_session.py output.")
        sys.exit(1)

    conversation_url = sys.argv[1]
    conversation_id = sys.argv[2]

    print("=" * 60)
    print("CAUSAL ANALYSIS BOT")
    print(f"Joining: {conversation_url}")
    print(f"Conversation: {conversation_id}")
    print("=" * 60)

    # Initialize Daily
    Daily.init()

    # Create bot
    bot = AnalysisBot(conversation_id)
    bot.call_client = CallClient(event_handler=bot)

    # Join the conversation room (audio/video off — bot is observer only)
    print("\n  Joining conversation room...")
    bot.call_client.join(
        conversation_url,
        client_settings={
            "inputs": {
                "camera": False,
                "microphone": False,
            },
        },
    )

    # Wait for conversation to end
    print("  Bot is listening. Press Ctrl+C to stop.\n")
    try:
        while bot.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Stopping bot...")

    bot.call_client.leave()
    bot.print_summary()


if __name__ == "__main__":
    main()