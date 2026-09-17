"""
batch_runner.py - Batch orchestration for running multiple persona evaluations

Loads all persona files from a directory, runs conversations in sequence,
and aggregates results. Supports resume on failure and parallel execution.
"""

import json
import os
import argparse
import time
from datetime import datetime
from conversation import ConversationRunner


class BatchRunner:
    """Orchestrates batch execution of persona-based red team evaluations."""

    def __init__(self, attacker_model="gpt-4o", target_model="gpt-4o-mini", api_key=None):
        self.runner = ConversationRunner(
            api_key=api_key,
            attacker_model=attacker_model,
            target_model=target_model
        )
        self.results_log = []

    def discover_personas(self, persona_dir):
        """Find all persona JSON files in a directory."""
        personas = []
        for filename in sorted(os.listdir(persona_dir)):
            if filename.endswith(".json"):
                filepath = os.path.join(persona_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    persona = json.load(f)
                    persona["_source_file"] = filename
                    personas.append(persona)

        print(f"Discovered {len(personas)} personas in {persona_dir}")
        return personas

    def run_batch(self, persona_dir, output_dir="results", turns_per_conversation=15,
                  target_system_prompt=None, resume=True):
        """
        Run all persona evaluations in batch.

        Args:
            persona_dir: Directory containing persona JSON files
            output_dir: Directory to save transcripts
            turns_per_conversation: Number of turns per conversation
            target_system_prompt: Custom system prompt for the target model
            resume: Skip personas that already have results
        """
        personas = self.discover_personas(persona_dir)
        os.makedirs(output_dir, exist_ok=True)

        # Check for existing results if resume is enabled
        existing = set()
        if resume:
            for f in os.listdir(output_dir):
                if f.endswith(".json"):
                    existing.add(f.split("_2")[0])  # Extract persona_id prefix

        total = len(personas)
        completed = 0
        failed = 0

        batch_start = time.time()
        print(f"\nStarting batch run: {total} personas, {turns_per_conversation} turns each")
        print(f"Target model: {self.runner.target_model}")
        print(f"Attacker model: {self.runner.attacker_model}")
        print("=" * 60)

        for i, persona in enumerate(personas):
            persona_id = persona.get("persona_id", f"unknown_{i}")

            # Skip if already completed
            if resume and persona_id in existing:
                print(f"[{i+1}/{total}] SKIP {persona_id} (already completed)")
                continue

            print(f"\n[{i+1}/{total}] Running: {persona_id} ({persona.get('risk_category', 'unknown')})")

            try:
                result = self.runner.run_conversation(
                    persona,
                    num_turns=turns_per_conversation,
                    target_system_prompt=target_system_prompt
                )
                filepath = self.runner.save_transcript(result, output_dir)

                self.results_log.append({
                    "persona_id": persona_id,
                    "status": "completed",
                    "filepath": filepath,
                    "risk_category": persona.get("risk_category"),
                    "turns": turns_per_conversation
                })
                completed += 1

            except Exception as e:
                print(f"  ERROR: {str(e)}")
                self.results_log.append({
                    "persona_id": persona_id,
                    "status": "failed",
                    "error": str(e)
                })
                failed += 1

            # Brief pause between conversations to avoid rate limits
            if i < total - 1:
                time.sleep(2)

        batch_elapsed = time.time() - batch_start

        # Save batch run summary
        summary = {
            "batch_timestamp": datetime.now().isoformat(),
            "total_personas": total,
            "completed": completed,
            "failed": failed,
            "skipped": total - completed - failed,
            "elapsed_seconds": round(batch_elapsed, 2),
            "target_model": self.runner.target_model,
            "attacker_model": self.runner.attacker_model,
            "turns_per_conversation": turns_per_conversation,
            "results": self.results_log
        }

        summary_path = os.path.join(output_dir, f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'=' * 60}")
        print(f"BATCH COMPLETE")
        print(f"Completed: {completed} | Failed: {failed} | Skipped: {total - completed - failed}")
        print(f"Time: {round(batch_elapsed/60, 1)} minutes")
        print(f"Summary: {summary_path}")

        return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run batch persona evaluations")
    parser.add_argument("--persona-dir", required=True, help="Directory with persona JSON files")
    parser.add_argument("--output", default="results", help="Output directory for transcripts")
    parser.add_argument("--turns", type=int, default=15, help="Turns per conversation")
    parser.add_argument("--target-model", default="gpt-4o-mini", help="Target model to test")
    parser.add_argument("--attacker-model", default="gpt-4o", help="Model to simulate personas")
    parser.add_argument("--target-prompt", default=None, help="Custom system prompt for target")
    parser.add_argument("--no-resume", action="store_true", help="Don't skip completed personas")
    args = parser.parse_args()

    batch = BatchRunner(
        attacker_model=args.attacker_model,
        target_model=args.target_model
    )

    batch.run_batch(
        persona_dir=args.persona_dir,
        output_dir=args.output,
        turns_per_conversation=args.turns,
        target_system_prompt=args.target_prompt,
        resume=not args.no_resume
    )
