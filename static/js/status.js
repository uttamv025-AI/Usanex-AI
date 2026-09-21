/* =========================================================
   USANEX STATUS
   status.js
========================================================= */

"use strict";


/* =========================================================
   API
========================================================= */

const API = "https://usanex-ai.onrender.com";


/* =========================================================
   DOM
========================================================= */

const statusApp =
    document.getElementById("statusApp");

const statusViewer =
    document.getElementById("statusViewer");

const statusMediaContainer =
    document.getElementById("statusMediaContainer");

const statusThumbnails =
    document.getElementById("statusThumbnails");

const statusCounter =
    document.getElementById("statusCounter");

const statusMediaInfo =
    document.getElementById("statusMediaInfo");

const statusEmpty =
    document.getElementById("statusEmpty");

const emptySelectBtn =
    document.getElementById("emptySelectBtn");

const statusMediaInput =
    document.getElementById("statusMediaInput");

const statusUploadBtn =
    document.getElementById("statusUploadBtn");

const statusBackBtn =
    document.getElementById("statusBackBtn");

const statusEditorToolbar =
    document.getElementById("statusEditorToolbar");

const textEditorModal =
    document.getElementById("textEditorModal");

const statusTextInput =
    document.getElementById("statusTextInput");

const closeTextEditorBtn =
    document.getElementById("closeTextEditorBtn");

const cancelTextBtn =
    document.getElementById("cancelTextBtn");

const applyTextBtn =
    document.getElementById("applyTextBtn");

const emojiPickerModal =
    document.getElementById("emojiPickerModal");

const closeEmojiBtn =
    document.getElementById("closeEmojiBtn");

const emojiGrid =
    document.getElementById("emojiGrid");

const statusToast =
    document.getElementById("statusToast");


/* =========================================================
   CONSTANTS
========================================================= */

const MAX_MEDIA = 50;

const SWIPE_DISTANCE = 55;

const FILTERS = [
    {
        name: "Normal",
        value: "none"
    },
    {
        name: "Gray",
        value: "grayscale(1)"
    },
    {
        name: "Warm",
        value: "sepia(.65) saturate(1.25)"
    },
    {
        name: "Bright",
        value: "brightness(1.18) contrast(1.05)"
    },
    {
        name: "Contrast",
        value: "contrast(1.28)"
    },
    {
        name: "Cool",
        value: "saturate(1.15) hue-rotate(12deg)"
    }
];


/* =========================================================
   STATE
========================================================= */

const state = {

    media: [],

    currentIndex: 0,

    transitionDirection: "left",

    touchStartX: 0,

    touchStartY: 0,

    isDrawing: false,

    drawingCanvas: null,

    drawingContext: null,

    drawColor: "#ffffff",

    drawSize: 5

};


/* =========================================================
   TOAST
========================================================= */

let toastTimer = null;

function showToast(message) {

    if (!statusToast) {
        return;
    }

    statusToast.textContent =
        message;

    statusToast.classList.add(
        "show"
    );

    clearTimeout(toastTimer);

    toastTimer =
        setTimeout(() => {

            statusToast.classList.remove(
                "show"
            );

        }, 2200);

}


/* =========================================================
   CURRENT USER
========================================================= */

function getCurrentUser() {

    try {

        const user =
            JSON.parse(
                localStorage.getItem("user") || "null"
            );

        return user;

    } catch (error) {

        console.error(
            "Unable to read user:",
            error
        );

        return null;

    }

}


/* =========================================================
   CURRENT MEDIA
========================================================= */

function getCurrentMedia() {

    if (!state.media.length) {
        return null;
    }

    return (
        state.media[state.currentIndex] ||
        null
    );

}


/* =========================================================
   FILE TYPE
========================================================= */

function getMediaType(file) {

    if (
        file &&
        typeof file.type === "string" &&
        file.type.startsWith("video/")
    ) {

        return "video";

    }

    return "image";

}


/* =========================================================
   ADD FILES
========================================================= */

