"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const statusLabels = { aberto: "Aberto", em_analise: "Em análise", em_manutencao: "Em manutenção", resolvido: "Resolvido" };
const priorityLabels = { 1: "Baixa", 2: "Média", 3: "Alta", 4: "Urgente" };
const viewHashes = { overview: "#visao-geral", occurrences: "#ocorrencias", queries: "#consultas" };
const state = { connected: false, epoch: 0, view: "overview", page: 1, pages: 1, editDoc: null, checking: false, saving: false, refreshId: 0, listId: 0, queryId: 0 };
const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const shortDate = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" });
const fullDate = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

// Todos os textos do banco são escapados antes de entrar em marcação HTML.
function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}
function icon(name) { return `<svg class="icon" aria-hidden="true"><use href="#i-${name}"/></svg>`; }
function statusBadge(status) { return `<span class="badge status-${escapeHTML(status)}">${escapeHTML(statusLabels[status] || status)}</span>`; }
function priorityBadge(priority) { return `<span class="badge priority-${Number(priority)}">${escapeHTML(priorityLabels[priority])}</span>`; }
function friendlyDate(value, complete = false) { return value ? (complete ? fullDate : shortDate).format(new Date(value)) : "—"; }

class AppError extends Error {
  constructor(message, silent = false) { super(message); this.silent = silent; }
}

let toastTimer;
function toast(message, error = false) {
  clearTimeout(toastTimer);
  const element = document.createElement("div");
  element.className = `toast${error ? " error" : ""}`;
  element.textContent = message;
  $("#toast-region").replaceChildren(element);
  toastTimer = setTimeout(() => $("#toast-region").replaceChildren(), 5000);
}
function report(error) { if (!error.silent) toast(error.message || "Não foi possível concluir a ação.", true); }

function blockApplication(message, title = "Ative o MongoDB para começar") {
  state.epoch += 1;
  state.connected = false;
  state.editDoc = null;
  state.page = 1;
  $("#app-shell").hidden = true;
  $("#connection-gate").hidden = false;
  $("#connection-title").textContent = title;
  $("#connection-message").textContent = message;
  $("#connection-help").hidden = false;
  $("#gate-indicator").classList.remove("checking");
  $("#retry-connection").disabled = false;
  $("#retry-connection span").textContent = "Tentar conexão";
  $$('dialog[open]').forEach(dialog => dialog.close());
  $("#occurrence-form").reset();
  ["#recent-list", "#block-list", "#occurrence-rows", "#query-results", "#photo-preview", "#history-list"].forEach(selector => $(selector).replaceChildren());
  ["#stat-total", "#stat-pending", "#stat-urgent", "#stat-resolved", "#nav-count"].forEach(selector => $(selector).textContent = "—");
  $$(".building-count").forEach(element => element.textContent = "—");
  $("#toast-region").replaceChildren();
}

async function api(path, options = {}) {
  if (!state.connected && path !== "/api/status") throw new AppError("Conecte ao MongoDB para continuar.", true);
  const epoch = state.epoch;
  let response;
  try {
    response = await fetch(path, { cache: "no-store", ...options, headers: { "Content-Type": "application/json", ...options.headers } });
  } catch {
    blockApplication("Não foi possível acessar o servidor da aplicação. Confira se o Flask está em execução e se o MongoDB está ativo.", "Conexão indisponível");
    throw new AppError("Conexão indisponível.", true);
  }
  if (epoch !== state.epoch) throw new AppError("A conexão mudou durante a solicitação.", true);
  const data = options.raw && response.ok ? response : await response.json().catch(() => ({ error: "Resposta inesperada do servidor." }));
  if (epoch !== state.epoch) throw new AppError("A conexão mudou durante a solicitação.", true);
  if (!response.ok) {
    if (response.status === 503 || String(data.code || "").startsWith("mongo_")) {
      blockApplication(data.error, data.code === "mongo_offline" ? "Ative o MongoDB para continuar" : "Verifique sua conexão com o banco");
      throw new AppError(data.error, true);
    }
    throw new AppError(data.error || "Não foi possível concluir a ação.");
  }
  return data;
}

