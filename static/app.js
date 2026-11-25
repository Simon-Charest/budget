"use strict";

const TEXT = {
  en: {
    navBudget: "Budget", navReport: "Report", navCategories: "Categories", navUsers: "Users", email: "Email address", password: "Password", signIn: "Sign in",
    overview: "YOUR FINANCES", budgetTitle: "Budget",
    budgetSubtitle: "Every expense, all in one place.", year: "Year", month: "Month", category: "Category", payer: "Payer", selectMember: "Select a person", clearFilters: "Clear filters", filterOptionsFailed: "Filter options could not be loaded. Please reload the page.", actions: "Actions", addExpense: "Add expense", editExpense: "Edit expense",
    deleteExpense: "Delete expense", addExpenseTooltip: "Add", editExpenseTooltip: "Edit", deleteExpenseTooltip: "Delete", confirmDeleteExpense: "Delete this expense?", saveExpense: "Save expense",
    categoryEnglish: "English name", addCategory: "Add category", editCategory: "Edit category",
    categoryFrench: "French name", usageCount: "Uses", manageCategories: "Manage categories", categoriesTitle: "Categories",
    saveCategory: "Save category", categoryCount: "{count} categories", noCategories: "No categories found.", noCategoryMatches: "No categories match these filters.", deleteCategory: "Delete category",
    confirmDeleteCategory: "Delete this category?", categoryInUse: "This category is used by existing expenses and cannot be deleted.",
    categoryNamesRequired: "Enter both category names.",
    filterEnglishCategory: "Filter English name", filterFrenchCategory: "Filter French name",
    close: "Close",
    filterDate: "Filter date", filterAmount: "Filter amount", filterCategory: "Filter category",
    filterMerchant: "Filter merchant", filterDescription: "Filter description", filterPayer: "Filter payer",
    filterRecipient: "Filter recipient", recipient: "Recipient",
    noCategory: "No category", conflict: "An item with that name already exists.", totalSpent: "Total spent",
    filteredTotal: "For the selected filters", selectionTotal: "Total",transactions: "Transactions", matchingRecords: "Matching records",
    reportTitle: "Financial report", reportSubtitle: "A summary of your household spending.",
    averageExpense: "Average expense", perTransaction: "Per transaction", spendingBreakdown: "SPENDING BREAKDOWN",
    byCategory: "By category", recentActivity: "RECENT ACTIVITY", monthlySpending: "Monthly spending",
    ledger: "THE LEDGER", all: "All", search: "Search expenses", searchPlaceholder: "Search merchant or notes…", date: "Date",
    merchant: "Merchant", description: "Description", amount: "Amount", transferTo: "Recipient",
    noExpenses: "No expenses match these filters.",
    pageOf: "Page {page} of {pages} · {count} expenses", accountAccess: "PEOPLE", usersTitle: "Users",
    usersSubtitle: "Manage household members and sign-in accounts in one list.", newAccount: "NEW PERSON", addUser: "Add a person",
    firstName: "First name", lastName: "Last name", passwordHint: "Use at least 12 characters.", optionalPassword: "Leave blank to keep the current password.",
    noAccount: "No sign-in account", accountDetailsOptional: "Leave email, account type, and password blank for a household member without sign-in access.",
    fullNameRequired: "Enter a first and last name for a sign-in account.",
    accountDetailsRequired: "To create a sign-in account, provide an email, account type, and password.",
    createAccount: "Create account", editUser: "Edit person", saveUser: "Save person", accessList: "PEOPLE", administrator: "Administrator",
    user: "User", accountType: "Account type", name: "Name", removeUser: "Remove person", editAccount: "Edit person", userCount: "{count} people", noUsers: "No people found.",
    confirmRemoveHouseholdMember: "Remove this person?",
    householdMemberInUse: "This person is assigned to existing expenses and cannot be removed.",
    personNameExists: "A person with that name already exists.",
    loginFailed: "We couldn't sign you in. Check your email and password.", failed: "Something went wrong. Please try again.",
    accountExists: "An account with that email already exists.", notAllowed: "You don't have permission to do that.",
    invalidInput: "Invalid input.", cannotRemove: "This account cannot be removed.",
    cannotDemoteAdmin: "You cannot demote your own account or the last administrator.",
    emailOrPassword: "Email or password is incorrect.", passwordTooShort: "Password must be at least 12 characters.",
    confirmRemove: "Remove this account?", signOut: "Sign out", changeLanguage: "Change language",
    previousPage: "Previous page", nextPage: "Next page",
  },
  fr: {
    navBudget: "Budget", navReport: "Rapport", navCategories: "Catégories", navUsers: "Utilisateurs", email: "Adresse courriel", password: "Mot de passe",
    signIn: "Connexion",
    overview: "VOS FINANCES", budgetTitle: "Budget", budgetSubtitle: "Toutes vos dépenses, au même endroit.",
    year: "Année", month: "Mois", category: "Catégorie", payer: "Payeur", selectMember: "Sélectionner une personne", clearFilters: "Effacer les filtres", filterOptionsFailed: "Impossible de charger les filtres. Veuillez actualiser la page.", actions: "Actions", addExpense: "Ajouter une dépense", editExpense: "Modifier la dépense",
    deleteExpense: "Supprimer la dépense", addExpenseTooltip: "Ajouter", editExpenseTooltip: "Modifier", deleteExpenseTooltip: "Supprimer", confirmDeleteExpense: "Supprimer cette dépense ?", saveExpense: "Enregistrer",
    categoryEnglish: "Nom anglais", addCategory: "Ajouter une catégorie", editCategory: "Modifier la catégorie",
    categoryFrench: "Nom français", usageCount: "Utilisations", manageCategories: "Gérer les catégories", categoriesTitle: "Catégories",
    saveCategory: "Enregistrer", categoryCount: "{count} catégories", noCategories: "Aucune catégorie.", noCategoryMatches: "Aucune catégorie ne correspond aux filtres.", deleteCategory: "Supprimer la catégorie",
    confirmDeleteCategory: "Supprimer cette catégorie ?", categoryInUse: "Cette catégorie est utilisée par des dépenses et ne peut pas être supprimée.",
    categoryNamesRequired: "Saisissez les deux noms de catégorie.",
    filterEnglishCategory: "Filtrer le nom anglais", filterFrenchCategory: "Filtrer le nom français",
    close: "Fermer",
    filterDate: "Filtrer par date", filterAmount: "Filtrer par montant", filterCategory: "Filtrer par catégorie",
    filterMerchant: "Filtrer par commerçant", filterDescription: "Filtrer par description", filterPayer: "Filtrer par payeur",
    filterRecipient: "Filtrer par bénéficiaire", recipient: "Bénéficiaire",
    noCategory: "Aucune catégorie", conflict: "Un élément portant ce nom existe déjà.", totalSpent: "Total des dépenses",
    reportTitle: "Rapport financier", reportSubtitle: "Un aperçu des dépenses du foyer.",
    filteredTotal: "Selon les filtres", selectionTotal: "Total",transactions: "Transactions", matchingRecords: "Résultats correspondants",
    averageExpense: "Dépense moyenne", perTransaction: "Par transaction", spendingBreakdown: "RÉPARTITION DES DÉPENSES",
    byCategory: "Par catégorie", recentActivity: "ACTIVITÉ RÉCENTE", monthlySpending: "Dépenses mensuelles",
    ledger: "LE GRAND LIVRE", all: "Tout", search: "Rechercher des dépenses", searchPlaceholder: "Commerçant ou notes…", date: "Date",
    merchant: "Commerçant", description: "Description", amount: "Montant", transferTo: "Bénéficiaire",
    noExpenses: "Aucune dépense ne correspond aux filtres.",
    pageOf: "Page {page} sur {pages} · {count} dépenses", accountAccess: "PERSONNES", usersTitle: "Utilisateurs",
    usersSubtitle: "Gérez les membres du foyer et les comptes de connexion dans une seule liste.", newAccount: "NOUVELLE PERSONNE",
    addUser: "Ajouter une personne", editUser: "Modifier la personne", saveUser: "Enregistrer la personne", firstName: "Prénom", lastName: "Nom de famille",
    passwordHint: "Utilisez au moins 12 caractères.", optionalPassword: "Laissez ce champ vide pour conserver le mot de passe actuel.", createAccount: "Créer le compte", accessList: "COMPTES AUTORISÉS",
    noAccount: "Aucun compte de connexion", accountDetailsOptional: "Laissez le courriel, le type de compte et le mot de passe vides pour un membre du foyer sans accès.",
    fullNameRequired: "Saisissez un prénom et un nom pour créer un compte de connexion.",
    accountDetailsRequired: "Pour créer un compte, saisissez une adresse courriel, un type de compte et un mot de passe.",
    administrator: "Administrateur", user: "Utilisateur", accountType: "Type de compte", name: "Nom", removeUser: "Supprimer la personne", editAccount: "Modifier la personne", userCount: "{count} personnes", noUsers: "Aucune personne.",
    confirmRemoveHouseholdMember: "Supprimer cette personne ?",
    householdMemberInUse: "Cette personne est associée à des dépenses et ne peut pas être supprimée.",
    personNameExists: "Une personne portant ce nom existe déjà.",
    loginFailed: "Connexion impossible. Vérifiez votre adresse courriel et votre mot de passe.",
    failed: "Une erreur est survenue. Veuillez réessayer.", accountExists: "Un compte utilise déjà cette adresse courriel.",
    notAllowed: "Vous n’avez pas l’autorisation d’effectuer cette action.",
    invalidInput: "Entrée invalide.", cannotRemove: "Ce compte ne peut pas être supprimé.",
    cannotDemoteAdmin: "Vous ne pouvez pas rétrograder votre propre compte ni le dernier administrateur.",
    emailOrPassword: "Adresse courriel ou mot de passe incorrect.",
    passwordTooShort: "Le mot de passe doit contenir au moins 12 caractères.", confirmRemove: "Supprimer ce compte ?",
    signOut: "Déconnexion", changeLanguage: "Langue", previousPage: "Page précédente", nextPage: "Page suivante",
  },
};

