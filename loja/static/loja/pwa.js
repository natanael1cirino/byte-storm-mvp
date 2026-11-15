// Registra o service worker para o painel funcionar como PWA.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js").catch(function () { /* PWA é opcional */ });
  });
}
document.addEventListener("DOMContentLoaded", function () {
  // Leva o foco ao alerta de erro, para ser anunciado por leitores de tela.
  var alerta = document.getElementById("alerta-estoque");
  if (alerta) { alerta.focus(); }

  // Trava a quantidade no estoque do produto escolhido (sugestão da 1ª validação).
  // O servidor continua validando; isto só evita o erro antes de salvar.
  var seletor = document.querySelector("[data-controla-quantidade]");
  if (!seletor) { return; }
  var campo = document.getElementById(seletor.getAttribute("data-controla-quantidade"));
  var dica = campo && campo.parentElement.querySelector(".dica");
  function atualizar() {
    var opcao = seletor.options[seletor.selectedIndex];
    var estoque = opcao ? parseInt(opcao.getAttribute("data-estoque"), 10) : NaN;
    if (!campo || isNaN(estoque)) { return; }
    campo.max = estoque;
    if (parseInt(campo.value, 10) > estoque) { campo.value = estoque; }
    if (dica) { dica.textContent = "Máximo disponível: " + estoque + (estoque === 1 ? " unidade." : " unidades."); }
  }
  seletor.addEventListener("change", atualizar);
  atualizar();
});