function addFiles(fileList) {

    const files =
        Array.from(fileList || []);

    if (!files.length) {
        return;
    }


    const remaining =
        MAX_MEDIA -
        state.media.length;


    if (remaining <= 0) {

        showToast(
            "Maximum 50 photos/videos allowed."
        );

        return;

    }


    const selected =
        files.slice(
            0,
            remaining
        );


    let addedCount = 0;


    selected.forEach(
        file => {

            if (
                !file.type.startsWith("image/") &&
                !file.type.startsWith("video/")
            ) {

                return;

            }


            const item = {

                id:
                    `${Date.now()}-${Math.random()
                        .toString(36)
                        .slice(2)}`,

                file:
                    file,

                url:
                    URL.createObjectURL(
                        file
                    ),

                type:
                    getMediaType(
                        file
                    ),

                text:
                    "",

                emojis:
                    [],

                filterIndex:
                    0,

                rotation:
                    0,

                scale:
                    1,

                crop: {

                    enabled:
                        false,

                    scale:
                        1

                },

                drawing:
                    null,

                uploaded:
                    false

            };


            state.media.push(
                item
            );

            addedCount++;

        }
    );


    if (!addedCount) {

        showToast(
            "Please select valid photos or videos."
        );

        return;

    }


    if (
        state.media.length ===
        addedCount
    ) {

        state.currentIndex =
            0;

    } else {

        state.currentIndex =
            state.media.length -
            addedCount;

    }


    render();

}


/* =========================================================
   FILE INPUT
========================================================= */

if (statusMediaInput) {

    statusMediaInput.addEventListener(
        "change",
        event => {

            addFiles(
                event.target.files
            );

            event.target.value =
                "";

        }
    );

}


/* =========================================================
   SELECT MEDIA
========================================================= */

function openMediaPicker() {

    if (!statusMediaInput) {
        return;
    }

    statusMediaInput.click();

}


if (emptySelectBtn) {

    emptySelectBtn.addEventListener(
        "click",
        openMediaPicker
    );

}


/* =========================================================
   STATUS UPLOAD
========================================================= */

let isUploading = false;


/* =========================================================
   UPLOAD SINGLE STATUS
========================================================= */

async function uploadSingleStatus(
    item,
    index,
    total
) {

    const currentUser =
        getCurrentUser();


    if (
        !currentUser ||
        !currentUser.user_id
    ) {

        throw new Error(
            "User login information not found."
        );

    }


    if (!item.file) {

        throw new Error(
            "Media file not found."
        );

    }


    showToast(
        `Uploading ${index} / ${total}...`
    );


    const formData =
        new FormData();


    formData.append(
        "file",
        item.file
    );


    const url =
        `${API}/api/status/upload?user_id=` +
        encodeURIComponent(
            currentUser.user_id
        );


    const response =
        await fetch(
            url,
            {
                method:
                    "POST",

                body:
                    formData
            }
        );


    let data =
        null;


    try {

        data =
            await response.json();

    } catch (error) {

        data =
            null;

    }


    if (!response.ok) {

        throw new Error(
            data?.detail ||
            `Upload failed (${response.status})`
        );

    }


    if (!data?.ok) {

        throw new Error(
            data?.message ||
            "Status upload failed."
        );

    }


    return data;

}


/* =========================================================
   UPLOAD ALL STATUSES
========================================================= */

async function uploadAllStatuses() {

    if (isUploading) {
        return;
    }


    if (!state.media.length) {

        openMediaPicker();

        return;

    }


    const currentUser =
        getCurrentUser();


    if (
        !currentUser ||
        !currentUser.user_id
    ) {

        showToast(
            "Please login again."
        );


        setTimeout(
            () => {

                window.location.href =
                    "/?open=login";

            },
            1000
        );


        return;

    }


    isUploading =
        true;


    if (statusUploadBtn) {

        statusUploadBtn.disabled =
            true;

        statusUploadBtn.textContent =
            "Uploading...";

    }


    let successCount =
        0;

    let failedCount =
        0;


    try {

        const total =
            state.media.length;


        for (
            let i = 0;
            i < total;
            i++
        ) {

            const item =
                state.media[i];


            try {

                await uploadSingleStatus(
                    item,
                    i + 1,
                    total
                );


                item.uploaded =
                    true;


                successCount++;


            } catch (error) {

                failedCount++;


                item.uploaded =
                    false;


                console.error(
                    `Status ${i + 1} upload failed:`,
                    error
                );

            }

        }


        /* =================================================
           ALL SUCCESS
        ================================================= */

        if (
            successCount ===
            total
        ) {

            showToast(
                `${successCount} status uploaded successfully.`
            );


            cleanupMediaUrls();


            state.media =
                [];


            state.currentIndex =
                0;


            state.drawingCanvas =
                null;


            state.drawingContext =
                null;


            render();


            setTimeout(
                () => {

                    window.location.href =
                        "/home";

                },
                1000
            );


            return;

        }


        /* =================================================
           PARTIAL SUCCESS
        ================================================= */

        if (
            successCount > 0
        ) {

            showToast(
                `${successCount} uploaded, ${failedCount} failed.`
            );


            const failedMedia =
                state.media.filter(
                    item =>
                        !item.uploaded
                );


            /*
             * Release URLs of successfully
             * uploaded files only.
             */

            state.media
                .filter(
                    item =>
                        item.uploaded
                )
                .forEach(
                    item => {

                        if (item.url) {

                            try {

                                URL.revokeObjectURL(
                                    item.url
                                );

                            } catch (error) {
                                /* Ignore */
                            }

                        }

                    }
                );


            state.media =
                failedMedia;


            state.currentIndex =
                Math.min(
                    state.currentIndex,
                    Math.max(
                        0,
                        state.media.length - 1
                    )
                );


            render();


            return;

        }


        /* =================================================
           COMPLETE FAILURE
        ================================================= */

        showToast(
            "Status upload failed. Please try again."
        );


    } finally {

        isUploading =
            false;


        if (statusUploadBtn) {

            statusUploadBtn.disabled =
                false;

            statusUploadBtn.textContent =
                "Upload";

        }

    }

}


