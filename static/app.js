"use strict";

const TEXT = {
  en: {
    navBudget: "Budget", navUsers: "Users", privateSpace: "YOUR PRIVATE SPACE", welcome: "A clearer view of your money.",
    signInPrompt: "Sign in to see your household budget.", email: "Email address", password: "Password", signIn: "Sign in",
    privateNote: "Your budget is private and only available to signed-in users.", overview: "YOUR FINANCES", budgetTitle: "Budget",
    budgetSubtitle: "Every expense, all in one place.", year: "Year", category: "Category", payer: "Paid by",
    allYears: "All years", allCategories: "All categories", allPayers: "Everyone", totalSpent: "Total spent",
    filteredTotal: "For the selected filters", transactions: "Transactions", matchingRecords: "Matching records",
    averageExpense: "Average expense", perTransaction: "Per transaction", spendingBreakdown: "SPENDING BREAKDOWN",
    byCategory: "By category", recentActivity: "RECENT ACTIVITY", monthlySpending: "Monthly spending",
    ledger: "THE LEDGER", search: "Search expenses", searchPlaceholder: "Search merchant or notes…", date: "Date",
    merchant: "Merchant", description: "Description", amount: "Amount", transferTo: "Transfer to", comments: "Comments",
    noExpenses: "No expenses match these filters.",
    pageOf: "Page {page} of {pages} · {count} expenses", accountAccess: "ACCOUNT ACCESS", usersTitle: "Users",
    usersSubtitle: "Only administrators can add or remove accounts.", newAccount: "NEW ACCOUNT", addUser: "Add a user",
    firstName: "First name", lastName: "Last name", passwordHint: "Use at least 12 characters.",
    createAccount: "Create account", accessList: "AUTHORIZED ACCOUNTS", administrator: "Administrator",
    user: "User", removeUser: "Remove account", noUsers: "No user accounts found.", footerNote: "A little more clarity, every day.",
    loginFailed: "We couldn't sign you in. Check your email and password.", failed: "Something went wrong. Please try again.",
    accountExists: "An account with that email already exists.", notAllowed: "You don't have permission to do that.",
    invalidInput: "Please check the information you entered.", cannotRemove: "This account cannot be removed.",
    emailOrPassword: "Email or password is incorrect.", passwordTooShort: "Password must be at least 12 characters.",
    confirmRemove: "Remove this account?", signOut: "Sign out", changeLanguage: "Change language",
    previousPage: "Previous page", nextPage: "Next page",
  },
  fr: {
    navBudget: "Budget", navUsers: "Utilisateurs", privateSpace: "VOTRE ESPACE PRIVÉ", welcome: "Voyez vos finances autrement.",
    signInPrompt: "Connectez-vous pour consulter le budget du foyer.", email: "Adresse courriel", password: "Mot de passe",
    signIn: "Connexion", privateNote: "Votre budget est privé et réservé aux utilisateurs connectés.",
    overview: "VOS FINANCES", budgetTitle: "Budget", budgetSubtitle: "Toutes vos dépenses, au même endroit.",
    year: "Année", category: "Catégorie", payer: "Payé par", allYears: "Toutes les années",
    allCategories: "Toutes les catégories", allPayers: "Tout le monde", totalSpent: "Total des dépenses",
    filteredTotal: "Selon les filtres", transactions: "Transactions", matchingRecords: "Résultats correspondants",
    averageExpense: "Dépense moyenne", perTransaction: "Par transaction", spendingBreakdown: "RÉPARTITION DES DÉPENSES",
    byCategory: "Par catégorie", recentActivity: "ACTIVITÉ RÉCENTE", monthlySpending: "Dépenses mensuelles",
    ledger: "LE GRAND LIVRE", search: "Rechercher des dépenses", searchPlaceholder: "Commerçant ou notes…", date: "Date",
    merchant: "Commerçant", description: "Description", amount: "Montant", transferTo: "À transférer à",
    comments: "Commentaires", noExpenses: "Aucune dépense ne correspond aux filtres.",
    pageOf: "Page {page} sur {pages} · {count} dépenses", accountAccess: "ACCÈS AU COMPTE", usersTitle: "Utilisateurs",
    usersSubtitle: "Seuls les administrateurs peuvent ajouter ou supprimer des comptes.", newAccount: "NOUVEAU COMPTE",
    addUser: "Ajouter un utilisateur", firstName: "Prénom", lastName: "Nom de famille",
    passwordHint: "Utilisez au moins 12 caractères.", createAccount: "Créer le compte", accessList: "COMPTES AUTORISÉS",
    administrator: "Administrateur", user: "Utilisateur", removeUser: "Supprimer le compte", noUsers: "Aucun compte utilisateur.",
    footerNote: "Un peu plus de clarté, chaque jour.",
    loginFailed: "Connexion impossible. Vérifiez votre adresse courriel et votre mot de passe.",
    failed: "Une erreur est survenue. Veuillez réessayer.", accountExists: "Un compte utilise déjà cette adresse courriel.",
    notAllowed: "Vous n’avez pas l’autorisation d’effectuer cette action.",
    invalidInput: "Veuillez vérifier les renseignements saisis.", cannotRemove: "Ce compte ne peut pas être supprimé.",
    emailOrPassword: "Adresse courriel ou mot de passe incorrect.",
    passwordTooShort: "Le mot de passe doit contenir au moins 12 caractères.", confirmRemove: "Supprimer ce compte ?",
    signOut: "Déconnexion", changeLanguage: "Changer de langue", previousPage: "Page précédente", nextPage: "Page suivante",
  },
};

