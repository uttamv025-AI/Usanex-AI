"use strict";

/* =========================================================
   USANEX HOME.JS
   Uses logged-in user saved by register.html
========================================================= */

let currentUser = null;
let searchTimer = null;
let notificationTimer = null;


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
   USER
========================================================= */

function normalizeUser(value) {

    if (!value) {
        return null;
    }

    if (typeof value === "string") {

        const text = value.trim();

        if (!text) {
            return null;
        }

        try {

            value = JSON.parse(text);

        } catch (error) {

            return {
                user_id: text,
                name: text,
                mobile: "",
                profile_photo: ""
            };

        }

    }

    if (value.user) {
        value = value.user;
    }

    const userId =
        value.user_id ||
        value.userId ||
        value.id;

    if (!userId) {
        return null;
    }

    return {

        user_id: String(userId),

        name:
            value.name ||
            value.full_name ||
            value.username ||
            String(userId),

        mobile:
            value.mobile || "",

        profile_photo:
            value.profile_photo ||
            value.profile_picture ||
            ""

    };

}


/* =========================================================
   GET USER FROM LOCAL STORAGE
========================================================= */

function getStoredCurrentUser() {

    const keys = [

        "user",
        "currentUser",
        "usanexUser",
        "loggedInUser",
        "userData",
        "user_id",
        "userId"

    ];

    for (const key of keys) {

        const raw =
            localStorage.getItem(key);

        if (!raw) {
            continue;
        }

        const user =
            normalizeUser(raw);

        if (user) {

            return user;

        }

    }

    return null;

}


/* =========================================================
   RESOLVE CURRENT USER
========================================================= */

async function resolveCurrentUser() {

    currentUser =
        getStoredCurrentUser();

    if (currentUser) {

        updateYourStatusAvatar();

        return currentUser;

    }

    console.error(
        "Usanex: logged-in user not found in localStorage."
    );

    return null;

}


/* =========================================================
   YOUR STATUS AVATAR
========================================================= */

function updateYourStatusAvatar() {

    const letter =
        document.getElementById("youLetter");

    if (!letter || !currentUser) {
        return;
    }

    const name =
        currentUser.name ||
        currentUser.user_id ||
        "U";

    letter.textContent =
        name.charAt(0).toUpperCase();

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

    toast.textContent =
        message;

    toast.classList.add("show");

    clearTimeout(
        showToast.timer
    );

    showToast.timer =
        setTimeout(() => {

            toast.classList.remove("show");

        }, 2200);

}


/* =========================================================
   HTML ESCAPE
========================================================= */

function escapeHtml(value) {

    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}


/* =========================================================
   LOAD CONNECTIONS
========================================================= */

async function loadConnections() {

    const list =
        document.getElementById(
            "connectionsList"
        );

    const count =
        document.getElementById(
            "connectionCount"
        );

    if (!list) {
        return;
    }

    if (
        !currentUser ||
        !currentUser.user_id
    ) {

        list.innerHTML = `

            <div class="empty-box">

                <div class="empty-icon">
                    ⚠
                </div>

                <div class="empty-title">
                    Login information not found
                </div>

                <div class="empty-text">
                    Please login again.
                </div>

            </div>

        `;

        if (count) {
            count.textContent = "0";
        }

        return;

    }


    list.innerHTML = `

        <div class="empty-box">

            <div class="empty-icon">
                ◌
            </div>

            <div class="empty-title">
                Loading connections...
            </div>

            <div class="empty-text">
                Please wait
            </div>

        </div>

    `;


    const userId =
        encodeURIComponent(
            currentUser.user_id
        );


    let data = null;


    /* =====================================================
       PRIMARY API
    ===================================================== */

    try {

        const response =
            await fetch(
                `/api/home/connections?user_id=${userId}`,
                {
                    cache: "no-store"
                }
            );


        if (response.ok) {

            const result =
                await response.json();

            if (result.ok !== false) {

                data = result;

            }

        }

    } catch (error) {

        console.error(
            "Home connections API error:",
            error
        );

    }


    /* =====================================================
       FALLBACK API
    ===================================================== */

    if (!data) {

        try {

            const response =
                await fetch(
                    `/api/connections?user_id=${userId}`,
                    {
                        cache: "no-store"
                    }
                );


            if (response.ok) {

                const result =
                    await response.json();

                if (result.ok !== false) {

                    data = result;

                }

            }

        } catch (error) {

            console.error(
                "Fallback connections API error:",
                error
            );

        }

    }


    if (!data) {

        list.innerHTML = `

            <div class="empty-box">

                <div class="empty-icon">
                    ⚠
                </div>

                <div class="empty-title">
                    Unable to load connections
                </div>

                <div class="empty-text">
                    Please try again.
                </div>

            </div>

        `;

        if (count) {
            count.textContent = "0";
        }

        return;

    }


    const users =
        Array.isArray(data.users)
            ? data.users
            : (
                Array.isArray(data.connections)
                    ? data.connections
                    : []
            );


    renderConnections(users);

}


