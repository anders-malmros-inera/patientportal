const API_BASE_URL = "http://127.0.0.1:8000/api";

const loginForm = document.getElementById("login-form");
const statusEl = document.getElementById("status");
const dashboardEl = document.getElementById("dashboard");
const prescriptionsEl = document.getElementById("prescriptions");
const scrapeUploadForm = document.getElementById("scrape-upload-form");
const scrapeFileInput = document.getElementById("scrape-file");
const manualMedicationForm = document.getElementById("manual-medication-form");
const manualMedicationInput = document.getElementById("manual-medication-name");
const manualMedicationSearchBtn = document.getElementById("manual-medication-search-btn");

let authToken = null;

const FASS_WINDOW_NAME = "fassAlternativ";
let fassWindowRef = null;

const TIME_GROUPS = [
  { key: "morgon", label: "Morgon" },
  { key: "dag", label: "Mitt på dagen" },
  { key: "kvall", label: "Kväll" },
  { key: "natt", label: "Natt" },
  { key: "okand", label: "Ej specificerad tid" },
];

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.color = isError ? "#b42318" : "#52606d";
}

function normalizeTimeGroup(value) {
  const token = String(value || "").trim().toLowerCase();
  if (token.includes("morgon")) {
    return "morgon";
  }
  if (token.includes("middag") || token.includes("dag") || token.includes("lunch") || token.includes("eftermiddag")) {
    return "dag";
  }
  if (token.includes("kvall")) {
    return "kvall";
  }
  if (token.includes("natt")) {
    return "natt";
  }
  return "okand";
}

function getPrimaryGroup(item) {
  if (!Array.isArray(item.administration_times) || item.administration_times.length === 0) {
    return "okand";
  }

  const seenGroups = new Set(item.administration_times.map(normalizeTimeGroup));
  const firstKnownGroup = TIME_GROUPS.find((group) => group.key !== "okand" && seenGroups.has(group.key));
  return firstKnownGroup ? firstKnownGroup.key : "okand";
}

