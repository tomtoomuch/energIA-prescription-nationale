// input_checks.js


// Ces fonctions interviennent dans la vérification des saisies dans les champs utilisateuers du 
function formatNumber(value) {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(Number(value))
  ) {
    return "Non disponible";
  }

  return new Intl.NumberFormat(
    "fr-FR",
    {
      maximumFractionDigits: 2,
    }
  ).format(Number(value));
}


function formatBoolean(
  value,
  trueText = "oui",
  falseText = "non"
) {
  if (value === true) {
    return trueText;
  }

  if (value === false) {
    return falseText;
  }

  return "Non disponible";
}


function summaryItem(
  label,
  value,
  cssClass = ""
) {
  return `
    <div class="assistant-summary-item">
      <span class="assistant-summary-label">
        ${label}
      </span>

      <span class="assistant-summary-value ${cssClass}">
        ${value}
      </span>
    </div>
  `;
}


function renderConsumptionData(data) {
  return `
    <div class="assistant-summary-title">
      consommation de référence
    </div>

    <div class="assistant-summary-grid">
      ${summaryItem(
        "région",
        data.region_id || "non disponible"
      )}

      ${summaryItem(
        "heure",
        data.timestamp || "non disponible"
      )}

      ${summaryItem(
        "consommation",
        `${formatNumber(
          data.consumption_mw
        )} MW`
      )}
    </div>
  `;
}


function renderSimulationData(data) {
  const scenarioId = (
    data.scenario?.scenario_id ||
    data.scenario?.id ||
    "non disponible"
  );

  const constraintsClass = (
    data.all_constraints_respected
      ? "assistant-status-ok"
      : "assistant-status-warn"
  );

  const demandClass = (
    data.all_demand_satisfied
      ? "assistant-status-ok"
      : "assistant-status-warn"
  );

  const reserveClass = (
    data.reserve_always_sufficient
      ? "assistant-status-ok"
      : "assistant-status-warn"
  );

  return `
    <div class="assistant-summary-title">
      Résumé de la simulation phase 3
    </div>

    <div class="assistant-summary-grid">
      ${summaryItem(
        "phase",
        data.phase ?? "Non disponible"
      )}

      ${summaryItem(
        "scénario",
        scenarioId
      )}

      ${summaryItem(
        "nombre de pas",
        data.steps_count ?? "Non disponible"
      )}

      ${summaryItem(
        "durée d’un pas",
        `${formatNumber(
          data.step_minutes
        )} minutes`
      )}

      ${summaryItem(
        "consommation totale",
        `${formatNumber(
          data.total_consumption_mw
        )} MW`
      )}

      ${summaryItem(
        "production solaire",
        `${formatNumber(
          data.total_solar_production_mw
        )} MW`
      )}

      ${summaryItem(
        "production éolienne",
        `${formatNumber(
          data.total_wind_production_mw
        )} MW`
      )}

      ${summaryItem(
        "production non pilotable",
        `${formatNumber(
          data.total_non_dispatchable_production_mw
        )} MW`
      )}

      ${summaryItem(
        "demande résiduelle",
        `${formatNumber(
          data.total_residual_demand_mw
        )} MW`
      )}

      ${summaryItem(
        "puissance manquante",
        `${formatNumber(
          data.total_missing_mw
        )} MW`,
        demandClass
      )}

      ${summaryItem(
        "contraintes respectées",
        formatBoolean(
          data.all_constraints_respected
        ),
        constraintsClass
      )}

      ${summaryItem(
        "réserve toujours suffisante",
        formatBoolean(
          data.reserve_always_sufficient
        ),
        reserveClass
      )}

      ${summaryItem(
        "nombre d’événements",
        data.events_count ?? 0
      )}

      ${summaryItem(
        "variation totale des événements",
        `${formatNumber(
          data.total_event_delta_mw
        )} MW`
      )}
    </div>
  `;
}


function renderPlantsData(data) {
  const plants = Array.isArray(
    data.plants
  )
    ? data.plants
    : [];

  const availablePlants = plants.filter(
    (plant) => plant.available === true
  );

  const maximumPower = availablePlants.reduce(
    (total, plant) => (
      total +
      Number(
        plant.maximum_power_mw || 0
      )
    ),
    0
  );

  return `
    <div class="assistant-summary-title">
      Résumé des centrales
    </div>

    <div class="assistant-summary-grid">
      ${summaryItem(
        "Nombre de centrales",
        data.plants_count ??
        data.count ??
        plants.length
      )}

      ${summaryItem(
        "Centrales disponibles",
        availablePlants.length,
        "assistant-status-ok"
      )}

      ${summaryItem(
        "puissance maximale disponible",
        `${formatNumber(
          maximumPower
        )} MW`
      )}
    </div>
  `;
}

// Cette fonction 
function renderAssistantData(
  data,
  toolName
) {
  if (
    Array.isArray(data) &&
    data.length === 1
  ) {
    data = data[0];
  }

  if (
    !data ||
    typeof data !== "object"
  ) {
    return `
      <div class="assistant-summary-title">
        Aucune donnée structurée disponible
      </div>
    `;
  }

  if (
    toolName === "get_consumption" ||
    data.consumption_mw !== undefined
  ) {
    return renderConsumptionData(
      data
    );
  }

  if (
    toolName === "simulate_phase3" ||
    data.phase === 3
  ) {
    return renderSimulationData(
      data
    );
  }

  if (
    toolName === "list_plants" ||
    Array.isArray(data.plants)
  ) {
    return renderPlantsData(
      data
    );
  }

  return `
    <div class="assistant-summary-title">
      Résultat energIA disponible
    </div>
  `;
}

// Cette fonction intervient dans la  manipulation du DOM afin d'afficher
// les résultats de l'assistant energIA dans la page web.
function renderAssistantResult(result) {
  const processBox = document.getElementById(
    "assistant-process"
  );

  const dataBox = document.getElementById(
    "assistant-data"
  );

  const answerBox = document.getElementById(
    "assistant-answer"
  );

  const steps = Array.isArray(
    result.steps
  )
    ? result.steps
    : [];

  const toolsUsed = Array.isArray(
    result.tools_used
  )
    ? result.tools_used
    : [];

  const toolName = (
    toolsUsed[0]?.name ||
    ""
  );

  processBox.innerHTML = `
    <strong>processus</strong>

    ${steps
      .map(
        (step) => `
          <div class="assistant-step">
            ✓ ${step}
          </div>
        `
      )
      .join("")}
  `;

  dataBox.innerHTML = renderAssistantData(
    result.data,
    toolName
  );

  answerBox.innerHTML = "";

  const answerTitle = document.createElement(
    "strong"
  );

  answerTitle.textContent = (
    "réponse gemma 4"
  );

  const answerText = document.createElement(
    "div"
  );

  answerText.textContent = (
    result.answer ||
    "aucune réponse disponible"
  );

  answerBox.appendChild(
    answerTitle
  );

  answerBox.appendChild(
    answerText
  );

  processBox.hidden = false;
  dataBox.hidden = false;
  answerBox.hidden = false;
}