const $ = (selector) => document.querySelector(selector);
let language = localStorage.getItem("budget-language") || "en";
let currentUser = null;
let currentPage = 1;
let expenseCount = 0;
let searchTimer;

function tr(key) { return TEXT[language][key] || key; }

function applyLanguage() {
  document.documentElement.lang = language;
  document.title = `Budget · ${tr("budgetTitle")}`;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = tr(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = tr(el.dataset.i18nPlaceholder); });
  $("#language-code").textContent = language === "en" ? "FR" : "EN";
  $("#language-button").setAttribute("aria-label", tr("changeLanguage"));
  $("#language-button").title = tr("changeLanguage");
  $("#logout-button").setAttribute("aria-label", tr("signOut"));
  $("#logout-button").title = tr("signOut");
  $("#previous-page").setAttribute("aria-label", tr("previousPage"));
  $("#previous-page").title = tr("previousPage");
  $("#next-page").setAttribute("aria-label", tr("nextPage"));
  $("#next-page").title = tr("nextPage");
  document.querySelectorAll(".icon-submit").forEach((button) => {
    const label = tr(button.type === "submit" && button.closest("#login-form") ? "signIn" : "createAccount");
    button.setAttribute("aria-label", label);
    button.title = label;
  });
  $("#current-year").textContent = new Date().getFullYear();
  renderPageStatus();
}

