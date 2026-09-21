"use strict";

/* =========================================================
   USANEX HOME.JS
   Existing Home functionality + New Automatic Status Viewer
========================================================= */


/* =========================================================
   GLOBAL STATE
========================================================= */

let currentUser = null;

let searchTimer = null;
let notificationTimer = null;
let toastTimer = null;

let connectedUsersData = [];


/* =========================================================
   DOM
========================================================= */

const searchInput =
    document.getElementById("searchInput");

const searchResults =
    document.getElementById("searchResults");

const menuBtn =
    document.getElementById("menuBtn");

const menuOverlay =
    document.getElementById("menuOverlay");


/* =========================================================
   BASIC HELPERS
========================================================= */

function normalizeUser(user) {

    if (!user) {
        return null;
    }

    if (typeof user === "string") {
        return {
            user_id: user,
            name: user
        };
    }

    return user;
}


function getStoredCurrentUser() {

    const possibleKeys = [
        "currentUser",
        "user",
        "usanex_user",
        "loggedInUser"
    ];

    for (const key of possibleKeys) {

        try {

            const raw =
                localStorage.getItem(key);

            if (!raw) {
                continue;
            }

            const parsed =
                JSON.parse(raw);

            if (parsed) {
                return normalizeUser(parsed);
            }

        } catch (error) {

            const raw =
                localStorage.getItem(key);

            if (raw) {

                return {
                    user_id: raw,
                    name: raw
                };

            }
        }
    }

    return null;
}


function resolveCurrentUser() {

    const stored =
        getStoredCurrentUser();

    if (stored) {

        currentUser =
            normalizeUser(stored);

        return currentUser;
    }

    return null;
}


function getCurrentUserId() {

    if (!currentUser) {
        return "";
    }

    return String(
        currentUser.user_id ||
        currentUser.username ||
        currentUser.id ||
        ""
    ).trim();
}


/* =========================================================
   ESCAPE HTML
========================================================= */

function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


/* =========================================================
   TOAST
========================================================= */

function showToast(message) {

    const toast =
        document.getElementById("toast");

    if (!toast) {
        return;
    }

    clearTimeout(toastTimer);

    toast.textContent =
        message;

    toast.classList.add("show");

    toastTimer =
        setTimeout(() => {

            toast.classList.remove("show");

        }, 2500);
}


/* =========================================================
   YOUR STATUS LETTER / AVATAR
========================================================= */

function updateYourStatusLetter() {

    const letter =
        document.getElementById("youLetter");

    const avatarInner =
        document.querySelector(
            "#myStatusCircle .status-avatar-inner"
        );

    if (!currentUser) {
        return;
    }

    const name =
        currentUser.name ||
        currentUser.user_id ||
        "U";

    const firstLetter =
        String(name)
            .trim()
            .charAt(0)
            .toUpperCase() || "U";

    if (avatarInner) {

        const photo =
            currentUser.profile_photo ||
            currentUser.profilePhoto ||
            "";

        if (photo) {

            avatarInner.innerHTML =
                `<img src="${escapeHtml(photo)}"
                      alt="Your profile photo">`;

        } else {

            avatarInner.innerHTML =
                `<span id="youLetter">
                    ${escapeHtml(firstLetter)}
                 </span>`;
        }

    } else if (letter) {

        letter.textContent =
            firstLetter;
    }
}


/* =========================================================
   =========================================================
   CONNECTIONS
   =========================================================
========================================================= */

async function loadConnections() {

    const userId =
        getCurrentUserId();

    if (!userId) {
        return;
    }

    try {

        let response =
            await fetch(
                `/api/home/connections?user_id=${encodeURIComponent(userId)}`
            );

        if (!response.ok) {

            response =
                await fetch(
                    `/api/connections?user_id=${encodeURIComponent(userId)}`
                );
        }

        if (!response.ok) {
            throw new Error("Connections request failed");
        }

        const data =
            await response.json();

        let users =
            data.users ||
            data.connections ||
            data.data ||
            [];

        if (!Array.isArray(users)) {
            users = [];
        }

        renderConnections(users);

    } catch (error) {

        console.error(
            "Connection loading error:",
            error
        );

        renderConnections([]);
    }
}


/* =========================================================
   RENDER CONNECTIONS
========================================================= */

function renderConnections(users) {

    const list =
        document.getElementById("connectionsList");

    const count =
        document.getElementById("connectionCount");

    if (!list) {
        return;
    }

    connectedUsersData =
        Array.isArray(users)
            ? users
            : [];

    if (count) {

        count.textContent =
            connectedUsersData.length;
    }

    if (!connectedUsersData.length) {

        list.innerHTML = `
            <div class="empty-box">

                <div class="empty-icon">
                    ◌
                </div>

                <div class="empty-title">
                    No connected people
                </div>

                <div class="empty-text">
                    Connect with people to see them here.
                </div>

            </div>
        `;

        return;
    }


    list.innerHTML =
        connectedUsersData
            .map((user, index) => {

                const normalized =
                    normalizeUser(user);

                const userId =
                    String(
                        normalized.user_id ||
                        normalized.username ||
                        normalized.id ||
                        ""
                    );

                const name =
                    normalized.name ||
                    normalized.full_name ||
                    userId ||
                    "User";

                const photo =
                    normalized.profile_photo ||
                    normalized.profilePhoto ||
                    "";

                const letter =
                    name
                        .trim()
                        .charAt(0)
                        .toUpperCase() || "U";


                const statusUser =
                    activeStatusUsers.find(
                        item =>
                            String(item.user_id) ===
                            String(userId)
                    );


                const hasStatus =
                    !!(
                        statusUser &&
                        Array.isArray(statusUser.statuses) &&
                        statusUser.statuses.length
                    );


                const fullySeen =
                    hasStatus &&
                    isUserFullySeen(statusUser);


                let statusClass = "";

                if (hasStatus) {

                    statusClass =
                        fullySeen
                            ? "connection-status-seen"
                            : "connection-status-unseen";
                }


                const photoHtml =
                    photo
                        ? `
                            <img
                                src="${escapeHtml(photo)}"
                                alt="${escapeHtml(name)}">
                          `
                        : `
                            <span>
                                ${escapeHtml(letter)}
                            </span>
                          `;


                return `
                    <div
                        class="connection-card"
                        data-user-id="${escapeHtml(userId)}">

                        <div
                            class="profile-photo ${statusClass}"
                            data-photo="${escapeHtml(photo)}"
                            data-name="${escapeHtml(name)}"
                            data-user-id="${escapeHtml(userId)}"
                            data-has-status="${hasStatus ? "1" : "0"}">

                            ${photoHtml}

                        </div>


                        <div
                            class="connection-info"
                            onclick="openUserProfile('${escapeHtml(userId)}')">

                            <div class="connection-name">
                                ${escapeHtml(name)}
                            </div>

                            <div class="connection-user-id">
                                @${escapeHtml(userId)}
                            </div>

                        </div>


                        <button
                            type="button"
                            class="connection-action"
                            onclick="openChat('${escapeHtml(userId)}')"
                            aria-label="Chat">

                            💬

                        </button>

                    </div>
                `;

            })
            .join("");


    attachConnectionEvents();
}