/* =========================================================
   RENDER CONNECTIONS
========================================================= */

function renderConnections(users) {

    const list =
        document.getElementById(
            "connectionsList"
        );

    const count =
        document.getElementById(
            "connectionCount"
        );

    if (!list) {
        return;
    }


    if (count) {

        count.textContent =
            String(users.length);

    }


    if (!users.length) {

        list.innerHTML = `

            <div class="empty-box">

                <div class="empty-icon">
                    👥
                </div>

                <div class="empty-title">
                    No connected people
                </div>

                <div class="empty-text">
                    Search people and connect with them.
                </div>

            </div>

        `;

        return;

    }


    list.innerHTML =
        users.map(user => {

            const userId =
                escapeHtml(
                    user.user_id || ""
                );

            const name =
                escapeHtml(
                    user.name ||
                    user.user_id ||
                    "User"
                );

            const photo =
                user.profile_photo ||
                user.profile_picture ||
                "";


            const firstLetter =
                (
                    user.name ||
                    user.user_id ||
                    "U"
                )
                .charAt(0)
                .toUpperCase();


            return `

                <div
                    class="connection-card"
                    data-user-id="${userId}"
                >

                    <div
                        class="connection-avatar"
                        data-photo="${escapeHtml(photo)}"
                        data-name="${name}"
                    >

                        ${
                            photo
                            ?
                            `<img
                                src="${escapeHtml(photo)}"
                                alt="${name}"
                                loading="lazy"
                            >`
                            :
                            `<span>${firstLetter}</span>`
                        }

                    </div>


                    <div class="connection-info">

                        <div class="connection-name">
                            ${name}
                        </div>

                        <div class="connection-user-id">
                            @${userId}
                        </div>

                    </div>


                    <div class="connection-actions">

                        <button
                            type="button"
                            class="connection-chat-btn"
                            data-action="chat"
                            data-user-id="${userId}"
                        >
                            Chat
                        </button>

                        <button
                            type="button"
                            class="connection-profile-btn"
                            data-action="profile"
                            data-user-id="${userId}"
                        >
                            Profile
                        </button>

                    </div>

                </div>

            `;

        }).join("");


    attachConnectionEvents();

}


/* =========================================================
   CONNECTION EVENTS
========================================================= */

function attachConnectionEvents() {

    const list =
        document.getElementById(
            "connectionsList"
        );

    if (!list) {
        return;
    }


    list
    .querySelectorAll(
        "[data-action='chat']"
    )
    .forEach(button => {

        button.addEventListener(
            "click",
            function(event) {

                event.stopPropagation();

                openChat(
                    this.dataset.userId
                );

            }
        );

    });


    list
    .querySelectorAll(
        "[data-action='profile']"
    )
    .forEach(button => {

        button.addEventListener(
            "click",
            function(event) {

                event.stopPropagation();

                openProfile(
                    this.dataset.userId
                );

            }
        );

    });


    list
    .querySelectorAll(
        ".connection-avatar"
    )
    .forEach(avatar => {

        avatar.addEventListener(
            "click",
            function(event) {

                event.stopPropagation();

                const photo =
                    this.dataset.photo;

                const name =
                    this.dataset.name;

                if (photo) {

                    openDPViewer(
                        photo,
                        name
                    );

                }

            }
        );

    });

}


