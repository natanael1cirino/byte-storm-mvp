// Service worker do painel (PWA).
// Estratégia "rede primeiro": sempre busca a versão mais nova dos arquivos estáticos
// e só usa o cache quando a conexão falha. Assim, uma atualização publicada chega
// aos sócios na hora, e o painel continua abrindo com 4G instável.
// Páginas e dados de estoque nunca passam pelo cache.
const CACHE = "bytestorm-estaticos-v2";

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(CACHE).then((c) => c.addAll([
    "/static/loja/app.css", "/static/loja/pwa.js", "/static/loja/icone.svg",
  ])));
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((nomes) => Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (evento) => {
  const url = new URL(evento.request.url);
  if (evento.request.method !== "GET" || !url.pathname.startsWith("/static/")) return;
  evento.respondWith(
    fetch(evento.request)
      .then((resposta) => {
        const copia = resposta.clone();
        caches.open(CACHE).then((c) => c.put(evento.request, copia));
        return resposta;
      })
      .catch(() => caches.match(evento.request))
  );
});
