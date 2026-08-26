try:
    from .allocation import allocate
except ImportError:
    from allocation import allocate


def allocate_regional_demands(
    regional_demands,
    current_state,
    graph,
    plants_index,
    regions_index,
    simulation_parameters,
):
    """
    Relie l'allocation régionale du premier brief
    à l'état du moteur temporel.

    regional_demands contient la demande par région.

    current_state contient la production des centrales
    au quart d'heure précédent.
    """

    next_state = current_state.copy()
    regional_results = {}

    return {
        "state": next_state,
        "regional_results": regional_results,
        "missing_mw": 0.0,
    }