const $ = (selector) => document.querySelector(selector);
let language = localStorage.getItem("budget-language") || "en";
let currentUser = null;
let currentPage = 1;
let expenseCount = 0;
let expenseSortField = "spent_on";
let expenseSortDirection = "asc";
let searchTimer;
let categories = [];
let householdMembers = [];
let categorySortField = "name_en";
let categorySortDirection = 1;
let editingExpenseId = null;
let editingCategoryKey = null;
let editingUserId = null;
let editingHouseholdMemberId = null;
let editingPersonKind = null;
// The month filter survives a page refresh (per tab); a new visit starts on the latest month
const MONTH_STORAGE_KEY = "budget-month";
let selectedMonth = sessionStorage.getItem(MONTH_STORAGE_KEY);

function setSelectedMonth(value) {
  selectedMonth = value || null;
  if (selectedMonth) sessionStorage.setItem(MONTH_STORAGE_KEY, selectedMonth);
  else sessionStorage.removeItem(MONTH_STORAGE_KEY);
}

function tr(key) { return TEXT[language][key] || key; }

function applyLanguage() {
  document.documentElement.lang = language;
  const pageTitle = location.hash === "#report"
    ? tr("reportTitle")
    : location.hash === "#users" ? tr("usersTitle")
      : location.hash === "#categories" ? tr("categoriesTitle") : tr("budgetTitle");
  document.title = `Budget · ${pageTitle}`;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = tr(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = tr(el.dataset.i18nPlaceholder); });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((el) => { el.setAttribute("aria-label", tr(el.dataset.i18nAriaLabel)); });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = tr(el.dataset.i18nTitle); });
  document.querySelectorAll("button[aria-label]:not([data-i18n-title])").forEach((button) => {
    button.title = button.getAttribute("aria-label");
  });
  document.querySelectorAll("[data-search-field]").forEach((el) => {
    const key = ({
      filter_date: "filterDate", filter_amount: "filterAmount", filter_category: "filterCategory",
      filter_supplier: "filterMerchant", filter_description: "filterDescription",
      filter_paid_by: "filterPayer", filter_transfer_to: "filterRecipient",
    })[el.dataset.searchField];
    el.setAttribute("aria-label", tr(key));
    el.placeholder = tr(key);
  });
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
    const labelKey = button.closest("#login-form") ? "signIn"
      : button.closest("#expense-form") ? "saveExpense"
        : button.closest("#user-form") ? (editingPersonKind === null ? "addUser" : "saveUser")
          : "createAccount";
    const label = tr(labelKey);
    button.setAttribute("aria-label", label);
    button.title = label;
  });
  $("#user-form-title").textContent = tr(editingPersonKind === null ? "addUser" : "editUser");
  $("#user-password-hint").textContent = tr(
    editingPersonKind === "account" ? "optionalPassword" : "accountDetailsOptional",
  );
  $("#user-submit").setAttribute("aria-label", tr(editingPersonKind === null ? "addUser" : "saveUser"));
  $("#user-submit").title = tr(editingPersonKind === null ? "addUser" : "saveUser");
  if ($("#category-dialog").open) {
    $("#category-form-title").textContent = tr(editingCategoryKey === null ? "addCategory" : "editCategory");
  }
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
    else if (response.status === 409) detail = tr("conflict");
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