/* =========================================================
   OPEN CHAT
========================================================= */

function openChat(userId) {

    if (!userId) {
        return;
    }

    window.location.href =
        `/chat?user_id=${encodeURIComponent(
            userId
        )}`;

}


/* =========================================================
   OPEN PROFILE
========================================================= */

function openProfile(userId) {

    if (!userId) {
        return;
    }

    window.location.href =
        `/profile?user_id=${encodeURIComponent(
            userId
        )}`;

}


/* =========================================================
   SEARCH
========================================================= */

async function performSearch(query) {

    if (!searchResults) {
        return;
    }


    query =
        String(query || "").trim();


    if (!query) {

        searchResults.innerHTML = "";

        searchResults.classList.remove(
            "show"
        );

        return;

    }


    try {

        const response =
            await fetch(
                `/api/search?q=${encodeURIComponent(query)}`,
                {
                    cache: "no-store"
                }
            );


        if (!response.ok) {
            throw new Error(
                "Search request failed"
            );
        }


        const data =
            await response.json();


        const users =
            Array.isArray(data.users)
                ? data.users
                : [];


        if (!users.length) {

            searchResults.innerHTML = `

                <div class="search-empty">
                    No users found
                </div>

            `;

            searchResults.classList.add(
                "show"
            );

            return;

        }


        searchResults.innerHTML =
            users.map(user => {

                const id =
                    escapeHtml(
                        user.user_id || ""
                    );

                const name =
                    escapeHtml(
                        user.name ||
                        user.user_id ||
                        "User"
                    );

                const photo =
                    user.profile_photo ||
                    user.profile_picture ||
                    "";

                const letter =
                    (
                        user.name ||
                        user.user_id ||
                        "U"
                    )
                    .charAt(0)
                    .toUpperCase();


                return `

                    <div
                        class="search-user"
                        data-user-id="${id}"
                    >

                        <div class="search-user-avatar">

                            ${
                                photo
                                ?
                                `<img
                                    src="${escapeHtml(photo)}"
                                    alt="${name}"
                                >`
                                :
                                `<span>${letter}</span>`
                            }

                        </div>


                        <div class="search-user-info">

                            <div class="search-user-name">
                                ${name}
                            </div>

                            <div class="search-user-id">
                                @${id}
                            </div>

                        </div>


                        <button
                            type="button"
                            class="search-follow-btn"
                            data-follow-id="${id}"
                        >
                            Follow
                        </button>

                    </div>

                `;

            }).join("");


        searchResults.classList.add(
            "show"
        );


        searchResults
        .querySelectorAll(
            "[data-follow-id]"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                async function(event) {

                    event.stopPropagation();

                    await followUser(
                        this.dataset.followId,
                        this
                    );

                }
            );

        });


        searchResults
        .querySelectorAll(
            ".search-user"
        )
        .forEach(item => {

            item.addEventListener(
                "click",
                function(event) {

                    if (
                        event.target.closest(
                            "[data-follow-id]"
                        )
                    ) {
                        return;
                    }

                    openProfile(
                        this.dataset.userId
                    );

                }
            );

        });


    } catch (error) {

        console.error(
            "Search error:",
            error
        );

        searchResults.innerHTML = `

            <div class="search-empty">
                Search failed
            </div>

        `;

        searchResults.classList.add(
            "show"
        );

    }

}


/* =========================================================
   SEARCH INPUT
========================================================= */

