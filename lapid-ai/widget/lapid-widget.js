/*!
 * Lapid.ai — widget de suporte.
 * <script src="https://SEU-LAPID/widget.js" data-key="lpd_..." defer></script>
 */
(function () {
  "use strict";
  var script = document.currentScript;
  if (!script) return;
  var KEY = script.getAttribute("data-key");
  if (!KEY) { console.warn("[Lapid] atributo data-key ausente."); return; }
  var API = (script.getAttribute("data-api") || new URL(script.src, location.href).origin).replace(/\/$/, "");
  var HIST = "lapid:history:" + KEY;
  var LABELS = { new: "Nova", in_review: "Em análise", resolved: "Resolvida", dismissed: "Descartada" };

  var CSS = [
    ":host{all:initial}",
    "*{box-sizing:border-box;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}",
    ".fab{position:fixed;right:20px;bottom:20px;z-index:2147483000;display:flex;align-items:center;gap:10px;min-height:46px;border:1px solid #2a396f;cursor:pointer;color:#eef3ff;background:#0b1127;border-radius:999px;padding:0 20px 0 16px;font-size:14px;font-weight:600;box-shadow:0 10px 30px rgba(5,8,22,.45)}",
    ".fab:hover{border-color:#4fe3f5}.fab i{width:8px;height:8px;border-radius:50%;background:#4fe3f5;box-shadow:0 0 10px #4fe3f5}",
    ".panel{position:fixed;right:20px;bottom:78px;z-index:2147483000;width:min(380px,calc(100vw - 24px));max-height:min(580px,calc(100vh - 100px));display:none;flex-direction:column;background:#0b1127;color:#eef3ff;border:1px solid #1b2650;border-radius:22px;box-shadow:0 24px 70px rgba(5,8,22,.6);overflow:hidden}",
    ".panel.open{display:flex}",
    ".head{display:flex;justify-content:space-between;align-items:center;padding:16px 18px 6px;font-weight:700;font-size:16px;letter-spacing:-.01em}",
    ".dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#4fe3f5;margin-right:9px;box-shadow:0 0 10px #4fe3f5}",
    ".x{background:none;border:0;color:#8fa0c8;cursor:pointer;font-size:22px;line-height:1;min-width:36px;min-height:36px}.x:hover{color:#fff}",
    ".tabs{display:flex;gap:2px;padding:0 12px;border-bottom:1px solid #1b2650}",
    ".tab{flex:1;background:none;border:0;border-bottom:2px solid transparent;color:#8fa0c8;padding:12px 8px;font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-1px}",
    ".tab[aria-selected=true]{color:#eef3ff;border-color:#4fe3f5}",
    ".body{padding:18px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;font-size:14px}",
    "label{font-size:13px;color:#8fa0c8}",
    "textarea,input{width:100%;background:#050816;color:#eef3ff;border:1px solid #2a396f;border-radius:10px;padding:11px 13px;font-size:14px}",
    "textarea{min-height:112px;resize:vertical}",
    "textarea:focus,input:focus{outline:none;border-color:#4fe3f5;box-shadow:0 0 0 3px rgba(79,227,245,.16)}",
    ".btn{border:0;border-radius:12px;background:#3560f0;color:#fff;min-height:44px;font-size:14px;font-weight:600;cursor:pointer}",
    ".btn:hover{background:#2c4fd0}.btn[disabled]{opacity:.6;cursor:wait}.btn.ghost{background:transparent;border:1px solid #2a396f}",
    ".err{color:#ff7a8a;font-size:13px}.hint{color:#8fa0c8;font-size:12px}",
    ".ok{text-align:center;display:flex;flex-direction:column;gap:10px;padding:10px 0}",
    ".proto{font-family:ui-monospace,Consolas,monospace;font-size:19px;color:#4fe3f5;user-select:all}",
    ".item{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:11px 0;border-bottom:1px solid #1b2650}",
    ".item .proto{font-size:13px}.st{font-size:12px;color:#8fa0c8;white-space:nowrap}",
    ".empty{color:#8fa0c8;text-align:center;padding:20px 0}",
    "button:focus-visible{outline:2px solid #4fe3f5;outline-offset:2px}",
    "@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}"
  ].join("");

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function history() { try { return JSON.parse(localStorage.getItem(HIST)) || []; } catch (e) { return []; } }
  function remember(protocol, createdAt) {
    var list = history().filter(function (h) { return h.protocol !== protocol; });
    list.unshift({ protocol: protocol, createdAt: createdAt });
    try { localStorage.setItem(HIST, JSON.stringify(list.slice(0, 20))); } catch (e) {}
  }
  function call(path, opts) {
    opts = opts || {};
    opts.headers = Object.assign({ "X-Lapid-Key": KEY }, opts.headers || {});
    return fetch(API + path, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (b) { return { ok: r.ok, status: r.status, body: b }; });
    });
  }

  var host = document.createElement("div");
  var root = host.attachShadow({ mode: "open" });
  var style = el("style"); style.textContent = CSS; root.appendChild(style);

  var fab = el("button", "fab");
  fab.type = "button"; fab.setAttribute("aria-expanded", "false"); fab.setAttribute("aria-controls", "lapid-panel");
  fab.appendChild(el("i"));
  fab.appendChild(document.createTextNode("Suporte"));

  var panel = el("div", "panel"); panel.id = "lapid-panel"; panel.setAttribute("role", "dialog"); panel.setAttribute("aria-label", "Suporte");
  var head = el("div", "head");
  var title = el("span"); title.appendChild(el("span", "dot")); title.appendChild(document.createTextNode("Suporte"));
  var close = el("button", "x", "×"); close.type = "button"; close.setAttribute("aria-label", "Fechar");
  head.appendChild(title); head.appendChild(close);

  var tabs = el("div", "tabs"); tabs.setAttribute("role", "tablist");
  var tabNew = el("button", "tab", "Relatar problema"), tabList = el("button", "tab", "Minhas solicitações");
  [tabNew, tabList].forEach(function (t) { t.type = "button"; t.setAttribute("role", "tab"); tabs.appendChild(t); });
  var body = el("div", "body");
  panel.appendChild(head); panel.appendChild(tabs); panel.appendChild(body);
  root.appendChild(panel); root.appendChild(fab);

  function select(which) {
    tabNew.setAttribute("aria-selected", which === "new");
    tabList.setAttribute("aria-selected", which === "list");
    body.textContent = "";
    which === "new" ? renderForm() : renderList();
  }

  function renderForm() {
    var l1 = el("label", null, "O que aconteceu?"); l1.setAttribute("for", "lp-desc");
    var desc = el("textarea"); desc.id = "lp-desc"; desc.maxLength = 2000; desc.required = true;
    desc.placeholder = "Ex.: ao clicar em “Cadastrar”, a página recarrega e nada acontece.";
    var l2 = el("label", null, "Seu e-mail (opcional)"); l2.setAttribute("for", "lp-mail");
    var mail = el("input"); mail.id = "lp-mail"; mail.type = "email"; mail.maxLength = 254; mail.autocomplete = "email";
    var err = el("div", "err"); err.setAttribute("role", "alert");
    var send = el("button", "btn", "Enviar relato"); send.type = "button";
    var hint = el("div", "hint", "Enviamos também o endereço desta página.");
    [l1, desc, l2, mail, err, send, hint].forEach(function (n) { body.appendChild(n); });
    setTimeout(function () { desc.focus(); }, 30);

    send.addEventListener("click", function () {
      err.textContent = "";
      if (desc.value.trim().length < 10) { err.textContent = "Descreva o problema com pelo menos 10 caracteres."; desc.focus(); return; }
      send.disabled = true; send.textContent = "Enviando…";
      call("/api/support/complaints", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: desc.value,
          contact_email: mail.value,
          page_url: location.origin + location.pathname
        })
      }).then(function (r) {
        if (r.ok) { remember(r.body.protocol, r.body.created_at); return renderDone(r.body.protocol); }
        var f = r.body.fields && Object.keys(r.body.fields)[0];
        err.textContent = (f && r.body.fields[f]) || r.body.message || "Não foi possível enviar. Tente novamente.";
        send.disabled = false; send.textContent = "Enviar relato";
      }).catch(function () {
        err.textContent = "Sem conexão com o suporte. Tente novamente.";
        send.disabled = false; send.textContent = "Enviar relato";
      });
    });
  }

  function renderDone(protocol) {
    body.textContent = "";
    var box = el("div", "ok");
    box.appendChild(el("strong", null, "Relato enviado"));
    box.appendChild(el("div", "proto", protocol));
    box.appendChild(el("div", "hint", "Guarde este protocolo para acompanhar a solicitação."));
    var again = el("button", "btn ghost", "Enviar outro relato"); again.type = "button";
    again.addEventListener("click", function () { select("new"); });
    box.appendChild(again); body.appendChild(box);
  }

  function renderList() {
    var items = history().slice(0, 10);
    if (!items.length) { body.appendChild(el("div", "empty", "Você ainda não enviou nenhum relato neste navegador.")); return; }
    items.forEach(function (h) {
      var row = el("div", "item"), st = el("span", "st", "…");
      row.appendChild(el("span", "proto", h.protocol)); row.appendChild(st); body.appendChild(row);
      call("/api/support/complaints/" + encodeURIComponent(h.protocol)).then(function (r) {
        st.textContent = r.ok ? (LABELS[r.body.status] || r.body.status) : "indisponível";
      }).catch(function () { st.textContent = "indisponível"; });
    });
  }

  function toggle(open) {
    panel.classList.toggle("open", open);
    fab.setAttribute("aria-expanded", String(open));
    if (open) select("new"); else fab.focus();
  }
  fab.addEventListener("click", function () { toggle(!panel.classList.contains("open")); });
  close.addEventListener("click", function () { toggle(false); });
  tabNew.addEventListener("click", function () { select("new"); });
  tabList.addEventListener("click", function () { select("list"); });
  root.addEventListener("keydown", function (e) { if (e.key === "Escape") toggle(false); });


  // ---------- Monitoramento de erros do site (desligue com data-monitor="false") ----------
  if (script.getAttribute("data-monitor") !== "false") {
    var seen = {}, budget = 5; // no máximo 5 erros distintos por carregamento de página
    var report = function (type, message, stack) {
      message = String(message || "").slice(0, 500);
      var sig = type + "|" + message;
      if (!message || seen[sig] || budget <= 0) return;
      seen[sig] = 1; budget--;
      var clean = String(stack || "").replace(/\?[^\s:)]*/g, "").slice(0, 6000); // remove query strings (podem ter tokens)
      try {
        fetch(API + "/api/monitor/errors", {
          method: "POST", keepalive: true,
          headers: { "Content-Type": "application/json", "X-Lapid-Key": KEY },
          body: JSON.stringify({ type: String(type || "Error").slice(0, 120), message: message, stack: clean, page_url: location.origin + location.pathname })
        }).catch(function () {});
      } catch (e) {}
    };
    window.addEventListener("error", function (ev) {
      var f = ev.filename || "";
      if (!f || /^(chrome|moz|safari|safari-web)-extension:/.test(f)) return; // ruído de extensões
      if (/^Script error\.?$/.test(ev.message || "")) return; // erro de outra origem, sem detalhes úteis
      report((ev.error && ev.error.name) || "Error", ev.message, ev.error && ev.error.stack);
    });
    window.addEventListener("unhandledrejection", function (ev) {
      var r = ev.reason;
      report((r && r.name) || "UnhandledRejection", (r && r.message) || String(r), r && r.stack);
    });
  }

  document.body.appendChild(host);
})();
