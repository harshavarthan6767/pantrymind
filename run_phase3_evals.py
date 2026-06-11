#!/usr/bin/env python
"""
run_phase3_evals.py — Phase 3 · Day 3
=======================================
Orchestrates the Phase 3 evaluation harness end-to-end:
  1. Runs all 5 scenarios against the live server
  2. Scores each scenario with the rubric
  3. Writes results to evaluation_results.json
  4. Prints a human-readable summary

Usage:
    # Make sure server is running first:
    .venv\\Scripts\\uvicorn main:app --reload

    # Then in another terminal:
    .venv\\Scripts\\python run_phase3_evals.py
    .venv\\Scripts\\python run_phase3_evals.py --scenario S1_PANTRY_SEMANTIC  # single scenario
    .venv\\Scripts\\python run_phase3_evals.py --verbose
"""
import asyncio
import argparse
import datetime
import json
import logging
import sys

from evaluation.scenarios import SCENARIOS, SCENARIO_MAP
from evaluation.runner import run_scenario
from evaluation.rubric import score_scenario, ScenarioScore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("pantrymind.eval")

PASS_THRESHOLD = 0.6
OUTPUT_FILE = "evaluation_results.json"

HEADER = """
╔══════════════════════════════════════════════════════════════════╗
║          PantryMind — Phase 3 Evaluation Harness                ║
║          Hackathon: Google Cloud Agent Builder + MongoDB MCP     ║
╚══════════════════════════════════════════════════════════════════╝
"""


def print_score(score: ScenarioScore, verbose: bool = False):
    status = "✅ PASS" if score.passed else "❌ FAIL"
    bar_len = int(score.total * 20)
    bar = "█" * bar_len + "░" * (20 - bar_len)

    print(f"\n  {status}  [{bar}] {score.total:.2f}  —  {score.scenario_id}")
    if verbose or not score.passed:
        print(f"    Keyword:  {score.keyword_score:.2f}/0.40")
        print(f"    Routing:  {score.agent_routing_score:.2f}/0.20")
        print(f"    Tools:    {score.tool_usage_score:.2f}/0.20")
        print(f"    Gov:      {score.governance_score:.2f}/0.10")
        print(f"    Format:   {score.format_score:.2f}/0.10")
        for note in score.notes:
            print(f"    ⚠  {note}")


async def main(scenario_filter: str | None = None, verbose: bool = False):
    print(HEADER)

    # Select scenarios
    if scenario_filter:
        if scenario_filter not in SCENARIO_MAP:
            print(f"❌ Unknown scenario ID: {scenario_filter}")
            print(f"   Available: {list(SCENARIO_MAP.keys())}")
            sys.exit(1)
        scenarios_to_run = [SCENARIO_MAP[scenario_filter]]
    else:
        scenarios_to_run = SCENARIOS

    print(f"  Running {len(scenarios_to_run)} scenario(s) against http://localhost:8000\n")
    print("  " + "─" * 60)

    all_scores: list[ScenarioScore] = []
    raw_results = []

    for scenario in scenarios_to_run:
        print(f"\n  ▶  {scenario.id}: {scenario.name}")
        print(f"     Message: \"{scenario.user_message[:60]}...\"")
        
        # Run the scenario
        raw = await run_scenario(scenario)
        raw_results.append(raw)

        if raw["status"] == "error":
            print(f"     ❌ Error: {raw['error']}")
            # Create a zero score
            score = ScenarioScore(
                scenario_id=scenario.id,
                keyword_score=0, agent_routing_score=0, tool_usage_score=0,
                governance_score=0, format_score=0, total=0, passed=False,
                notes=[f"Execution error: {raw['error']}"]
            )
        else:
            score = score_scenario(
                scenario=scenario,
                response_text=raw["response_text"],
                trace_events=raw["trace_events"],
                pending_actions=raw["pending_actions"]
            )

        all_scores.append(score)
        print_score(score, verbose=verbose)

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n\n  " + "═" * 60)
    print("  SUMMARY")
    print("  " + "═" * 60)

    passed = sum(1 for s in all_scores if s.passed)
    total_scenarios = len(all_scores)
    avg_score = sum(s.total for s in all_scores) / total_scenarios if total_scenarios else 0

    print(f"\n  Passed:    {passed}/{total_scenarios} scenarios")
    print(f"  Avg Score: {avg_score:.3f} / 1.000")
    print(f"  Status:    {'✅ READY FOR SUBMISSION' if passed == total_scenarios else '⚠️  SOME SCENARIOS NEED ATTENTION'}")

    # ── Write results ─────────────────────────────────────────────────────────
    results = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "server": "http://localhost:8000",
        "pass_threshold": PASS_THRESHOLD,
        "summary": {
            "passed": passed,
            "total": total_scenarios,
            "average_score": round(avg_score, 4)
        },
        "scenarios": [s.to_dict() for s in all_scores]
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n  Results written to: {OUTPUT_FILE}")
    print("  Run export_submission_evidence.py to bundle everything for submission.\n")

    return 0 if passed == total_scenarios else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PantryMind Phase 3 Evaluation Harness")
    parser.add_argument("--scenario", help="Run a specific scenario by ID (e.g. S1_PANTRY_SEMANTIC)")
    parser.add_argument("--verbose", action="store_true", help="Show per-dimension scores for all scenarios")
    args = parser.parse_args()

    exit_code = asyncio.run(main(scenario_filter=args.scenario, verbose=args.verbose))
    sys.exit(exit_code)