function normalizeMedicationToken(value) {
  return String(value || "").trim();
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function normalizeMedicationForComparison(value) {
  return normalizeMedicationToken(value)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizePrescribedName(prescribedName, activeSubstance) {
  const cleanedPrescribed = normalizeMedicationToken(prescribedName).replace(/\s+/g, " ");
  const cleanedSubstance = normalizeMedicationToken(activeSubstance).replace(/\s+/g, " ");

  if (!cleanedSubstance || !cleanedPrescribed) {
    return cleanedPrescribed;
  }

  const duplicatePrefixPattern = new RegExp(
    `^(${escapeRegex(cleanedSubstance)})\\s+(${escapeRegex(cleanedSubstance)}\\b.*)$`,
    "i",
  );
  const duplicateMatch = cleanedPrescribed.match(duplicatePrefixPattern);
  if (duplicateMatch) {
    return duplicateMatch[2].trim();
  }

  return cleanedPrescribed;
}

function buildMedicationDisplay(item) {
  const prescribedName = normalizeMedicationToken(item.medication_name || item.prescribed_product) || "Okänt läkemedel";
  const activeSubstance = normalizeMedicationToken(item.active_substance);
  const normalizedPrescribedName = normalizePrescribedName(prescribedName, activeSubstance);

  if (!activeSubstance) {
    return normalizedPrescribedName;
  }

  const sameName = normalizeMedicationForComparison(normalizedPrescribedName)
    === normalizeMedicationForComparison(activeSubstance);
  return sameName ? normalizedPrescribedName : `${normalizedPrescribedName} (${activeSubstance})`;
}

function extractSearchTerm(medicationName) {
  if (!medicationName) return medicationName;
  return medicationName.trim().split(/\s+/).slice(0, 2).join(" ");
}

function buildAdviceMap(entries) {
  if (!Array.isArray(entries)) {
    return new Map();
  }
  return new Map(entries.map((entry) => [entry.prescription_id, entry]));
}

function renderRenewalInline(entry) {
  if (!entry) {
    return '<div class="rx-meta">Förnyelseråd: Ej tillgängligt</div>';
  }

  const daysRemaining = entry.estimated_days_left;
  const colorClass = getRenewalColorClass(daysRemaining);
  const reasonLine = entry.reason && entry.reason !== "Ingen åtgärd behövs ännu"
    ? `<div class="rx-meta">Orsak: ${entry.reason}</div>`
    : "";
  const issuedByLine = entry.renewal_needed && entry.issued_by
    ? `<div class="rx-meta">Utfärdat av: ${entry.issued_by}</div>`
    : "";

  return `
    <section class="renewal-inline">
      <h4>Receptförnyelse</h4>
      <div class="badge ${colorClass}">Dagar kvar: ${daysRemaining}</div>
      <div class="rx-meta">Dagar kvar av läkemedel: ${entry.estimated_days_left}</div>
      <div class="rx-meta">Dagar kvar av receptets giltighet: ${entry.days_until_validity_ends}</div>
      ${reasonLine}
      ${issuedByLine}
    </section>
  `;
}

function renderPrescriptions(prescriptions, adviceEntries = []) {
  const adviceByPrescriptionId = buildAdviceMap(adviceEntries);
  const grouped = {
    morgon: [],
    dag: [],
    kvall: [],
    natt: [],
    okand: [],
  };

  prescriptions.forEach((item) => {
    grouped[getPrimaryGroup(item)].push(item);
  });

  const sections = TIME_GROUPS
    .filter((group) => grouped[group.key].length > 0)
    .map((group) => {
      const cards = grouped[group.key]
        .map((item) => {
          const ordinationDose = item.dose_per_intake && item.dose_unit
            ? `${item.dose_per_intake} ${item.dose_unit}`
            : "Ej tillgänglig";
          const ordinationTimes = Array.isArray(item.administration_times) && item.administration_times.length > 0
            ? item.administration_times.join(", ")
            : "Ej tillgänglig";
          const ordinationText = item.instruction_text || "Ej tillgänglig";
          const prescriptionStatus = item.has_active_prescription
            ? "Aktivt recept"
            : "Saknar aktivt recept";
          const statusClass = item.has_active_prescription ? "status-active" : "status-missing";
          const prescribedName = normalizePrescribedName(
            item.prescribed_product || item.medication_name,
            item.active_substance,
          );
          const displayName = buildMedicationDisplay(item);
          const fassSearchTerm = extractSearchTerm(prescribedName || displayName);
          const alternativesUrl = `https://fass.se/search?query=${encodeURIComponent(fassSearchTerm)}&index=human-product-index`;
          const renewalEntry = adviceByPrescriptionId.get(item.id);
          const renewalMarkup = renderRenewalInline(renewalEntry);
          const titleColorClass = getTitleColorClass(renewalEntry);
          const titleColorAttr = titleColorClass ? ` ${titleColorClass}` : "";

          return `
            <article class="card card-prescription" data-prescription-id="${item.id}" data-expanded="false">
              <div class="card-header card-header-clickable${titleColorAttr}" role="button" tabindex="0" aria-expanded="false">
                <h3>${displayName}</h3>
                <div class="card-header-actions">
                  <span class="expand-indicator">▶</span>
                  <button
                    type="button"
                    class="remove-prescription-btn${titleColorAttr}"
                    data-prescription-id="${item.id}"
                    aria-label="Ta bort ${displayName}"
                    title="Ta bort recept"
                  >
                    ×
                  </button>
                </div>
              </div>
              <div class="card-content-collapsible">
              <div class="rx-meta">Dos/dag: ${item.prescribed_daily_dose}</div>
              <div class="rx-meta">Förpackningsstorlek: ${item.package_size}</div>
              <div class="rx-meta">Kvarvarande förpackningar: ${item.remaining_packages}</div>
              <div class="rx-meta">Giltigt till: ${item.valid_until}</div>
              <div class="rx-meta ${statusClass}">Receptstatus: ${prescriptionStatus}</div>
              <div class="rx-meta">
                <button
                  type="button"
                  class="fass-link-btn"
                  data-fass-url="${alternativesUrl}"
                  aria-label="Visa läkemedelsalternativ för ${displayName}"
                >Läkemedelsalternativ</button>
              </div>

              <section class="ordination">
                <h4>Ordination</h4>
                <div class="ordination-row"><span class="label">Dos:</span> <span>${ordinationDose}</span></div>
                <div class="ordination-row"><span class="label">När på dygnet:</span> <span>${ordinationTimes}</span></div>
                <div class="ordination-row"><span class="label">Instruktion:</span> <span>${ordinationText}</span></div>
              </section>

              ${renewalMarkup}
              </div>
            </article>
          `;
        })
        .join("");

      return `
        <section class="time-group">
          <h3 class="time-group-title">${group.label}</h3>
          ${cards}
        </section>
      `;
    })
    .join("");

  prescriptionsEl.innerHTML = sections || '<div class="card">Inga recept hittades.</div>';
}

function getRenewalColorClass(daysRemaining) {
  if (daysRemaining > 60) {
    return "renewal-green";
  }
  if (daysRemaining >= 30) {
    return "renewal-yellow";
  }
  return "renewal-red";
}

function getTitleColorClass(entry) {
  if (!entry) {
    return "";
  }
  return getRenewalColorClass(entry.estimated_days_left);
}

function openFassWindow(url) {
  const windowFeatures = [
    "popup=yes",
    "width=1200",
    "height=900",
    "left=80",
    "top=40",
    "menubar=no",
    "toolbar=no",
    "location=yes",
    "status=no",
    "scrollbars=yes",
    "resizable=yes",
  ].join(",");

  fassWindowRef = window.open(url, FASS_WINDOW_NAME, windowFeatures);
  if (!fassWindowRef) {
    return false;
  }

  fassWindowRef.focus();
  return true;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const fallback = "Något gick fel";
    try {
      const payload = await response.json();
      throw new Error(payload.detail || fallback);
    } catch {
      throw new Error(fallback);
    }
  }
  return response.json();
}

async function refreshDashboard() {
  if (!authToken) {
    throw new Error("Du måste vara inloggad först");
  }

  const authHeader = { Authorization: `Bearer ${authToken}` };
  const [prescriptions, renewalAdvice] = await Promise.all([
    fetchJson(`${API_BASE_URL}/prescriptions`, { headers: authHeader }),
    fetchJson(`${API_BASE_URL}/renewal-advice`, { headers: authHeader }),
  ]);

  renderPrescriptions(prescriptions, renewalAdvice.advice);
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Loggar in...");

  const personnummer = document.getElementById("personnummer").value.trim();
  if (!personnummer) {
    setStatus("Fyll i personnummer", true);
    return;
  }

  try {
    const login = await fetchJson(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ personnummer }),
    });

    authToken = login.access_token;
    await refreshDashboard();
    dashboardEl.classList.remove("hidden");
    setStatus("Inloggad. Data hämtad från tjänstens adapter.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

scrapeUploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!authToken) {
    setStatus("Logga in innan du laddar upp fil", true);
    return;
  }

  const file = scrapeFileInput.files && scrapeFileInput.files[0];
  if (!file) {
    setStatus("Välj en PDF-fil att ladda upp", true);
    return;
  }

  setStatus("Laddar upp och tolkar fil...");
  const formData = new FormData();
  formData.append("file", file);

  try {
    const result = await fetchJson(`${API_BASE_URL}/prescriptions/upload-scrape`, {
      method: "POST",
      headers: { Authorization: `Bearer ${authToken}` },
      body: formData,
    });

    await refreshDashboard();
    scrapeUploadForm.reset();
    setStatus(
      `Import klar: ${result.imported_prescriptions} recept inlästa, totalt ${result.total_prescriptions} i din lista.`
    );
  } catch (error) {
    setStatus(error.message, true);
  }
});