if (statusUploadBtn) {

    statusUploadBtn.addEventListener(
        "click",
        uploadAllStatuses
    );

}


/* =========================================================
   RENDER
========================================================= */

function render() {

    renderMedia();

    renderThumbnails();

    updateUI();

}


/* =========================================================
   RENDER MEDIA
========================================================= */

function renderMedia() {

    if (!statusMediaContainer) {
        return;
    }


    statusMediaContainer
        .querySelectorAll("video")
        .forEach(
            video => {

                try {

                    video.pause();

                } catch (error) {
                    /* Ignore */
                }

            }
        );


    statusMediaContainer.innerHTML =
        "";


    state.media.forEach(
        (item, index) => {

            let element;


            if (
                item.type ===
                "video"
            ) {

                element =
                    document.createElement(
                        "video"
                    );


                element.autoplay =
                    true;

                element.muted =
                    true;

                element.loop =
                    true;

                element.playsInline =
                    true;

                element.preload =
                    "metadata";

                element.controls =
                    false;


            } else {

                element =
                    document.createElement(
                        "img"
                    );


                element.alt =
                    `Status media ${index + 1}`;

            }


            element.className =
                "status-media";


            element.dataset.index =
                String(index);


            element.src =
                item.url;


            applyMediaStyle(
                element,
                item
            );


            if (
                index ===
                state.currentIndex
            ) {

                element.classList.add(
                    "active"
                );

            }


            statusMediaContainer
                .appendChild(
                    element
                );


            renderOverlays(
                element,
                item
            );


            if (
                item.type === "video" &&
                index === state.currentIndex
            ) {

                element.addEventListener(
                    "loadeddata",
                    () => {

                        element.play()
                            .catch(
                                () => {}
                            );

                    },
                    {
                        once:
                            true
                    }
                );

            }

        }
    );

}


/* =========================================================
   MEDIA STYLE
========================================================= */

function applyMediaStyle(
    element,
    item
) {

    const filter =
        FILTERS[
            item.filterIndex
        ]
        ? FILTERS[
            item.filterIndex
        ].value
        : "none";


    let scale =
        Number(
            item.scale
        ) || 1;


    if (
        item.crop &&
        item.crop.enabled
    ) {

        scale *=
            Number(
                item.crop.scale
            ) || 1;

    }


    element.style.filter =
        filter;


    element.style.transform =
        `rotate(${item.rotation}deg) scale(${scale})`;

}


/* =========================================================
   OVERLAYS
========================================================= */

