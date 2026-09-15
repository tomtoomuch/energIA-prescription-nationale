const regionSelect = document.getElementById("region");
const moisSelect = document.getElementById("mois");
const message = document.getElementById("message");
const resultats = document.getElementById("resultats");
const nomsMois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
let regions = [];

function option(select, valeur, texte) {
  const element = document.createElement("option");
  element.value = valeur;
  element.textContent = texte;
  select.append(element);
}

function afficher() {
  const region = regions.find((item) => item.id === regionSelect.value);
  const mois = moisSelect.value;
  resultats.hidden = !region || !mois;
  if (!region || !mois) return;

  const libelle = `${nomsMois[Number(mois.slice(-2)) - 1]} 2025, ${region.nom}`;
  message.textContent = `Résultats pour ${libelle}.`;
  const images = [
    ["comparaison", "reel_predit", "reel_predit"],
    ["correlation", "correlations", "correlation"],
  ];
  for (const [id, dossier, prefixe] of images) {
    const image = document.getElementById(id);
    image.src = `/graphiques/${dossier}/${region.id}/${prefixe}_${mois}.png`;
    image.alt = `${id === "comparaison" ? "Consommation réelle et prédite" : "Matrice de corrélation"} pour ${libelle}`;
    image.hidden = false;
    image.onerror = () => { image.hidden = true; message.textContent = `Un graphique manque pour ${libelle}.`; };
  }
}

regionSelect.addEventListener("change", () => {
  const region = regions.find((item) => item.id === regionSelect.value);
  moisSelect.replaceChildren();
  option(moisSelect, "", "Choisir un mois…");
  for (const mois of region?.mois || []) option(moisSelect, mois, nomsMois[Number(mois.slice(-2)) - 1]);
  moisSelect.disabled = !region;
  moisSelect.value = "";
  resultats.hidden = true;
  message.textContent = "";
});
moisSelect.addEventListener("change", afficher);

fetch("/api/graphiques")
  .then((response) => { if (!response.ok) throw new Error("Service indisponible"); return response.json(); })
  .then((data) => {
    regions = data.regions;
    regionSelect.replaceChildren();
    option(regionSelect, "", "Choisir une région…");
    for (const region of regions) option(regionSelect, region.id, region.nom);
    moisSelect.disabled = true;
    if (!regions.length) message.textContent = "Aucun graphique disponible. Vérifiez le dossier prediction/graphiques.";
  })
  .catch(() => { regionSelect.replaceChildren(); option(regionSelect, "", "Régions indisponibles"); message.textContent = "Impossible de charger la liste des graphiques."; });
