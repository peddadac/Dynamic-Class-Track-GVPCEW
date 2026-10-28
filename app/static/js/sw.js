// Service Worker for Dynamic Class Track Web Push Notifications

self.addEventListener("push", function (event) {
    let data = { title: "Dynamic Class Track Alert", body: "Classroom or schedule update available." };
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }

    const options = {
        body: data.body,
        icon: data.icon || "/static/images/logo.png",
        badge: "/static/images/logo.png",
        vibrate: [200, 100, 200],
        data: {
            url: "/"
        }
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

self.addEventListener("notificationclick", function (event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url || "/")
    );
});
