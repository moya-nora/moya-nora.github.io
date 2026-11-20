// Нора: уведомления (веб-пуши) и работа без интернета.
// Без интернета: приложение и каталог берутся из копии на телефоне. Сначала всегда пробуем сеть (свежая версия важнее),
// копию отдаём, только если сети нет или она не ответила за несколько секунд. Чужие сайты (обложки, облако) не трогаем.
const CACHE = "nora-off-v2";
const OK = /^\/(app(-dev)?\.html|books\/[^?]*\.(json|js)|fonts\/|icons\/|img\/|manifest[^/]*\.(json|webmanifest)|site\.css)/;
self.addEventListener("fetch", e => {
  const r = e.request; if (r.method !== "GET") return;
  const u = new URL(r.url); if (u.origin !== location.origin) return;
  const nav = r.mode === "navigate";
  if (!(nav && /^\/app(-dev)?\.html$/.test(u.pathname)) && !OK.test(u.pathname)) return;
  const key = nav || /\.html$/.test(u.pathname) ? u.origin + u.pathname : r;
  e.respondWith((async () => {
    const c = await caches.open(CACHE), old = await c.match(key, { ignoreSearch: nav || /\.html$/.test(u.pathname) });
    const net = fetch(r).then(res => { if (res && res.ok && res.type === "basic") c.put(key, res.clone()).catch(() => {}); return res; });
    if (!old) return net;
    const wait = new Promise(ok => setTimeout(() => ok(null), nav ? 4000 : 8000));
    try { const res = await Promise.race([net, wait]); if (res && res.ok) return res; } catch (x) {}
    net.catch(() => {}); return old;
  })());
});
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(K => Promise.all(K.filter(k => k.startsWith("nora-off-") && k !== CACHE).map(k => caches.delete(k))))));
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (x) { d = { body: e.data ? e.data.text() : "" }; }
  e.waitUntil(self.registration.showNotification(d.title || "Нора", {
    body: d.body || "", icon: "/icons/icon-192.png?v=5", badge: "/icons/icon-192.png?v=5",
    tag: d.tag || "nora", data: { url: d.url || "/app.html?app=1" }
  }));
});
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/app.html?app=1";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(L => {
    for (const c of L) if (c.url.includes("/app") && "focus" in c) return c.focus();
    return self.clients.openWindow(url);
  }));
});
