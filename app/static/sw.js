// Service Worker for VoltWay PWA
const CACHE_NAME = 'voltway-v2';
const STATIC_CACHE = 'voltway-static-v2';
const API_CACHE = 'voltway-api-v2';

const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/manifest.json',
  '/static/favicon.ico'
];

// Install event - cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Opened static cache');
        return cache.addAll(urlsToCache);
      })
      .catch(err => {
        console.error('Failed to cache assets:', err);
      })
  );
  self.skipWaiting();
});

// Fetch event - serve from cache with network fallback
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle API requests with cache-first strategy
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      caches.open(API_CACHE).then(cache => {
        return cache.match(request).then(cachedResponse => {
          if (cachedResponse) {
            // Return cached response and update in background
            fetch(request).then(response => {
              if (response.ok) {
                cache.put(request, response.clone());
              }
            }).catch(() => {});
            return cachedResponse;
          }
          return fetch(request).then(response => {
            if (response.ok) {
              cache.put(request, response.clone());
            }
            return response;
          });
        });
      })
    );
    return;
  }

  // Handle static assets with cache-first strategy
  event.respondWith(
    caches.match(request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(request).then(response => {
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }
          const responseToCache = response.clone();
          caches.open(STATIC_CACHE).then(cache => {
            cache.put(request, responseToCache);
          });
          return response;
        });
      })
      .catch(err => {
        console.error('Fetch failed:', err);
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
          return caches.match('/');
        }
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE && cacheName !== API_CACHE) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Handle push notifications
self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'VoltWay';
  const options = {
    body: data.body || 'Новое уведомление',
    icon: '/static/icons/icon-192x192.svg',
    badge: '/static/icons/icon-72x72.svg',
    tag: data.tag || 'voltway-notification',
    data: data.url || '/',
    vibrate: [200, 100, 200],
    actions: [
      { action: 'open', title: 'Открыть' },
      { action: 'close', title: 'Закрыть' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'close') {
    return;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(clientList => {
      // Check if window is already open
      for (const client of clientList) {
        if (client.url === event.notification.data && 'focus' in client) {
          return client.focus();
        }
      }
      // Open new window
      if (clients.openWindow) {
        return clients.openWindow(event.notification.data);
      }
    })
  );
});

// Handle background sync
self.addEventListener('sync', event => {
  if (event.tag === 'sync-stations') {
    event.waitUntil(syncStations());
  }
});

async function syncStations() {
  // Sync favorite stations or other data when online
  console.log('Background sync: stations');
}
