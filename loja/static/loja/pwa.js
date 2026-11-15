// Registra o service worker para o painel funcionar como PWA.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js").catch(function () { /* PWA é opcional */ });
  });
}
// Leva o foco ao alerta de erro, para ser anunciado por leitores de tela.
document.addEventListener("DOMContentLoaded", function () {
  var alerta = document.getElementById("alerta-estoque");
  if (alerta) { alerta.focus(); }
});