function setView(name) {
  $("#app-error").hidden = true;
  $("#budget-error").hidden = true;
  $("#categories-page-error").hidden = true;
  document.title = `Budget · ${tr(name === "report" ? "reportTitle" : name === "users" ? "usersTitle" : name === "categories" ? "categoriesTitle" : "budgetTitle")}`;
  const signedIn = Boolean(currentUser);
  $("#login-view").hidden = signedIn;
  $("#navigation").hidden = !signedIn;
  $("#logout-button").hidden = !signedIn;
  $("#budget-view").hidden = !signedIn || name !== "budget";
  $("#report-view").hidden = !signedIn || name !== "report";
  $("#categories-view").hidden = !signedIn || name !== "categories" || !currentUser.is_admin;
  $("#users-view").hidden = !signedIn || name !== "users" || !currentUser.is_admin;
  $("#categories-link").hidden = !signedIn || !currentUser.is_admin;
  $("#users-link").hidden = !signedIn || !currentUser.is_admin;
  document.querySelectorAll(".navigation a").forEach((link) => {
    link.classList.toggle("active", link.dataset.view === name);
  });
  if (!signedIn) {
    $("#password").value = "";
    $("#email").focus();
    return;
  }
  if ((name === "categories" || name === "users") && !currentUser.is_admin) {
    location.hash = "#budget";
    return;
  }
  if (name === "categories") loadCategories().catch(showError);
  else if (name === "users") loadUsers().catch(showError);
  else {
    Promise.all([loadFilters(), loadCategories(), loadHouseholdMembers()]).then(loadExpenses).catch(showError);
  }
}

