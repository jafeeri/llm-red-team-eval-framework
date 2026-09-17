"""
run_eval.py - Run a single persona evaluation against a target model

Quick way to test individual personas without running the full batch.
Useful for iterating on persona designs and escalation patterns.
"""

import argparse
import json
from conversation import ConversationRunner


def main():
    parser = argparse.ArgumentParser(description="Run a single persona evaluation")
    parser.add_argument("--persona", required=True, help="Path to persona JSON file")
    parser.add_argument("--turns", type=int, default=15, help="Number of conversation turns")
    parser.add_argument("--target-model", default="gpt-4o-mini", help="Target model to evaluate")
    parser.add_argument("--attacker-model", default="gpt-4o", help="Model to play the persona")
    parser.add_argument("--output", default="results", help="Output directory")
    parser.add_argument("--target-prompt", default=None, help="Custom target system prompt")
    parser.add_argument("--verbose", action="store_true", help="Print conversation in real-time")
    args = parser.parse_args()

    # Load persona
    with open(args.persona, "r", encoding="utf-8") as f:
        persona = json.load(f)

    print(f"Persona: {persona.get('name', 'unknown')} (ID: {persona.get('persona_id', 'unknown')})")
    print(f"Risk Category: {persona.get('risk_category', 'unknown')}")
    print(f"Target Model: {args.target_model}")
    print(f"Turns: {args.turns}")
    print("=" * 50)

    runner = ConversationRunner(
        attacker_model=args.attacker_model,
        target_model=args.target_model
    )

    result = runner.run_conversation(
        persona,
        num_turns=args.turns,
        target_system_prompt=args.target_prompt
    )

    # Print conversation if verbose
    if args.verbose:
        print("\n--- CONVERSATION TRANSCRIPT ---\n")
        for entry in result["transcript"]:
            role = "CHILD" if entry["role"] == "simulated_user" else "AI"
            print(f"[Turn {entry['turn']}] {role}:")
            print(f"  {entry['content']}\n")

    # Save
    filepath = runner.save_transcript(result, args.output)
    print(f"\nCompleted in {result['elapsed_seconds']}s")
    print(f"Saved to: {filepath}")


if __name__ == "__main__":
    main()
