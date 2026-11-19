// Site de agendamento: conversa com a API usando fetch, sem frameworks.

const $ = (seletor) => document.querySelector(seletor);

const estado = {
  info: null,
  servicos: [],
  servico: null, // serviço escolhido
  dia: null, // "AAAA-MM-DD"
  horario: null, // "HH:MM"
  token: lerToken(),
};

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const diaSemanaCurto = new Intl.DateTimeFormat("pt-BR", { weekday: "short" });
const dataLonga = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" });

// ------------------------------------------------------------------ utilitários

async function api(caminho, opcoes = {}) {
  const resposta = await fetch(caminho, opcoes);
  const corpo = resposta.status === 204 ? null : await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const erro = new Error(mensagemDeErro(corpo, resposta.status));
    erro.status = resposta.status;
    throw erro;
  }
  return corpo;
}

function mensagemDeErro(corpo, status) {
  const detalhe = corpo && corpo.detail;
  if (typeof detalhe === "string") return detalhe;
  if (Array.isArray(detalhe) && detalhe.length) {
    // Erros de validação (422) vêm como lista; mostramos o primeiro
    return String(detalhe[0].msg || "Dados inválidos").replace(/^Value error, /, "");
  }
  return `Não foi possível concluir (erro ${status}). Tente de novo.`;
}

// Datas locais no formato da API, sem passar por UTC
function paraISO(data) {
  const p = (n) => String(n).padStart(2, "0");
  return `${data.getFullYear()}-${p(data.getMonth() + 1)}-${p(data.getDate())}`;
}

function deISO(texto) {
  const [a, m, d] = texto.split("-").map(Number);
  return new Date(a, m - 1, d);
}

// JS: 0 = domingo. API: 0 = segunda.
const diaDaSemanaApi = (data) => (data.getDay() + 6) % 7;