async function loadFilters() {
  const filters = await api("/api/filters");
  const latestMonth = filters.months[filters.months.length - 1] || "all";
  const month = selectedMonth || filterValue("month") || latestMonth;
  // A remembered month that no longer has expenses falls back to the latest one
  setSelectedMonth(month === "all" || filters.months.includes(month) ? month : latestMonth);
  document.querySelectorAll("[data-month-filter]").forEach((select) => {
    select.replaceChildren(new Option(tr("all"), "all"));
    filters.months.forEach((value) => select.add(new Option(value, value)));
    select.value = selectedMonth;
  });
  for (const [key, values, placeholder] of [
    ["year", filters.years, tr("all")],
    ["category", filters.categories, tr("all")],
    ["payer", filters.payers, tr("all")],
  ]) {
    document.querySelectorAll(`[data-filter="${key}"]`).forEach((select) => {
      populateSelect(select, values, placeholder);
    });
  }
  populateSelect($("#budget-payer-filter"), filters.payers, tr("all"));
  populateSelect(
    $("#budget-recipient-filter"),
    Array.isArray(filters.recipients) ? filters.recipients : [],
    tr("all"),
  );
}

function filterValue(key) {
  if (key === "month") {
    const prefix = $("#budget-view").hidden ? "report" : "budget";
    return $(`#${prefix}-month-filter`)?.value || selectedMonth || "";
  }
  return $(`#report-${key}-filter`)?.value || "";
}

function populateSelect(select, values, placeholder) {
  if (!Array.isArray(values)) throw new Error(tr("filterOptionsFailed"));
  const oldValue = select.value;
  select.replaceChildren(new Option(placeholder, ""));
  values.forEach((value) => select.add(new Option(value, value)));
  if (values.includes(oldValue)) select.value = oldValue;
}

async function loadHouseholdMembers() {
  householdMembers = await api("/api/household-members");
  const names = householdMembers.map((member) => member.name);
  for (const select of [$("#expense-payer"), $("#expense-recipient")]) {
    populateSelect(select, names, tr("selectMember"));
  }
}

function showError(error) {
  const target = !currentUser ? $("#login-error")
    : !$("#budget-view").hidden ? $("#budget-error")
      : !$("#categories-view").hidden ? $("#categories-page-error") : $("#app-error");
  target.textContent = error.message || tr("failed");
  target.hidden = false;
}

function categoryName(key) {
  const category = categories.find((item) => item.category_key === key);
  return category ? (language === "fr" ? category.name_fr : category.name_en) : key || "—";
}

async function loadCategories() {
  $("#categories-page-error").hidden = true;
  categories = await api("/api/categories");
  const budgetCategory = $("#budget-category-filter");
  if (budgetCategory) {
    const selected = budgetCategory.value;
    budgetCategory.replaceChildren(new Option(tr("all"), ""));
    categories.forEach((item) => budgetCategory.add(
      new Option(categoryName(item.category_key), item.category_key),
    ));
    if (categories.some((item) => item.category_key === selected)) budgetCategory.value = selected;
  }
  const select = $("#expense-category");
  select.replaceChildren(new Option(tr("noCategory"), ""));
  categories.forEach((item) => select.add(new Option(categoryName(item.category_key), item.category_key)));
  const reportCategory = $("#report-category-filter");
  if (reportCategory) {
    const selected = reportCategory.value;
    reportCategory.replaceChildren(new Option(tr("all"), ""));
    categories.forEach((item) => reportCategory.add(new Option(categoryName(item.category_key), item.category_key)));
    if (categories.some((item) => item.category_key === selected)) reportCategory.value = selected;
  }
  renderCategoryList();
}

function formatCount(value) {
  return new Intl.NumberFormat(language === "fr" ? "fr-CA" : "en-CA").format(value ?? 0);
}

