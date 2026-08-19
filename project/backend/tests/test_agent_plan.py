"""Pruebas de integración del agente UCS contra el simulador oficial."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from agent import solve_scenario  # noqa: E402
from simulator import find_corridor, goal_satisfied, load_scenario, simulate  # noqa: E402


def costo_oficial_del_paso(scenario: dict, step: dict) -> int:
    """Obtiene el costo que exige el escenario para un paso del contrato."""
    action_costs = scenario["action_costs"]
    op = step["op"]

    if op == "MOVE":
        corridor = find_corridor(scenario, step["from"], step["to"])
        return corridor["cost"]

    if op == "PICKUP":
        return action_costs["pickup"]

    if op == "DROP":
        return action_costs["drop"]

    if op == "INTERACT":
        if step["action"] == "RECHARGE":
            return action_costs["recharge"]
        return action_costs["interact"]

    raise AssertionError(f"Operación desconocida: {op}")


def test_ucs_agent_finds_a_legal_solution() -> None:
    """El agente encuentra un plan y el simulador oficial lo puede ejecutar."""
    scenario = load_scenario()
    result = solve_scenario(scenario)

    assert result["solution_found"] is True, result["message"]
    assert result["steps"], "El agente indicó éxito pero no devolvió pasos."

    final_state = simulate(scenario, result["steps"])

    assert goal_satisfied(scenario, final_state), (
        "El plan fue ejecutable, pero no dejó todas las estaciones objetivo ONLINE."
    )


def test_ucs_agent_uses_only_contract_operations() -> None:
    """El plan externo solo puede usar las cuatro operaciones permitidas."""
    scenario = load_scenario()
    result = solve_scenario(scenario)

    valid_ops = {"MOVE", "PICKUP", "DROP", "INTERACT"}
    valid_interactions = {"OPEN_DOOR", "REPAIR", "ACTIVATE", "RECHARGE"}

    for step in result["steps"]:
        assert step["op"] in valid_ops, step

        if step["op"] == "INTERACT":
            assert step["action"] in valid_interactions, step


def test_ucs_agent_reports_official_costs() -> None:
    """Cada paso y el costo total deben coincidir con scenario.json."""
    scenario = load_scenario()
    result = solve_scenario(scenario)

    for step in result["steps"]:
        expected_cost = costo_oficial_del_paso(scenario, step)
        assert step["cost"] == expected_cost, (
            f"Costo inválido en {step}. "
            f"El escenario exige {expected_cost}, pero el plan reportó {step['cost']}."
        )

    calculated_total = sum(step["cost"] for step in result["steps"])

    assert result["total_cost"] == calculated_total
    assert result["total_cost"] == 82


if __name__ == "__main__":
    test_ucs_agent_finds_a_legal_solution()
    test_ucs_agent_uses_only_contract_operations()
    test_ucs_agent_reports_official_costs()
    print("All UCS agent tests passed.")