function renderOverlays(
    mediaElement,
    item
) {

    const wrapper =
        document.createElement(
            "div"
        );


    wrapper.className =
        "status-overlay-container";


    wrapper.style.position =
        "absolute";


    wrapper.style.inset =
        "0";


    wrapper.style.pointerEvents =
        "none";


    wrapper.style.zIndex =
        "16";


    if (item.text) {

        const text =
            document.createElement(
                "div"
            );


        text.className =
            "status-text-overlay";


        text.textContent =
            item.text;


        wrapper.appendChild(
            text
        );

    }


    if (
        Array.isArray(
            item.emojis
        ) &&
        item.emojis.length
    ) {

        item.emojis.forEach(
            (
                emoji,
                index
            ) => {

                const emojiElement =
                    document.createElement(
                        "div"
                    );


                emojiElement.className =
                    "status-text-overlay";


                emojiElement.textContent =
                    emoji;


                emojiElement.style.top =
                    `${35 + (index * 13)}%`;


                emojiElement.style.fontSize =
                    "42px";


                wrapper.appendChild(
                    emojiElement
                );

            }
        );

    }


    mediaElement.parentNode
        .appendChild(
            wrapper
        );

}


/* =========================================================
   THUMBNAILS
========================================================= */

function renderThumbnails() {

    if (!statusThumbnails) {
        return;
    }


    statusThumbnails.innerHTML =
        "";


    state.media.forEach(
        (item, index) => {

            const button =
                document.createElement(
                    "button"
                );


            button.type =
                "button";


            button.className =
                "status-thumbnail";


            if (
                index ===
                state.currentIndex
            ) {

                button.classList.add(
                    "active"
                );

            }


            button.dataset.index =
                String(index);


            let preview;


            if (
                item.type ===
                "video"
            ) {

                preview =
                    document.createElement(
                        "video"
                    );


                preview.src =
                    item.url;


                preview.muted =
                    true;


                preview.playsInline =
                    true;


                preview.preload =
                    "metadata";


            } else {

                preview =
                    document.createElement(
                        "img"
                    );


                preview.src =
                    item.url;


                preview.alt =
                    `Thumbnail ${index + 1}`;

            }


            button.appendChild(
                preview
            );


            if (
                item.type ===
                "video"
            ) {

                const icon =
                    document.createElement(
                        "span"
                    );


                icon.className =
                    "status-video-icon";


                icon.textContent =
                    "▶";


                button.appendChild(
                    icon
                );

            }


            button.addEventListener(
                "click",
                () => {

                    selectMedia(
                        index,
                        index >
                            state.currentIndex
                            ? "left"
                            : "right"
                    );

                }
            );


            statusThumbnails
                .appendChild(
                    button
                );

        }
    );


    const active =
        statusThumbnails.querySelector(
            ".status-thumbnail.active"
        );


    if (active) {

        active.scrollIntoView({
            behavior:
                "smooth",

            block:
                "nearest",

            inline:
                "center"
        });

    }

}


/* =========================================================
   UPDATE UI
========================================================= */

function updateUI() {

    const count =
        state.media.length;


    if (statusCounter) {

        statusCounter.textContent =
            `${count ? state.currentIndex + 1 : 0} / ${MAX_MEDIA}`;

    }


    if (statusMediaInfo) {

        if (!count) {

            statusMediaInfo.textContent =
                "Add photos or videos";

        } else {

            const current =
                getCurrentMedia();


            const type =
                current &&
                current.type ===
                "video"
                    ? "Video"
                    : "Photo";


            statusMediaInfo.textContent =
                `${type} • ${count} selected`;

        }

    }


    if (statusEmpty) {

        statusEmpty.style.display =
            count
                ? "none"
                : "flex";

    }


    if (statusEditorToolbar) {

        statusEditorToolbar.style.display =
            count
                ? "flex"
                : "none";

    }

}


/* =========================================================
   SELECT MEDIA
========================================================= */

function selectMedia(
    index,
    direction = "left"
) {

    if (
        index < 0 ||
        index >= state.media.length ||
        index === state.currentIndex
    ) {

        return;

    }


    state.transitionDirection =
        direction;


    state.currentIndex =
        index;


    render();


    const active =
        statusMediaContainer
            ?.querySelector(
                `.status-media[data-index="${index}"]`
            );


    if (active) {

        active.classList.remove(
            "enter-left",
            "enter-right"
        );


        void active.offsetWidth;


        active.classList.add(
            direction === "left"
                ? "enter-left"
                : "enter-right"
        );


        requestAnimationFrame(
            () => {

                active.classList.remove(
                    "enter-left",
                    "enter-right"
                );


                active.classList.add(
                    "active"
                );

            }
        );

    }

}


/* =========================================================
   NEXT / PREVIOUS
========================================================= */

function nextMedia() {

    if (
        state.currentIndex <
        state.media.length - 1
    ) {

        selectMedia(
            state.currentIndex + 1,
            "left"
        );

    }

}