function renderCategoryList() {
  const body = $("#category-table-body");
  body.replaceChildren();
  const englishFilter = $("#category-filter-en").value.trim().toLocaleLowerCase();
  const frenchFilter = $("#category-filter-fr").value.trim().toLocaleLowerCase();
  const filtered = categories.filter((category) =>
    category.name_en.toLocaleLowerCase().includes(englishFilter)
    && category.name_fr.toLocaleLowerCase().includes(frenchFilter));
  const collator = new Intl.Collator(language === "fr" ? "fr-CA" : "en-CA", { sensitivity: "base" });
  filtered.sort((a, b) => categorySortDirection * (categorySortField === "usage_count"
    ? (a.usage_count - b.usage_count) || collator.compare(a.name_en, b.name_en)
    : collator.compare(a[categorySortField], b[categorySortField])));
  $("#category-count").textContent = tr("categoryCount").replace("{count}", String(filtered.length));
  if (!filtered.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.className = "empty-state";
    cell.textContent = categories.length ? tr("noCategoryMatches") : tr("noCategories");
    row.append(cell);
    body.append(row);
    return;
  }
  for (const category of filtered) {
    const row = document.createElement("tr");
    const name = document.createElement("td");
    name.className = "category-name-cell category-name-en";
    name.textContent = category.name_en;
    const frenchName = document.createElement("td");
    frenchName.className = "category-name-cell category-name-fr";
    frenchName.textContent = category.name_fr;
    const uses = document.createElement("td");
    uses.className = "usage-count-cell";
    uses.textContent = formatCount(category.usage_count);
    const actions = document.createElement("td");
    actions.className = "category-actions-cell";
    const buttons = document.createElement("span");
    buttons.className = "category-actions";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "icon-button";
    edit.setAttribute("aria-label", tr("editCategory"));
    edit.title = tr("editCategory");
    edit.innerHTML = '<svg><use href="#i-edit"></use></svg>';
    edit.addEventListener("click", () => openCategoryForm(category));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "icon-button danger-button";
    remove.setAttribute("aria-label", tr("deleteCategory"));
    remove.title = tr("deleteCategory");
    remove.innerHTML = '<svg><use href="#i-trash"></use></svg>';
    remove.addEventListener("click", async () => {
      if (!window.confirm(tr("confirmDeleteCategory"))) return;
      try {
        await api(`/api/categories/${encodeURIComponent(category.category_key)}`, { method: "DELETE" });
        await loadCategories();
        await loadExpenses();
      } catch (error) {
        $("#categories-page-error").textContent = error.status === 409 ? tr("categoryInUse") : (error.message || tr("failed"));
        $("#categories-page-error").hidden = false;
      }
    });
    buttons.append(edit, remove);
    actions.append(buttons);
    row.append(name, frenchName, uses, actions);
    body.append(row);
  }
}

function updateCategorySortIndicators() {
  document.querySelectorAll("[data-category-sort]").forEach((button) => {
    const active = button.dataset.categorySort === categorySortField;
    button.closest("th").setAttribute("aria-sort", active
      ? categorySortDirection === 1 ? "ascending" : "descending"
      : "none");
    button.querySelector(".sort-indicator").textContent = active
      ? categorySortDirection === 1 ? "↑" : "↓"
      : "";
  });
}

function openCategoryForm(category = null) {
  editingCategoryKey = category?.category_key ?? null;
  $("#category-form").reset();
  $("#category-error").hidden = true;
  $("#categories-page-error").hidden = true;
  $("#category-en").value = category?.name_en || "";
  $("#category-fr").value = category?.name_fr || "";
  $("#category-form-title").textContent = tr(category ? "editCategory" : "addCategory");
  $("#category-dialog").showModal();
}

async function loadExpenses() {
  if (!currentUser) return;
  const params = new URLSearchParams({ page: String(currentPage) });
  params.set("month", filterValue("month"));
  params.set("sort_by", expenseSortField);
  params.set("sort_dir", expenseSortDirection);
  params.set("category_language", language);
  if (!$("#report-view").hidden) {
    for (const key of ["year", "category", "payer"]) {
      const value = filterValue(key);
      if (value) params.set(key, value);
    }
  }
  if (!$("#budget-view").hidden) {
    document.querySelectorAll("[data-search-field]").forEach((input) => {
      if (input.value.trim()) params.set(input.dataset.searchField, input.value.trim());
    });
  }
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
  $("#expense-total").textContent = money(data.total);
  $("#expense-total-row").hidden = data.items.length === 0;
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
      [item.spent_on, "date-cell"],
      [item.supplier || "—", "merchant-cell"],
      [categoryName(item.category), "category-cell"],
      [money(item.amount), "amount-cell"],
      [item.paid_by || "—", "payer-cell"],
      [item.transfer_to || "—", "payer-cell"],
      [item.description || "—", "description-cell"],
    ]) {
      const cell = document.createElement("td");
      cell.className = className;
      cell.textContent = value;
      row.append(cell);
    }
    const actions = document.createElement("td");
    actions.className = "action-cell";
    const buttons = document.createElement("span");
    buttons.className = "row-actions";
    for (const [key, tooltipKey, icon, callback] of [
      ["editExpense", "editExpenseTooltip", "i-edit", () => openExpenseForm(item)],
      ["deleteExpense", "deleteExpenseTooltip", "i-trash", () => removeExpense(item.id)],
    ]) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `icon-button${key === "deleteExpense" ? " danger-button" : ""}`;
      button.setAttribute("aria-label", tr(key));
      button.dataset.i18nTitle = tooltipKey;
      button.title = tr(tooltipKey);
      button.innerHTML = `<svg><use href="#${icon}"></use></svg>`;
      button.addEventListener("click", callback);
      buttons.append(button);
    }
    actions.append(buttons);
    row.append(actions);
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

