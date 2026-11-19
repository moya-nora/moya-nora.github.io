// Нора: только уведомления (веб-пуши). Страницы не кеширует и запросы не перехватывает.
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