function previousMedia() {

    if (
        state.currentIndex > 0
    ) {

        selectMedia(
            state.currentIndex - 1,
            "right"
        );

    }

}


/* =========================================================
   SWIPE
========================================================= */

if (statusViewer) {

    statusViewer.addEventListener(
        "touchstart",
        event => {

            if (
                !event.touches.length
            ) {
                return;
            }


            state.touchStartX =
                event.touches[0].clientX;


            state.touchStartY =
                event.touches[0].clientY;

        },
        {
            passive:
                true
        }
    );


    statusViewer.addEventListener(
        "touchend",
        event => {

            if (
                !event.changedTouches.length
            ) {
                return;
            }


            const endX =
                event.changedTouches[0].clientX;


            const endY =
                event.changedTouches[0].clientY;


            const deltaX =
                endX -
                state.touchStartX;


            const deltaY =
                endY -
                state.touchStartY;


            if (
                Math.abs(deltaX) <
                SWIPE_DISTANCE
            ) {

                return;

            }


            if (
                Math.abs(deltaX) <=
                Math.abs(deltaY)
            ) {

                return;

            }


            if (deltaX < 0) {

                nextMedia();

            } else {

                previousMedia();

            }

        },
        {
            passive:
                true
        }
    );

}


/* =========================================================
   TEXT EDITOR
========================================================= */

function openTextEditor() {

    const current =
        getCurrentMedia();


    if (!current) {

        showToast(
            "First select a photo or video."
        );

        return;

    }


    statusTextInput.value =
        current.text || "";


    textEditorModal.hidden =
        false;


    setTimeout(
        () => {

            statusTextInput.focus();

        },
        50
    );

}


function closeTextEditor() {

    textEditorModal.hidden =
        true;

}


if (closeTextEditorBtn) {

    closeTextEditorBtn.addEventListener(
        "click",
        closeTextEditor
    );

}


if (cancelTextBtn) {

    cancelTextBtn.addEventListener(
        "click",
        closeTextEditor
    );

}


if (applyTextBtn) {

    applyTextBtn.addEventListener(
        "click",
        () => {

            const current =
                getCurrentMedia();


            if (!current) {
                return;
            }


            current.text =
                statusTextInput.value.trim();


            closeTextEditor();

            render();


            showToast(
                "Text saved."
            );

        }
    );

}


/* =========================================================
   TEXT BACKDROP
========================================================= */

document
    .querySelectorAll(
        "[data-close-text-editor]"
    )
    .forEach(
        element => {

            element.addEventListener(
                "click",
                closeTextEditor
            );

        }
    );


/* =========================================================
   EMOJI
========================================================= */

function openEmojiPicker() {

    const current =
        getCurrentMedia();


    if (!current) {

        showToast(
            "First select a photo or video."
        );

        return;

    }


    emojiPickerModal.hidden =
        false;

}


function closeEmojiPicker() {

    emojiPickerModal.hidden =
        true;

}


if (closeEmojiBtn) {

    closeEmojiBtn.addEventListener(
        "click",
        closeEmojiPicker
    );

}


document
    .querySelectorAll(
        "[data-close-emoji]"
    )
    .forEach(
        element => {

            element.addEventListener(
                "click",
                closeEmojiPicker
            );

        }
    );


if (emojiGrid) {

    emojiGrid
        .querySelectorAll(
            "[data-emoji]"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        const current =
                            getCurrentMedia();


                        if (!current) {
                            return;
                        }


                        current.emojis.push(
                            button.dataset.emoji
                        );


                        closeEmojiPicker();

                        render();


                        showToast(
                            "Emoji added."
                        );

                    }
                );

            }
        );

}


/* =========================================================
   DRAWING
========================================================= */

function createDrawingCanvas() {

    if (!statusMediaContainer) {
        return null;
    }


    let canvas =
        statusMediaContainer
            .querySelector(
                ".status-drawing-canvas"
            );


    if (canvas) {
        return canvas;
    }


    canvas =
        document.createElement(
            "canvas"
        );


    canvas.className =
        "status-drawing-canvas";


    statusMediaContainer.appendChild(
        canvas
    );


    resizeDrawingCanvas(
        canvas
    );


    canvas.addEventListener(
        "pointerdown",
        startDrawing
    );


    canvas.addEventListener(
        "pointermove",
        drawMove
    );


    canvas.addEventListener(
        "pointerup",
        stopDrawing
    );


    canvas.addEventListener(
        "pointercancel",
        stopDrawing
    );


    return canvas;

}