function openExpenseForm(item = null) {
  editingExpenseId = item?.id ?? null;
  const form = $("#expense-form");
  form.reset();
  for (const select of [$("#expense-payer"), $("#expense-recipient")]) {
    populateSelect(select, householdMembers.map((member) => member.name), tr("selectMember"));
  }
  $("#expense-error").hidden = true;
  $("#expense-form-title").textContent = tr(item ? "editExpense" : "addExpense");
  const today = new Date();
  const localToday = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  $("#expense-date").value = item?.spent_on || localToday;
  $("#expense-amount").value = item?.amount ?? "";
  $("#expense-category").value = item?.category || "";
  $("#expense-supplier").value = item?.supplier || "";
  $("#expense-description").value = item?.description || "";
  $("#expense-payer").value = item?.paid_by || "";
  $("#expense-recipient").value = item?.transfer_to || "";
  $("#expense-dialog").showModal();
}

async function removeExpense(id) {
  if (!window.confirm(tr("confirmDeleteExpense"))) return;
  try {
    await api(`/api/expenses/${id}`, { method: "DELETE" });
    await loadFilters();
    await loadExpenses();
  } catch (error) {
    showError(error);
  }
}

async function loadUsers() {
  const list = $("#users-table-body");
  list.replaceChildren();
  const [users, members] = await Promise.all([
    api("/api/users"),
    api("/api/household-members"),
  ]);
  householdMembers = members;
  const accountNames = new Set(
    users.map((user) => `${user.first_name} ${user.last_name}`.toLocaleLowerCase()),
  );
  const people = [
    ...users.map((user) => {
      const name = `${user.first_name} ${user.last_name}`;
      const member = members.find((item) => item.name.toLocaleLowerCase() === name.toLocaleLowerCase());
      return { ...user, kind: "account", name, usage_count: member?.usage_count ?? 0 };
    }),
    ...members
      .filter((member) => !accountNames.has(member.name.toLocaleLowerCase()))
      .map((member) => ({ ...member, kind: "member", email: "", is_admin: null })),
  ].sort((a, b) => {
    const rank = (person) => person.kind === "member" ? 2 : person.is_admin ? 0 : 1;
    return rank(a) - rank(b) || a.name.localeCompare(b.name, language, { sensitivity: "base" });
  });
  const names = [...new Set(members.map((member) => member.name))];
  for (const select of [$("#expense-payer"), $("#expense-recipient")]) {
    populateSelect(select, names, tr("selectMember"));
  }
  $("#user-count").textContent = tr("userCount").replace("{count}", String(people.length));
  if (!people.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.className = "empty-state";
    cell.textContent = tr("noUsers");
    row.append(cell);
    list.append(row);
    return;
  }
  for (const user of people) {
    const row = document.createElement("tr");
    const name = document.createElement("td");
    name.className = "user-name-cell";
    name.textContent = user.name;
    const email = document.createElement("td");
    email.className = "user-email-cell";
    email.textContent = user.email;
    const accountType = document.createElement("td");
    const role = document.createElement("span");
    role.className = "role-badge";
    if (user.kind === "account") {
      role.textContent = user.is_admin ? tr("administrator") : tr("user");
      accountType.append(role);
    }
    const uses = document.createElement("td");
    uses.className = "usage-count-cell";
    uses.textContent = formatCount(user.usage_count);
    const actions = document.createElement("td");
    actions.className = "user-actions-cell";
    const actionButtons = document.createElement("span");
    actionButtons.className = "user-actions";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "icon-button";
    edit.setAttribute("aria-label", tr("editAccount"));
    edit.title = tr("editAccount");
    edit.innerHTML = '<svg><use href="#i-edit"></use></svg>';
    edit.addEventListener("click", () => openUserForm(user));
    actionButtons.append(edit);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "icon-button danger-button";
    remove.setAttribute("aria-label", tr("removeUser"));
    remove.title = tr("removeUser");
    remove.innerHTML = '<svg><use href="#i-trash"></use></svg>';
    remove.addEventListener("click", async () => {
      if (!window.confirm(tr(user.kind === "member" ? "confirmRemoveHouseholdMember" : "confirmRemove"))) return;
      try {
        if (user.kind === "account") {
          if (user.email === currentUser.email) return;
          await api(`/api/users/${user.id}`, { method: "DELETE" });
        } else {
          await api(`/api/household-members/${user.id}`, { method: "DELETE" });
        }
        await loadUsers();
      } catch (error) {
        if (error.status === 409 && user.kind === "member") error.message = tr("householdMemberInUse");
        showError(error);
      }
    });
    remove.disabled = user.kind === "account" && user.email === currentUser.email;
    actionButtons.append(remove);
    actions.append(actionButtons);
    row.append(name, email, accountType, uses, actions);
    list.append(row);
  }
}

