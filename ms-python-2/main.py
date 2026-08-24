from fastapi import FastAPI, HTTPException, Header, Depends
app = FastAPI()

import argparse

from services.graph_loader import (
    load_reference_consumption,
    load_temporal_nuclear_parameters,
)
from services.temporal_engine import simulate_day


def run_phase1(number_of_steps=96):
    consumption = load_reference_consumption()
    nuclear_parameters = load_temporal_nuclear_parameters()
    return simulate_day(consumption, nuclear_parameters, number_of_steps)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulation temporelle EnergIA - Phase 1")
    parser.add_argument("--steps", type=int, default=96, help="Nombre de quarts d'heure")
    arguments = parser.parse_args()

    simulation = run_phase1(arguments.steps)
    for step in simulation["steps"]:
        print(
            f"{step['timestamp']} | demande={step['demand_mw']:.0f} MW | "
            f"nucléaire={step['production_mw']:.0f} MW | "
            f"manquant={step['missing_mw']:.0f} MW | "
            f"surplus={step['forced_surplus_mw']:.0f} MW"
        )

    print(
        f"Résumé : {simulation['steps_count']} pas, "
        f"journée complète={simulation['complete_day']}, "
        f"demande toujours satisfaite={simulation['all_demand_satisfied']}"
    )
