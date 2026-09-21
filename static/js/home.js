// ============================================================
// USANEX - HOME PAGE JAVASCRIPT
// ============================================================


// ============================================================
// GLOBAL USER
// ============================================================

let currentUser = null;

let searchTimeout = null;

let toastTimer = null;


// ============================================================
// DOM ELEMENTS
// ============================================================

const searchInput =
    document.getElementById("searchInput");

const searchResults =
    document.getElementById("searchResults");

const menuBtn =
    document.getElementById("menuBtn");

const menuOverlay =
    document.getElementById("menuOverlay");


// ============================================================
// USER RESOLUTION
// ============================================================

async function resolveCurrentUser() {

    try {

        const response = await fetch(
            "/api/me",
            {
                credentials: "include"
            }
        );

        if (!response.ok) {
            return null;
        }

        const data =
            await response.json();

        if (
            data &&
            data.ok &&
            data.user
        ) {

            currentUser =
                data.user;

            updateCurrentUserUI();

            return currentUser;
        }

    } catch (error) {

        console.error(
            "User resolution error:",
            error
        );

    }

    return null;
}


// ============================================================
// UPDATE CURRENT USER UI
// ============================================================

function updateCurrentUserUI() {

    const youLetter =
        document.getElementById("youLetter");

    if (!youLetter) {
        return;
    }

    if (!currentUser) {
        youLetter.textContent = "U";
        return;
    }

    const name =
        currentUser.name ||
        currentUser.display_name ||
        currentUser.username ||
        currentUser.user_id ||
        "U";

    youLetter.textContent =
        String(name)
            .charAt(0)
            .toUpperCase();

}


// ============================================================
// CONNECTION CHECK
// ============================================================

async function checkConnection() {

    try {

        const response =
            await fetch(
                "/api/health",
                {
                    credentials: "include"
                }
            );

        return response.ok;

    } catch (error) {

        return false;

    }

}


// ============================================================
// SEARCH INPUT
// ============================================================

if (searchInput) {

    searchInput.addEventListener(
        "input",
        function () {

            clearTimeout(searchTimeout);

            const query =
                this.value.trim();

            if (!query) {

                closeSearchResults();

                return;
            }

            searchTimeout =
                setTimeout(
                    function () {

                        searchUsers(query);

                    },
                    300
                );

        }
    );

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

        const response =
            await fetch(
                `/api/search?q=${encodeURIComponent(query)}`,
                {
                    credentials: "include"
                }
            );

        if (!response.ok) {

            throw new Error(
                "Search failed"
            );

        }

        const data =
            await response.json();

        const users =
            data.users ||
            data.results ||
            [];

        renderSearchResults(users);

    } catch (error) {

        console.error(
            "Search error:",
            error
        );

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

    if (
        !users ||
        users.length === 0
    ) {

        searchResults.innerHTML = `
            <div class="search-empty">
                No users found
            </div>
        `;

        return;
    }

    searchResults.innerHTML = "";

    users.forEach(
        function (user) {

            const card =
                document.createElement("div");

            card.className =
                "search-user-card";

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
                            ?
                            `
                            <img
                                src="${escapeHtml(avatar)}"
                                alt="Profile">
                            `
                            :
                            `
                            <span>
                                ${escapeHtml(
                                    name
                                        .charAt(0)
                                        .toUpperCase()
                                )}
                            </span>
                            `
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
                            ?
                            `
                            <div class="search-user-id">
                                ID: ${escapeHtml(userId)}
                            </div>
                            `
                            :
                            ""
                        }

                    </div>

                </div>

                <button
                    class="search-profile-btn"
                    type="button"
                    onclick="openProfile('${escapeJs(userId)}')">

                    Profile

                </button>

            `;

            searchResults.appendChild(card);

        }
    );

}


// ============================================================
// CLOSE SEARCH RESULTS
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

async function followUser(
    userId,
    button
) {

    if (!userId) {
        return;
    }

    if (button) {
        button.disabled = true;
    }

    try {

        const response =
            await fetch(
                "/api/follow",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    credentials: "include",

                    body: JSON.stringify({
                        user_id: userId
                    })
                }
            );

        const data =
            await response.json();

        if (data.ok) {

            if (button) {

                button.textContent =
                    "Unfollow";

                button.classList.add(
                    "following"
                );

            }

            showToast(
                "Follow request sent"
            );

        } else {

            showToast(
                data.message ||
                data.detail ||
                "Unable to follow"
            );

        }

    } catch (error) {

        console.error(
            "Follow error:",
            error
        );

        showToast(
            "Something went wrong"
        );

    } finally {

        if (button) {
            button.disabled = false;
        }

    }

}


// ============================================================
// CONNECTIONS
// ============================================================

async function loadConnections() {

    const container =
        document.getElementById(
            "connectionsList"
        );

    if (!container) {
        return;
    }

    try {

        const response =
            await fetch(
                "/api/connections",
                {
                    credentials: "include"
                }
            );

        if (!response.ok) {
            return;
        }

        const data =
            await response.json();

        const users =
            data.connections ||
            data.users ||
            [];

        updateConnectionCount(
            users.length
        );

        renderConnections(users);

    } catch (error) {

        console.error(
            "Connections error:",
            error
        );

    }

}


// ============================================================
// CONNECTION COUNT
// ============================================================

function updateConnectionCount(count) {

    const element =
        document.getElementById(
            "connectionCount"
        );

    if (!element) {
        return;
    }

    element.textContent =
        Number(count) || 0;

}


// ============================================================
// RENDER CONNECTIONS
// ============================================================

function renderConnections(users) {

    const container =
        document.getElementById(
            "connectionsList"
        );

    if (!container) {
        return;
    }

    if (
        !users ||
        users.length === 0
    ) {

        container.innerHTML = `
            <div class="empty-box">

                <div class="empty-icon">
                    👥
                </div>

                <div class="empty-title">
                    No connections yet
                </div>

                <div class="empty-text">
                    Connect with people to see them here.
                </div>

            </div>
        `;

        return;
    }

    container.innerHTML = "";

    users.forEach(
        function (user) {

            const name =
                user.name ||
                user.display_name ||
                "User";

            const userId =
                user.user_id ||
                user.username ||
                "";

            const username =
                user.username ||
                user.user_id ||
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
                    )">

                    ${
                        avatar
                        ?
                        `
                        <img
                            src="${escapeHtml(avatar)}"
                            alt="Profile">
                        `
                        :
                        `
                        <span>
                            ${escapeHtml(
                                name
                                    .charAt(0)
                                    .toUpperCase()
                            )}
                        </span>
                        `
                    }

                </div>

                <div
                    class="connection-info"
                    onclick="openProfile(
                        '${escapeJs(userId)}'
                    )">

                    <div class="connection-name">
                        ${escapeHtml(name)}
                    </div>

                    <div class="connection-username">
                        @${escapeHtml(username)}
                    </div>

                </div>

                <button
                    class="connection-chat-btn"
                    type="button"
                    onclick="openChat(
                        '${escapeJs(userId)}'
                    )">

                    Chat

                </button>

            `;

            container.appendChild(card);

        }
    );

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