function openUserForm(user = null) {
  const form = $("#user-form");
  editingPersonKind = user?.kind ?? null;
  editingUserId = user?.kind === "account" ? user.id : null;
  editingHouseholdMemberId = user?.kind === "member" ? user.id : null;
  form.reset();
  $("#user-error").hidden = true;
  $("#person-name").value = user?.name || "";
  $("#user-email").value = user?.email || "";
  $("#user-password").required = false;
  $("#user-password").value = "";
  $("#user-admin").value = user?.kind === "account" ? String(Boolean(user.is_admin)) : "";
  $("#user-admin").disabled = Boolean(user?.kind === "member" || (user?.email && user.email === currentUser.email));
  const accountFieldsVisible = user?.kind !== "member";
  document.querySelectorAll(".account-only").forEach((field) => {
    field.hidden = !accountFieldsVisible;
    field.disabled = !accountFieldsVisible;
  });
  $("#user-admin").disabled = !accountFieldsVisible || Boolean(user?.email && user.email === currentUser.email);
  $("#user-email").required = user?.kind === "account";
  $("#user-password-hint").hidden = user?.kind === "member";
  $("#user-form-title").textContent = tr(user ? "editUser" : "addUser");
  $("#user-password-hint").textContent = tr(
    user?.kind === "account" ? "optionalPassword" : "accountDetailsOptional",
  );
  $("#user-submit").setAttribute("aria-label", tr(user ? "saveUser" : "addUser"));
  $("#user-submit").title = tr(user ? "saveUser" : "addUser");
  $("#user-submit").innerHTML = `<svg><use href="#${user ? "i-check" : "i-plus"}"></use></svg>`;
  $("#user-dialog").showModal();
}

$("#language-button").addEventListener("click", () => {
  language = language === "en" ? "fr" : "en";
  localStorage.setItem("budget-language", language);
  applyLanguage();
  if (currentUser) {
    if (!$("#users-view").hidden) loadUsers().catch(showError);
    else Promise.all([loadCategories(), loadHouseholdMembers(), loadExpenses()]).catch(showError);
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
    setSelectedMonth(null);
    location.hash = "";
    setView("budget");
  } catch (error) { showError(error); }
});

$("#user-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#user-error").hidden = true;
  const name = $("#person-name").value.trim();
  const email = $("#user-email").value.trim();
  const password = $("#user-password").value;
  const role = $("#user-admin").value;
  const isAccount = editingPersonKind === "account" || (editingPersonKind === null && Boolean(email || password || role));
  if (isAccount && (!email || (editingPersonKind === null && !password) || !role)) {
    $("#user-error").textContent = tr("accountDetailsRequired");
    $("#user-error").hidden = false;
    return;
  }
  const nameParts = name.split(/\s+/);
  if (isAccount && nameParts.length < 2) {
    $("#user-error").textContent = tr("fullNameRequired");
    $("#user-error").hidden = false;
    return;
  }
  if (password && password.length < 12) {
    $("#user-error").textContent = tr("passwordTooShort");
    $("#user-error").hidden = false;
    return;
  }
  try {
    if (editingPersonKind === "member") {
      await api(`/api/household-members/${editingHouseholdMemberId}`, {
        method: "PUT",
        body: JSON.stringify({ name }),
      });
    } else if (isAccount) {
      const payload = {
        email,
        first_name: nameParts.shift(),
        last_name: nameParts.join(" "),
        is_admin: $("#user-admin").disabled ? currentUser.is_admin : role === "true",
        password: password || null,
      };
      await api(editingUserId === null ? "/api/users" : `/api/users/${editingUserId}`, {
        method: editingUserId === null ? "POST" : "PUT",
        body: JSON.stringify(payload),
      });
      if (editingUserId === currentUser.id) {
        currentUser = {
          ...currentUser,
          email: payload.email.trim().toLowerCase(),
          first_name: payload.first_name,
          last_name: payload.last_name,
          is_admin: payload.is_admin,
        };
      }
    } else {
      await api("/api/household-members", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
    }
  } catch (error) {
    $("#user-error").textContent = error.status === 409
      ? tr(editingPersonKind === "member" ? "personNameExists" : "accountExists")
      : error.status === 400 && editingUserId !== null ? tr("cannotDemoteAdmin")
        : (error.message || tr("failed"));
    $("#user-error").hidden = false;
    return;
  }
  editingUserId = null;
  editingHouseholdMemberId = null;
  editingPersonKind = null;
  event.currentTarget.reset();
  $("#user-dialog").close();
  await loadUsers().catch(showError);
});

