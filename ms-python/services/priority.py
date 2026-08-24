"""
Détermine, pour une région donnée, quelles centrales chercher en priorité.
"""


def get_region(regions_index, region_id):
# Retourne le dictionnaire complet d'une région à partir de son id.
    if region_id not in regions_index:
        raise ValueError(f"Région inconnue : {region_id}")
    return regions_index[region_id]


def local_plant_ids(region):
    #Centrales situées  dans la région (priorite 1)
    return region["local_plant_ids"]


def external_entry_plant_ids(region):
    #entrales voisines connues(priorite 2).
    return region["external_entry_plant_ids"]


def candidate_search_order(region):
  # Retourne la liste des centrales à examiner, dans l'ordre de priorité :
  #d'abord les centrales locales, ensuite les centrales d'entrée externes.

    ordered = []
    seen = set()

    for plant_id in local_plant_ids(region) + external_entry_plant_ids(region):
        if plant_id not in seen:
            ordered.append(plant_id)
            seen.add(plant_id)

    return ordered


if __name__ == "__main__":
    from graph_loader import load_data, build_regions_index

    data = load_data()
    regions_index = build_regions_index(data)

    occitanie = get_region(regions_index, "occitanie")
    print("Centrales locales Occitanie :", local_plant_ids(occitanie))
    print("Centrales d'entrée Occitanie :", external_entry_plant_ids(occitanie))
    print("Ordre de recherche Occitanie :", candidate_search_order(occitanie))

    ile_de_france = get_region(regions_index, "ile_de_france")
    print("Ordre de recherche Île-de-France (pas de centrale locale) :", candidate_search_order(ile_de_france))