manualMedicationSearchBtn.addEventListener("click", () => {
  const searchTerm = manualMedicationInput.value.trim();
  if (!searchTerm) {
    setStatus("Skriv ett läkemedelsnamn eller sökord först", true);
    return;
  }

  const fassSearchTerm = extractSearchTerm(searchTerm);
  const searchUrl = `https://fass.se/search?query=${encodeURIComponent(fassSearchTerm)}`;
  if (!openFassWindow(searchUrl)) {
    setStatus("Popup blockerad. Tillåt popup-fönster för att visa FASS.", true);
    return;
  }

  setStatus(`FASS-sökning öppnad för "${fassSearchTerm}". Kopiera exakt läkemedelsnamn tillbaka och lägg till i listan.`);
});

manualMedicationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!authToken) {
    setStatus("Logga in innan du lägger till medicin", true);
    return;
  }

  const medicationName = manualMedicationInput.value.trim();
  if (!medicationName) {
    setStatus("Skriv läkemedelsnamn innan du lägger till", true);
    return;
  }

  setStatus("Lägger till medicin i listan...");
  try {
    await fetchJson(`${API_BASE_URL}/prescriptions/manual`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${authToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ medication_name: medicationName }),
    });

    await refreshDashboard();
    setStatus(`Medicinen ${medicationName} är tillagd i listan utan recept.`);
  } catch (error) {
    setStatus(error.message || "Kunde inte lägga till medicinen", true);
  }
});