$("#add-user-button").addEventListener("click", () => openUserForm());
$("#close-user-dialog").addEventListener("click", () => $("#user-dialog").close());
$("#add-expense-button").addEventListener("click", () => openExpenseForm());
$("#close-expense-dialog").addEventListener("click", () => $("#expense-dialog").close());
$("#expense-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#expense-error").hidden = true;
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form);
  payload.amount = Number(payload.amount);
  for (const key of ["category", "supplier", "description", "paid_by", "transfer_to"]) {
    payload[key] = payload[key].trim() || null;
  }
  try {
    const url = editingExpenseId ? `/api/expenses/${editingExpenseId}` : "/api/expenses";
    await api(url, { method: editingExpenseId ? "PUT" : "POST", body: JSON.stringify(payload) });
    // Stay on the month being viewed (or "all"), even when the saved expense belongs to another month
    await loadFilters();
    $("#expense-dialog").close();
    await loadExpenses();
  } catch (error) {
    $("#expense-error").textContent = error.message || tr("failed");
    $("#expense-error").hidden = false;
  }
});

$("#category-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#category-error").hidden = true;
  const categoryKey = editingCategoryKey;
  const payload = { name_en: $("#category-en").value.trim(), name_fr: $("#category-fr").value.trim() };
  try {
    await api(categoryKey ? `/api/categories/${encodeURIComponent(categoryKey)}` : "/api/categories", {
      method: categoryKey ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    editingCategoryKey = null;
    $("#category-dialog").close();
    await loadCategories();
    await loadExpenses();
  } catch (error) {
    $("#category-error").textContent = error.status === 422 ? tr("categoryNamesRequired") : (error.message || tr("failed"));
    $("#category-error").hidden = false;
  }
});
$("#add-category-button").addEventListener("click", () => openCategoryForm());
$("#close-category-dialog").addEventListener("click", () => $("#category-dialog").close());
document.querySelectorAll("[data-category-sort]").forEach((button) => {
  button.addEventListener("click", () => {
    if (categorySortField === button.dataset.categorySort) categorySortDirection *= -1;
    else {
      categorySortField = button.dataset.categorySort;
      categorySortDirection = 1;
    }
    updateCategorySortIndicators();
    renderCategoryList();
  });
});
$("#category-filter-en").addEventListener("input", renderCategoryList);
$("#category-filter-fr").addEventListener("input", renderCategoryList);
$("#clear-category-filters").addEventListener("click", () => {
  $("#category-filter-en").value = "";
  $("#category-filter-fr").value = "";
  renderCategoryList();
});

document.querySelectorAll("[data-filter]").forEach((select) => {
  select.addEventListener("change", () => {
    currentPage = 1;
    loadExpenses().catch(showError);
  });
});
document.querySelectorAll("[data-month-filter]").forEach((select) => {
  select.addEventListener("change", () => {
    setSelectedMonth(select.value);
    document.querySelectorAll("[data-month-filter]").forEach((peer) => { peer.value = select.value; });
    currentPage = 1;
    loadExpenses().catch(showError);
  });
});
document.querySelectorAll("[data-search-field]").forEach((control) => {
  control.addEventListener(control instanceof HTMLSelectElement ? "change" : "input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => { currentPage = 1; loadExpenses().catch(showError); }, 250);
  });
});
$("#clear-filters-button").addEventListener("click", () => {
  document.querySelectorAll("#budget-view [data-search-field]").forEach((control) => { control.value = ""; });
  $("#budget-month-filter").value = "all";
  setSelectedMonth("all");
  currentPage = 1;
  loadExpenses().catch(showError);
});
$("#previous-page").addEventListener("click", () => { if (currentPage > 1) { currentPage -= 1; loadExpenses().catch(showError); } });
$("#next-page").addEventListener("click", () => { currentPage += 1; loadExpenses().catch(showError); });
function updateExpenseSortIndicators() {
  document.querySelectorAll("[data-budget-sort]").forEach((button) => {
    const active = button.dataset.budgetSort === expenseSortField;
    button.closest("th").setAttribute("aria-sort", active
      ? expenseSortDirection === "asc" ? "ascending" : "descending"
      : "none");
    button.querySelector(".sort-indicator").textContent = active
      ? expenseSortDirection === "asc" ? "↑" : "↓"
      : "";
  });
}
document.querySelectorAll("[data-budget-sort]").forEach((button) => {
  button.addEventListener("click", () => {
    if (expenseSortField === button.dataset.budgetSort) {
      expenseSortDirection = expenseSortDirection === "asc" ? "desc" : "asc";
    } else {
      expenseSortField = button.dataset.budgetSort;
      expenseSortDirection = "asc";
    }
    currentPage = 1;
    updateExpenseSortIndicators();
    loadExpenses().catch(showError);
  });
});
window.addEventListener("hashchange", () => {
  const view = location.hash === "#users" ? "users"
    : location.hash === "#categories" ? "categories"
      : location.hash === "#report" ? "report" : "budget";
  setView(view);
});

async function start() {
  applyLanguage();
  try {
    currentUser = await api("/api/me");
    const view = (location.hash === "#users" || location.hash === "#categories") && currentUser.is_admin
      ? location.hash.slice(1)
      : location.hash === "#report" ? "report" : "budget";
    setView(view);
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
