// Service worker simples: guarda em cache só os arquivos estáticos (CSS, JS, ícones).
// As páginas e os dados sempre vêm da rede, para o estoque nunca aparecer desatualizado.
const CACHE = "bytestorm-estaticos-v1";

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(CACHE).then((c) => c.addAll([
    "/static/loja/app.css", "/static/loja/pwa.js", "/static/loja/icone.svg",
  ])));
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(caches.keys().then((nomes) =>
    Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n)))));
});

self.addEventListener("fetch", (evento) => {
  const url = new URL(evento.request.url);
  if (evento.request.method !== "GET" || !url.pathname.startsWith("/static/")) return;
  evento.respondWith(caches.match(evento.request).then((r) => r || fetch(evento.request)));
});
