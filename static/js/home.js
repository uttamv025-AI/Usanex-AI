"use strict";

/* =========================================================
   USANEX HOME.JS
   Compatible with current home.html + home.css
========================================================= */


/* =========================================================
   GLOBAL STATE
========================================================= */

let currentUser = null;
let searchTimer = null;
let notificationTimer = null;
let toastTimer = null;


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
   USER HELPERS
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
   GET CURRENT USER
========================================================= */

function getStoredCurrentUser() {

    /*
       register.html saves user as:

       localStorage.setItem(
           "user",
           JSON.stringify(loggedInUser)
       );
    */

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
   RESOLVE USER
========================================================= */

async function resolveCurrentUser() {

    currentUser =
        getStoredCurrentUser();


    if (currentUser) {

        console.log(
            "USANEX CURRENT USER:",
            currentUser
        );

        updateYourStatusLetter();

        return currentUser;

    }


    console.error(
        "USANEX: User not found in localStorage."
    );


    return null;

}


/* =========================================================
   YOUR STATUS LETTER
========================================================= */

function updateYourStatusLetter() {

    const element =
        document.getElementById(
            "youLetter"
        );


    if (!element) {
        return;
    }


    if (!currentUser) {

        element.textContent =
            "U";

        return;

    }


    const name =
        currentUser.name ||
        currentUser.user_id ||
        "U";


    element.textContent =
        name.charAt(0).toUpperCase();

}


/* =========================================================
   ESCAPE HTML
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
   TOAST
========================================================= */

function showToast(message) {

    const toast =
        document.getElementById(
            "toast"
        );


    if (!toast) {
        return;
    }


    clearTimeout(toastTimer);


    toast.textContent =
        message;


    toast.style.display =
        "block";


    toastTimer =
        setTimeout(
            function() {

                toast.style.display =
                    "none";

            },
            2200
        );

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


    /* -----------------------------------------------
       USER CHECK
    ------------------------------------------------ */

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

            count.textContent =
                "0";

        }


        return;

    }


    /* -----------------------------------------------
       LOADING
    ------------------------------------------------ */

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


    /* =================================================
       PRIMARY API
    ================================================= */

    try {

        const response =
            await fetch(
                `/api/home/connections?user_id=${userId}`,
                {
                    method: "GET",
                    cache: "no-store"
                }
            );


        console.log(
            "HOME CONNECTION RESPONSE:",
            response.status
        );


        if (response.ok) {

            const result =
                await response.json();


            console.log(
                "HOME CONNECTION DATA:",
                result
            );


            if (result.ok !== false) {

                data = result;

            }

        }

    } catch (error) {

        console.error(
            "Primary connections error:",
            error
        );

    }


    /* =================================================
       FALLBACK API
    ================================================= */

    if (!data) {

        try {

            const response =
                await fetch(
                    `/api/connections?user_id=${userId}`,
                    {
                        method: "GET",
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
                "Fallback connections error:",
                error
            );

        }

    }


    /* =================================================
       API FAILED
    ================================================= */

    if (!data) {

        list.innerHTML = `

            <div class="error-box">

                <div class="error-title">
                    Unable to load connections
                </div>

                <div class="error-text">
                    Please try again.
                </div>

            </div>

        `;


        if (count) {

            count.textContent =
                "0";

        }


        return;

    }


    /* =================================================
       RESPONSE ARRAY
    ================================================= */

    let users = [];


    if (Array.isArray(data.users)) {

        users =
            data.users;

    } else if (
        Array.isArray(data.connections)
    ) {

        users =
            data.connections;

    }


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


    /* =====================================================
       NO CONNECTIONS
    ===================================================== */

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


    /* =====================================================
       USERS
    ===================================================== */

    list.innerHTML =
        users.map(function(user) {


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
                    class="user-card"
                    data-user-id="${userId}"
                >

                    <div
                        class="profile-photo"
                        data-photo="${escapeHtml(photo)}"
                        data-name="${name}"
                    >

                        ${
                            photo
                            ?
                            `
                            <img
                                src="${escapeHtml(photo)}"
                                alt="${name}"
                                loading="lazy"
                            >
                            `
                            :
                            `
                            <span>
                                ${firstLetter}
                            </span>
                            `
                        }

                    </div>


                    <div class="user-info">

                        <div class="user-name">
                            ${name}
                        </div>

                        <div class="user-id">
                            @${userId}
                        </div>

                    </div>


                    <button
                        type="button"
                        class="connected-btn"
                        data-action="chat"
                        data-user-id="${userId}"
                    >
                        Chat
                    </button>

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


    /* =====================================================
       CHAT BUTTON
    ===================================================== */

    list
    .querySelectorAll(
        "[data-action='chat']"
    )
    .forEach(function(button) {

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


    /* =====================================================
       PROFILE PHOTO
    ===================================================== */

    list
    .querySelectorAll(
        ".profile-photo"
    )
    .forEach(function(photoElement) {

        photoElement.addEventListener(
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


    /* =====================================================
       WHOLE USER CARD
    ===================================================== */

    list
    .querySelectorAll(
        ".user-card"
    )
    .forEach(function(card) {

        card.addEventListener(
            "click",
            function(event) {

                if (
                    event.target.closest(
                        ".connected-btn"
                    ) ||
                    event.target.closest(
                        ".profile-photo"
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
        String(query || "")
        .trim();


    if (!query) {

        searchResults.innerHTML =
            "";

        searchResults.classList.remove(
            "active"
        );

        return;

    }


    /* =====================================================
       LOADING
    ===================================================== */

    searchResults.innerHTML = `

        <div class="search-loading">
            Searching...
        </div>

    `;


    searchResults.classList.add(
        "active"
    );


    try {

        const response =
            await fetch(
                `/api/search?q=${encodeURIComponent(query)}`,
                {
                    method: "GET",
                    cache: "no-store"
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
            Array.isArray(data.users)
                ? data.users
                : [];


        /* =================================================
           NO USERS
        ================================================= */

        if (!users.length) {

            searchResults.innerHTML = `

                <div class="search-empty">
                    No users found
                </div>

            `;


            searchResults.classList.add(
                "active"
            );


            return;

        }


        /* =================================================
           RESULTS
        ================================================= */

        searchResults.innerHTML =
            users.map(function(user) {


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


                const mobile =
                    escapeHtml(
                        user.mobile || ""
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
                        class="search-result-card"
                        data-user-id="${id}"
                    >

                        <div class="search-result-photo">

                            ${
                                photo
                                ?
                                `
                                <img
                                    src="${escapeHtml(photo)}"
                                    alt="${name}"
                                >
                                `
                                :
                                `
                                <span>
                                    ${letter}
                                </span>
                                `
                            }

                        </div>


                        <div class="search-result-info">

                            <div class="search-result-name">
                                ${name}
                            </div>

                            <div class="search-result-id">
                                @${id}
                            </div>

                            ${
                                mobile
                                ?
                                `
                                <div class="search-result-mobile">
                                    ${mobile}
                                </div>
                                `
                                :
                                ""
                            }

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
            "active"
        );


        /* =================================================
           FOLLOW BUTTONS
        ================================================= */

        searchResults
        .querySelectorAll(
            "[data-follow-id]"
        )
        .forEach(function(button) {

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


        /* =================================================
           RESULT CARD
        ================================================= */

        searchResults
        .querySelectorAll(
            ".search-result-card"
        )
        .forEach(function(card) {

            card.addEventListener(
                "click",
                function(event) {

                    if (
                        event.target.closest(
                            ".search-follow-btn"
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
            "SEARCH ERROR:",
            error
        );


        searchResults.innerHTML = `

            <div class="search-empty">
                Search failed
            </div>

        `;


        searchResults.classList.add(
            "active"
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

                searchResults.innerHTML =
                    "";

                searchResults.classList.remove(
                    "active"
                );

                return;

            }


            searchTimer =
                setTimeout(
                    function() {

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
    button
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

        button.disabled =
            true;

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


        if (
            !response.ok ||
            !data.ok
        ) {

            throw new Error(
                data.message ||
                "Unable to send follow request."
            );

        }


        if (button) {

            button.textContent =
                "Requested";

            button.classList.add(
                "following"
            );

        }


        showToast(
            data.message ||
            "Follow request sent."
        );


    } catch (error) {

        console.error(
            "FOLLOW ERROR:",
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
   NOTIFICATION COUNT
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

        badge.textContent =
            "0";

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
                    method: "GET",
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
                function(item) {

                    return !(
                        item.is_read === true ||
                        item.read === true
                    );

                }
            ).length;


        if (unread <= 0) {

            badge.textContent =
                "0";

            badge.style.display =
                "none";

        } else {

            badge.textContent =
                unread > 99
                    ? "99+"
                    : String(unread);

            badge.style.display =
                "flex";

        }


    } catch (error) {

        console.error(
            "NOTIFICATION ERROR:",
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
   BOTTOM NAVIGATION
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
        "active"
    );

}


function closeMenu() {

    if (!menuOverlay) {
        return;
    }


    menuOverlay.classList.remove(
        "active"
    );

}


function toggleMenu() {

    if (!menuOverlay) {
        return;
    }


    menuOverlay.classList.toggle(
        "active"
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
   MENU ITEMS
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
            "Logout API not available."
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
        "active"
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
            "active"
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


    hint.style.display =
        "block";


    clearTimeout(
        showStatusHint.timer
    );


    showStatusHint.timer =
        setTimeout(
            function() {

                hint.style.display =
                    "none";

            },
            5000
        );

}


/* =========================================================
   OUTSIDE SEARCH CLICK
========================================================= */

document.addEventListener(
    "click",
    function(event) {

        if (
            searchResults &&
            searchInput &&
            !searchResults.contains(
                event.target
            ) &&
            !searchInput.contains(
                event.target
            )
        ) {

            searchResults.classList.remove(
                "active"
            );

        }

    }
);


/* =========================================================
   ESCAPE KEY
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
                    "active"
                );

            }

            closeDPViewer();

        }

    }
);


/* =========================================================
   GLOBAL FUNCTIONS
   Required because home.html uses onclick=""
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

window.openDPViewer =
    openDPViewer;

window.closeDPViewer =
    closeDPViewer;

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
        "================================"
    );

    console.log(
        "USANEX HOME INITIALIZING"
    );

    console.log(
        "================================"
    );


    const user =
        await resolveCurrentUser();


    console.log(
        "CURRENT USER:",
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


    /* =====================================================
       LOAD CONNECTIONS
    ===================================================== */

    await loadConnections();


    /* =====================================================
       LOAD NOTIFICATION COUNT
    ===================================================== */

    await loadNotificationCount();


    /* =====================================================
       REFRESH NOTIFICATIONS
    ===================================================== */

    clearInterval(
        notificationTimer
    );


    notificationTimer =
        setInterval(
            loadNotificationCount,
            30000
        );


    /* =====================================================
       STATUS HINT
    ===================================================== */

    showStatusHint();

}


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
