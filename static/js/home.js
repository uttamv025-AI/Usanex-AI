// ============================================================
// USANEX - HOME PAGE JAVASCRIPT
// ============================================================


// ============================================================
// GLOBAL USER
// ============================================================

let currentUser = null;


// ============================================================
// USER RESOLUTION
// ============================================================

async function resolveCurrentUser() {
    try {
        const response = await fetch("/api/me", {
            credentials: "include"
        });

        if (!response.ok) {
            return null;
        }

        const data = await response.json();

        if (data && data.ok && data.user) {
            currentUser = data.user;
            return currentUser;
        }

    } catch (error) {
        console.error("User resolution error:", error);
    }

    return null;
}


// ============================================================
// CONNECTION CHECK
// ============================================================

async function checkConnection() {
    try {
        const response = await fetch("/api/health", {
            credentials: "include"
        });

        return response.ok;

    } catch (error) {
        return false;
    }
}


// ============================================================
// SEARCH
// ============================================================

let searchTimeout = null;

const searchInput = document.getElementById("searchInput");
const searchResults = document.getElementById("searchResults");


if (searchInput) {

    searchInput.addEventListener("input", function () {

        clearTimeout(searchTimeout);

        const query = this.value.trim();

        if (!query) {
            closeSearchResults();
            return;
        }

        searchTimeout = setTimeout(() => {
            searchUsers(query);
        }, 300);

    });

}


// ============================================================
// SEARCH USERS
// ============================================================

async function searchUsers(query) {

    if (!searchResults) {
        return;
    }

    searchResults.innerHTML = `
        <div class="search-loading">
            Searching...
        </div>
    `;

    searchResults.classList.add("show");

    try {

        const response = await fetch(
            `/api/search?q=${encodeURIComponent(query)}`,
            {
                credentials: "include"
            }
        );

        if (!response.ok) {
            throw new Error("Search failed");
        }

        const data = await response.json();

        const users = data.users || data.results || [];

        renderSearchResults(users);

    } catch (error) {

        console.error("Search error:", error);

        searchResults.innerHTML = `
            <div class="search-error">
                Unable to search right now.
            </div>
        `;
    }
}


// ============================================================
// RENDER SEARCH RESULTS
// ============================================================

function renderSearchResults(users) {

    if (!searchResults) {
        return;
    }

    if (!users || users.length === 0) {

        searchResults.innerHTML = `
            <div class="search-empty">
                No users found
            </div>
        `;

        return;
    }

    searchResults.innerHTML = "";

    users.forEach(user => {

        const card = document.createElement("div");

        card.className = "search-user-card";

        const name =
            user.name ||
            user.display_name ||
            "User";

        const username =
            user.username ||
            user.user_id ||
            "";

        const userId =
            user.user_id ||
            user.username ||
            "";

        const avatar =
            user.profile_picture ||
            user.avatar ||
            "";

        card.innerHTML = `

            <div class="search-user-left">

                <div class="search-user-avatar">

                    ${
                        avatar
                        ? `<img src="${avatar}" alt="">`
                        : `<span>${escapeHtml(name.charAt(0).toUpperCase())}</span>`
                    }

                </div>

                <div class="search-user-info">

                    <div class="search-user-name">
                        ${escapeHtml(name)}
                    </div>

                    <div class="search-user-username">
                        @${escapeHtml(username)}
                    </div>

                    ${
                        userId
                        ? `
                        <div class="search-user-id">
                            ID: ${escapeHtml(userId)}
                        </div>
                        `
                        : ""
                    }

                </div>

            </div>

            <button
                class="search-profile-btn"
                onclick="openProfile('${escapeJs(userId)}')"
            >
                Profile
            </button>

        `;

        searchResults.appendChild(card);

    });
}


// ============================================================
// CHAT
// ============================================================

function openChat(userId) {

    if (!userId) {
        return;
    }

    window.location.href =
        `/chat?user_id=${encodeURIComponent(userId)}`;
}


// ============================================================
// FOLLOW
// ============================================================

async function followUser(userId, button) {

    if (!userId) {
        return;
    }

    if (button) {
        button.disabled = true;
    }

    try {

        const response = await fetch("/api/follow", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            credentials: "include",

            body: JSON.stringify({
                user_id: userId
            })

        });

        const data = await response.json();

        if (data.ok) {

            if (button) {
                button.textContent = "Unfollow";
                button.classList.add("following");
            }

            showToast("Follow request sent");

        } else {

            showToast(
                data.message ||
                data.detail ||
                "Unable to follow"
            );
        }

    } catch (error) {

        console.error("Follow error:", error);

        showToast("Something went wrong");

    } finally {

        if (button) {
            button.disabled = false;
        }

    }
}