async function api(url, options = {}) {
  const headers = { Accept: "application/json", ...options.headers };
  if (options.body) headers["Content-Type"] = "application/json";
  const response = await fetch(url, { credentials: "same-origin", ...options, headers });
  if (!response.ok) {
    let detail = tr("failed");
    try { detail = (await response.json()).detail || detail; } catch { /* Response isn't JSON. */ }
    if (response.status === 400) detail = tr("cannotRemove");
    else if (response.status === 403) detail = tr("notAllowed");
    else if (response.status === 409) detail = tr("accountExists");
    else if (response.status === 422) detail = tr("invalidInput");
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

function money(value) {
  return new Intl.NumberFormat(language === "fr" ? "fr-CA" : "en-CA", { style: "currency", currency: "CAD" }).format(value);
}

function dateLabel(value) {
  return new Intl.DateTimeFormat(language === "fr" ? "fr-CA" : "en-CA", { dateStyle: "medium", timeZone: "UTC" })
    .format(new Date(`${value}T00:00:00Z`));
}

function setView(name) {
  $("#app-error").hidden = true;
  const signedIn = Boolean(currentUser);
  $("#login-view").hidden = signedIn;
  $("#navigation").hidden = !signedIn;
  $("#logout-button").hidden = !signedIn;
  $("#budget-view").hidden = !signedIn || name !== "budget";
  $("#users-view").hidden = !signedIn || name !== "users" || !currentUser.is_admin;
  $("#users-link").hidden = !signedIn || !currentUser.is_admin;
  document.querySelectorAll(".navigation a").forEach((link) => {
    link.classList.toggle("active", link.dataset.view === name);
  });
  if (!signedIn) {
    $("#password").value = "";
    $("#email").focus();
    return;
  }
  if (name === "users" && currentUser.is_admin) loadUsers().catch(showError);
  else {
    if (name === "users") location.hash = "#budget";
    loadFilters().then(loadExpenses).catch(showError);
  }
}

async function loadFilters() {
  const filters = await api("/api/filters");
  populateSelect($("#year-filter"), filters.years, tr("allYears"));
  populateSelect($("#category-filter"), filters.categories, tr("allCategories"));
  populateSelect($("#payer-filter"), filters.payers, tr("allPayers"));
}

function populateSelect(select, values, placeholder) {
  const oldValue = select.value;
  select.replaceChildren(new Option(placeholder, ""));
  values.forEach((value) => select.add(new Option(value, value)));
  if (values.includes(oldValue)) select.value = oldValue;
}

function showError(error) {
  const target = currentUser ? $("#app-error") : $("#login-error");
  target.textContent = error.message || tr("failed");
  target.hidden = false;
}

async function loadExpenses() {
  if (!currentUser) return;
  const params = new URLSearchParams({ page: String(currentPage) });
  for (const [key, selector] of [["year", "#year-filter"], ["category", "#category-filter"], ["payer", "#payer-filter"]]) {
    if ($(selector).value) params.set(key, $(selector).value);
  }
  if ($("#search-filter").value.trim()) params.set("search", $("#search-filter").value.trim());
  const data = await api(`/api/expenses?${params}`);
  expenseCount = data.count;
  const pageCount = Math.max(1, Math.ceil(data.count / data.page_size));
  if (currentPage > pageCount) {
    currentPage = pageCount;
    return loadExpenses();
  }
  $("#total-spent").textContent = money(data.total);
  $("#transaction-count").textContent = new Intl.NumberFormat(language === "fr" ? "fr-CA" : "en-CA").format(data.count);
  $("#average-expense").textContent = money(data.average);
  renderCategoryChart(data.categories);
  renderMonthlyChart(data.monthly);
  renderExpenses(data.items);
  $("#empty-state").hidden = data.items.length > 0;
  $("#empty-state").textContent = tr("noExpenses");
  $("#previous-page").disabled = currentPage <= 1;
  $("#next-page").disabled = currentPage >= pageCount;
  renderPageStatus(pageCount);
}

function renderCategoryChart(items) {
  const root = $("#category-chart");
  root.replaceChildren();
  const max = Math.max(...items.map((item) => item.total), 1);
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "bar-row";
    const name = document.createElement("span");
    name.className = "bar-name";
    name.textContent = item.category || "—";
    const track = document.createElement("span");
    track.className = "bar-track";
    const bar = document.createElement("span");
    bar.className = "bar-fill";
    bar.style.width = `${Math.max(3, (item.total / max) * 100)}%`;
    track.append(bar);
    const value = document.createElement("span");
    value.className = "bar-value";
    value.textContent = money(item.total);
    row.append(name, track, value);
    root.append(row);
  }
}

function renderMonthlyChart(items) {
  const root = $("#monthly-chart");
  root.replaceChildren();
  const max = Math.max(...items.map((item) => item.total), 1);
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "month-row";
    const label = document.createElement("span");
    label.textContent = new Intl.DateTimeFormat(language === "fr" ? "fr-CA" : "en-CA", {
      month: "short", year: "2-digit", timeZone: "UTC",
    }).format(new Date(`${item.month}-01T00:00:00Z`));
    const track = document.createElement("span");
    track.className = "month-track";
    const bar = document.createElement("span");
    bar.className = "month-fill";
    bar.style.height = `${Math.max(4, (item.total / max) * 100)}%`;
    track.append(bar);
    const value = document.createElement("span");
    value.className = "month-value";
    value.textContent = money(item.total);
    row.append(label, track, value);
    root.append(row);
  }
}

function renderExpenses(items) {
  const tbody = $("#expense-rows");
  tbody.replaceChildren();
  for (const item of items) {
    const row = document.createElement("tr");
    for (const [value, className] of [
      [dateLabel(item.spent_on), "date-cell"],
      [money(item.amount), "amount-cell"],
      [item.category || "—", "category-cell"],
      [item.supplier || "—", "merchant-cell"],
      [item.description || "—", "description-cell"],
      [item.paid_by || "—", "payer-cell"],
      [item.transfer_to || "—", "payer-cell"],
      [item.comments || "—", "description-cell"],
    ]) {
      const cell = document.createElement("td");
      cell.className = className;
      cell.textContent = value;
      row.append(cell);
    }
    tbody.append(row);
  }
}

