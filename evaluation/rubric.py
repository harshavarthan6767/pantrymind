"""
evaluation/rubric.py — Phase 3 · Day 3
========================================
Scoring rubric for each evaluation scenario.

Scores are 0.0 – 1.0, broken into 5 dimensions:
  1. Keyword Coverage  (0.0 – 0.4)  — did the response mention expected keywords?
  2. Agent Routing     (0.0 – 0.2)  — did the right sub-agent respond?
  3. Tool Usage        (0.0 – 0.2)  — did the trace show MCP / expected tools being called?
  4. Governance        (0.0 – 0.1)  — was an approval created if scenario.expects_approval?
  5. Format Quality    (0.0 – 0.1)  — response is ≥ 50 chars, no raw JSON dumped to user
"""
import re
from dataclasses import dataclass

from evaluation.scenarios import EvalScenario


@dataclass
class ScenarioScore:
    scenario_id: str
    keyword_score: float
    agent_routing_score: float
    tool_usage_score: float
    governance_score: float
    format_score: float
    total: float
    passed: bool
    notes: list[str]

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "keyword_score": round(self.keyword_score, 3),
            "agent_routing_score": round(self.agent_routing_score, 3),
            "tool_usage_score": round(self.tool_usage_score, 3),
            "governance_score": round(self.governance_score, 3),
            "format_score": round(self.format_score, 3),
            "total": round(self.total, 3),
            "passed": self.passed,
            "notes": self.notes
        }


DOMAIN_AGENT_MAP = {
    "pantry":        "pantry_agent",
    "kitchen":       "kitchen_chef_agent",
    "finance":       "finance_agent",
    "receipt":       "receipt_agent",
    "shopping":      "shopping_agent",
    "vector_search": "pantry_agent",
    "governance":    "receipt_agent",
    "reflexion":     "kitchen_chef_agent",
}

DOMAIN_EXPECTED_TOOLS = {
    "pantry":        {"find", "aggregate", "semantic_pantry_search"},
    "kitchen":       {"find", "run_meal_optimizer"},
    "finance":       {"aggregate", "parse_date_range"},
    "receipt":       {"insertOne", "insertMany", "parse_receipt_image"},
    "shopping":      {"find", "compute_ingredient_gaps", "prioritize_shopping_list"},
    "vector_search": {"semantic_pantry_search"},
}


def score_scenario(
    scenario: EvalScenario,
    response_text: str,
    trace_events: list[dict],
    pending_actions: list[dict]
) -> ScenarioScore:
    """
    Score a single scenario run.
    
    Args:
        scenario: The EvalScenario definition.
        response_text: The full text response from the agent.
        trace_events: List of trace events from evidence_logger.
        pending_actions: List of pending_actions created during this run.
    """
    notes = []
    response_lower = response_text.lower()

    # ── 1. Keyword Coverage (max 0.4) ─────────────────────────────────────────
    matched = [kw for kw in scenario.expected_keywords if kw.lower() in response_lower]
    keyword_ratio = len(matched) / len(scenario.expected_keywords) if scenario.expected_keywords else 1.0
    keyword_score = min(0.4, keyword_ratio * 0.4)
    if keyword_ratio < 0.3:
        notes.append(f"Low keyword coverage: {len(matched)}/{len(scenario.expected_keywords)} matched")

    # ── 2. Agent Routing (max 0.2) ────────────────────────────────────────────
    expected_agents = {DOMAIN_AGENT_MAP[d] for d in scenario.domains if d in DOMAIN_AGENT_MAP}
    actual_agents = {e["agent"] for e in trace_events if e.get("event_type") == "agent_transfer"}
    # Also check if expected agent authored any event
    authored_agents = {e["agent"] for e in trace_events}

    routed_correctly = bool(expected_agents & (actual_agents | authored_agents))
    agent_routing_score = 0.2 if routed_correctly else 0.0
    if not routed_correctly:
        notes.append(f"Wrong agent routing. Expected one of {expected_agents}, got {actual_agents}")

    # ── 3. Tool Usage (max 0.2) ───────────────────────────────────────────────
    expected_tools = set()
    for d in scenario.domains:
        expected_tools.update(DOMAIN_EXPECTED_TOOLS.get(d, set()))
    
    actual_tools = {e["data"].get("tool") for e in trace_events
                   if e.get("event_type") == "tool_call" and e.get("data")}
    
    tool_overlap = len(expected_tools & actual_tools) if expected_tools else 1
    tool_max = max(len(expected_tools), 1)
    tool_usage_score = min(0.2, (tool_overlap / tool_max) * 0.2)
    if tool_usage_score < 0.1:
        notes.append(f"Tool usage low. Expected {expected_tools}, saw {actual_tools}")

    # ── 4. Governance (max 0.1) ───────────────────────────────────────────────
    if scenario.expects_approval:
        # Check that at least one pending action was created
        approval_events = [e for e in trace_events if e.get("event_type") == "approval_required"]
        if approval_events or pending_actions:
            governance_score = 0.1
        else:
            governance_score = 0.0
            notes.append("Expected approval gate was NOT triggered — governance layer may not be wired.")
    else:
        # No write expected — check no unintended pending actions were created
        governance_score = 0.1  # Passes by default (no expectation)

    # ── 5. Format Quality (max 0.1) ───────────────────────────────────────────
    format_score = 0.1
    if len(response_text) < 50:
        format_score = 0.0
        notes.append("Response too short (< 50 chars)")
    elif re.search(r'\{.*"_id".*\}', response_text, re.DOTALL):
        format_score = 0.05
        notes.append("Response may contain raw MongoDB JSON — polish needed")

    # ── Total ──────────────────────────────────────────────────────────────────
    total = keyword_score + agent_routing_score + tool_usage_score + governance_score + format_score
    passed = total >= 0.6

    return ScenarioScore(
        scenario_id=scenario.id,
        keyword_score=keyword_score,
        agent_routing_score=agent_routing_score,
        tool_usage_score=tool_usage_score,
        governance_score=governance_score,
        format_score=format_score,
        total=total,
        passed=passed,
        notes=notes
    )
