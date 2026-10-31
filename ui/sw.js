// Offline app shell. API calls always go to the network (the page caches the last data itself).
const C = "swarm-shell-v7";
const SHELL = ["/", "/manifest.webmanifest", "/icon.svg", "/icon-192.png", "/icon-512.png", "/apple-touch-icon.png"];
const API = ["/cameras", "/status", "/discover", "/settings", "/health", "/login", "/events", "/remote", "/push"];
self.addEventListener("install", e => { self.skipWaiting(); e.waitUntil(caches.open(C).then(c => c.addAll(SHELL))); });
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin || API.some(p => u.pathname.startsWith(p))) return;
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(C).then(c => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request).then(r => r || caches.match("/"))));
});

self.addEventListener("push", e => {
  let d = { title: "Swarm alert", body: "" };
  try { d = e.data.json(); } catch (x) {}
  e.waitUntil(self.registration.showNotification(d.title || "Swarm alert", { body: d.body, icon: "/icon-192.png", badge: "/icon-192.png", tag: "swarm", renotify: true }));
});
self.addEventListener("notificationclick", e => {
  e.notification.close();
  e.waitUntil(clients.matchAll({ type: "window" }).then(cs => (cs.length ? cs[0].focus() : clients.openWindow("/"))));
});
