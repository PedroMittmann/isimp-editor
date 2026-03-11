const APP = {
  container: null,
  currentUrl: "/dashboard-content",
  pendingRequest: null,
  moduleCleanup: null,
  currentModuleRoot: null,
};

const ISIMP = {
  campoIndex: null,
  campoAtual: null,
  timerBusca: null,
  abortBusca: null,
  tempoLoading: 300,
};

document.addEventListener("DOMContentLoaded", () => {
  APP.container = document.getElementById("app-content");
  if (!APP.container) return;

  bindShellEvents();

  // Se abriu a aplicação com hash, carrega o módulo do hash.
  // Caso contrário, aproveita o conteúdo já renderizado pelo servidor.
  if (window.location.hash) {
    loadModule(getUrlFromHash());
  } else {
    APP.currentUrl = "/dashboard-content";
    hydrateCurrentView();
  }

  window.addEventListener("hashchange", () => {
    loadModule(getUrlFromHash());
  });
});

/* =========================
   SHELL / NAVEGAÇÃO
========================= */

function bindShellEvents() {
  // Delegação opcional para futuro uso com data-module-link
  document.body.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-module-link]");
    if (!trigger) return;

    event.preventDefault();
    abrirModulo(trigger.dataset.moduleLink);
  });
}

function getUrlFromHash() {
  const hash = window.location.hash || "#/dashboard-content";

  if (hash === "#" || hash === "#/" || hash === "") {
    return "/dashboard-content";
  }

  return hash.slice(1);
}

function abrirModulo(url) {
  const targetHash = `#${url}`;

  if (window.location.hash === targetHash) {
    loadModule(url);
    return;
  }

  window.location.hash = targetHash;
}

async function loadModule(url, options = {}) {
  const method = options.method || "GET";
  const body = options.body || null;
  const loaderText = options.loaderText || "Carregando módulo...";

  cleanupCurrentModule();
  abortPendingRequest();
  setMainLoader(loaderText);

  const controller = new AbortController();
  APP.pendingRequest = controller;

  try {
    const response = await fetch(url, {
      method,
      body,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const html = await response.text();

    APP.container.innerHTML = html;
    APP.currentUrl = url;

    hydrateCurrentView();
    updateActiveMenu(url);
  } catch (error) {
    if (error.name === "AbortError") return;

    APP.container.innerHTML = `
      <div class="module-error">
        <h2>Erro ao carregar módulo</h2>
        <p>Não foi possível carregar o conteúdo solicitado.</p>
      </div>
    `;
    console.error(error);
  } finally {
    if (APP.pendingRequest === controller) {
      APP.pendingRequest = null;
    }
  }
}

function abortPendingRequest() {
  if (APP.pendingRequest) {
    APP.pendingRequest.abort();
    APP.pendingRequest = null;
  }
}

function setMainLoader(text) {
  APP.container.innerHTML = `
    <div class="module-loader">
      <div class="loader-spinner"></div>
      <p>${text}</p>
    </div>
  `;
}

function updateActiveMenu(url) {
  document.querySelectorAll(".menu-item").forEach((item) => {
    const itemUrl = item.dataset.moduleLink;
    if (!itemUrl) return;

    item.classList.toggle("active", itemUrl === url);
  });
}

/* =========================
   HIDRATAÇÃO DE MÓDULO
========================= */

function hydrateCurrentView() {
  APP.currentModuleRoot = APP.container.firstElementChild || APP.container;

  bindAjaxModuleForms(APP.currentModuleRoot);
  initModuleByUrl(APP.currentUrl, APP.currentModuleRoot);
}

function cleanupCurrentModule() {
  if (typeof APP.moduleCleanup === "function") {
    try {
      APP.moduleCleanup();
    } catch (error) {
      console.warn("Erro ao limpar módulo:", error);
    }
  }

  APP.moduleCleanup = null;
  APP.currentModuleRoot = null;
}

function bindAjaxModuleForms(root) {
  const forms = root.querySelectorAll("[data-ajax-module-form]");

  forms.forEach((form) => {
    if (form.dataset.bound === "1") return;

    form.dataset.bound = "1";

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      await loadModule(form.action || APP.currentUrl, {
        method: (form.method || "POST").toUpperCase(),
        body: new FormData(form),
        loaderText: "Processando...",
      });
    });
  });
}

