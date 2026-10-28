/**
 * Dynamic Class Track - Main Client JavaScript
 * Gayatri Vidya Parishad College of Engineering for Women (GVPCEW)
 */

document.addEventListener("DOMContentLoaded", () => {
    initNotificationPolling();
    initCascadingDropdowns();
    initSocketIO();
    initWebPush();
});

// -------------------------------------------------------------------------
// NOTIFICATION POLLING (Fallback & Live Badge)
// -------------------------------------------------------------------------
function initNotificationPolling() {
    const badge = document.getElementById("navNotificationBadge");
    if (!badge) return;

    function pollUnread() {
        fetch("/api/notifications/unread")
            .then(res => res.json())
            .then(data => {
                if (data && typeof data.count !== "undefined") {
                    if (data.count > 0) {
                        badge.textContent = data.count > 99 ? "99+" : data.count;
                        badge.classList.remove("d-none");
                    } else {
                        badge.classList.add("d-none");
                    }
                }
            })
            .catch(err => console.debug("Notification poll failed:", err));
    }

    // Poll every 15 seconds
    setInterval(pollUnread, 15000);
}

// -------------------------------------------------------------------------
// CASCADING DROPDOWNS (Branch -> Sections / Subjects)
// -------------------------------------------------------------------------
function initCascadingDropdowns() {
    const branchSelect = document.getElementById("branchSelect");
    const sectionSelect = document.getElementById("sectionSelect");

    if (branchSelect && sectionSelect) {
        branchSelect.addEventListener("change", (e) => {
            const branchId = e.target.value;
            if (!branchId) {
                sectionSelect.innerHTML = '<option value="">-- Select Section --</option>';
                return;
            }

            fetch(`/api/sections-by-branch/${branchId}`)
                .then(res => res.json())
                .then(sections => {
                    sectionSelect.innerHTML = '<option value="">-- Select Section --</option>';
                    sections.forEach(sec => {
                        const opt = document.createElement("option");
                        opt.value = sec.id;
                        opt.textContent = sec.name;
                        sectionSelect.appendChild(opt);
                    });
                })
                .catch(err => console.error("Error fetching sections:", err));
        });
    }
}

// -------------------------------------------------------------------------
// REAL-TIME SOCKET.IO INTEGRATION
// -------------------------------------------------------------------------
function initSocketIO() {
    if (typeof io === "undefined") return;

    try {
        const socket = io();
        socket.on("connect", () => {
            console.log("Connected to live notification stream.");
        });

        socket.on("new_notification", (notif) => {
            console.log("Live notification received:", notif);
            const badge = document.getElementById("navNotificationBadge");
            if (badge) {
                let current = parseInt(badge.textContent) || 0;
                badge.textContent = current + 1;
                badge.classList.remove("d-none");
            }
            // Show toast or alert banner
            showLiveToast(notif.title, notif.message);
        });
    } catch (e) {
        console.debug("Socket.IO client init failed, relying on polling fallback.");
    }
}

function showLiveToast(title, message) {
    const toastContainer = document.getElementById("toastContainer");
    if (!toastContainer) return;

    const toastEl = document.createElement("div");
    toastEl.className = "toast show align-items-center text-white bg-primary border-0 mb-2 shadow";
    toastEl.setAttribute("role", "alert");
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong><br>
                <span>${message}</span>
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    toastContainer.appendChild(toastEl);
    setTimeout(() => {
        toastEl.remove();
    }, 6000);
}

// -------------------------------------------------------------------------
// BROWSER WEB PUSH (Service Worker)
// -------------------------------------------------------------------------
function initWebPush() {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        return;
    }

    navigator.serviceWorker.register("/static/js/sw.js")
        .then(registration => {
            // Service worker registered
            return fetch("/api/push/vapid-public-key")
                .then(res => res.json())
                .then(data => {
                    if (data.publicKey && Notification.permission === "granted") {
                        subscribeUserToPush(registration, data.publicKey);
                    }
                });
        })
        .catch(err => console.debug("Service Worker registration:", err));
}

function subscribeUserToPush(registration, vapidPublicKey) {
    const convertedVapidKey = urlBase64ToUint8Array(vapidPublicKey);
    registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: convertedVapidKey
    })
    .then(subscription => {
        fetch("/api/push/subscribe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(subscription)
        });
    })
    .catch(err => console.debug("Push subscription notice:", err));
}

function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/\-/g, "+").replace(/_/g, "/");
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}
