
  let map;
  let plantMarkers = {};
  let plantsById = {};
  let routeLayers = [];


  async function fetchJSON(url, options) {
    const response = await fetch(
      url,
      options
    );

    let body;

    try {
      body = await response.json();
    } catch (error) {
      throw new Error(
        "Le serveur n'a pas retourné un JSON valide"
      );
    }

    if (
      !response.ok ||
      body.success === false
    ) {
      let message = "Erreur inconnue";

      if (
        typeof body.error === "string"
      ) {
        message = body.error;

      } else if (
        typeof body.error?.message === "string"
      ) {
        message = body.error.message;

      } else if (
        typeof body.error?.detail === "string"
      ) {
        message = body.error.detail;

      } else if (
        typeof body.error?.error === "string"
      ) {
        message = body.error.error;

      } else if (
        typeof body.detail === "string"
      ) {
        message = body.detail;
      }

      throw new Error(
        message
      );
    }

    return body.response;
  }


  function initMap() {
    map = L.map(
      "map"
    ).setView(
      [46.6, 2.5],
      6
    );

    L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        attribution: (
          "&copy; OpenStreetMap contributors"
        ),
      }
    ).addTo(
      map
    );
  }


  function plantColor(plant) {
    if (
      !plant.simulation?.available
    ) {
      return "#9ca3af";
    }

    const ratio = (
      plant.simulation.initial_load_ratio ??
      0
    );

    if (ratio > 0.9) {
      return "#ef4444";
    }

    if (ratio > 0.75) {
      return "#f59e0b";
    }

    return "#22c55e";
  }


  async function loadPlants() {
    const plants = await fetchJSON(
      "/plants"
    );

    plants.forEach(
      (plant) => {
        plantsById[plant.id] = plant;

        const marker = L.circleMarker(
          [
            plant.location.latitude,
            plant.location.longitude,
          ],
          {
            radius: 7,
            color: "#0f172a",
            weight: 1,
            fillColor: plantColor(
              plant
            ),
            fillOpacity: 0.9,
          }
        ).addTo(
          map
        );

        marker.bindPopup(`
          <strong>${plant.name}</strong><br>
          puissance installée :
          ${plant.installed_power_mw} MW<br>

          production actuelle :
          ${plant.simulation.initial_output_mw} MW<br>

          marge disponible :
          ${plant.simulation.initial_dispatchable_margin_mw} MW<br>

          taux de charge :
          ${(
            plant.simulation.initial_load_ratio *
            100
          ).toFixed(1)} %
        `);

        plantMarkers[plant.id] = marker;
      }
    );
  }


  async function loadRegions() {
    const regions = await fetchJSON(
      "/regions"
    );

    const select = document.getElementById(
      "region-select"
    );

    regions
      .slice()
      .sort(
        (firstRegion, secondRegion) => (
          firstRegion.name.localeCompare(
            secondRegion.name
          )
        )
      )
      .forEach(
        (region) => {
          const option = document.createElement(
            "option"
          );

          option.value = region.id;
          option.textContent = region.name;

          select.appendChild(
            option
          );
        }
      );
  }


  function clearRoutes() {
    routeLayers.forEach(
      (layer) => {
        map.removeLayer(
          layer
        );
      }
    );

    routeLayers = [];

    Object
      .values(plantMarkers)
      .forEach(
        (marker) => {
          marker.setStyle({
            radius: 7,
            weight: 1,
          });
        }
      );
  }


  function drawAllocation(allocation) {
    const coordinates = allocation.path
      .map(
        (plantId) => (
          plantsById[plantId]
        )
      )
      .filter(
        Boolean
      )
      .map(
        (plant) => [
          plant.location.latitude,
          plant.location.longitude,
        ]
      );

    if (
      coordinates.length > 1
    ) {
      const line = L.polyline(
        coordinates,
        {
          color: (
            allocation.distance_km === 0
              ? "#22c55e"
              : "#3b82f6"
          ),
          weight: Math.max(
            2,
            Math.min(
              8,
              allocation.allocated_mw / 50
            )
          ),
          opacity: 0.85,
        }
      ).addTo(
        map
      );

      routeLayers.push(
        line
      );
    }

    const marker = (
      plantMarkers[allocation.plant_id]
    );

    if (marker) {
      marker.setStyle({
        radius: 11,
        weight: 3,
      });
    }
  }


  function renderResults(
    result,
    demand
  ) {
    const panel = document.getElementById(
      "results"
    );

    const statusClass = (
      result.fully_satisfied
        ? "ok"
        : "warn"
    );

    const statusText = (
      result.fully_satisfied
        ? "Demande entièrement couverte"
        : (
          `${result.missing_mw.toFixed(1)} MW ` +
          `manquants sur ${demand} MW`
        )
    );

    const allocations = Array.isArray(
      result.allocations
    )
      ? result.allocations
      : [];

    const rows = allocations
      .map(
        (allocation) => `
          <tr>
            <td>
              ${
                plantsById[
                  allocation.plant_id
                ]?.name ??
                allocation.plant_id
              }
            </td>

            <td>
              ${allocation.allocated_mw.toFixed(1)} MW
            </td>

            <td>
              ${(
                allocation.final_load_ratio *
                100
              ).toFixed(1)} %
            </td>

            <td>
              ${allocation.distance_km.toFixed(0)} km
            </td>

            <td>
              ${allocation.loss_percent.toFixed(2)} %
            </td>
          </tr>
        `
      )
      .join("");

    panel.innerHTML = `
      <div class="status ${statusClass}">
        ${statusText}
      </div>

      <table>
        <thead>
          <tr>
            <th>centrale</th>
            <th>alloué</th>
            <th>taux final</th>
            <th>distance</th>
            <th>pertes</th>
          </tr>
        </thead>

        <tbody>
          ${
            rows ||
            `
              <tr>
                <td colspan="5">
                  aucune centrale disponible
                </td>
              </tr>
            `
          }
        </tbody>
      </table>
    `;
  }


  async function runSimulation(event) {
    event.preventDefault();

    const region = document
      .getElementById("region-select")
      .value;

    const demand = parseFloat(
      document
        .getElementById("demand-input")
        .value
    );

    const errorBox = document.getElementById(
      "error-box"
    );

    errorBox.textContent = "";

    if (
      !region ||
      !demand ||
      demand <= 0
    ) {
      errorBox.textContent = (
        "Choisissez une région et une demande valide"
      );

      return;
    }

    clearRoutes();

    try {
      const result = await fetchJSON(
        "/simulate",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            region,
            additional_demand_mw: demand,
          }),
        }
      );

      result.allocations.forEach(
        drawAllocation
      );

      renderResults(
        result,
        demand
      );

    } catch (error) {
      errorBox.textContent = (
        error.message
      );
    }
  }


  function formatNumber(value) {
    if (
      value === null ||
      value === undefined ||
      Number.isNaN(Number(value))
    ) {
      return "non disponible";
    }

    return new Intl.NumberFormat(
      "fr-FR",
      {
        maximumFractionDigits: 2,
      }
    ).format(
      Number(value)
    );
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

    return "non disponible";
  }


  function escapeHTML(value) {
    const element = document.createElement(
      "div"
    );

    element.textContent = String(
      value ?? ""
    );

    return element.innerHTML;
  }


  function summaryItem(
    label,
    value,
    cssClass = ""
  ) {
    return `
      <div class="assistant-summary-item">
        <span class="assistant-summary-label">
          ${escapeHTML(label)}
        </span>

        <span class="assistant-summary-value ${cssClass}">
          ${escapeHTML(value)}
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
          data.region_id ||
          "non disponible"
        )}

        ${summaryItem(
          "heure",
          data.timestamp ||
          "non disponible"
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
        résumé de la simulation phase 3
      </div>

      <div class="assistant-summary-grid">
        ${summaryItem(
          "phase",
          data.phase ??
          "non disponible"
        )}

        ${summaryItem(
          "scénario",
          scenarioId
        )}

        ${summaryItem(
          "nombre de pas",
          data.steps_count ??
          "non disponible"
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
      (plant) => (
        plant.available === true
      )
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
        résumé des centrales
      </div>

      <div class="assistant-summary-grid">
        ${summaryItem(
          "nombre de centrales",
          data.plants_count ??
          data.count ??
          plants.length
        )}

        ${summaryItem(
          "centrales disponibles",
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
          aucune donnée structurée disponible
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
        résultat energIA disponible
      </div>
    `;
  }


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
              ✓ ${escapeHTML(step)}
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


  async function askAssistant(event) {
    event.preventDefault();

    const questionInput = document.getElementById(
      "assistant-question"
    );

    const button = document.getElementById(
      "assistant-button"
    );

    const errorBox = document.getElementById(
      "assistant-error"
    );

    const processBox = document.getElementById(
      "assistant-process"
    );

    const dataBox = document.getElementById(
      "assistant-data"
    );

    const answerBox = document.getElementById(
      "assistant-answer"
    );

    const question = (
      questionInput.value.trim()
    );

    errorBox.textContent = "";

    processBox.hidden = false;
    processBox.textContent = (
      "traitement de la question en cours"
    );

    dataBox.hidden = true;
    answerBox.hidden = true;

    button.disabled = true;
    button.textContent = (
      "gemma 4 prépare la réponse"
    );

    try {
      const result = await fetchJSON(
        "/assistant",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question,
          }),
        }
      );

      renderAssistantResult(
        result
      );

    } catch (error) {
      processBox.hidden = true;
      errorBox.textContent = (
        error.message
      );

    } finally {
      button.disabled = false;
      button.textContent = (
        "envoyer la question"
      );
    }
  }


  window.addEventListener(
    "DOMContentLoaded",
    async () => {
      const errorBox = document.getElementById(
        "error-box"
      );

      try {
        initMap();

        await Promise.all([
          loadPlants(),
          loadRegions(),
        ]);

      } catch (error) {
        errorBox.textContent = (
          `initialisation impossible : ${error.message}`
        );
      }

      const simulationForm = document.getElementById(
        "sim-form"
      );

      if (simulationForm) {
        simulationForm.addEventListener(
          "submit",
          runSimulation
        );
      }

      const assistantForm = document.getElementById(
        "assistant-form"
      );

      if (assistantForm) {
        assistantForm.addEventListener(
          "submit",
          askAssistant
        );
      }
    }
  );