if (searchInput) {

    searchInput.addEventListener(
        "input",
        function() {

            clearTimeout(
                searchTimer
            );

            const value =
                this.value.trim();


            if (!value) {

                if (searchResults) {

                    searchResults.innerHTML = "";

                    searchResults.classList.remove(
                        "show"
                    );

                }

                return;

            }


            searchTimer =
                setTimeout(
                    () => {

                        performSearch(
                            value
                        );

                    },
                    300
                );

        }
    );

}


/* =========================================================
   FOLLOW USER
========================================================= */

async function followUser(
    targetUserId,
    button = null
) {

    if (
        !currentUser ||
        !currentUser.user_id
    ) {

        showToast(
            "Please login again."
        );

        return;

    }


    if (!targetUserId) {
        return;
    }


    if (
        String(targetUserId) ===
        String(currentUser.user_id)
    ) {

        showToast(
            "You cannot follow yourself."
        );

        return;

    }


    if (button) {

        button.disabled = true;

        button.textContent =
            "Sending...";

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

                        requester_user_id:
                            currentUser.user_id,

                        target_user_id:
                            targetUserId

                    })

                }
            );


        const data =
            await response.json();


        if (!response.ok || !data.ok) {

            throw new Error(
                data.message ||
                "Unable to follow user."
            );

        }


        if (button) {

            button.textContent =
                "Requested";

            button.classList.add(
                "requested"
            );

        }


        showToast(
            data.message ||
            "Follow request sent."
        );


    } catch (error) {

        console.error(
            "Follow error:",
            error
        );


        if (button) {

            button.disabled =
                false;

            button.textContent =
                "Follow";

        }


        showToast(
            error.message ||
            "Unable to send request."
        );

    }

}


/* =========================================================
   NOTIFICATIONS
========================================================= */

async function loadNotificationCount() {

    const badge =
        document.getElementById(
            "notificationBadge"
        );

    if (!badge) {
        return;
    }


    if (
        !currentUser ||
        !currentUser.user_id
    ) {

        badge.textContent = "0";

        badge.style.display =
            "none";

        return;

    }


    try {

        const response =
            await fetch(
                `/api/notifications?user_id=${encodeURIComponent(
                    currentUser.user_id
                )}`,
                {
                    cache: "no-store"
                }
            );


        if (!response.ok) {
            return;
        }


        const data =
            await response.json();


        const notifications =
            Array.isArray(
                data.notifications
            )
            ? data.notifications
            : [];


        const unread =
            notifications.filter(
                item =>
                    !(
                        item.is_read === true ||
                        item.read === true
                    )
            ).length;


        badge.textContent =
            unread > 99
                ? "99+"
                : String(unread);


        badge.style.display =
            unread > 0
                ? "flex"
                : "none";


    } catch (error) {

        console.error(
            "Notification count error:",
            error
        );

    }

}


/* =========================================================
   STATUS
========================================================= */

function addMyStatus() {

    window.location.href =
        "/status";

}


function showAllStatuses() {

    showToast(
        "All statuses coming soon."
    );

}


function openStatus(
    letter,
    name,
    seen
) {

    showToast(
        `${name} status`
    );

}


/* =========================================================
   BOTTOM NAV
========================================================= */

function goHome() {

    window.location.href =
        "/home";

}


function goReels() {

    window.location.href =
        "/reels";

}


function createPost() {

    showToast(
        "Create post coming soon."
    );

}


function goNotifications() {

    window.location.href =
        "/notifications";

}


function goProfile() {

    if (
        currentUser &&
        currentUser.user_id
    ) {

        window.location.href =
            `/profile?user_id=${encodeURIComponent(
                currentUser.user_id
            )}`;

        return;

    }

    window.location.href =
        "/profile";

}


/* =========================================================
   MENU
========================================================= */

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


if (menuBtn) {

    menuBtn.addEventListener(
        "click",
        function(event) {

            event.stopPropagation();

            toggleMenu();

        }
    );

}


if (menuOverlay) {

    menuOverlay.addEventListener(
        "click",
        function(event) {

            if (
                event.target ===
                menuOverlay
            ) {

                closeMenu();

            }

        }
    );

}