function renderPageStatus(pageCount = Math.max(1, Math.ceil(expenseCount / 50))) {
  const status = $("#page-status");
  if (!status || !currentUser || $("#budget-view").hidden) return;
  const message = language === "fr"
    ? `Page ${currentPage} sur ${pageCount} · ${new Intl.NumberFormat("fr-CA").format(expenseCount)} dépenses`
    : `Page ${currentPage} of ${pageCount} · ${new Intl.NumberFormat("en-CA").format(expenseCount)} expenses`;
  status.textContent = message;
}

async function loadUsers() {
  const list = $("#users-list");
  list.replaceChildren();
  const users = await api("/api/users");
  if (!users.length) {
    list.textContent = language === "fr" ? "Aucun compte utilisateur." : "No user accounts found.";
    return;
  }
  for (const user of users) {
    const row = document.createElement("article");
    row.className = "user-row";
    const initials = document.createElement("span");
    initials.className = "user-avatar";
    initials.textContent = `${user.first_name[0] || ""}${user.last_name[0] || ""}`.toUpperCase();
    const details = document.createElement("span");
    details.className = "user-details";
    const name = document.createElement("strong");
    name.textContent = `${user.first_name} ${user.last_name}`;
    const email = document.createElement("span");
    email.textContent = user.email;
    details.append(name, email);
    const role = document.createElement("span");
    role.className = "role-badge";
    role.textContent = user.is_admin
      ? (language === "fr" ? "Administrateur" : "Administrator")
      : (language === "fr" ? "Utilisateur" : "User");
    row.append(initials, details, role);
    if (user.email !== currentUser.email) {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "icon-button danger-button";
      remove.setAttribute("aria-label", tr("removeUser"));
      remove.title = tr("removeUser");
      remove.innerHTML = '<svg><use href="#i-trash"></use></svg>';
      remove.addEventListener("click", async () => {
        if (!window.confirm(tr("confirmRemove"))) return;
        try {
          await api(`/api/users/${user.id}`, { method: "DELETE" });
          await loadUsers();
        } catch (error) { showError(error); }
      });
      row.append(remove);
    }
    list.append(row);
  }
}

$("#language-button").addEventListener("click", () => {
  language = language === "en" ? "fr" : "en";
  localStorage.setItem("budget-language", language);
  applyLanguage();
  if (currentUser) {
    if (!$("#users-view").hidden) loadUsers().catch(showError);
    else loadExpenses().catch(showError);
  }
});

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#login-error").hidden = true;
  const form = new FormData(event.currentTarget);
  try {
    await api("/api/login", { method: "POST", body: JSON.stringify({ email: form.get("email"), password: form.get("password") }) });
    currentUser = await api("/api/me");
    setView("budget");
    location.hash = "#budget";
  } catch {
    $("#login-error").textContent = tr("loginFailed");
    $("#login-error").hidden = false;
  }
});

$("#logout-button").addEventListener("click", async () => {
  try {
    await api("/api/logout", { method: "POST" });
    currentUser = null;
    location.hash = "";
    setView("budget");
  } catch (error) { showError(error); }
});

$("#user-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#user-error").hidden = true;
  const payload = Object.fromEntries(new FormData(event.currentTarget));
  if (payload.password.length < 12) {
    $("#user-error").textContent = tr("passwordTooShort");
    $("#user-error").hidden = false;
    return;
  }
  try {
    await api("/api/users", { method: "POST", body: JSON.stringify(payload) });
    event.currentTarget.reset();
    await loadUsers();
  } catch (error) {
    $("#user-error").textContent = error.status === 409 ? tr("accountExists") : (error.message || tr("failed"));
    $("#user-error").hidden = false;
  }
});

for (const selector of ["#year-filter", "#category-filter", "#payer-filter"]) {
  $(selector).addEventListener("change", () => { currentPage = 1; loadExpenses().catch(showError); });
}
$("#search-filter").addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => { currentPage = 1; loadExpenses().catch(showError); }, 250);
});
$("#previous-page").addEventListener("click", () => { if (currentPage > 1) { currentPage -= 1; loadExpenses().catch(showError); } });
$("#next-page").addEventListener("click", () => { currentPage += 1; loadExpenses().catch(showError); });
window.addEventListener("hashchange", () => setView(location.hash === "#users" ? "users" : "budget"));

async function start() {
  applyLanguage();
  try {
    currentUser = await api("/api/me");
    setView(location.hash === "#users" && currentUser.is_admin ? "users" : "budget");
  } catch (error) {
    currentUser = null;
    setView("budget");
    if (error.status !== 401) {
      $("#login-error").textContent = tr("failed");
      $("#login-error").hidden = false;
    }
  }
}

start();
