/**
 * EduConnect Lesotho Digital Library - Service Worker
 * Provides offline capabilities for the library system
 */

const CACHE_NAME = 'butha-buthe-library-v1';
const STATIC_CACHE = 'static-v1';
const DYNAMIC_CACHE = 'dynamic-v1';

// Files to cache for offline access
const STATIC_FILES = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/images/book-placeholder.png',
    '/offline.html',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
];

// API endpoints to cache
const API_CACHE_PATTERNS = [
    /\/api\/books/,
    /\/api\/categories/,
    /\/api\/user\/profile/
];

// Install event - cache static files
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Service Worker: Caching static files');
                return cache.addAll(STATIC_FILES);
            })
            .catch(error => {
                console.error('Service Worker: Failed to cache static files', error);
            })
    );
    
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cache => {
                        if (cache !== STATIC_CACHE && cache !== DYNAMIC_CACHE) {
                            console.log('Service Worker: Deleting old cache', cache);
                            return caches.delete(cache);
                        }
                    })
                );
            })
    );
    
    self.clients.claim();
});

// Fetch event - serve cached files when offline
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip external requests (except for CDN files we explicitly cache)
    if (!url.origin.includes(self.location.origin) && !STATIC_FILES.includes(request.url)) {
        return;
    }
    
    event.respondWith(
        caches.match(request)
            .then(cachedResponse => {
                // Return cached version if available
                if (cachedResponse) {
                    return cachedResponse;
                }
                
                // If it's an API request, try to cache it
                if (isApiRequest(request.url)) {
                    return fetchAndCache(request, DYNAMIC_CACHE);
                }
                
                // For other requests, fetch normally and cache if successful
                return fetchAndCache(request, DYNAMIC_CACHE);
            })
            .catch(error => {
                console.error('Service Worker: Fetch failed', error);
                
                // Return offline page for navigation requests
                if (request.mode === 'navigate') {
                    return caches.match('/offline.html');
                }
                
                // Return a fallback response for other requests
                return new Response('Offline', {
                    status: 503,
                    statusText: 'Service Unavailable'
                });
            })
    );
});

// Helper function to fetch and cache responses
function fetchAndCache(request, cacheName) {
    return fetch(request)
        .then(response => {
            // Don't cache error responses
            if (!response.ok) {
                return response;
            }
            
            // Clone the response because it can only be consumed once
            const responseClone = response.clone();
            
            caches.open(cacheName)
                .then(cache => {
                    cache.put(request, responseClone);
                })
                .catch(error => {
                    console.error('Service Worker: Failed to cache response', error);
                });
            
            return response;
        });
}

// Helper function to check if request is an API call
function isApiRequest(url) {
    return API_CACHE_PATTERNS.some(pattern => pattern.test(url));
}

// Background sync for offline actions
self.addEventListener('sync', event => {
    console.log('Service Worker: Background sync', event.tag);
    
    if (event.tag === 'sync-offline-actions') {
        event.waitUntil(syncOfflineActions());
    }
});

// Sync offline actions when connection is restored
function syncOfflineActions() {
    // This would typically read from IndexedDB or another storage
    // and replay any actions that were queued while offline
    console.log('Service Worker: Syncing offline actions...');
    
    return new Promise(resolve => {
        // Implementation would depend on specific offline actions
        // For now, just log and resolve
        setTimeout(() => {
            console.log('Service Worker: Offline actions synced');
            resolve();
        }, 1000);
    });
}

// Push notification handling (for future implementation)
self.addEventListener('push', event => {
    console.log('Service Worker: Push notification received', event);
    
    if (event.data) {
        const data = event.data.json();
        
        const options = {
            body: data.body,
            icon: '/static/images/library-icon.png',
            badge: '/static/images/library-badge.png',
            data: data.data || {},
            actions: [
                {
                    action: 'view',
                    title: 'View'
                },
                {
                    action: 'dismiss',
                    title: 'Dismiss'
                }
            ]
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    console.log('Service Worker: Notification clicked', event);
    
    event.notification.close();
    
    if (event.action === 'view') {
        // Open the app
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Handle messages from the main thread
self.addEventListener('message', event => {
    console.log('Service Worker: Message received', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_NAME });
    }
});