function togglePrescriptionExpand(element) {
  const card = element.closest(".card-prescription");
  if (!card) return;

  const isExpanded = card.dataset.expanded === "true";
  card.dataset.expanded = isExpanded ? "false" : "true";
  const header = card.querySelector(".card-header-clickable");
  if (header) {
    header.setAttribute("aria-expanded", String(!isExpanded));
  }
}

prescriptionsEl.addEventListener("click", async (event) => {
  const rawTarget = event.target;
  const target = rawTarget instanceof Element
    ? rawTarget
    : rawTarget instanceof Node
      ? rawTarget.parentElement
      : null;

  if (!target) {
    return;
  }

  const button = target.closest(".remove-prescription-btn");
  if (button instanceof HTMLButtonElement) {
    event.stopPropagation();

    if (!authToken) {
      setStatus("Du måste vara inloggad först", true);
      return;
    }

    const prescriptionId = button.dataset.prescriptionId;
    if (!prescriptionId) {
      setStatus("Kunde inte identifiera receptet", true);
      return;
    }

    setStatus("Tar bort recept...");
    try {
      const response = await fetch(`${API_BASE_URL}/prescriptions/${encodeURIComponent(prescriptionId)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${authToken}` },
      });

      if (!response.ok) {
        throw new Error("Kunde inte ta bort receptet");
      }

      await refreshDashboard();
      setStatus("Receptet är borttaget från listan.");
    } catch (error) {
      setStatus(error.message || "Kunde inte ta bort receptet", true);
    }
    return;
  }

  const fassButton = target.closest(".fass-link-btn");
  if (fassButton instanceof HTMLButtonElement) {
    const fassUrl = fassButton.dataset.fassUrl;
    if (!fassUrl) {
      setStatus("Kunde inte öppna FASS-länken", true);
      return;
    }

    if (!openFassWindow(fassUrl)) {
      setStatus("Popup blockerad. Tillåt popup-fönster för att visa FASS.", true);
      return;
    }

    setStatus("Läkemedelsalternativ öppnat i separat fönster.");
    return;
  }

  const clickableHeader = target.closest(".card-header-clickable");
  if (clickableHeader) {
    togglePrescriptionExpand(clickableHeader);
  }
});
