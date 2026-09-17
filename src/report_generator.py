"""
report_generator.py - Generate structured safety reports from evaluation results

Produces two report formats:
1. Technical report - Full details with prompts, transcripts, and failure analysis
2. Executive summary - High-level findings suitable for non-technical stakeholders

Key principle: Executive reports explain RISKS without providing exploitation details.
Parents and stakeholders need to understand what could go wrong, not how to make it happen.
"""

import json
import os
from datetime import datetime


class ReportGenerator:
    """Generates safety evaluation reports from judging results."""

    SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "PASS": 4}

    def __init__(self, evaluations_path):
        with open(evaluations_path, "r", encoding="utf-8") as f:
            self.evaluations = json.load(f)

    def generate_technical_report(self, output_path="results/technical_report.md"):
        """Generate detailed technical report for engineering teams."""
        lines = []
        lines.append("# Safety Evaluation - Technical Report")
        lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"\nTotal evaluations: {len(self.evaluations)}")

        # Sort by severity
        sorted_evals = sorted(
            self.evaluations,
            key=lambda x: self.SEVERITY_ORDER.get(x.get("severity", "PASS"), 5)
        )

        # Summary stats
        severity_counts = {}
        for e in self.evaluations:
            sev = e.get("severity", "UNKNOWN")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        lines.append("\n## Severity Distribution\n")
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "PASS"]:
            count = severity_counts.get(sev, 0)
            bar = "█" * count
            lines.append(f"- **{sev}**: {count} {bar}")

        # Category breakdown
        all_categories = {}
        for e in self.evaluations:
            for cat in e.get("failure_categories", []):
                all_categories[cat] = all_categories.get(cat, 0) + 1

        if all_categories:
            lines.append("\n## Failure Categories\n")
            for cat, count in sorted(all_categories.items(), key=lambda x: -x[1]):
                lines.append(f"- **{cat}**: {count} occurrences")

        # Detailed findings
        lines.append("\n## Detailed Findings\n")

        for eval_data in sorted_evals:
            severity = eval_data.get("severity", "UNKNOWN")
            persona = eval_data.get("persona_id", "unknown")

            lines.append(f"### [{severity}] {persona}")
            lines.append(f"- **Risk Category**: {eval_data.get('risk_category', 'N/A')}")
            lines.append(f"- **Overall Score**: {eval_data.get('overall_score', 'N/A')}/5")
            lines.append(f"- **Target Model**: {eval_data.get('target_model', 'N/A')}")

            if eval_data.get("summary"):
                lines.append(f"- **Summary**: {eval_data['summary']}")

            # Criterion-level scores
            if eval_data.get("criteria_scores"):
                lines.append("\n**Criterion Breakdown:**\n")
                for cs in eval_data["criteria_scores"]:
                    score = cs.get("score", "?")
                    try:
                        s = float(score)
                    except (TypeError, ValueError):
                        s = 0  # unscored/missing -> treat as a fail marker, never crash
                    icon = "✅" if s >= 4 else "⚠️" if s == 3 else "❌"
                    lines.append(f"  {icon} **{cs.get('criterion', '?')}**: {score}/5")
                    if cs.get("reasoning"):
                        lines.append(f"    - {cs['reasoning'][:200]}")
                    if cs.get("evidence"):
                        for ev in cs["evidence"][:2]:
                            lines.append(f"    - Evidence: \"{ev[:150]}\"")

            lines.append("\n---\n")

        report_text = "\n".join(lines)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)

        print(f"Technical report saved: {output_path}")
        return report_text

    def generate_executive_summary(self, output_path="results/executive_summary.md"):
        """
        Generate non-technical summary for stakeholders.

        This intentionally excludes:
        - Specific prompts or attack techniques
        - Step-by-step reproduction details
        - Raw transcripts
        - Technical model names or API details

        It focuses on:
        - What risks were found
        - How severe they are
        - What the impact could be on real users
        - Recommended actions
        """
        lines = []
        lines.append("# AI Safety Evaluation - Executive Summary")
        lines.append(f"\nDate: {datetime.now().strftime('%B %d, %Y')}")

        # High level overview
        total = len(self.evaluations)
        critical = len([e for e in self.evaluations if e.get("severity") == "CRITICAL"])
        high = len([e for e in self.evaluations if e.get("severity") == "HIGH"])
        passing = len([e for e in self.evaluations if e.get("severity") in ["LOW", "PASS"]])

        lines.append("\n## Overview\n")
        lines.append(f"We tested the AI system across {total} different scenarios simulating ")
        lines.append(f"how children and young users might interact with it. ")

        if critical > 0 or high > 0:
            lines.append(f"\n**{critical + high} significant safety concerns were identified** ")
            lines.append(f"that require attention before the product reaches end users.")
        else:
            lines.append(f"\nThe system performed well across most scenarios with no critical failures detected.")

        # Risk summary without technical details
        lines.append("\n## Key Findings\n")

        risk_descriptions = {
            "emotional_attachment": {
                "title": "Emotional Boundary Concerns",
                "description": "The AI did not consistently maintain appropriate emotional boundaries when children expressed loneliness or sought deep emotional connection.",
                "impact": "Children could develop unhealthy reliance on AI for emotional support instead of seeking help from trusted adults."
            },
            "secrecy": {
                "title": "Secret-Keeping Behavior",
                "description": "In some scenarios the AI agreed to keep information private from parents or guardians when asked by the simulated child user.",
                "impact": "This behavior could enable situations where a child is isolated from their support network."
            },
            "harmful_content": {
                "title": "Content Safety",
                "description": "The AI occasionally produced content that may not be appropriate for its intended age group.",
                "impact": "Young users could be exposed to material that is confusing or harmful for their developmental stage."
            },
            "manipulation": {
                "title": "Response to Pressure",
                "description": "When simulated users applied emotional pressure the AI sometimes changed its safety-related responses.",
                "impact": "This suggests the safety boundaries may not be robust enough against persistent or emotionally charged requests."
            }
        }

        # Map actual findings to descriptions
        found_categories = set()
        for e in self.evaluations:
            for cat in e.get("failure_categories", []):
                found_categories.add(cat)
            if e.get("risk_category"):
                found_categories.add(e["risk_category"])

        for cat_key, cat_info in risk_descriptions.items():
            if cat_key in found_categories:
                lines.append(f"### {cat_info['title']}")
                lines.append(f"\n{cat_info['description']}")
                lines.append(f"\n**Potential Impact**: {cat_info['impact']}\n")

        # Recommendations
        lines.append("\n## Recommendations\n")
        lines.append("1. Address all critical and high severity findings before public release")
        lines.append("2. Implement stronger emotional boundary guidelines in the AI's instructions")
        lines.append("3. Add explicit refusal patterns for secret-keeping requests")
        lines.append("4. Re-test after applying fixes to confirm improvements")
        lines.append("5. Consider ongoing periodic testing as the product evolves")

        report_text = "\n".join(lines)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)

        print(f"Executive summary saved: {output_path}")
        return report_text


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate safety reports")
    parser.add_argument("--evaluations", required=True, help="Path to evaluations JSON")
    parser.add_argument("--output-dir", default="results", help="Output directory")
    args = parser.parse_args()

    generator = ReportGenerator(args.evaluations)
    generator.generate_technical_report(os.path.join(args.output_dir, "technical_report.md"))
    generator.generate_executive_summary(os.path.join(args.output_dir, "executive_summary.md"))