// ============================================================
// CLOSE SEARCH
// ============================================================

function closeSearchResults() {

    if (!searchResults) {
        return;
    }

    searchResults.classList.remove("show");
    searchResults.innerHTML = "";

}


function closeSearch() {

    if (searchInput) {
        searchInput.value = "";
    }

    closeSearchResults();

}


// ============================================================
// CONNECTIONS
// ============================================================

async function loadConnections() {

    const container =
        document.getElementById("connectionsList");

    if (!container) {
        return;
    }

    try {

        const response = await fetch(
            "/api/connections",
            {
                credentials: "include"
            }
        );

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        const users =
            data.connections ||
            data.users ||
            [];

        renderConnections(users);

    } catch (error) {

        console.error(
            "Connections error:",
            error
        );

    }
}


function renderConnections(users) {

    const container =
        document.getElementById("connectionsList");

    if (!container) {
        return;
    }

    if (!users || users.length === 0) {

        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">👥</div>
                <div>No connections yet</div>
            </div>
        `;

        return;
    }

    container.innerHTML = "";

    users.forEach(user => {

        const name =
            user.name ||
            user.display_name ||
            "User";

        const userId =
            user.user_id ||
            user.username ||
            "";

        const avatar =
            user.profile_picture ||
            user.avatar ||
            "";

        const card =
            document.createElement("div");

        card.className =
            "connection-card";

        card.innerHTML = `

            <div
                class="connection-avatar"
                onclick="openDPViewer(
                    '${escapeJs(userId)}',
                    '${escapeJs(name)}',
                    '${escapeJs(avatar)}'
                )"
            >

                ${
                    avatar
                    ? `<img src="${avatar}" alt="">`
                    : `<span>${escapeHtml(name.charAt(0).toUpperCase())}</span>`
                }

            </div>

            <div
                class="connection-info"
                onclick="openProfile('${escapeJs(userId)}')"
            >

                <div class="connection-name">
                    ${escapeHtml(name)}
                </div>

                <div class="connection-username">
                    @${escapeHtml(user.username || userId)}
                </div>

            </div>

            <button
                class="connection-chat-btn"
                onclick="openChat('${escapeJs(userId)}')"
            >
                Chat
            </button>

        `;

        container.appendChild(card);

    });
}


// ============================================================
// PROFILE
// ============================================================

function openProfile(userId) {

    if (!userId) {
        return;
    }

    window.location.href =
        `/profile?user_id=${encodeURIComponent(userId)}`;
}


// ============================================================
// DP VIEWER
// ============================================================

function openDPViewer(userId, name, avatar) {

    const viewer =
        document.getElementById("dpViewer");

    if (!viewer) {
        return;
    }

    const image =
        document.getElementById("dpViewerImage");

    const title =
        document.getElementById("dpViewerName");

    if (image) {

        if (avatar) {

            image.src = avatar;
            image.style.display = "block";

        } else {

            image.removeAttribute("src");
            image.style.display = "none";

        }
    }

    if (title) {
        title.textContent = name || "User";
    }

    viewer.classList.add("show");

}


function closeDPViewer() {

    const viewer =
        document.getElementById("dpViewer");

    if (viewer) {
        viewer.classList.remove("show");
    }

}


// ============================================================
// NOTIFICATION COUNT
// ============================================================

async function loadNotificationCount() {

    const badge =
        document.getElementById("notificationBadge");

    if (!badge) {
        return;
    }

    try {

        const response = await fetch(
            "/api/notifications/unread-count",
            {
                credentials: "include"
            }
        );

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        const count =
            Number(
                data.count ||
                data.unread ||
                0
            );

        if (count > 0) {

            badge.textContent =
                count > 99 ? "99+" : count;

            badge.style.display = "flex";

        } else {

            badge.style.display = "none";

        }

    } catch (error) {

        console.error(
            "Notification count error:",
            error
        );

    }
}


// ============================================================
// ADD MY STATUS
// ============================================================

function addMyStatus() {

    /*
     * Status editor is now a separate page.
     */

    window.location.href = "/status";
}


// ============================================================
// STATUS HINT
// ============================================================

function showStatusHint() {

    const hint =
        document.getElementById("statusHint");

    if (!hint) {
        return;
    }

    hint.classList.add("show");

    setTimeout(() => {

        hint.classList.remove("show");

    }, 5000);
}


// ============================================================
// SHOW ALL STATUSES
// ============================================================

function showAllStatuses() {

    showToast(
        "All statuses will appear here."
    );

}


// ============================================================
// OPEN STATUS
// ============================================================

function openStatus(userId) {

    if (!userId) {
        return;
    }

    showToast(
        "Status viewer coming soon."
    );

}


// ============================================================
// NAVIGATION
// ============================================================

function navigateTo(page) {

    if (!page) {
        return;
    }

    switch (page) {

        case "home":
            window.location.href = "/home";
            break;

        case "reels":
            window.location.href = "/reels";
            break;

        case "coll":
            window.location.href = "/search";
            break;

        case "profile":
            window.location.href = "/profile";
            break;

        case "notifications":
            window.location.href =
                "/notifications";
            break;

        default:
            console.warn(
                "Unknown navigation:",
                page
            );

    }

}


// ============================================================
// MENU
// ============================================================

function toggleMenu() {

    const menu =
        document.getElementById("sideMenu");

    if (!menu) {
        return;
    }

    menu.classList.toggle("show");

}


function openMenu() {

    const menu =
        document.getElementById("sideMenu");

    if (menu) {
        menu.classList.add("show");
    }

}


function closeMenu() {

    const menu =
        document.getElementById("sideMenu");

    if (menu) {
        menu.classList.remove("show");
    }

}


// ============================================================
// MENU ACTIONS
// ============================================================

function openNotifications() {

    closeMenu();

    window.location.href =
        "/notifications";
}


function openSearchPage() {

    closeMenu();

    window.location.href =
        "/search";
}


function openProfilePage() {

    closeMenu();

    window.location.href =
        "/profile";
}


// ============================================================
// TOAST
// ============================================================

let toastTimer = null;


function showToast(message) {

    const toast =
        document.getElementById("toast");

    if (!toast) {
        return;
    }

    toast.textContent =
        message || "";

    toast.classList.add("show");

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {

        toast.classList.remove("show");

    }, 2500);

}


// ============================================================
// LOGOUT
// ============================================================

async function logout() {

    try {

        await fetch(
            "/logout",
            {
                method: "POST",
                credentials: "include"
            }
        );

    } catch (error) {

        console.error(
            "Logout error:",
            error
        );

    }

    window.location.href = "/";

}


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(value) {

    if (value === null ||
        value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function escapeJs(value) {

    if (value === null ||
        value === undefined) {
        return "";
    }

    return String(value)
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, "\\n")
        .replace(/\r/g, "\\r");

}


// ============================================================
// CLICK OUTSIDE MENU
// ============================================================

document.addEventListener(
    "click",
    function (event) {

        const menu =
            document.getElementById("sideMenu");

        const menuButton =
            document.getElementById("menuButton");

        if (!menu ||
            !menu.classList.contains("show")) {
            return;
        }

        if (
            !menu.contains(event.target) &&
            (!menuButton ||
             !menuButton.contains(event.target))
        ) {

            closeMenu();

        }

    }
);


// ============================================================
// CLICK OUTSIDE SEARCH
// ============================================================

document.addEventListener(
    "click",
    function (event) {

        if (!searchResults ||
            !searchResults.classList.contains("show")) {
            return;
        }

        if (
            !searchResults.contains(event.target) &&
            (!searchInput ||
             !searchInput.contains(event.target))
        ) {

            closeSearchResults();

        }

    }
);


// ============================================================
// INITIAL LOAD
// ============================================================

async function initializeHome() {

    try {

        await resolveCurrentUser();

    } catch (error) {

        console.error(
            "Initial user loading error:",
            error
        );

    }

    loadConnections();
    loadNotificationCount();

    /*
     * Optional status hint.
     * It does not open the editor automatically.
     */
    // showStatusHint();

}


// ============================================================
// AUTO REFRESH
// ============================================================

setInterval(
    () => {

        loadNotificationCount();

    },
    30000
);


// ============================================================
// ESCAPE KEY
// ============================================================

document.addEventListener(
    "keydown",
    function (event) {

        if (event.key !== "Escape") {
            return;
        }

        closeSearchResults();
        closeDPViewer();
        closeMenu();

    }
);


// ============================================================
// START
// ============================================================

if (
    document.readyState === "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeHome
    );

} else {

    initializeHome();

}