function resizeDrawingCanvas(
    canvas
) {

    const rect =
        statusMediaContainer
            .getBoundingClientRect();


    const ratio =
        Math.max(
            1,
            window.devicePixelRatio || 1
        );


    canvas.width =
        Math.round(
            rect.width *
            ratio
        );


    canvas.height =
        Math.round(
            rect.height *
            ratio
        );


    canvas.style.width =
        `${rect.width}px`;


    canvas.style.height =
        `${rect.height}px`;


    const context =
        canvas.getContext("2d");


    context.scale(
        ratio,
        ratio
    );


    context.lineCap =
        "round";


    context.lineJoin =
        "round";


    context.strokeStyle =
        state.drawColor;


    context.lineWidth =
        state.drawSize;

}


function getCanvasPoint(
    event,
    canvas
) {

    const rect =
        canvas.getBoundingClientRect();


    return {

        x:
            event.clientX -
            rect.left,

        y:
            event.clientY -
            rect.top

    };

}


function startDrawing(
    event
) {

    if (
        !state.drawingContext
    ) {

        return;

    }


    state.isDrawing =
        true;


    const point =
        getCanvasPoint(
            event,
            state.drawingCanvas
        );


    state.drawingContext.beginPath();


    state.drawingContext.moveTo(
        point.x,
        point.y
    );


    state.drawingCanvas
        .setPointerCapture?.(
            event.pointerId
        );

}


function drawMove(
    event
) {

    if (
        !state.isDrawing ||
        !state.drawingContext
    ) {

        return;

    }


    const point =
        getCanvasPoint(
            event,
            state.drawingCanvas
        );


    state.drawingContext.lineTo(
        point.x,
        point.y
    );


    state.drawingContext.stroke();

}


function stopDrawing() {

    if (
        !state.isDrawing
    ) {

        return;

    }


    state.isDrawing =
        false;


    saveDrawing();

}


function saveDrawing() {

    const current =
        getCurrentMedia();


    if (
        !current ||
        !state.drawingCanvas
    ) {

        return;

    }


    try {

        current.drawing =
            state.drawingCanvas.toDataURL(
                "image/png"
            );

    } catch (error) {

        console.error(
            "Unable to save drawing:",
            error
        );

    }

}


function loadDrawing() {

    const current =
        getCurrentMedia();


    if (
        !current ||
        !current.drawing ||
        !state.drawingContext
    ) {

        return;

    }


    const image =
        new Image();


    image.onload =
        () => {

            const canvas =
                state.drawingCanvas;


            const rect =
                canvas.getBoundingClientRect();


            state.drawingContext.clearRect(
                0,
                0,
                rect.width,
                rect.height
            );


            state.drawingContext.drawImage(
                image,
                0,
                0,
                rect.width,
                rect.height
            );

        };


    image.src =
        current.drawing;

}


/* =========================================================
   DRAW TOOL
========================================================= */

function activateDraw() {

    const current =
        getCurrentMedia();


    if (!current) {

        showToast(
            "First select a photo or video."
        );

        return;

    }


    const canvas =
        createDrawingCanvas();


    if (!canvas) {
        return;
    }


    state.drawingCanvas =
        canvas;


    state.drawingContext =
        canvas.getContext("2d");


    state.drawingContext.strokeStyle =
        state.drawColor;


    state.drawingContext.lineWidth =
        state.drawSize;


    canvas.classList.add(
        "active"
    );


    loadDrawing();


    showToast(
        "Draw mode active."
    );

}


/* =========================================================
   FILTER
========================================================= */

function applyNextFilter() {

    const current =
        getCurrentMedia();


    if (!current) {

        showToast(
            "First select a photo or video."
        );

        return;

    }


    current.filterIndex++;


    if (
        current.filterIndex >=
        FILTERS.length
    ) {

        current.filterIndex =
            0;

    }


    const mediaElement =
        statusMediaContainer
            ?.querySelector(
                `.status-media[data-index="${state.currentIndex}"]`
            );


    if (mediaElement) {

        applyMediaStyle(
            mediaElement,
            current
        );

    }


    showToast(
        `${FILTERS[current.filterIndex].name} filter`
    );

}


