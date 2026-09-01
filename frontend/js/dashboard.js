const state = {
  page: 1,
  pageSize: 20,
};

const elements = {
  tableBody: document.querySelector("#customer-table-body"),
  tableStatus: document.querySelector("#table-status"),
  errorBanner: document.querySelector("#error-banner"),
  riskTier: document.querySelector("#risk-tier"),
  contract: document.querySelector("#contract"),
  outreachStatus: document.querySelector("#outreach-status"),
  sort: document.querySelector("#sort"),
  search: document.querySelector("#search"),
  searchButton: document.querySelector("#search-button"),
  clearButton: document.querySelector("#clear-filters"),
  previousButton: document.querySelector("#previous-page"),
  nextButton: document.querySelector("#next-page"),
  pageLabel: document.querySelector("#page-label"),
  matchingCount: document.querySelector("#matching-count"),
  highRiskCount: document.querySelector("#high-risk-count"),
  notContactedCount: document.querySelector("#not-contacted-count"),
  inProgressCount: document.querySelector("#in-progress-count"),
};

function riskClass(tier) {
  return `risk-${String(tier).toLowerCase()}`;
}

function outreachLabel(status) {
  return String(status).replaceAll("_", " ");
}

function setError(message = "") {
  elements.errorBanner.textContent = message;
  elements.errorBanner.hidden = !message;
}

function setLoading(isLoading) {
  elements.tableStatus.hidden = !isLoading;
  elements.previousButton.disabled = isLoading;
  elements.nextButton.disabled = isLoading;
}

function currentQuery() {
  const params = new URLSearchParams({
    page: String(state.page),
    page_size: String(state.pageSize),
    sort: elements.sort.value,
  });

  if (elements.riskTier.value) params.set("risk_tier", elements.riskTier.value);
  if (elements.contract.value) params.set("contract", elements.contract.value);
  if (elements.outreachStatus.value) params.set("outreach_status", elements.outreachStatus.value);
  if (elements.search.value.trim()) params.set("search", elements.search.value.trim());

  return params.toString();
}

function addCell(row, text, className = "") {
  const cell = document.createElement("td");
  cell.textContent = text;
  if (className) cell.className = className;
  row.appendChild(cell);
  return cell;
}

function renderCustomers(items) {
  elements.tableBody.replaceChildren();

  if (!items.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.className = "empty-state";
    cell.textContent = "No customers match these filters.";
    row.appendChild(cell);
    elements.tableBody.appendChild(row);
    return;
  }

  for (const customer of items) {
    const row = document.createElement("tr");
    row.className = "customer-row";
    row.tabIndex = 0;
    row.setAttribute("role", "link");
    row.setAttribute("aria-label", `Open customer ${customer.customerID}`);

    addCell(row, customer.customerID, "customer-id");

    const riskCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `risk-badge ${riskClass(customer.risk_tier)}`;
    badge.textContent = customer.risk_tier;
    riskCell.appendChild(badge);
    row.appendChild(riskCell);

    addCell(row, String(customer.risk_score), "score-cell");
    addCell(row, `${customer.tenure} mo`);
    addCell(row, customer.Contract);
    addCell(row, `$${Number(customer.MonthlyCharges).toFixed(2)}`);
    addCell(row, outreachLabel(customer.outreach_status), "outreach-cell");

    const open = () => {
      window.location.href = `customer.html?id=${encodeURIComponent(customer.customerID)}`;
    };
    row.addEventListener("click", open);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") open();
    });

    elements.tableBody.appendChild(row);
  }
}

function renderSummary(summary) {
  elements.matchingCount.textContent = summary.matching_customers;
  elements.highRiskCount.textContent = summary.high_risk;
  elements.notContactedCount.textContent = summary.not_contacted;
  elements.inProgressCount.textContent = summary.in_progress;
}

function renderPagination(pagination) {
  const totalPages = pagination.total_pages;
  elements.pageLabel.textContent = totalPages
    ? `Page ${pagination.page} of ${totalPages}`
    : "No pages";

  elements.previousButton.disabled = pagination.page <= 1;
  elements.nextButton.disabled = !totalPages || pagination.page >= totalPages;
}

async function loadCustomers() {
  setError();
  setLoading(true);

  try {
    const data = await apiRequest(`/customers?${currentQuery()}`);
    renderCustomers(data.items);
    renderSummary(data.summary);
    renderPagination(data.pagination);
  } catch (error) {
    elements.tableBody.replaceChildren();
    setError(`${error.message} Make sure the backend is running on http://localhost:5000.`);
  } finally {
    setLoading(false);
  }
}

function resetToFirstPageAndLoad() {
  state.page = 1;
  loadCustomers();
}

for (const input of [elements.riskTier, elements.contract, elements.outreachStatus, elements.sort]) {
  input.addEventListener("change", resetToFirstPageAndLoad);
}

elements.searchButton.addEventListener("click", resetToFirstPageAndLoad);
elements.search.addEventListener("keydown", (event) => {
  if (event.key === "Enter") resetToFirstPageAndLoad();
});

elements.clearButton.addEventListener("click", () => {
  elements.riskTier.value = "";
  elements.contract.value = "";
  elements.outreachStatus.value = "";
  elements.sort.value = "risk_desc";
  elements.search.value = "";
  resetToFirstPageAndLoad();
});

elements.previousButton.addEventListener("click", () => {
  if (state.page > 1) {
    state.page -= 1;
    loadCustomers();
  }
});

elements.nextButton.addEventListener("click", () => {
  state.page += 1;
  loadCustomers();
});

loadCustomers();