function formatarTelefone(valor) {
  const d = valor.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d.length ? `(${d}` : "";
  const meio = d.length === 11 ? 7 : 6;
  if (d.length <= meio) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, meio)}-${d.slice(meio)}`;
}

function lerToken() {
  try { return sessionStorage.getItem("token"); } catch { return null; }
}

function salvarToken(token) {
  estado.token = token;
  try {
    if (token) sessionStorage.setItem("token", token);
    else sessionStorage.removeItem("token");
  } catch { /* navegação privada: o login vale só enquanto a página estiver aberta */ }
}

function mostrarErro(elemento, mensagem) {
  elemento.textContent = mensagem || "";
  elemento.hidden = !mensagem;
}

// Cria um botão de escolha (role="radio") dentro de um grupo
function botaoEscolha(classe, conteudoHTML, aoEscolher) {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.className = `escolha ${classe}`;
  botao.setAttribute("role", "radio");
  botao.setAttribute("aria-checked", "false");
  botao.innerHTML = conteudoHTML;
  botao.addEventListener("click", () => {
    for (const irmao of botao.parentElement.children) irmao.setAttribute("aria-checked", "false");
    botao.setAttribute("aria-checked", "true");
    aoEscolher();
  });
  return botao;
}

const escapar = (texto) =>
  String(texto).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// Mostra só os passos cujos requisitos já foram escolhidos
function atualizarPassos() {
  const feito = { servico: !!estado.servico, dia: !!estado.dia, horario: !!estado.horario };
  for (const passo of document.querySelectorAll("[data-depende]")) {
    passo.hidden = !feito[passo.dataset.depende];
  }
  $("#botao-agendar").textContent = estado.horario ? `Agendar às ${estado.horario}` : "Agendar";
}

// ------------------------------------------------------------------ agendamento (cliente)

function desenharServicos() {
  const lista = $("#lista-servicos");
  lista.innerHTML = "";
  if (!estado.servicos.length) {
    lista.innerHTML = '<p class="vazio">Nenhum serviço cadastrado ainda.</p>';
    return;
  }
  for (const s of estado.servicos) {
    const html = `
      <span class="servico-nome">${escapar(s.nome)}</span>
      <span class="servico-preco">${moeda.format(Number(s.preco))}</span>
      <span class="servico-duracao">${s.duracao_minutos} min</span>`;
    lista.append(
      botaoEscolha("servico", html, () => {
        estado.servico = s;
        estado.horario = null;
        if (estado.dia) carregarHorarios();
        atualizarPassos();
      })
    );
  }
}

function desenharDias() {
  const lista = $("#lista-dias");
  lista.innerHTML = "";
  const abertos = new Set(estado.info.dias_funcionamento);
  const hoje = new Date();
  for (let i = 0; i < 21 && lista.children.length < 14; i++) {
    const data = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() + i);
    if (!abertos.has(diaDaSemanaApi(data))) continue;
    const iso = paraISO(data);
    const rotulo = i === 0 ? "hoje" : diaSemanaCurto.format(data).replace(".", "");
    const botao = botaoEscolha(
      "dia",
      `<span class="dia-semana">${rotulo}</span><span class="dia-numero">${data.getDate()}</span>`,
      () => {
        estado.dia = iso;
        estado.horario = null;
        carregarHorarios();
        atualizarPassos();
      }
    );
    botao.setAttribute("aria-label", dataLonga.format(data));
    lista.append(botao);
  }
}

async function carregarHorarios() {
  const lista = $("#lista-horarios");
  const pedido = `${estado.dia}|${estado.servico.id}`;
  lista.dataset.pedido = pedido;
  lista.innerHTML = '<p class="carregando">Buscando horários livres…</p>';
  try {
    const r = await api(`/horarios-livres?data=${estado.dia}&servico_id=${estado.servico.id}`);
    if (lista.dataset.pedido !== pedido) return; // o usuário já trocou de dia ou serviço
    lista.innerHTML = "";
    if (!r.horarios.length) {
      lista.innerHTML = '<p class="vazio">Nenhum horário livre neste dia. Escolha outro dia.</p>';
      return;
    }
    for (const h of r.horarios) {
      lista.append(
        botaoEscolha("horario", h, () => {
          estado.horario = h;
          atualizarPassos();
          $("#form-agendar [name=nome]").focus({ preventScroll: true });
          $("#p4").scrollIntoView({ behavior: "smooth", block: "start" });
        })
      );
    }
  } catch (e) {
    lista.innerHTML = `<p class="vazio">${escapar(e.message)}</p>`;
  }
}

async function agendar(evento) {
  evento.preventDefault();
  const form = evento.target;
  const erro = $("#erro-agendar");
  const nome = form.nome.value.trim();
  const telefone = form.telefone.value.replace(/\D/g, "");

  if (nome.length < 2) return mostrarErro(erro, "Informe seu nome.");
  if (telefone.length < 10) return mostrarErro(erro, "Informe o telefone com DDD, por exemplo (11) 91234-5678.");
  mostrarErro(erro, "");

  const botao = $("#botao-agendar");
  botao.disabled = true;
  try {
    const ag = await api("/agendamentos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cliente_nome: nome,
        cliente_telefone: telefone,
        servico_id: estado.servico.id,
        inicio: `${estado.dia}T${estado.horario}:00`,
      }),
    });
    $("#c-servico").textContent = estado.servico.nome;
    $("#c-dia").textContent = dataLonga.format(deISO(estado.dia));
    $("#c-horario").textContent = `${ag.inicio.slice(11, 16)} às ${ag.fim.slice(11, 16)}`;
    $("#c-nome").textContent = ag.cliente_nome;
    $("#c-id").textContent = ag.id;
    $("#fluxo").hidden = true;
    $("#confirmacao").hidden = false;
    $("#confirmacao").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    mostrarErro(erro, e.message);
    if (e.status === 409) carregarHorarios(); // alguém pegou o horário antes: atualiza a lista
  } finally {
    botao.disabled = false;
  }
}

function novoAgendamento() {
  estado.horario = null;
  $("#confirmacao").hidden = true;
  $("#fluxo").hidden = false;
  carregarHorarios();
  atualizarPassos();
  $("#p3").scrollIntoView({ behavior: "smooth", block: "start" });
}

// ------------------------------------------------------------------ agenda (admin)

function mostrarPainel(logado) {
  $("#form-login").hidden = logado;
  $("#painel").hidden = !logado;
  if (logado) carregarAgenda();
}

async function entrar(evento) {
  evento.preventDefault();
  const form = evento.target;
  const erro = $("#erro-login");
  try {
    const corpo = new URLSearchParams({ username: form.usuario.value, password: form.senha.value });
    const r = await api("/auth/login", { method: "POST", body: corpo });
    salvarToken(r.access_token);
    mostrarErro(erro, "");
    form.senha.value = "";
    mostrarPainel(true);
  } catch (e) {
    mostrarErro(erro, e.message);
  }
}

function sair(mensagem) {
  salvarToken(null);
  mostrarPainel(false);
  mostrarErro($("#erro-login"), mensagem);
}

async function carregarAgenda() {
  const dia = $("#dia-agenda").value;
  const cancelados = $("#mostrar-cancelados").checked;
  const lista = $("#lista-agenda");
  const resumo = $("#resumo-dia");
  const pedido = `${dia}|${cancelados}`;
  lista.dataset.pedido = pedido;
  lista.innerHTML = "";
  resumo.textContent = "Carregando agenda…";
  try {
    const itens = await api(`/agendamentos?data=${dia}&incluir_cancelados=${cancelados}`, {
      headers: { Authorization: `Bearer ${estado.token}` },
    });
    if (lista.dataset.pedido !== pedido) return; // o usuário já trocou de dia: ignora esta resposta
    const porId = Object.fromEntries(estado.servicos.map((s) => [s.id, s]));
    const confirmados = itens.filter((a) => a.status === "confirmado");
    const previsto = confirmados.reduce((soma, a) => soma + Number(porId[a.servico_id]?.preco || 0), 0);

    resumo.textContent = confirmados.length
      ? `${confirmados.length} ${confirmados.length === 1 ? "atendimento" : "atendimentos"}, ${moeda.format(previsto)} previstos`
      : "Nenhum atendimento neste dia.";

    lista.innerHTML = "";
    for (const a of itens) {
      const cancelado = a.status === "cancelado";
      const servico = porId[a.servico_id]?.nome || "Serviço removido";
      const li = document.createElement("li");
      li.className = `item${cancelado ? " item-cancelado" : ""}`;
      li.innerHTML = `
        <span class="item-hora">${a.inicio.slice(11, 16)}<span class="item-fim">até ${a.fim.slice(11, 16)}</span></span>
        <span>
          <span class="item-cliente">${escapar(a.cliente_nome)}</span>
          <span class="item-detalhe">${escapar(servico)}, <span class="sem-quebra">${formatarTelefone(a.cliente_telefone)}</span></span>
        </span>`;
      if (cancelado) {
        li.insertAdjacentHTML("beforeend", '<span class="selo">Cancelado</span>');
      } else {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "botao-cancelar";
        botao.textContent = "Cancelar";
        botao.setAttribute("aria-label", `Cancelar o horário de ${a.cliente_nome} às ${a.inicio.slice(11, 16)}`);
        botao.addEventListener("click", () => cancelar(a));
        li.append(botao);
      }
      lista.append(li);
    }
  } catch (e) {
    if (e.status === 401) return sair("Sua sessão expirou. Entre de novo.");
    resumo.textContent = e.message;
  }
}

async function cancelar(agendamento) {
  const hora = agendamento.inicio.slice(11, 16);
  if (!confirm(`Cancelar o horário de ${agendamento.cliente_nome} às ${hora}?`)) return;
  try {
    await api(`/agendamentos/${agendamento.id}/cancelar`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${estado.token}` },
    });
    carregarAgenda();
  } catch (e) {
    if (e.status === 401) return sair("Sua sessão expirou. Entre de novo.");
    alert(e.message);
  }
}

