from datetime import date, timedelta

def telecharger_calendrier(annee, chemin_fichier):
    url = (
        "https://calendrier.api.gouv.fr/jours-feries/"
        f"metropole/{annee}.json"
    )

    reponse = requests.get(url, timeout=30)
    reponse.raise_for_status()
    jours_feries = reponse.json()

    calendrier = []
    jour = date(annee, 1, 1)

    while jour.year == annee:
        date_texte = jour.isoformat()

        calendrier.append({
            "date": date_texte,
            "jour_semaine": jour.weekday(),  # Lundi = 0, dimanche = 6
            "weekend": jour.weekday() >= 5,
            "ferie": date_texte in jours_feries,
            "nom_ferie": jours_feries.get(date_texte),
        })

        jour += timedelta(days=1)

    chemin = Path(chemin_fichier)
    chemin.parent.mkdir(parents=True, exist_ok=True)


    with chemin.open("w", encoding="utf-8") as fichier:
        json.dump(calendrier, fichier, indent=2, ensure_ascii=False)

    print(f"Calendrier créé : {chemin.resolve()}")
    return str(chemin)
    dossier = Path(file).resolve().parent

    telecharger_calendrier(
        2026,
        dossier / "data" / "calendrier-2026.json",
    )

    with chemin.open("w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, indent=2, ensure_ascii=False)

    print(f"Nombre de mesures : {len(donnees.get('records', []))}")
    print(f"Fichier créé ici : {chemin.resolve()}")

    return str(chemin)


if __name__ == "__main__":
    telecharger_json(URL_API, FICHIER_SORTIE)