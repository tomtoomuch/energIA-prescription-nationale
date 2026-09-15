
from pathlib import Path
import re
import unicodedata

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo


LIBELLES = {
    "consommation": "Consommation",
    "temperature_2m": "Température",
    "relative_humidity_2m": "Humidité",
    "jour_semaine": "Jour de semaine",
    "heure_locale": "Heure locale",
    "minute": "Minute",
    "weekend": "Week-end",
    "ferie": "Jour férié",
    "vacances_scolaires": "Vacances scolaires",
}


def nom_fichier(region):
    texte = unicodedata.normalize("NFKD", str(region))
    texte = texte.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", texte.lower()).strip("_")


def preparer_graphiques(df):
    tableau = df.copy()
    tableau["date_heure"] = pd.to_datetime(tableau["date_heure"], utc=True)
    locales = tableau["date_heure"].dt.tz_convert("Europe/Paris")
    tableau["mois_graphique"] = locales.dt.strftime("%Y-%m")
    tableau["jour_graphique"] = locales.dt.tz_localize(None).dt.normalize()
    return tableau


def partition(mois):
    if mois < "2025-09":
        return "Entraînement : ajustement sur données déjà vues"
    if mois < "2025-11":
        return "Validation : données non utilisées par fit"
    return "Test : données non utilisées par fit"


def matrices_correlation(df, dossier):
    """Une matrice de Pearson par région et par mois, calculée sur le réel."""
    dossier = Path(dossier)
    tableau = preparer_graphiques(df)
    index = []
    for (region, mois), groupe in tableau.groupby(
        ["libelle_region", "mois_graphique"], sort=True
    ):
        destination = dossier / nom_fichier(region)
        destination.mkdir(parents=True, exist_ok=True)
        colonnes = [c for c in LIBELLES if c in groupe.columns]
        donnees = groupe[colonnes].apply(pd.to_numeric, errors="coerce")
        donnees = donnees.replace([np.inf, -np.inf], np.nan)
        # Une constante (par exemple aucun jour férié) n'a pas de corrélation définie.
        constantes = [c for c in colonnes if donnees[c].nunique() < 2]
        variables = [c for c in colonnes if c not in constantes]
        fig, ax = plt.subplots(figsize=(11, 9), layout="constrained")
        if len(variables) >= 2:
            correlation = donnees[variables].corr(method="pearson", min_periods=3)
            correlation.to_csv(destination / f"correlation_{mois}.csv", encoding="utf-8-sig")
            cmap = plt.get_cmap("RdBu_r").copy()
            cmap.set_bad("#eeeeee")
            im = ax.imshow(np.ma.masked_invalid(correlation.to_numpy()),
                           cmap=cmap, vmin=-1, vmax=1)
            labels = [LIBELLES[c] for c in variables]
            ax.set_xticks(range(len(labels)), labels, rotation=40, ha="right")
            ax.set_yticks(range(len(labels)), labels)
            for i in range(len(labels)):
                for j in range(len(labels)):
                    valeur = correlation.iloc[i, j]
                    texte = "ND" if pd.isna(valeur) else f"{valeur:.2f}"
                    ax.text(j, i, texte, ha="center", va="center", fontsize=9,
                            color="white" if pd.notna(valeur) and abs(valeur) > .65 else "black")
            fig.colorbar(im, ax=ax, label="Corrélation de Pearson (−1 à +1)", shrink=.8)
        else:
            ax.text(.5, .5, "Pas assez de variables non constantes", ha="center")
            ax.set_axis_off()
        ax.set_title(f"Corrélations des observations — {region}\n{mois} | {len(groupe):,} lignes", pad=16)
        details = ", ".join(LIBELLES[c] for c in constantes) or "aucune"
        fig.supxlabel("Variables constantes exclues : " + details +
                      "\nAnalyse descriptive ; corrélation ≠ causalité.", fontsize=9)
        fichier = destination / f"correlation_{mois}.png"
        fig.savefig(fichier, dpi=140)
        plt.close(fig)
        index.append({"region": region, "mois": mois, "lignes": len(groupe),
                      "constantes_exclues": ",".join(constantes), "fichier": str(fichier)})
    pd.DataFrame(index).to_csv(dossier / "index_matrices.csv", index=False, encoding="utf-8-sig")
    print(f"Matrices enregistrées : {len(index)} dans {dossier}")


def courbes_reel_predit(df, predictions, dossier):

    dossier = Path(dossier)
    tableau = preparer_graphiques(df)
    predictions = np.asarray(predictions).reshape(-1)
    if len(predictions) != len(tableau):
        raise ValueError("Une prédiction par ligne du tableau est nécessaire.")
    tableau["consommation_predite"] = predictions
    tableau["consommation"] = pd.to_numeric(tableau["consommation"], errors="coerce")
    if not np.isfinite(tableau[["consommation", "consommation_predite"]].to_numpy(dtype=float)).all():
        raise ValueError("Les consommations et prédictions doivent être finies.")
    rapports = []
    for (region, mois), groupe in tableau.groupby(
        ["libelle_region", "mois_graphique"], sort=True
    ):
        groupe = groupe.sort_values("date_heure")
        destination = dossier / nom_fichier(region)
        destination.mkdir(parents=True, exist_ok=True)
        erreur = groupe["consommation_predite"] - groupe["consommation"]
        mae = float(erreur.abs().mean())
        biais = float(erreur.mean())
        fig, axes = plt.subplots(2, 1, figsize=(15, 8), layout="constrained")
        dates = groupe["date_heure"].dt.tz_convert("Europe/Paris")
        axes[0].plot(dates, groupe["consommation"], color="#175a96", lw=.9, label="Réelle")
        axes[0].plot(dates, groupe["consommation_predite"], color="#d36c16", lw=.9,
                     alpha=.9, linestyle="--", label="Prédite")
        axes[0].set_title("Valeurs aux horaires réellement disponibles — aucune interpolation du réel")
        jours = groupe.groupby("jour_graphique")[["consommation", "consommation_predite"]].mean()
        axes[1].plot(jours.index, jours["consommation"], color="#175a96", marker=".", label="Réelle")
        axes[1].plot(jours.index, jours["consommation_predite"], color="#d36c16",
                     marker=".", linestyle="--", label="Prédite")
        axes[1].set_title("Moyennes journalières — facilite la lecture du mois")
        for i, ax in enumerate(axes):
            tz = ZoneInfo("Europe/Paris") if i == 0 else None
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=4, tz=tz))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m", tz=tz))
            ax.set_xlabel("Date locale")
            ax.set_ylabel("Consommation (unité du CSV)")
            ax.grid(alpha=.2)
            ax.legend(loc="upper right")
        fig.suptitle(f"{region} — {mois}\n{partition(mois)}\n"
                     f"MAE aux horaires observés : {mae:.2f} | Biais : {biais:.2f}", fontsize=13)
        fichier = destination / f"reel_predit_{mois}.png"
        fig.savefig(fichier, dpi=140)
        plt.close(fig)
        groupe[["date_heure", "libelle_region", "consommation", "consommation_predite"]].to_csv(
            destination / f"reel_predit_{mois}.csv", index=False, encoding="utf-8-sig")
        rapports.append({"region": region, "mois": mois, "partition": partition(mois),
                         "observations": len(groupe), "mae": mae, "biais": biais,
                         "fichier": str(fichier)})
    pd.DataFrame(rapports).to_csv(dossier / "metrics_par_region_mois.csv", index=False, encoding="utf-8-sig")
    print(f"Courbes enregistrées : {len(rapports)} dans {dossier}")