function mudarDia(delta) {
  const campo = $("#dia-agenda");
  const data = deISO(campo.value);
  data.setDate(data.getDate() + delta);
  campo.value = paraISO(data);
  carregarAgenda();
}

// ------------------------------------------------------------------ abas

function abrirAba(nome) {
  for (const aba of document.querySelectorAll(".aba")) {
    const ativa = aba.dataset.aba === nome;
    if (ativa) aba.setAttribute("aria-current", "page");
    else aba.removeAttribute("aria-current");
  }
  $("#agendar").hidden = nome !== "agendar";
  $("#agenda").hidden = nome !== "agenda";
  if (nome === "agenda") mostrarPainel(!!estado.token);
}

// ------------------------------------------------------------------ início

async function iniciar() {
  for (const aba of document.querySelectorAll(".aba")) {
    aba.addEventListener("click", () => {
      history.replaceState(null, "", aba.dataset.aba === "agenda" ? "#agenda" : location.pathname);
      abrirAba(aba.dataset.aba);
    });
  }

  $("#form-agendar").addEventListener("submit", agendar);
  $("#form-agendar [name=telefone]").addEventListener("input", (e) => {
    e.target.value = formatarTelefone(e.target.value);
  });
  $("#botao-novo").addEventListener("click", novoAgendamento);

  $("#form-login").addEventListener("submit", entrar);
  $("#botao-demo").addEventListener("click", () => {
    const form = $("#form-login");
    form.usuario.value = "demo";
    form.senha.value = "demo1234";
    form.requestSubmit();
  });
  $("#botao-sair").addEventListener("click", () => sair());
  $("#dia-anterior").addEventListener("click", () => mudarDia(-1));
  $("#dia-seguinte").addEventListener("click", () => mudarDia(1));
  $("#dia-agenda").addEventListener("change", carregarAgenda);
  $("#mostrar-cancelados").addEventListener("change", carregarAgenda);
  $("#dia-agenda").value = paraISO(new Date());

  try {
    [estado.info, estado.servicos] = await Promise.all([api("/info"), api("/servicos")]);
  } catch (e) {
    $("#lista-servicos").innerHTML = `<p class="vazio">Não foi possível falar com a API: ${escapar(e.message)}</p>`;
    return;
  }

  const nomesDias = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"];
  const abertos = estado.info.dias_funcionamento;
  const faixa =
    abertos.length > 1 && abertos.every((d, i) => i === 0 || d === abertos[i - 1] + 1)
      ? `de ${nomesDias[abertos[0]]} a ${nomesDias[abertos.at(-1)]}`
      : abertos.map((d) => nomesDias[d]).join(", ");
  $("#intro-funcionamento").textContent =
    `Aberto ${faixa}, das ${estado.info.abertura} às ${estado.info.fechamento}. Escolha o serviço, o dia e o horário.`;

  if (estado.info.demo) {
    $("#botao-demo").hidden = false;
    $("#aviso-demo").hidden = false;
  }

  desenharServicos();
  desenharDias();
  atualizarPassos();
  abrirAba(location.hash === "#agenda" ? "agenda" : "agendar");
}

iniciar();