/* =========================================================
   CONNECTION EVENTS
========================================================= */

function attachConnectionEvents() {

    const photos =
        document.querySelectorAll(
            ".profile-photo"
        );

    photos.forEach(photoElement => {

        photoElement.addEventListener(
            "click",
            function (event) {

                event.stopPropagation();

                const userId =
                    this.dataset.userId;

                const hasStatus =
                    this.dataset.hasStatus === "1";

                if (
                    hasStatus &&
                    userId
                ) {

                    openUserStatus(userId);

                    return;
                }


                const photo =
                    this.dataset.photo || "";

                const name =
                    this.dataset.name ||
                    "User";

                openDPViewer(
                    photo,
                    name
                );

            }
        );

    });
}


/* =========================================================
   OPEN USER PROFILE
========================================================= */

function openUserProfile(userId) {

    if (!userId) {
        return;
    }

    window.location.href =
        `/profile.html?user_id=${encodeURIComponent(userId)}`;
}


/* =========================================================
   CHAT
========================================================= */

function openChat(userId) {

    if (!userId) {
        return;
    }

    window.location.href =
        `/chat.html?user_id=${encodeURIComponent(userId)}`;
}


/* =========================================================
   SEARCH
========================================================= */

if (searchInput) {

    searchInput.addEventListener(
        "input",
        function () {

            clearTimeout(searchTimer);

            const query =
                this.value.trim();

            if (!query) {

                hideSearchResults();

                return;
            }

            searchTimer =
                setTimeout(
                    () => searchUsers(query),
                    300
                );
        }
    );

    searchInput.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Escape") {

                this.value = "";

                hideSearchResults();
            }
        }
    );
}


/* =========================================================
   SEARCH USERS
========================================================= */

async function searchUsers(query) {

    const currentId =
        getCurrentUserId();

    try {

        const response =
            await fetch(
                `/api/search?q=${encodeURIComponent(query)}&user_id=${encodeURIComponent(currentId)}`
            );

        if (!response.ok) {
            throw new Error("Search failed");
        }

        const data =
            await response.json();

        const users =
            data.users ||
            data.results ||
            data.data ||
            [];

        renderSearchResults(
            Array.isArray(users)
                ? users
                : []
        );

    } catch (error) {

        console.error(
            "Search error:",
            error
        );

        renderSearchResults([]);
    }
}


/* =========================================================
   SEARCH RESULTS
========================================================= */

function renderSearchResults(users) {

    if (!searchResults) {
        return;
    }

    if (!users.length) {

        searchResults.innerHTML = `
            <div style="
                padding:20px;
                color:#8190a5;
                text-align:center;
                font-size:13px;
            ">
                No users found
            </div>
        `;

        searchResults.classList.add("active");

        return;
    }


    searchResults.innerHTML =
        users
            .map(user => {

                const userId =
                    String(
                        user.user_id ||
                        user.username ||
                        user.id ||
                        ""
                    );

                const name =
                    user.name ||
                    user.full_name ||
                    userId ||
                    "User";

                const photo =
                    user.profile_photo ||
                    user.profilePhoto ||
                    "";

                const letter =
                    name
                        .trim()
                        .charAt(0)
                        .toUpperCase() || "U";


                return `
                    <div
                        style="
                            display:flex;
                            align-items:center;
                            gap:11px;
                            padding:11px 13px;
                            border-bottom:1px solid rgba(255,255,255,.05);
                            cursor:pointer;
                        "
                        onclick="openSearchUser('${escapeHtml(userId)}')">

                        <div
                            style="
                                width:42px;
                                height:42px;
                                border-radius:50%;
                                overflow:hidden;
                                flex:0 0 auto;
                                display:flex;
                                align-items:center;
                                justify-content:center;
                                background:#142743;
                                color:#fff;
                                font-weight:800;
                            ">

                            ${
                                photo
                                    ? `
                                        <img
                                            src="${escapeHtml(photo)}"
                                            style="
                                                width:100%;
                                                height:100%;
                                                object-fit:cover;
                                            "
                                            alt="${escapeHtml(name)}">
                                      `
                                    : escapeHtml(letter)
                            }

                        </div>


                        <div style="
                            min-width:0;
                            flex:1;
                        ">

                            <div style="
                                color:#fff;
                                font-size:13px;
                                font-weight:700;
                                white-space:nowrap;
                                overflow:hidden;
                                text-overflow:ellipsis;
                            ">
                                ${escapeHtml(name)}
                            </div>

                            <div style="
                                color:#718096;
                                font-size:10px;
                                margin-top:3px;
                            ">
                                @${escapeHtml(userId)}
                            </div>

                        </div>


                        <button
                            type="button"
                            style="
                                background:#1685ff;
                                color:#fff;
                                border:0;
                                border-radius:9px;
                                padding:7px 10px;
                                font-size:10px;
                                font-weight:700;
                            "
                            onclick="event.stopPropagation(); followUser('${escapeHtml(userId)}')">

                            Follow

                        </button>

                    </div>
                `;

            })
            .join("");


    searchResults.classList.add("active");
}


/* =========================================================
   OPEN SEARCH USER
========================================================= */

function openSearchUser(userId) {

    if (!userId) {
        return;
    }

    window.location.href =
        `/profile.html?user_id=${encodeURIComponent(userId)}`;
}


/* =========================================================
   HIDE SEARCH
========================================================= */

function hideSearchResults() {

    if (!searchResults) {
        return;
    }

    searchResults.classList.remove("active");
}


/* =========================================================
   FOLLOW
========================================================= */

async function followUser(userId) {

    const currentId =
        getCurrentUserId();

    if (!currentId || !userId) {
        return;
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

                    body: JSON.stringify({
                        user_id: currentId,
                        target_user_id: userId
                    })
                }
            );


        const data =
            await response.json()
                .catch(() => ({}));


        if (!response.ok) {

            showToast(
                data.detail ||
                data.message ||
                "Follow request failed"
            );

            return;
        }


        showToast(
            data.message ||
            "Follow request sent"
        );

    } catch (error) {

        console.error(
            "Follow error:",
            error
        );

        showToast(
            "Network error"
        );
    }
}