async function checkConnection() {
  if (state.checking) return;
  const starting = !state.connected;
  state.checking = true;
  if (!state.connected) {
    $("#retry-connection").disabled = true;
    $("#retry-connection span").textContent = "Verificando…";
    $("#gate-indicator").classList.add("checking");
  }
  try {
    await api("/api/status");
    if (!state.connected) {
      state.connected = true;
      await refreshAll();
      if (!state.connected) return;
      $("#connection-gate").hidden = true;
      $("#app-shell").hidden = false;
    }
  } catch (error) {
    if (!error.silent && starting) blockApplication(error.message, "Não foi possível abrir o campus");
    else report(error);
  } finally {
    state.checking = false;
    if (!state.connected) {
      $("#retry-connection").disabled = false;
      $("#retry-connection span").textContent = "Tentar conexão";
      $("#gate-indicator").classList.remove("checking");
    }
  }
}

function renderDashboard(data) {
  $("#stat-total").textContent = data.total;
  $("#stat-pending").textContent = data.pendentes;
  $("#stat-urgent").textContent = data.urgentes;
  $("#stat-resolved").textContent = data.resolvidos;
  $("#nav-count").textContent = data.total;
  $("#resolution-rate").textContent = data.total ? `${Math.round(data.resolvidos / data.total * 100)}% das ocorrências solucionadas` : "Nenhuma ocorrência registrada";
  $("#block-list").innerHTML = data.blocos.map(block => `<button class="block-row" data-block="${escapeHTML(block.bloco)}"><span class="block-avatar">${escapeHTML(block.bloco)}</span><span><span class="block-name">Bloco ${escapeHTML(block.bloco)}</span><span class="block-subtitle">${escapeHTML(block.nome)}</span></span><span class="block-pending">${block.pendentes} ${block.pendentes === 1 ? "pendência" : "pendências"}${block.urgentes ? `<small>${block.urgentes} ${block.urgentes === 1 ? "urgente" : "urgentes"}</small>` : ""}</span>${icon("arrow")}</button>`).join("");
  data.blocos.forEach(block => {
    const button = $(`.map-building[data-block="${block.bloco}"]`);
    $(".building-count", button).textContent = block.pendentes;
    button.classList.toggle("has-urgent", block.urgentes > 0);
    button.classList.toggle("no-pending", block.pendentes === 0);
    button.setAttribute("aria-label", `Bloco ${block.bloco}, ${block.nome}: ${block.pendentes} pendências, ${block.urgentes} urgentes. Ver ocorrências.`);
  });
}

function renderRecent(items) {
  $("#recent-list").innerHTML = items.length ? items.slice(0, 5).map(item => `<button class="recent-row" data-open="${item._id}"><span class="recent-icon">${icon(item.acessibilidade ? "alert" : "list")}</span><span class="recent-text"><span class="recent-title">${escapeHTML(item.titulo)}</span><span class="recent-meta">Bloco ${escapeHTML(item.localizacao.bloco)} · ${escapeHTML(item.localizacao.sala)} · ${friendlyDate(item.criado_em)}</span></span>${statusBadge(item.status)}${icon("arrow")}</button>`).join("") : `<div class="empty-state">${icon("check")}<h3>Um novo começo para o campus</h3><p>Registre a primeira ocorrência para começar o acompanhamento.</p></div>`;
}

function filterParams() {
  const params = new URLSearchParams(new FormData($("#filter-form")));
  [...params.keys()].forEach(key => { if (!params.get(key)) params.delete(key); });
  params.set("pagina", state.page);
  return params;
}