function initModuleByUrl(url, root) {
  if (url.startsWith("/isimp")) {
    initISimpModule(root);
    return;
  }

  // fallback: sem JS específico
  APP.moduleCleanup = null;
}

/* =========================
   MÓDULO i-SIMP
========================= */

function initISimpModule(root) {
  addSearchChecks(root);

  const inputPesquisa = root.querySelector("#pesquisa");

  const onInput = () => {
    clearTimeout(ISIMP.timerBusca);
    ISIMP.timerBusca = setTimeout(() => {
      filtrarTabela();
    }, 300);
  };

  if (inputPesquisa) {
    inputPesquisa.addEventListener("input", onInput);
  }

  // expõe para os botões inline atuais
  window.verDetalhes = verDetalhes;
  window.fecharModal = fecharModal;
  window.filtrarTabela = filtrarTabela;

  APP.moduleCleanup = () => {
    clearTimeout(ISIMP.timerBusca);

    if (ISIMP.abortBusca) {
      ISIMP.abortBusca.abort();
      ISIMP.abortBusca = null;
    }

    if (inputPesquisa) {
      inputPesquisa.removeEventListener("input", onInput);
    }

    delete window.verDetalhes;
    delete window.fecharModal;
    delete window.filtrarTabela;
  };
}

function addSearchChecks(root) {
  const camposComPesquisa = [
    "AGENTE REGULADO INFORMANTE",
    "CÓDIGO DA OPERAÇÃO",
    "CÓDIGO DO MODAL",
    "CÓDIGO DO PRODUTO OPERADO",
  ];

  root.querySelectorAll(".nomeCampo").forEach((el) => {
    const nome = el.innerText.trim();

    if (!camposComPesquisa.includes(nome)) return;

    el.innerHTML = `
      ${nome}
      <span class="check-dev" title="Consulta disponível">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 
          10-4.48 10-10S17.52 2 12 2zm-1.2 14.2l-3.5-3.5 
          1.4-1.4 2.1 2.1 5.1-5.1 1.4 1.4-6.5 6.5z"/>
        </svg>
      </span>
    `;
  });
}

function verDetalhes(campo, index) {
  ISIMP.campoIndex = index;
  ISIMP.campoAtual = campo;

  const modal = APP.currentModuleRoot.querySelector("#modal");
  const input = APP.currentModuleRoot.querySelector("#pesquisa");

  if (!modal || !input) return;

  modal.style.display = "flex";
  input.value = "";

  mostrarLoading();

  fetch(`/detalhes/${encodeURIComponent(campo)}`)
    .then((res) => res.json())
    .then((data) => {
      if (data.status === "dev") {
        mostrarEmDesenvolvimento(campo);
        return;
      }

      if (!data.dados || data.dados.length === 0) {
        mostrarNenhumResultado();
        return;
      }

      renderTabela(data.dados);
    })
    .catch(() => {
      mostrarErro();
    });

  setTimeout(() => input.focus(), 80);
}

function mostrarLoading() {
  const conteudo = APP.currentModuleRoot.querySelector("#conteudo");
  if (!conteudo) return;

  conteudo.innerHTML = `
    <div style="text-align:center;padding:20px">
      <div style="
        width:35px;
        height:35px;
        border:4px solid #eee;
        border-top:4px solid #2f6db5;
        border-radius:50%;
        margin:auto;
        animation:spin 1s linear infinite"></div>

      <div style="margin-top:10px;color:#666">
        Carregando códigos...
      </div>
    </div>
  `;
}

function mostrarNenhumResultado() {
  const conteudo = APP.currentModuleRoot.querySelector("#conteudo");
  if (!conteudo) return;

  conteudo.innerHTML = `
    <div style="text-align:center;padding:20px;color:#888">
      ⚠️ Nenhum código encontrado
    </div>
  `;
}