/* =========================================================
   MENU OPTIONS
========================================================= */

function goMonetization() {

    showToast(
        "Monetization coming soon."
    );

}


function goBlocked() {

    showToast(
        "Blocked users coming soon."
    );

}


function goPrivacy() {

    showToast(
        "Privacy & Security coming soon."
    );

}


function goSettings() {

    showToast(
        "Settings coming soon."
    );

}


function goHelp() {

    showToast(
        "Help & Support coming soon."
    );

}


function goAbout() {

    showToast(
        "Usanex"
    );

}


/* =========================================================
   LOGOUT
========================================================= */

async function logoutUser() {

    try {

        await fetch(
            "/logout",
            {
                method: "POST"
            }
        );

    } catch (error) {

        console.log(
            "Logout endpoint not available."
        );

    }


    localStorage.removeItem(
        "user"
    );

    localStorage.removeItem(
        "token"
    );

    localStorage.removeItem(
        "currentUser"
    );

    localStorage.removeItem(
        "usanexUser"
    );

    localStorage.removeItem(
        "loggedInUser"
    );

    localStorage.removeItem(
        "userData"
    );


    window.location.href =
        "/?open=login";

}


/* =========================================================
   DP VIEWER
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

    const title =
        document.getElementById(
            "dpViewerName"
        );


    if (
        !viewer ||
        !image
    ) {
        return;
    }


    image.src =
        photo || "";


    if (title) {

        title.textContent =
            name || "";

    }


    viewer.classList.add(
        "show"
    );

}


function closeDPViewer(event) {

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


/* =========================================================
   STATUS HINT
========================================================= */

function showStatusHint() {

    const hint =
        document.getElementById(
            "statusNewUserHint"
        );

    if (!hint) {
        return;
    }

    hint.classList.add(
        "show"
    );

    clearTimeout(
        showStatusHint.timer
    );

    showStatusHint.timer =
        setTimeout(
            () => {

                hint.classList.remove(
                    "show"
                );

            },
            5000
        );

}


/* =========================================================
   OUTSIDE CLICK
========================================================= */

document.addEventListener(
    "click",
    function(event) {

        if (
            searchResults &&
            searchInput &&
            !searchResults.contains(event.target) &&
            !searchInput.contains(event.target)
        ) {

            searchResults.classList.remove(
                "show"
            );

        }

    }
);


/* =========================================================
   ESCAPE
========================================================= */

document.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Escape"
        ) {

            closeMenu();

            if (searchResults) {

                searchResults.classList.remove(
                    "show"
                );

            }

            closeDPViewer();

        }

    }
);


/* =========================================================
   MAKE INLINE FUNCTIONS GLOBAL
========================================================= */

window.addMyStatus =
    addMyStatus;

window.showAllStatuses =
    showAllStatuses;

window.openStatus =
    openStatus;

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

window.closeDPViewer =
    closeDPViewer;

window.openDPViewer =
    openDPViewer;

window.followUser =
    followUser;

window.openProfile =
    openProfile;

window.openChat =
    openChat;


/* =========================================================
   INITIALIZATION
========================================================= */

async function initializeHome() {

    console.log(
        "Usanex Home: initializing..."
    );


    const user =
        await resolveCurrentUser();


    console.log(
        "Usanex Home: current user =",
        user
    );


    if (!user) {

        const list =
            document.getElementById(
                "connectionsList"
            );

        if (list) {

            list.innerHTML = `

                <div class="empty-box">

                    <div class="empty-icon">
                        ⚠
                    </div>

                    <div class="empty-title">
                        Login information not found
                    </div>

                    <div class="empty-text">
                        Please login again.
                    </div>

                </div>

            `;

        }

        return;

    }


    await loadConnections();

    await loadNotificationCount();


    notificationTimer =
        setInterval(
            loadNotificationCount,
            30000
        );


    showStatusHint();

}


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