/* =========================================================
   =========================================================
   NOTIFICATIONS
   =========================================================
========================================================= */

async function loadNotificationCount() {

    const userId =
        getCurrentUserId();

    if (!userId) {
        return;
    }

    try {

        const response =
            await fetch(
                `/api/notifications?user_id=${encodeURIComponent(userId)}`
            );

        if (!response.ok) {
            return;
        }

        const data =
            await response.json();

        const notifications =
            data.notifications ||
            data.data ||
            [];

        const unread =
            Array.isArray(notifications)
                ? notifications.filter(
                    item =>
                        !item.is_read &&
                        !item.read
                ).length
                : (
                    data.unread_count ||
                    data.count ||
                    0
                );


        const badge =
            document.getElementById(
                "notificationBadge"
            );

        if (!badge) {
            return;
        }


        if (unread > 0) {

            badge.textContent =
                unread > 99
                    ? "99+"
                    : unread;

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


/* =========================================================
   =========================================================
   STATUS STATE
   =========================================================
========================================================= */

let myStatuses = [];

let activeStatusUsers = [];

let currentStatusUser = null;

let currentStatusIndex = 0;


/* =========================================================
   STATUS VIEWER STATE
========================================================= */

let statusViewerQueue = [];

let statusViewerUserIndex = -1;

let statusAdvanceTimer = null;

let statusViewerToken = 0;


/* =========================================================
   SEEN STORAGE
========================================================= */

function getSeenStorageKey() {

    const userId =
        getCurrentUserId();

    return (
        "usanex_seen_statuses_" +
        userId
    );
}


function getSeenStatusIds() {

    const key =
        getSeenStorageKey();

    try {

        const raw =
            localStorage.getItem(key);

        if (!raw) {
            return new Set();
        }

        const data =
            JSON.parse(raw);

        if (!Array.isArray(data)) {
            return new Set();
        }

        return new Set(
            data.map(String)
        );

    } catch (error) {

        return new Set();
    }
}


function saveSeenStatusIds(set) {

    const key =
        getSeenStorageKey();

    try {

        localStorage.setItem(
            key,
            JSON.stringify(
                Array.from(set)
            )
        );

    } catch (error) {

        console.error(
            "Seen status storage error:",
            error
        );
    }
}


function isStatusSeen(statusId) {

    if (
        statusId === null ||
        statusId === undefined
    ) {
        return false;
    }

    const seen =
        getSeenStatusIds();

    return seen.has(
        String(statusId)
    );
}


/* =========================================================
   MARK STATUS SEEN
========================================================= */

function markStatusAsSeen(statusId) {

    if (
        statusId === null ||
        statusId === undefined
    ) {
        return;
    }

    const seen =
        getSeenStatusIds();

    seen.add(
        String(statusId)
    );

    saveSeenStatusIds(seen);
}


/* =========================================================
   ACTIVE STATUS IDS
========================================================= */

function getCurrentActiveStatusIds() {

    const ids = [];

    myStatuses.forEach(status => {

        if (status && status.id !== undefined) {

            ids.push(
                String(status.id)
            );
        }

    });


    activeStatusUsers.forEach(user => {

        if (
            !user ||
            !Array.isArray(user.statuses)
        ) {
            return;
        }

        user.statuses.forEach(status => {

            if (
                status &&
                status.id !== undefined
            ) {

                ids.push(
                    String(status.id)
                );
            }

        });

    });


    return ids;
}


/* =========================================================
   CLEAN EXPIRED / OLD SEEN IDS
========================================================= */

function cleanupSeenStatusIds() {

    const activeIds =
        new Set(
            getCurrentActiveStatusIds()
        );

    const seen =
        getSeenStatusIds();

    const cleaned =
        new Set();

    seen.forEach(id => {

        if (activeIds.has(id)) {

            cleaned.add(id);
        }

    });

    saveSeenStatusIds(cleaned);
}


/* =========================================================
   USER FULLY SEEN
========================================================= */

function isUserFullySeen(user) {

    if (
        !user ||
        !Array.isArray(user.statuses) ||
        !user.statuses.length
    ) {
        return false;
    }

    return user.statuses.every(
        status =>
            isStatusSeen(status.id)
    );
}


/* =========================================================
   ORDER USER STATUSES
========================================================= */

function getOrderedStatuses(user) {

    if (
        !user ||
        !Array.isArray(user.statuses)
    ) {
        return [];
    }

    return [...user.statuses]
        .filter(status => status)
        .sort(
            (a, b) => {

                const aTime =
                    new Date(
                        a.created_at || 0
                    ).getTime();

                const bTime =
                    new Date(
                        b.created_at || 0
                    ).getTime();

                return aTime - bTime;
            }
        );
}


/* =========================================================
   =========================================================
   LOAD HOME STATUSES
   =========================================================
========================================================= */

async function loadHomeStatuses() {

    const userId =
        getCurrentUserId();

    if (!userId) {
        return;
    }

    try {

        const response =
            await fetch(
                `/api/status/home?user_id=${encodeURIComponent(userId)}`
            );

        if (!response.ok) {
            throw new Error(
                "Status home request failed"
            );
        }

        const data =
            await response.json();


        /* ================================================
           MY STATUS
        ================================================= */

        myStatuses =
            Array.isArray(data.my_statuses)
                ? data.my_statuses
                : [];


        /* ================================================
           OTHER USERS
        ================================================= */

        const users =
            Array.isArray(data.users)
                ? data.users
                : [];


        activeStatusUsers =
            users
                .map(user => {

                    return {
                        ...user,

                        statuses:
                            getOrderedStatuses(user)
                    };

                })
                .filter(
                    user =>
                        user.statuses.length > 0
                );


        cleanupSeenStatusIds();

        updateMyStatusUI();

        renderActiveStatusUsers();

        refreshConnectionStatusRings();

    } catch (error) {

        console.error(
            "Home status loading error:",
            error
        );
    }
}


/* =========================================================
   COMPATIBILITY: MY STATUS
========================================================= */

async function loadMyStatuses() {

    const userId =
        getCurrentUserId();

    if (!userId) {
        return;
    }

    try {

        const response =
            await fetch(
                `/api/status/my?user_id=${encodeURIComponent(userId)}`
            );

        if (!response.ok) {
            return;
        }

        const data =
            await response.json();

        myStatuses =
            Array.isArray(data.statuses)
                ? data.statuses
                : (
                    Array.isArray(data)
                        ? data
                        : []
                );

        updateMyStatusUI();

    } catch (error) {

        console.error(
            "My status loading error:",
            error
        );
    }
}


/* =========================================================
   COMPATIBILITY: ACTIVE STATUS
========================================================= */

async function loadActiveStatuses() {

    const userId =
        getCurrentUserId();

    if (!userId) {
        return;
    }

    try {

        const response =
            await fetch(
                `/api/status/active?user_id=${encodeURIComponent(userId)}`
            );

        if (!response.ok) {
            return;
        }

        const data =
            await response.json();

        const users =
            Array.isArray(data.users)
                ? data.users
                : (
                    Array.isArray(data)
                        ? data
                        : []
                );


        activeStatusUsers =
            users
                .map(user => ({
                    ...user,
                    statuses:
                        getOrderedStatuses(user)
                }))
                .filter(
                    user =>
                        user.statuses.length
                );


        cleanupSeenStatusIds();

        renderActiveStatusUsers();

        refreshConnectionStatusRings();

    } catch (error) {

        console.error(
            "Active status loading error:",
            error
        );
    }
}


/* =========================================================
   =========================================================
   YOUR STATUS UI
   =========================================================
========================================================= */

function updateMyStatusUI() {

    const item =
        document.getElementById(
            "myStatusItem"
        );

    if (!item) {
        return;
    }


    updateYourStatusLetter();


    const hasStatus =
        myStatuses.length > 0;


    item.classList.toggle(
        "has-status",
        hasStatus
    );


    /*
       NO STATUS:
       Whole card opens upload.

       HAS STATUS:
       Main card opens own status.

       PLUS:
       Always opens upload/add status.
    */

    item.onclick =
        function (event) {

            if (
                event.target.closest(
                    "#myStatusPlus"
                )
            ) {
                return;
            }

            if (myStatuses.length > 0) {

                openMyStatus();

            } else {

                window.location.href =
                    "/status";
            }
        };
}


/* =========================================================
   ADD ANOTHER STATUS
========================================================= */

function addAnotherStatus(event) {

    if (event) {
        event.stopPropagation();
    }

    window.location.href =
        "/status";
}


/* =========================================================
   OPEN MY STATUS
========================================================= */

function openMyStatus() {

    if (!myStatuses.length) {

        window.location.href =
            "/status";

        return;
    }


    currentStatusUser = {

        user_id:
            getCurrentUserId(),

        name:
            currentUser?.name ||
            "You",

        profile_photo:
            currentUser?.profile_photo ||
            currentUser?.profilePhoto ||
            "",

        statuses:
            getOrderedStatuses({
                statuses:
                    myStatuses
            })
    };


    currentStatusIndex = 0;

    statusViewerQueue =
        [currentStatusUser];

    statusViewerUserIndex = 0;

    showStatusViewer();
}


/* =========================================================
   =========================================================
   RENDER OTHER STATUS USERS
   =========================================================
========================================================= */

function renderActiveStatusUsers() {

    const container =
        document.getElementById(
            "otherStatusScroll"
        );

    if (!container) {
        return;
    }


    const users =
        activeStatusUsers
            .filter(
                user =>
                    user &&
                    Array.isArray(user.statuses) &&
                    user.statuses.length > 0
            )
            .sort(
                (a, b) => {

                    const aSeen =
                        isUserFullySeen(a);

                    const bSeen =
                        isUserFullySeen(b);


                    if (
                        aSeen !== bSeen
                    ) {

                        return aSeen
                            ? 1
                            : -1;
                    }


                    const aLatest =
                        Math.max(
                            ...a.statuses.map(
                                s =>
                                    new Date(
                                        s.created_at || 0
                                    ).getTime()
                            )
                        );


                    const bLatest =
                        Math.max(
                            ...b.statuses.map(
                                s =>
                                    new Date(
                                        s.created_at || 0
                                    ).getTime()
                            )
                        );


                    return bLatest - aLatest;
                }
            );


    if (!users.length) {

        container.innerHTML = "";

        return;
    }


    container.innerHTML =
        users
            .map(user => {

                const name =
                    user.name ||
                    user.user_id ||
                    "User";

                const userId =
                    String(
                        user.user_id || ""
                    );

                const photo =
                    user.profile_photo ||
                    user.profilePhoto ||
                    "";

                const letter =
                    name
                        .trim()
                        .charAt(0)
                        .toUpperCase() || "U";


                const fullySeen =
                    isUserFullySeen(user);


                const statusClass =
                    fullySeen
                        ? "seen"
                        : "unseen";


                const avatar =
                    photo
                        ? `
                            <img
                                src="${escapeHtml(photo)}"
                                alt="${escapeHtml(name)}">
                          `
                        : `
                            <span>
                                ${escapeHtml(letter)}
                            </span>
                          `;


                return `
                    <div
                        class="status-item"
                        data-user-id="${escapeHtml(userId)}">

                        <div
                            class="status-circle ${statusClass}">

                            <div
                                class="status-avatar-inner">

                                ${avatar}

                            </div>

                        </div>


                        <div class="status-name">
                            ${escapeHtml(name)}
                        </div>

                    </div>
                `;

            })
            .join("");


    container
        .querySelectorAll(".status-item")
        .forEach(item => {

            item.addEventListener(
                "click",
                () => {

                    openUserStatus(
                        item.dataset.userId
                    );

                }
            );

        });
}


/* =========================================================
   REFRESH CONNECTION STATUS RINGS
========================================================= */

function refreshConnectionStatusRings() {

    if (!connectedUsersData.length) {
        return;
    }

    renderConnections(
        connectedUsersData
    );
}


/* =========================================================
   =========================================================
   OPEN OTHER USER STATUS
   =========================================================
========================================================= */

function openUserStatus(userId) {

    if (!userId) {
        return;
    }


    const user =
        activeStatusUsers.find(
            item =>
                String(item.user_id) ===
                String(userId)
        );


    if (!user) {
        return;
    }


    const statuses =
        getOrderedStatuses(user);


    if (!statuses.length) {
        return;
    }


    currentStatusUser = {

        ...user,

        statuses:
            statuses
    };


    /*
       Viewer starts from clicked user.

       After this user's statuses,
       it continues to next active users.
    */

    const sortedUsers =
        [...activeStatusUsers]
            .filter(
                item =>
                    item &&
                    Array.isArray(item.statuses) &&
                    item.statuses.length
            )
            .sort(
                (a, b) => {

                    const aSeen =
                        isUserFullySeen(a);

                    const bSeen =
                        isUserFullySeen(b);

                    if (
                        aSeen !== bSeen
                    ) {
                        return aSeen
                            ? 1
                            : -1;
                    }

                    return 0;
                }
            );


    const clickedIndex =
        sortedUsers.findIndex(
            item =>
                String(item.user_id) ===
                String(userId)
        );


    if (clickedIndex >= 0) {

        statusViewerQueue = [
            ...sortedUsers.slice(clickedIndex),
            ...sortedUsers.slice(0, clickedIndex)
        ];

    } else {

        statusViewerQueue =
            sortedUsers;
    }


    /*
       Make clicked user first.
    */

    if (
        statusViewerQueue.length &&
        String(
            statusViewerQueue[0].user_id
        ) !== String(userId)
    ) {

        statusViewerQueue =
            [
                currentStatusUser,
                ...statusViewerQueue.filter(
                    item =>
                        String(item.user_id) !==
                        String(userId)
                )
            ];
    }


    statusViewerUserIndex = 0;

    currentStatusUser =
        statusViewerQueue[0];

    currentStatusIndex = 0;

    showStatusViewer();
}


/* =========================================================
   =========================================================
   STATUS VIEWER HELPERS
   =========================================================
========================================================= */

function clearStatusAdvanceTimer() {

    if (statusAdvanceTimer) {

        clearTimeout(
            statusAdvanceTimer
        );

        statusAdvanceTimer = null;
    }
}


/* =========================================================
   FORMAT STATUS TIME
========================================================= */

function formatStatusTime(dateValue) {

    if (!dateValue) {
        return "now";
    }

    const time =
        new Date(dateValue).getTime();

    if (Number.isNaN(time)) {
        return "now";
    }


    const diff =
        Math.max(
            0,
            Date.now() - time
        );


    const seconds =
        Math.floor(
            diff / 1000
        );

    if (seconds < 60) {
        return "now";
    }


    const minutes =
        Math.floor(
            seconds / 60
        );

    if (minutes < 60) {
        return `${minutes}m`;
    }


    const hours =
        Math.floor(
            minutes / 60
        );

    if (hours < 24) {
        return `${hours}h`;
    }


    const days =
        Math.floor(
            hours / 24
        );

    return `${days}d`;
}


/* =========================================================
   SET VIEWER AVATAR
========================================================= */

function setViewerAvatar(
    element,
    photo,
    name
) {

    if (!element) {
        return;
    }


    const letter =
        String(
            name ||
            "U"
        )
            .trim()
            .charAt(0)
            .toUpperCase() || "U";


    if (photo) {

        element.innerHTML =
            `
                <img
                    src="${escapeHtml(photo)}"
                    alt="${escapeHtml(name || "User")}">
            `;

    } else {

        element.innerHTML =
            escapeHtml(letter);
    }
}


/* =========================================================
   RENDER PROGRESS
========================================================= */

function renderStatusProgress(
    total,
    currentIndex
) {

    const progress =
        document.getElementById(
            "statusProgress"
        );

    if (!progress) {
        return;
    }


    progress.innerHTML = "";


    for (
        let i = 0;
        i < total;
        i++
    ) {

        const segment =
            document.createElement("div");

        segment.className =
            "status-progress-segment";


        const fill =
            document.createElement("div");

        fill.className =
            "status-progress-fill";


        if (i < currentIndex) {

            fill.style.width =
                "100%";

        } else {

            fill.style.width =
                "0%";
        }


        segment.appendChild(fill);

        progress.appendChild(segment);
    }
}


/* =========================================================
   CURRENT PROGRESS FILL
========================================================= */

function getCurrentProgressFill() {

    const progress =
        document.getElementById(
            "statusProgress"
        );

    if (!progress) {
        return null;
    }


    const segments =
        progress.querySelectorAll(
            ".status-progress-segment"
        );


    if (
        currentStatusIndex < 0 ||
        currentStatusIndex >= segments.length
    ) {
        return null;
    }


    return segments[
        currentStatusIndex
    ].querySelector(
        ".status-progress-fill"
    );
}


/* =========================================================
   IMAGE AUTO PROGRESS
========================================================= */

function startImageProgress(
    token
) {

    const fill =
        getCurrentProgressFill();

    if (!fill) {
        return;
    }


    const duration =
        5000;


    fill.style.transition =
        "none";

    fill.style.width =
        "0%";


    requestAnimationFrame(() => {

        if (
            token !==
            statusViewerToken
        ) {
            return;
        }


        fill.style.transition =
            `width ${duration}ms linear`;

        fill.style.width =
            "100%";

    });


    statusAdvanceTimer =
        setTimeout(
            () => {

                if (
                    token !==
                    statusViewerToken
                ) {
                    return;
                }

                advanceStatus();

            },
            duration
        );
}


/* =========================================================
   VIDEO PROGRESS
========================================================= */

function setupVideoStatus(
    video,
    token
) {

    if (!video) {
        return;
    }


    video.addEventListener(
        "timeupdate",
        () => {

            if (
                token !==
                statusViewerToken
            ) {
                return;
            }


            if (
                !Number.isFinite(
                    video.duration
                ) ||
                video.duration <= 0
            ) {
                return;
            }


            const percentage =
                (
                    video.currentTime /
                    video.duration
                ) * 100;


            const fill =
                getCurrentProgressFill();


            if (fill) {

                fill.style.transition =
                    "none";

                fill.style.width =
                    `${Math.min(
                        100,
                        Math.max(
                            0,
                            percentage
                        )
                    )}%`;
            }

        }
    );


    video.addEventListener(
        "ended",
        () => {

            if (
                token !==
                statusViewerToken
            ) {
                return;
            }

            advanceStatus();

        }
    );


    video.addEventListener(
        "error",
        () => {

            if (
                token !==
                statusViewerToken
            ) {
                return;
            }


            /*
               If video cannot load,
               move forward instead of
               leaving viewer stuck.
            */

            statusAdvanceTimer =
                setTimeout(
                    () => {

                        advanceStatus();

                    },
                    3000
                );

        }
    );


    video.addEventListener(
        "click",
        () => {

            try {

                if (video.paused) {

                    video.muted = false;

                    video.play();

                } else {

                    video.pause();
                }

            } catch (error) {

                console.error(
                    "Video control error:",
                    error
                );
            }

        }
    );


    /*
       Try normal autoplay first.
    */

    const playPromise =
        video.play();


    if (
        playPromise &&
        typeof playPromise.catch ===
        "function"
    ) {

        playPromise.catch(() => {

            /*
               Browser may block
               autoplay with sound.

               Retry muted so the
               automatic viewer does
               not get stuck.
            */

            try {

                video.muted = true;

                video.play();

            } catch (error) {

                console.error(
                    "Video autoplay error:",
                    error
                );
            }

        });
    }
}


/* =========================================================
   =========================================================
   SHOW STATUS VIEWER
   =========================================================
========================================================= */

function showStatusViewer() {

    clearStatusAdvanceTimer();

    statusViewerToken++;


    const token =
        statusViewerToken;


    if (
        !currentStatusUser ||
        !Array.isArray(
            currentStatusUser.statuses
        )
    ) {

        closeStatusViewer();

        return;
    }


    const statuses =
        getOrderedStatuses(
            currentStatusUser
        );


    currentStatusUser.statuses =
        statuses;


    if (!statuses.length) {

        closeStatusViewer();

        return;
    }


    if (
        currentStatusIndex < 0 ||
        currentStatusIndex >= statuses.length
    ) {

        currentStatusIndex = 0;
    }


    const status =
        statuses[
            currentStatusIndex
        ];


    if (!status) {

        closeStatusViewer();

        return;
    }


    const viewer =
        document.getElementById(
            "statusViewer"
        );


    const media =
        document.getElementById(
            "statusViewerMedia"
        );


    const nameElement =
        document.getElementById(
            "statusViewerName"
        );


    const userIdElement =
        document.getElementById(
            "statusViewerUserId"
        );


    const timeElement =
        document.getElementById(
            "statusViewerTime"
        );


    const avatarElement =
        document.getElementById(
            "statusViewerAvatar"
        );


    const miniAvatar =
        document.getElementById(
            "statusMiniAvatar"
        );


    const miniName =
        document.getElementById(
            "statusMiniName"
        );


    const miniId =
        document.getElementById(
            "statusMiniId"
        );


    if (!viewer || !media) {
        return;
    }


    const userName =
        currentStatusUser.name ||
        currentStatusUser.user_id ||
        "User";


    const userId =
        String(
            currentStatusUser.user_id ||
            ""
        );


    const photo =
        currentStatusUser.profile_photo ||
        currentStatusUser.profilePhoto ||
        "";


    const isOwnStatus =
        String(userId) ===
        String(getCurrentUserId());


    /* ================================================
       VIEWER OPEN
    ================================================= */

    viewer.classList.add("active");

    viewer.classList.toggle(
        "status-viewer-own",
        isOwnStatus
    );


    viewer.setAttribute(
        "aria-hidden",
        "false"
    );


    document.body.style.overflow =
        "hidden";


    /* ================================================
       USER DATA
    ================================================= */

    if (nameElement) {

        nameElement.textContent =
            userName;
    }


    if (userIdElement) {

        userIdElement.textContent =
            userId
                ? `@${userId}`
                : "";
    }


    if (timeElement) {

        timeElement.textContent =
            formatStatusTime(
                status.created_at
            );
    }


    setViewerAvatar(
        avatarElement,
        photo,
        userName
    );


    setViewerAvatar(
        miniAvatar,
        photo,
        userName
    );


    if (miniName) {

        miniName.textContent =
            userName;
    }


    if (miniId) {

        miniId.textContent =
            userId
                ? `@${userId}`
                : "";
    }


    /* ================================================
       PROGRESS
    ================================================= */

    renderStatusProgress(
        statuses.length,
        currentStatusIndex
    );


    /* ================================================
       CLEAR MEDIA
    ================================================= */

    media.innerHTML = "";


    /* ================================================
       MARK SEEN
       Only OTHER users' status.
    ================================================= */

    if (!isOwnStatus) {

        markStatusAsSeen(
            status.id
        );

        /*
           Re-render circles after marking
           the current status as seen.
        */

        setTimeout(
            () => {

                renderActiveStatusUsers();

                refreshConnectionStatusRings();

            },
            0
        );
    }


    /* ================================================
       IMAGE
    ================================================= */

    const mediaType =
        String(
            status.media_type ||
            ""
        ).toLowerCase();


    const isVideo =
        mediaType.includes(
            "video"
        );


    if (!isVideo) {

        const image =
            document.createElement("img");


        image.src =
            status.media_url;


        image.alt =
            `${userName} status`;


        image.draggable =
            false;


        image.addEventListener(
            "error",
            () => {

                media.innerHTML = `
                    <div class="status-media-error">
                        Status media load nahi ho paya.
                    </div>
                `;

            }
        );


        media.appendChild(
            image
        );


        startImageProgress(
            token
        );

    } else {

        /* ==========================================
           VIDEO
        ========================================== */

        const video =
            document.createElement("video");


        video.src =
            status.media_url;


        video.playsInline =
            true;


        video.autoplay =
            true;


        video.preload =
            "auto";


        video.controls =
            false;


        video.setAttribute(
            "playsinline",
            ""
        );


        video.setAttribute(
            "webkit-playsinline",
            ""
        );


        video.addEventListener(
            "loadedmetadata",
            () => {

                if (
                    token !==
                    statusViewerToken
                ) {
                    return;
                }


                const fill =
                    getCurrentProgressFill();


                if (
                    fill &&
                    video.duration > 0
                ) {

                    fill.style.width =
                        "0%";
                }

            }
        );


        media.appendChild(
            video
        );


        setupVideoStatus(
            video,
            token
        );

    }


    /* ================================================
       COMMENT INPUT
    ================================================= */

    const commentInput =
        document.getElementById(
            "statusCommentInput"
        );


    if (commentInput) {

        commentInput.value =
            "";


        commentInput.onkeydown =
            function (event) {

                if (
                    event.key ===
                    "Enter"
                ) {

                    event.preventDefault();

                    submitStatusComment();
                }

            };
    }
}


/* =========================================================
   =========================================================
   AUTOMATIC NEXT STATUS
   =========================================================
========================================================= */

function advanceStatus() {

    clearStatusAdvanceTimer();


    if (
        !currentStatusUser
    ) {

        closeStatusViewer();

        return;
    }


    const statuses =
        getOrderedStatuses(
            currentStatusUser
        );


    currentStatusUser.statuses =
        statuses;


    /* ================================================
       NEXT STATUS OF SAME USER
    ================================================= */

    if (
        currentStatusIndex <
        statuses.length - 1
    ) {

        currentStatusIndex++;

        showStatusViewer();

        return;
    }


    /* ================================================
       NEXT USER
    ================================================= */

    const nextUserIndex =
        statusViewerUserIndex + 1;


    if (
        nextUserIndex <
        statusViewerQueue.length
    ) {

        const nextUser =
            statusViewerQueue[
                nextUserIndex
            ];


        const nextStatuses =
            getOrderedStatuses(
                nextUser
            );


        if (nextStatuses.length) {

            statusViewerUserIndex =
                nextUserIndex;

            currentStatusUser = {
                ...nextUser,

                statuses:
                    nextStatuses
            };

            currentStatusIndex =
                0;

            showStatusViewer();

            return;
        }

    }


    /* ================================================
       EVERYTHING FINISHED
    ================================================= */

    closeStatusViewer();
}


/* =========================================================
   COMPATIBILITY NEXT STATUS
========================================================= */

function nextStatus() {

    advanceStatus();
}


/* =========================================================
   PREVIOUS STATUS
   No UI arrow.
   Kept only for compatibility.
========================================================= */

function previousStatus() {

    clearStatusAdvanceTimer();


    if (
        !currentStatusUser
    ) {
        return;
    }


    if (
        currentStatusIndex > 0
    ) {

        currentStatusIndex--;

        showStatusViewer();

        return;
    }


    if (
        statusViewerUserIndex > 0
    ) {

        statusViewerUserIndex--;

        const previousUser =
            statusViewerQueue[
                statusViewerUserIndex
            ];


        const statuses =
            getOrderedStatuses(
                previousUser
            );


        if (statuses.length) {

            currentStatusUser = {
                ...previousUser,

                statuses:
                    statuses
            };

            currentStatusIndex =
                statuses.length - 1;

            showStatusViewer();
        }
    }
}


/* =========================================================
   =========================================================
   CLOSE STATUS VIEWER
   =========================================================
========================================================= */

function closeStatusViewer() {

    clearStatusAdvanceTimer();

    statusViewerToken++;


    const viewer =
        document.getElementById(
            "statusViewer"
        );


    const media =
        document.getElementById(
            "statusViewerMedia"
        );


    if (media) {

        const video =
            media.querySelector(
                "video"
            );

        if (video) {

            try {
                video.pause();
            } catch (error) {
                console.error(error);
            }
        }


        media.innerHTML = "";
    }


    if (viewer) {

        viewer.classList.remove(
            "active"
        );

        viewer.classList.remove(
            "status-viewer-own"
        );

        viewer.setAttribute(
            "aria-hidden",
            "true"
        );
    }


    document.body.style.overflow =
        "";


    currentStatusUser =
        null;

    currentStatusIndex =
        0;

    statusViewerQueue =
        [];

    statusViewerUserIndex =
        -1;
}


/* =========================================================
   =========================================================
   STATUS INTERACTIONS
   =========================================================
========================================================= */

function likeCurrentStatus() {

    /*
       UI is ready.
       Backend like endpoint can be
       connected later without changing
       the viewer structure.
    */

    showToast(
        "Like feature backend se connect karna baaki hai."
    );
}


function submitStatusComment() {

    const input =
        document.getElementById(
            "statusCommentInput"
        );

    if (!input) {
        return;
    }


    const text =
        input.value.trim();


    if (!text) {
        return;
    }


    /*
       Backend comment endpoint abhi
       existing status API mein nahi hai.
    */

    showToast(
        "Comment feature backend se connect karna baaki hai."
    );
}


function shareCurrentStatus() {

    if (
        !currentStatusUser
    ) {
        return;
    }


    const userId =
        currentStatusUser.user_id ||
        "";


    const shareUrl =
        `${window.location.origin}/profile.html?user_id=${encodeURIComponent(userId)}`;


    if (
        navigator.share
    ) {

        navigator.share({

            title:
                `${currentStatusUser.name || "User"} • Usanex`,

            text:
                `Usanex par ${currentStatusUser.name || "User"} ka profile dekhein.`,

            url:
                shareUrl

        }).catch(() => {});

        return;
    }


    if (
        navigator.clipboard &&
        navigator.clipboard.writeText
    ) {

        navigator.clipboard
            .writeText(shareUrl)
            .then(() => {

                showToast(
                    "Profile link copied."
                );

            })
            .catch(() => {

                showToast(
                    "Share link copy nahi ho paya."
                );

            });

        return;
    }


    showToast(
        "Share supported nahi hai."
    );
}


function reportCurrentStatus() {

    showToast(
        "Report feature backend se connect karna baaki hai."
    );
}


function mentionCurrentStatus() {

    if (
        !currentStatusUser
    ) {
        return;
    }


    const input =
        document.getElementById(
            "statusCommentInput"
        );


    if (!input) {
        return;
    }


    const userId =
        currentStatusUser.user_id ||
        "";


    const mention =
        userId
            ? `@${userId} `
            : "";


    if (
        !input.value.startsWith(
            mention
        )
    ) {

        input.value =
            mention +
            input.value;
    }


    input.focus();
}


/* =========================================================
   SHOW ALL STATUSES
========================================================= */

function showAllStatuses() {

    if (
        !activeStatusUsers.length
    ) {

        showToast(
            "Abhi koi active status nahi hai."
        );

        return;
    }


    const sorted =
        [...activeStatusUsers]
            .sort(
                (a, b) => {

                    const aSeen =
                        isUserFullySeen(a);

                    const bSeen =
                        isUserFullySeen(b);


                    if (
                        aSeen !== bSeen
                    ) {

                        return aSeen
                            ? 1
                            : -1;
                    }


                    return 0;
                }
            );


    if (sorted.length) {

        openUserStatus(
            sorted[0].user_id
        );
    }
}


/* =========================================================
   =========================================================
   DP VIEWER
   =========================================================
========================================================= */

function openDPViewer(
    photo,
    name
) {

    const viewer =
        document.getElementById(
            "dpViewer"
        );

    const image =
        document.getElementById(
            "dpViewerImage"
        );

    const nameElement =
        document.getElementById(
            "dpViewerName"
        );


    if (!viewer) {
        return;
    }


    if (image) {

        image.src =
            photo || "";
    }


    if (nameElement) {

        nameElement.textContent =
            name || "User";
    }


    viewer.classList.add(
        "active"
    );

    document.body.style.overflow =
        "hidden";
}


function closeDPViewer(event) {

    if (
        event &&
        event.stopPropagation
    ) {

        event.stopPropagation();
    }


    const viewer =
        document.getElementById(
            "dpViewer"
        );


    if (!viewer) {
        return;
    }


    viewer.classList.remove(
        "active"
    );

    document.body.style.overflow =
        "";
}


/* =========================================================
   =========================================================
   NAVIGATION
   =========================================================
========================================================= */

function goHome() {

    window.location.href =
        "/home.html";
}


function goReels() {

    window.location.href =
        "/reels.html";
}


function createPost() {

    /*
       Existing project can later route
       this to post/status creation.
    */

    window.location.href =
        "/status";
}


function goNotifications() {

    window.location.href =
        "/notifications.html";
}


function goProfile() {

    const userId =
        getCurrentUserId();


    if (userId) {

        window.location.href =
            `/profile.html?user_id=${encodeURIComponent(userId)}`;

    } else {

        window.location.href =
            "/profile.html";
    }
}


/* =========================================================
   MENU NAVIGATION
========================================================= */

function goMonetization() {

    window.location.href =
        "/monetization.html";
}


function goBlocked() {

    window.location.href =
        "/blocked.html";
}


function goPrivacy() {

    window.location.href =
        "/privacy.html";
}


function goSettings() {

    window.location.href =
        "/settings.html";
}


function goHelp() {

    window.location.href =
        "/help.html";
}


function goAbout() {

    window.location.href =
        "/about.html";
}


/* =========================================================
   LOGOUT
========================================================= */

function logoutUser() {

    const confirmed =
        window.confirm(
            "Logout from Usanex?"
        );


    if (!confirmed) {
        return;
    }


    const keys = [
        "currentUser",
        "user",
        "usanex_user",
        "loggedInUser"
    ];


    keys.forEach(key => {

        localStorage.removeItem(
            key
        );

    });


    sessionStorage.clear();


    window.location.href =
        "/login.html";
}


/* =========================================================
   =========================================================
   MENU
   =========================================================
========================================================= */

if (menuBtn) {

    menuBtn.addEventListener(
        "click",
        function (event) {

            event.stopPropagation();

            if (menuOverlay) {

                menuOverlay.classList.toggle(
                    "active"
                );
            }
        }
    );
}


if (menuOverlay) {

    menuOverlay.addEventListener(
        "click",
        function (event) {

            if (
                event.target ===
                menuOverlay
            ) {

                menuOverlay.classList.remove(
                    "active"
                );
            }
        }
    );
}


/* =========================================================
   SEARCH OUTSIDE CLICK
========================================================= */

document.addEventListener(
    "click",
    function (event) {

        if (
            searchResults &&
            searchInput &&
            !searchResults.contains(event.target) &&
            !searchInput.contains(event.target)
        ) {

            hideSearchResults();
        }
    }
);


/* =========================================================
   ESCAPE KEY
========================================================= */

document.addEventListener(
    "keydown",
    function (event) {

        if (
            event.key !== "Escape"
        ) {
            return;
        }


        const statusViewer =
            document.getElementById(
                "statusViewer"
            );


        const dpViewer =
            document.getElementById(
                "dpViewer"
            );


        if (
            statusViewer &&
            statusViewer.classList.contains(
                "active"
            )
        ) {

            closeStatusViewer();

            return;
        }


        if (
            dpViewer &&
            dpViewer.classList.contains(
                "active"
            )
        ) {

            closeDPViewer();

            return;
        }


        if (menuOverlay) {

            menuOverlay.classList.remove(
                "active"
            );
        }


        hideSearchResults();
    }
);


/* =========================================================
   =========================================================
   INITIALIZE HOME
   =========================================================
========================================================= */

async function initializeHome() {

    const user =
        resolveCurrentUser();


    if (!user) {

        /*
           Existing login system should normally
           provide currentUser.

           Do not redirect aggressively here,
           because some existing login flows
           may initialize storage asynchronously.
        */

        console.warn(
            "Usanex: current user not found."
        );
    }


    updateYourStatusLetter();


    /*
       Keep existing loading order:
       Connections first,
       then Status data refreshes
       connection status rings.
    */

    await loadConnections();

    await loadNotificationCount();

    await loadHomeStatuses();


    /*
       Notification refresh.
    */

    clearInterval(
        notificationTimer
    );


    notificationTimer =
        setInterval(
            () => {

                loadNotificationCount();

            },
            30000
        );


    /*
       Status refresh every 30 seconds.
       This helps remove expired statuses
       without requiring page refresh.
    */

    setInterval(
        () => {

            loadHomeStatuses();

        },
        30000
    );


    /*
       New user hint.
    */

    const hint =
        document.getElementById(
            "statusNewUserHint"
        );


    if (hint) {

        const hintShown =
            localStorage.getItem(
                "usanex_status_hint_seen"
            );


        if (hintShown) {

            hint.style.display =
                "none";

        } else {

            setTimeout(
                () => {

                    hint.style.display =
                        "none";

                    localStorage.setItem(
                        "usanex_status_hint_seen",
                        "1"
                    );

                },
                7000
            );
        }
    }
}


/* =========================================================
   GLOBAL FUNCTIONS
   Required by HTML onclick handlers
========================================================= */

window.addAnotherStatus =
    addAnotherStatus;

window.openMyStatus =
    openMyStatus;

window.openUserStatus =
    openUserStatus;

window.showAllStatuses =
    showAllStatuses;

window.nextStatus =
    nextStatus;

window.previousStatus =
    previousStatus;

window.closeStatusViewer =
    closeStatusViewer;

window.likeCurrentStatus =
    likeCurrentStatus;

window.submitStatusComment =
    submitStatusComment;

window.shareCurrentStatus =
    shareCurrentStatus;

window.reportCurrentStatus =
    reportCurrentStatus;

window.mentionCurrentStatus =
    mentionCurrentStatus;

window.openDPViewer =
    openDPViewer;

window.closeDPViewer =
    closeDPViewer;

window.goHome =
    goHome;

window.goReels =
    goReels;

window.createPost =
    createPost;

window.goNotifications =
    goNotifications;

window.goProfile =
    goProfile;

window.goMonetization =
    goMonetization;

window.goBlocked =
    goBlocked;

window.goPrivacy =
    goPrivacy;

window.goSettings =
    goSettings;

window.goHelp =
    goHelp;

window.goAbout =
    goAbout;

window.logoutUser =
    logoutUser;

window.openUserProfile =
    openUserProfile;

window.openChat =
    openChat;

window.openSearchUser =
    openSearchUser;

window.followUser =
    followUser;


/* =========================================================
   START
========================================================= */

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