function mostrarErro() {
  const conteudo = APP.currentModuleRoot.querySelector("#conteudo");
  if (!conteudo) return;

  conteudo.innerHTML = `
    <div style="text-align:center;padding:20px;color:#888">
      Erro ao carregar dados
    </div>
  `;
}

function mostrarEmDesenvolvimento(campo) {
  const conteudo = APP.currentModuleRoot.querySelector("#conteudo");
  if (!conteudo) return;

  conteudo.innerHTML = `
    <div style="text-align:center;padding:30px;color:#666">
      <div style="font-size:30px;margin-bottom:10px">🚧</div>
      <div style="font-size:16px;margin-bottom:6px">
        Detalhamento em desenvolvimento
      </div>
      <div style="font-size:13px;color:#888">
        O campo "<b>${campo}</b>" ainda não possui tabela de consulta.
      </div>
    </div>
  `;
}

function renderTabela(dados) {
  const conteudo = APP.currentModuleRoot.querySelector("#conteudo");
  if (!conteudo) return;

  if (!dados || dados.length === 0) {
    mostrarNenhumResultado();
    return;
  }

  const colunas = Object.keys(dados[0]);

  let html = "<table><thead><tr>";

  colunas.forEach((coluna) => {
    html += `<th>${coluna.replaceAll("_", " ").toUpperCase()}</th>`;
  });

  html += "</tr></thead><tbody>";

  dados.forEach((item) => {
    const codigo = item.codigo || Object.values(item)[0] || "";

    html += `<tr onclick="selecionarCodigo('${String(codigo).replaceAll("'", "")}')">`;

    colunas.forEach((coluna) => {
      html += `<td>${item[coluna] || ""}</td>`;
    });

    html += "</tr>";
  });

  html += "</tbody></table>";

  conteudo.innerHTML = html;
}

function selecionarCodigo(codigo) {
  const campo = APP.currentModuleRoot.querySelector(
    `[name="campo${ISIMP.campoIndex}"]`
  );

  if (campo) {
    campo.value = codigo;
  }

  fecharModal();
}

function fecharModal() {
  const modal = APP.currentModuleRoot.querySelector("#modal");
  if (!modal) return;

  modal.style.display = "none";
}

function filtrarTabela() {
  if (!ISIMP.campoAtual) return;

  const input = APP.currentModuleRoot.querySelector("#pesquisa");
  if (!input) return;

  const termo = input.value.trim();

  if (termo.length < 2) {
    const conteudo = APP.currentModuleRoot.querySelector("#conteudo");
    if (conteudo) conteudo.innerHTML = "";
    return;
  }

  if (ISIMP.abortBusca) {
    ISIMP.abortBusca.abort();
  }

  ISIMP.abortBusca = new AbortController();

  mostrarLoading();

  fetch(
    `/buscar?campo=${encodeURIComponent(ISIMP.campoAtual)}&termo=${encodeURIComponent(termo)}`,
    { signal: ISIMP.abortBusca.signal }
  )
    .then((res) => res.json())
    .then((data) => {
      if (!data.dados || data.dados.length === 0) {
        mostrarNenhumResultado();
        return;
      }

      renderTabela(data.dados);
    })
    .catch((err) => {
      if (err.name === "AbortError") return;
      mostrarErro();
    });
}

/* =========================
   UI GERAL
========================= */

function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.classList.toggle("collapsed");
}

function toggleTheme() {
  document.body.classList.toggle("light");

  localStorage.setItem(
    "theme",
    document.body.classList.contains("light") ? "light" : "dark"
  );
}

if (localStorage.getItem("theme") === "light") {
  document.body.classList.add("light");
}

window.addEventListener("click", (event) => {
  const modal = APP.currentModuleRoot?.querySelector?.("#modal");
  if (!modal) return;

  if (event.target === modal) {
    fecharModal();
  }
});

// expõe no escopo global para os onclicks existentes
window.abrirModulo = abrirModulo;
window.selecionarCodigo = selecionarCodigo;
window.toggleSidebar = toggleSidebar;
window.toggleTheme = toggleTheme;