function renderList(data) {
  state.page = data.pagina;
  state.pages = data.paginas;
  $("#list-total").textContent = `${data.total} ${data.total === 1 ? "ocorrência encontrada" : "ocorrências encontradas"}`;
  $("#occurrence-rows").innerHTML = data.items.map(item => `<tr><td><button class="row-title" data-open="${item._id}">${escapeHTML(item.titulo)}</button><span class="row-category">${escapeHTML(item.categoria)}${item.acessibilidade ? " · Acessibilidade" : ""}</span></td><td>Bloco ${escapeHTML(item.localizacao.bloco)}<span class="cell-subtitle">${escapeHTML(item.localizacao.sala)}</span></td><td>${priorityBadge(item.prioridade)}</td><td>${statusBadge(item.status)}</td><td class="cell-date">${friendlyDate(item.criado_em)}</td><td><button class="row-open" data-open="${item._id}" aria-label="Abrir ${escapeHTML(item.titulo)}">${icon("arrow")}</button></td></tr>`).join("");
  $("#list-empty").hidden = data.items.length > 0;
  $("#page-info").textContent = `Página ${data.pagina} de ${data.paginas}`;
  $("#previous-page").disabled = data.pagina <= 1;
  $("#next-page").disabled = data.pagina >= data.paginas;
}

async function loadList() {
  const id = ++state.listId;
  const result = await api(`/api/ocorrencias?${filterParams()}`);
  if (id === state.listId && state.connected) renderList(result);
}