function goProfile() {

    window.location.href =
        "/profile";

}


// ============================================================
// HOME
// ============================================================

function goHome() {

    window.location.href =
        "/home";

}


// ============================================================
// REELS
// ============================================================

function goReels() {

    window.location.href =
        "/reels";

}


// ============================================================
// CREATE POST
// ============================================================

function createPost() {

    showToast(
        "Create post coming soon."
    );

}


// ============================================================
// NOTIFICATIONS
// ============================================================

function goNotifications() {

    window.location.href =
        "/notifications";

}


// ============================================================
// NOTIFICATION COUNT
// ============================================================

async function loadNotificationCount() {

    const badge =
        document.getElementById(
            "notificationBadge"
        );

    if (!badge) {
        return;
    }

    try {

        const response =
            await fetch(
                "/api/notifications/unread-count",
                {
                    credentials: "include"
                }
            );

        if (!response.ok) {
            return;
        }

        const data =
            await response.json();

        const count =
            Number(
                data.count ||
                data.unread ||
                0
            );

        if (count > 0) {

            badge.textContent =
                count > 99
                ? "99+"
                : count;

            badge.style.display =
                "flex";

        } else {

            badge.style.display =
                "none";

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

    window.location.href =
        "/status";

}


// ============================================================
// STATUS HINT
// ============================================================

function showStatusHint() {

    const hint =
        document.getElementById(
            "statusNewUserHint"
        );

    if (!hint) {
        return;
    }

    hint.classList.add("show");

    setTimeout(
        function () {

            hint.classList.remove("show");

        },
        5000
    );

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

function openStatus(
    userId,
    userName,
    seen
) {

    if (!userId) {
        return;
    }

    showToast(
        "Status viewer coming soon."
    );

}


// ============================================================
// MENU
// ============================================================

function openMenu() {

    if (!menuOverlay) {
        return;
    }

    menuOverlay.classList.add(
        "show"
    );

}


function closeMenu() {

    if (!menuOverlay) {
        return;
    }

    menuOverlay.classList.remove(
        "show"
    );

}


function toggleMenu() {

    if (!menuOverlay) {
        return;
    }

    menuOverlay.classList.toggle(
        "show"
    );

}


// ============================================================
// MENU BUTTON
// ============================================================

if (menuBtn) {

    menuBtn.addEventListener(
        "click",
        function (event) {

            event.stopPropagation();

            toggleMenu();

        }
    );

}


// ============================================================
// MENU ACTIONS
// ============================================================

function goMonetization() {

    closeMenu();

    showToast(
        "Monetization coming soon."
    );

}


function goBlocked() {

    closeMenu();

    showToast(
        "Blocked users coming soon."
    );

}


function goPrivacy() {

    closeMenu();

    showToast(
        "Privacy & Security coming soon."
    );

}


function goSettings() {

    closeMenu();

    showToast(
        "Settings coming soon."
    );

}


function goHelp() {

    closeMenu();

    showToast(
        "Help & Support coming soon."
    );

}


function goAbout() {

    closeMenu();

    showToast(
        "Usanex"
    );

}


// ============================================================
// LOGOUT
// ============================================================

async function logoutUser() {

    closeMenu();

    try {

        const response =
            await fetch(
                "/logout",
                {
                    method: "POST",
                    credentials: "include"
                }
            );

        /*
         * Logout endpoint response is not required
         * for redirect.
         */

        console.log(
            "Logout response:",
            response.status
        );

    } catch (error) {

        console.error(
            "Logout error:",
            error
        );

    }

    window.location.href =
        "/";

}


// ============================================================
// DP VIEWER
// ============================================================

function openDPViewer(
    userId,
    name,
    avatar
) {

    const viewer =
        document.getElementById(
            "dpViewer"
        );

    if (!viewer) {
        return;
    }

    const image =
        document.getElementById(
            "dpViewerImage"
        );

    const title =
        document.getElementById(
            "dpViewerName"
        );

    if (image) {

        if (avatar) {

            image.src =
                avatar;

            image.style.display =
                "block";

        } else {

            image.removeAttribute(
                "src"
            );

            image.style.display =
                "none";

        }

    }

    if (title) {

        title.textContent =
            name || "User";

    }

    viewer.classList.add(
        "show"
    );

}


function closeDPViewer(event) {

    /*
     * Prevent the button click from
     * bubbling unnecessarily.
     */

    if (event) {
        event.stopPropagation();
    }

    const viewer =
        document.getElementById(
            "dpViewer"
        );

    if (viewer) {

        viewer.classList.remove(
            "show"
        );

    }

}


// ============================================================
// TOAST
// ============================================================

function showToast(message) {

    const toast =
        document.getElementById(
            "toast"
        );

    if (!toast) {
        return;
    }

    toast.textContent =
        message || "";

    toast.classList.add(
        "show"
    );

    clearTimeout(
        toastTimer
    );

    toastTimer =
        setTimeout(
            function () {

                toast.classList.remove(
                    "show"
                );

            },
            2500
        );

}


// ============================================================
// CLICK OUTSIDE MENU
// ============================================================

document.addEventListener(
    "click",
    function (event) {

        if (!menuOverlay) {
            return;
        }

        if (
            !menuOverlay.classList.contains(
                "show"
            )
        ) {
            return;
        }

        /*
         * Menu panel ke andar click karne par
         * menu automatically close nahi hoga.
         */

        const panel =
            menuOverlay.querySelector(
                ".menu-panel"
            );

        if (
            panel &&
            panel.contains(event.target)
        ) {
            return;
        }

        if (
            menuBtn &&
            menuBtn.contains(event.target)
        ) {
            return;
        }

        closeMenu();

    }
);


// ============================================================
// CLICK OUTSIDE SEARCH
// ============================================================

document.addEventListener(
    "click",
    function (event) {

        if (!searchResults) {
            return;
        }

        if (
            !searchResults.classList.contains(
                "show"
            )
        ) {
            return;
        }

        if (
            searchResults.contains(
                event.target
            )
        ) {
            return;
        }

        if (
            searchInput &&
            searchInput.contains(
                event.target
            )
        ) {
            return;
        }

        closeSearchResults();

    }
);


// ============================================================
// ESCAPE KEY
// ============================================================

document.addEventListener(
    "keydown",
    function (event) {

        if (
            event.key !== "Escape"
        ) {
            return;
        }

        closeSearchResults();

        closeDPViewer();

        closeMenu();

    }
);


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}


// ============================================================
// ESCAPE JAVASCRIPT
// ============================================================

function escapeJs(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replace(
            /\\/g,
            "\\\\"
        )
        .replace(
            /'/g,
            "\\'"
        )
        .replace(
            /"/g,
            '\\"'
        )
        .replace(
            /\n/g,
            "\\n"
        )
        .replace(
            /\r/g,
            "\\r"
        );

}


// ============================================================
// INITIALIZE HOME
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

}


// ============================================================
// AUTO REFRESH NOTIFICATIONS
// ============================================================

setInterval(
    function () {

        loadNotificationCount();

    },
    30000
);


// ============================================================
// START
// ============================================================

if (
    document.readyState ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeHome
    );

} else {

    initializeHome();

}