/* =========================================================
   ROTATE
========================================================= */

function rotateCurrent() {

    const current =
        getCurrentMedia();


    if (!current) {

        showToast(
            "First select a photo or video."
        );

        return;

    }


    current.rotation +=
        90;


    if (
        current.rotation >=
        360
    ) {

        current.rotation =
            0;

    }


    const mediaElement =
        statusMediaContainer
            ?.querySelector(
                `.status-media[data-index="${state.currentIndex}"]`
            );


    if (mediaElement) {

        applyMediaStyle(
            mediaElement,
            current
        );

    }


    showToast(
        "Media rotated."
    );

}


/* =========================================================
   CROP
========================================================= */

function cropCurrent() {

    const current =
        getCurrentMedia();


    if (!current) {

        showToast(
            "First select a photo or video."
        );

        return;

    }


    current.crop.enabled =
        !current.crop.enabled;


    if (
        current.crop.enabled
    ) {

        current.crop.scale =
            1.18;


        showToast(
            "Crop mode applied."
        );

    } else {

        current.crop.scale =
            1;


        showToast(
            "Crop reset."
        );

    }


    const mediaElement =
        statusMediaContainer
            ?.querySelector(
                `.status-media[data-index="${state.currentIndex}"]`
            );


    if (mediaElement) {

        applyMediaStyle(
            mediaElement,
            current
        );

    }

}


/* =========================================================
   TOOLBAR
========================================================= */

if (statusEditorToolbar) {

    statusEditorToolbar
        .querySelectorAll(
            ".status-tool"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        const tool =
                            button.dataset.tool;


                        statusEditorToolbar
                            .querySelectorAll(
                                ".status-tool"
                            )
                            .forEach(
                                item => {

                                    item.classList.remove(
                                        "active"
                                    );

                                }
                            );


                        button.classList.add(
                            "active"
                        );


                        switch (tool) {

                            case "text":

                                openTextEditor();

                                break;


                            case "emoji":

                                openEmojiPicker();

                                break;


                            case "draw":

                                activateDraw();

                                break;


                            case "filter":

                                applyNextFilter();

                                break;


                            case "crop":

                                cropCurrent();

                                break;


                            case "rotate":

                                rotateCurrent();

                                break;


                            default:

                                break;

                        }

                    }
                );

            }
        );

}


/* =========================================================
   BACK BUTTON
========================================================= */

if (statusBackBtn) {

    statusBackBtn.addEventListener(
        "click",
        () => {

            cleanupMediaUrls();


            window.location.href =
                "/home";

        }
    );

}


/* =========================================================
   CLEANUP
========================================================= */

function cleanupMediaUrls() {

    state.media.forEach(
        item => {

            if (item.url) {

                try {

                    URL.revokeObjectURL(
                        item.url
                    );

                } catch (error) {
                    /* Ignore */
                }

            }

        }
    );

}


/* =========================================================
   KEYBOARD
========================================================= */

document.addEventListener(
    "keydown",
    event => {

        const tag =
            document.activeElement?.tagName;


        if (
            tag === "INPUT" ||
            tag === "TEXTAREA"
        ) {

            return;

        }


        if (
            event.key === "Escape"
        ) {

            if (
                textEditorModal &&
                !textEditorModal.hidden
            ) {

                closeTextEditor();

                return;

            }


            if (
                emojiPickerModal &&
                !emojiPickerModal.hidden
            ) {

                closeEmojiPicker();

                return;

            }

        }


        if (
            !state.media.length
        ) {

            return;

        }


        if (
            event.key ===
            "ArrowRight"
        ) {

            nextMedia();

        }


        if (
            event.key ===
            "ArrowLeft"
        ) {

            previousMedia();

        }

    }
);


/* =========================================================
   RESIZE
========================================================= */

window.addEventListener(
    "resize",
    () => {

        if (
            state.drawingCanvas
        ) {

            const oldDrawing =
                getCurrentMedia()?.drawing;


            resizeDrawingCanvas(
                state.drawingCanvas
            );


            if (oldDrawing) {

                loadDrawing();

            }

        }

    }
);


/* =========================================================
   PAGE EXIT CLEANUP
========================================================= */

window.addEventListener(
    "beforeunload",
    cleanupMediaUrls
);


/* =========================================================
   INITIAL STATE
========================================================= */

function initializeStatus() {

    render();

}


initializeStatus();
