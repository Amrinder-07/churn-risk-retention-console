const customerId = new URLSearchParams(window.location.search).get("id");
let currentCustomer = null;

const elements = {
  loading: document.querySelector("#detail-loading"),
  content: document.querySelector("#detail-content"),
  error: document.querySelector("#detail-error"),
  customerId: document.querySelector("#customer-id"),
  riskScore: document.querySelector("#risk-score"),
  riskTier: document.querySelector("#risk-tier"),
  modelNote: document.querySelector("#model-note"),
  factors: document.querySelector("#risk-factors"),
  details: document.querySelector("#customer-details"),
  outreachStatus: document.querySelector("#current-outreach-status"),
  outreachHint: document.querySelector("#outreach-hint"),
  outreachAction: document.querySelector("#outreach-action"),
  outreachError: document.querySelector("#outreach-error"),
};

function riskClass(tier) {
  return `risk-${String(tier).toLowerCase()}`;
}

function prettyLabel(value) {
  return String(value).replaceAll("_", " ");
}

function showPageError(message) {
  elements.loading.hidden = true;
  elements.content.hidden = true;
  elements.error.hidden = false;
  elements.error.textContent = message;
}

function renderFactors(factors) {
  elements.factors.replaceChildren();

  if (!factors.length) {
    const message = document.createElement("p");
    message.className = "muted";
    message.textContent = "No configured risk factors were triggered for this customer.";
    elements.factors.appendChild(message);
    return;
  }

  for (const factor of factors) {
    const item = document.createElement("div");
    item.className = "factor-item";

    const text = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = factor.label;
    const reason = document.createElement("p");
    reason.textContent = factor.reason;
    text.append(title, reason);

    const points = document.createElement("span");
    points.className = "factor-points";
    points.textContent = `+${factor.points}`;

    item.append(text, points);
    elements.factors.appendChild(item);
  }
}

const detailFields = [
  ["gender", "Gender"],
  ["SeniorCitizen", "Senior citizen"],
  ["Partner", "Partner"],
  ["Dependents", "Dependents"],
  ["tenure", "Tenure (months)"],
  ["PhoneService", "Phone service"],
  ["MultipleLines", "Multiple lines"],
  ["InternetService", "Internet service"],
  ["OnlineSecurity", "Online security"],
  ["OnlineBackup", "Online backup"],
  ["DeviceProtection", "Device protection"],
  ["TechSupport", "Tech support"],
  ["StreamingTV", "Streaming TV"],
  ["StreamingMovies", "Streaming movies"],
  ["Contract", "Contract"],
  ["PaperlessBilling", "Paperless billing"],
  ["PaymentMethod", "Payment method"],
  ["MonthlyCharges", "Monthly charges"],
  ["TotalCharges", "Total charges"],
  ["Churn", "Historical churn label"],
];

function formatField(key, value) {
  if (value === null || value === undefined || value === "") return "—";
  if (key === "MonthlyCharges" || key === "TotalCharges") return `$${Number(value).toFixed(2)}`;
  if (key === "SeniorCitizen") return Number(value) === 1 ? "Yes" : "No";
  return String(value);
}

function renderDetails(customer) {
  elements.details.replaceChildren();
  for (const [key, label] of detailFields) {
    const item = document.createElement("div");
    item.className = "detail-item";

    const term = document.createElement("span");
    term.className = "detail-label";
    term.textContent = label;

    const value = document.createElement("strong");
    value.textContent = formatField(key, customer[key]);

    item.append(term, value);
    elements.details.appendChild(item);
  }
}

function renderOutreach(customer) {
  elements.outreachError.hidden = true;
  elements.outreachStatus.textContent = prettyLabel(customer.outreach_status);
  elements.outreachStatus.className = `status-pill status-${customer.outreach_status.toLowerCase()}`;

  const [nextStatus] = customer.allowed_outreach_transitions || [];
  if (!nextStatus) {
    elements.outreachHint.textContent = "This outreach workflow is complete.";
    elements.outreachAction.hidden = true;
    return;
  }

  elements.outreachAction.hidden = false;
  elements.outreachAction.dataset.nextStatus = nextStatus;
  elements.outreachAction.textContent =
    nextStatus === "IN_PROGRESS" ? "Start Outreach" : "Mark Resolved";
  elements.outreachHint.textContent =
    nextStatus === "IN_PROGRESS"
      ? "Begin working this customer and record the outreach as in progress."
      : "Mark the case resolved once the retention action is complete.";
}

function renderCustomer(customer, model) {
  currentCustomer = customer;
  elements.customerId.textContent = customer.customerID;
  elements.riskScore.textContent = customer.risk_score;
  elements.riskTier.textContent = `${customer.risk_tier} RISK`;
  elements.riskTier.className = `risk-badge large ${riskClass(customer.risk_tier)}`;
  elements.modelNote.textContent = model.note;
  renderFactors(customer.risk_factors);
  renderDetails(customer);
  renderOutreach(customer);

  elements.loading.hidden = true;
  elements.error.hidden = true;
  elements.content.hidden = false;
}

async function loadCustomer() {
  if (!customerId) {
    showPageError("No customer id was provided. Return to the dashboard and select a customer.");
    return;
  }

  try {
    // Independent reads are requested in parallel to reduce detail-page wait time.
    const [customer, model] = await Promise.all([
      apiRequest(`/customers/${encodeURIComponent(customerId)}`),
      apiRequest("/model/info"),
    ]);
    renderCustomer(customer, model);
  } catch (error) {
    showPageError(`${error.message} Make sure the backend is running.`);
  }
}

elements.outreachAction.addEventListener("click", async () => {
  const nextStatus = elements.outreachAction.dataset.nextStatus;
  if (!nextStatus || !currentCustomer) return;

  elements.outreachError.hidden = true;
  elements.outreachAction.disabled = true;
  const originalText = elements.outreachAction.textContent;
  elements.outreachAction.textContent = "Saving...";

  try {
    currentCustomer = await apiRequest(
      `/customers/${encodeURIComponent(currentCustomer.customerID)}/outreach`,
      {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      }
    );
    renderOutreach(currentCustomer);
  } catch (error) {
    elements.outreachError.textContent = error.message;
    elements.outreachError.hidden = false;
    elements.outreachAction.textContent = originalText;
  } finally {
    elements.outreachAction.disabled = false;
  }
});

loadCustomer();