async function refreshAll() {
  const id = ++state.refreshId;
  $("#app-shell").classList.add("busy");
  try {
    const [dashboard, recent] = await Promise.all([api("/api/painel"), api("/api/ocorrencias")]);
    if (id !== state.refreshId || !state.connected) return;
    renderDashboard(dashboard);
    renderRecent(recent.items);
    if (state.view === "occurrences") await loadList();
    if (state.view === "queries") await loadQueries();
    $("#last-update").textContent = `Atualizado às ${new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;
  } finally {
    if (id === state.refreshId) $("#app-shell").classList.remove("busy");
  }
}

function emptyQuery() { return `<div class="empty-state">${icon("search")}<h3>Nenhum resultado neste recorte</h3><p>Experimente selecionar outro bloco.</p></div>`; }
function queryTable(headers, rows) { return `<table><thead><tr>${headers.map(header => `<th scope="col">${escapeHTML(header)}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table>`; }
function queryVisual(query) {
  const rows = query.resultados;
  if (!rows.length) return emptyQuery();
  if (query.id === "urgentes") return queryTable(["Ocorrência", "Prioridade", "Bloco"], rows.map(row => [`<button class="row-title" data-open="${row._id}">${escapeHTML(row.titulo)}</button><span class="cell-subtitle">${escapeHTML(statusLabels[row.status])}</span>`, priorityBadge(row.prioridade), escapeHTML(row.localizacao.bloco)]));
  if (query.id === "categorias") {
    const max = Math.max(1, ...rows.map(row => row.total));
    return `<p class="query-result-caption">Total de registros · Custo estimado</p>` + rows.map(row => `<div class="chart-row"><div class="chart-row-top"><span>${escapeHTML(row.categoria)} <small>(${row.pendentes} pendentes)</small></span><span>${row.total} <small>· ${money.format(row.custo)}</small></span></div><div class="chart-track"><div class="chart-fill" data-width="${row.total / max * 100}"></div></div></div>`).join("");
  }
  if (query.id === "resolucao") return queryTable(["Categoria", "Resolvidas", "Média"], rows.map(row => [escapeHTML(row.categoria), row.resolvidos, `<strong>${escapeHTML(String(row.media_horas).replace(".", ","))} h</strong>`]));
  return queryTable(["Bloco", "Ocorrências", "Urgências abertas"], rows.map(row => [`<strong>Bloco ${escapeHTML(row.bloco)}</strong><span class="cell-subtitle">${escapeHTML([...row.categorias].sort().join(", "))}</span>`, row.total, row.urgentes]));
}

async function loadQueries() {
  const id = ++state.queryId;
  const block = $("#query-block").value;
  const data = await api(`/api/consultas?${new URLSearchParams({ bloco: block })}`);
  if (id !== state.queryId || !state.connected) return;
  $("#query-results").innerHTML = data.consultas.map((query, index) => `<article class="card query-card"><div class="query-card-top"><span class="query-number">CONSULTA 0${index + 1}</span><span class="query-type">${escapeHTML(query.tipo)}</span></div><h2>${escapeHTML(query.titulo)}</h2><p class="query-description">${escapeHTML(query.descricao)}</p><div class="operator-list">${query.operadores.map(operator => `<span class="operator">${escapeHTML(operator)}</span>`).join("")}</div><div class="query-result">${queryVisual(query)}</div><details class="query-source"><summary>Ver consulta executada no MongoDB</summary><pre>${escapeHTML(JSON.stringify(query.consulta, null, 2))}</pre></details></article>`).join("");
  // Valores numéricos são aplicados por CSSOM, mantendo a política de scripts restrita.
  $$(".chart-fill").forEach(element => { element.style.width = `${Number(element.dataset.width)}%`; });
}

function currentView() { return Object.keys(viewHashes).find(view => viewHashes[view] === location.hash) || "overview"; }
function switchView(load = true) {
  state.view = currentView();
  $$(".view").forEach(element => element.hidden = element.id !== `view-${state.view}`);
  $$(".nav-link").forEach(element => {
    const selected = element.dataset.view === state.view;
    element.classList.toggle("active", selected);
    if (selected) element.setAttribute("aria-current", "page"); else element.removeAttribute("aria-current");
  });
  const labels = {
    overview: ["Visão geral", "GESTÃO COLABORATIVA", "Um campus cuidado por todos", "Problemas visíveis. Soluções em movimento. Acompanhe o que acontece por aqui."],
    occurrences: ["Ocorrências", "DA IDENTIFICAÇÃO À SOLUÇÃO", "Cada registro faz a diferença", "Encontre ocorrências, acompanhe o atendimento e mantenha a comunidade informada."],
    queries: ["Consultas e indicadores", "DADOS QUE ORIENTAM O CUIDADO", "Entender para transformar", "Explore os dados reais do campus e veja as consultas que dão vida aos indicadores."]
  };
  const [breadcrumb, eyebrow, title, description] = labels[state.view];
  $("#breadcrumb-current").textContent = breadcrumb;
  $("#page-eyebrow").textContent = eyebrow;
  $("#page-title").innerHTML = `${escapeHTML(title)}<span>.</span>`;
  $("#page-description").textContent = description;
  if (load && state.connected) refreshAll().catch(report);
}

function selectBlock(block) {
  $("#filter-form").reset();
  $("#filter-block").value = block;
  state.page = 1;
  if (location.hash === "#ocorrencias") loadList().catch(report); else location.hash = "ocorrencias";
}

function prepareForm() {
  $("#occurrence-form").reset();
  $("#form-error").hidden = true;
  $("#form-error").textContent = "";
  $("#history-list").replaceChildren();
  $("#photo-preview").replaceChildren();
  $("#history-section").hidden = true;
  $("#delete-occurrence").hidden = true;
  $("#save-occurrence").disabled = false;
  state.editDoc = null;
}

async function openNew() {
  // Até a abertura do formulário confirma que o banco continua disponível.
  await api("/api/status");
  prepareForm();
  $("#dialog-title").textContent = "Nova ocorrência";
  $("#dialog-eyebrow").textContent = "VAMOS CUIDAR DO CAMPUS";
  $("#save-occurrence").innerHTML = `Cadastrar ocorrência${icon("arrow")}`;
  $("#occurrence-dialog").showModal();
}

function renderPhotos(photos) {
  const container = $("#photo-preview");
  container.replaceChildren();
  photos.forEach(url => {
    // Defesa adicional para documentos que tenham sido editados pelo Compass.
    try { if (!["http:", "https:"].includes(new URL(url).protocol)) return; } catch { return; }
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    const image = document.createElement("img");
    image.src = url;
    image.alt = "Foto anexada à ocorrência. Abrir em nova aba.";
    image.loading = "lazy";
    image.referrerPolicy = "no-referrer";
    image.addEventListener("error", () => { link.textContent = "Foto indisponível · abrir link"; link.className = "photo-error"; });
    link.append(image);
    container.append(link);
  });
}

async function openOccurrence(id) {
  const documentData = await api(`/api/ocorrencias/${encodeURIComponent(id)}`);
  if (!state.connected) return;
  prepareForm();
  state.editDoc = documentData;
  const form = $("#occurrence-form");
  const fields = { ...documentData, ...documentData.localizacao, ...documentData.solicitante, tags: documentData.tags.join(", "), fotos: documentData.fotos.join("\n") };
  ["titulo", "descricao", "categoria", "prioridade", "status", "responsavel", "bloco", "sala", "andar", "nome", "email", "tags", "fotos", "custo_estimado"].forEach(name => form.elements.namedItem(name).value = fields[name]);
  form.elements.namedItem("acessibilidade").checked = documentData.acessibilidade;
  $("#dialog-title").textContent = "Acompanhar ocorrência";
  $("#dialog-eyebrow").textContent = `BLOCO ${documentData.localizacao.bloco} · ${documentData.categoria}`;
  $("#save-occurrence").innerHTML = `Salvar alterações${icon("check")}`;
  $("#delete-occurrence").hidden = false;
  $("#history-section").hidden = false;
  $("#history-list").innerHTML = documentData.historico.map(event => `<li><div><strong>${escapeHTML(statusLabels[event.status] || event.status)}</strong><time datetime="${escapeHTML(event.data)}">${friendlyDate(event.data, true)}</time><small>${escapeHTML(event.observacao)}</small></div></li>`).join("");
  $("#record-meta").textContent = `ID: ${documentData._id} · ${documentData.demonstracao ? "Registro fictício de demonstração" : "Registro da comunidade"} · Atualizado em ${friendlyDate(documentData.atualizado_em, true)}`;
  renderPhotos(documentData.fotos);
  $("#occurrence-dialog").showModal();
}

function formPayload() {
  const form = new FormData($("#occurrence-form"));
  return {
    titulo: form.get("titulo"), descricao: form.get("descricao"), categoria: form.get("categoria"),
    prioridade: Number(form.get("prioridade")), status: form.get("status"), responsavel: form.get("responsavel"),
    localizacao: { bloco: form.get("bloco"), sala: form.get("sala"), andar: Number(form.get("andar")) },
    solicitante: { nome: form.get("nome"), email: form.get("email") },
    custo_estimado: Number(form.get("custo_estimado") || 0), acessibilidade: form.has("acessibilidade"),
    tags: form.get("tags").split(",").map(value => value.trim()).filter(Boolean),
    fotos: form.get("fotos").split(/\r?\n/).map(value => value.trim()).filter(Boolean),
    ...(state.editDoc ? { versao: state.editDoc.atualizado_em } : {})
  };
}

async function saveOccurrence(event) {
  event.preventDefault();
  if (state.saving) return;
  const editing = Boolean(state.editDoc);
  const id = state.editDoc?._id;
  state.saving = true;
  $("#save-occurrence").disabled = true;
  $("#form-error").hidden = true;
  try {
    await api(`/api/ocorrencias${id ? `/${id}` : ""}`, { method: editing ? "PUT" : "POST", body: JSON.stringify(formPayload()) });
    $("#occurrence-dialog").close();
    state.editDoc = null;
    await refreshAll();
    if (state.connected) toast(editing ? "Ocorrência atualizada. Mais um passo no cuidado do campus!" : "Ocorrência registrada. Obrigado por cuidar do campus!");
  } catch (error) {
    if (!error.silent) {
      $("#form-error").textContent = error.message;
      $("#form-error").hidden = false;
      $("#form-error").scrollIntoView({ block: "center", behavior: "smooth" });
    }
  } finally {
    state.saving = false;
    $("#save-occurrence").disabled = false;
  }
}

async function promptDelete() {
  if (!state.editDoc || state.saving) return;
  await api("/api/status");
  $("#delete-description").textContent = state.editDoc.titulo;
  $("#delete-dialog").showModal();
}
async function deleteOccurrence() {
  if (!state.editDoc || state.saving) return;
  state.saving = true;
  $("#confirm-delete").disabled = true;
  try {
    await api(`/api/ocorrencias/${state.editDoc._id}`, { method: "DELETE" });
    $("#delete-dialog").close();
    $("#occurrence-dialog").close();
    state.editDoc = null;
    await refreshAll();
    if (state.connected) toast("Ocorrência excluída do MongoDB.");
  } catch (error) { report(error); }
  finally { state.saving = false; $("#confirm-delete").disabled = false; }
}

async function exportJSON(button) {
  button.disabled = true;
  try {
    const response = await api("/api/exportar", { raw: true });
    const epoch = state.epoch;
    const blob = await response.blob();
    if (!state.connected || epoch !== state.epoch) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "resolve-campus-ocorrencias.json";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("JSON exportado com os registros atuais do MongoDB.");
  } catch (error) { report(error); }
  finally { button.disabled = false; }
}

document.addEventListener("click", event => {
  const target = event.target.closest("button, a");
  if (!target) return;
  if (target.dataset.action === "new") openNew().catch(report);
  if (target.dataset.open) openOccurrence(target.dataset.open).catch(report);
  if (target.dataset.block) selectBlock(target.dataset.block);
  if (target.dataset.close && !state.saving) document.getElementById(target.dataset.close).close();
  if (target.classList.contains("export-button")) exportJSON(target);
});

$("#retry-connection").addEventListener("click", checkConnection);
$("#occurrence-form").addEventListener("submit", saveOccurrence);
$("#delete-occurrence").addEventListener("click", () => promptDelete().catch(report));
$("#confirm-delete").addEventListener("click", deleteOccurrence);
$$('dialog').forEach(dialog => dialog.addEventListener("cancel", event => { if (state.saving) event.preventDefault(); }));
$("#occurrence-dialog").addEventListener("close", () => { if (!state.saving) state.editDoc = null; });
$("#filter-form").addEventListener("submit", event => { event.preventDefault(); state.page = 1; loadList().catch(report); });
let searchTimer;
$("#filter-search").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { if (state.connected) { state.page = 1; loadList().catch(report); } }, 300); });
$("#filter-form").addEventListener("change", event => { if (event.target.matches("select")) { state.page = 1; loadList().catch(report); } });
$("#clear-filters").addEventListener("click", () => { clearTimeout(searchTimer); $("#filter-form").reset(); state.page = 1; loadList().catch(report); });
$("#previous-page").addEventListener("click", () => { if (state.page > 1) { state.page -= 1; loadList().catch(report); } });
$("#next-page").addEventListener("click", () => { if (state.page < state.pages) { state.page += 1; loadList().catch(report); } });
$("#query-block").addEventListener("change", () => loadQueries().catch(report));
window.addEventListener("hashchange", () => switchView());
window.addEventListener("focus", () => { checkConnection(); });
document.addEventListener("visibilitychange", () => { if (!document.hidden) checkConnection(); });
switchView(false);
checkConnection();
// Não guarda documentos em localStorage, IndexedDB, Service Worker ou arquivos locais.
setInterval(() => { if (!document.hidden) checkConnection(); }, 8000);
