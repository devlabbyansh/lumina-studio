/**
 * Lumina Studio - Core Client Controller
 * Manages canvas state, split/side-by-side comparison, interactive sliders,
 * histogram rendering, clipboard paste, export options, and NLP chat edits.
 */

document.addEventListener("DOMContentLoaded", () => {
    // --- Top Nav & View Controls ---
    const activeFilename = document.getElementById("activeFilename");
    const navViewControls = document.getElementById("navViewControls");
    const btnViewSplit = document.getElementById("btnViewSplit");
    const btnViewSide = document.getElementById("btnViewSide");
    const btnViewHold = document.getElementById("btnViewHold");
    const btnToggleAssistant = document.getElementById("btnToggleAssistant");
    const btnNewCanvas = document.getElementById("btnNewCanvas");
    const btnOpenExport = document.getElementById("btnOpenExport");
    const btnShortcuts = document.getElementById("btnShortcuts");

    // --- Theme & Zoom Controls ---
    const btnToggleTheme = document.getElementById("btnToggleTheme");
    const themeIcon = document.getElementById("themeIcon");
    const themeText = document.getElementById("themeText");
    const btnZoomIn = document.getElementById("btnZoomIn");
    const btnZoomOut = document.getElementById("btnZoomOut");
    const btnZoomFit = document.getElementById("btnZoomFit");
    const zoomVal = document.getElementById("zoomVal");

    // --- Left Creative Toolrail ---
    const railToolSelect = document.getElementById("railToolSelect");
    const railToolCrop = document.getElementById("railToolCrop");
    const railToolEraser = document.getElementById("railToolEraser");
    const railToolAutoBG = document.getElementById("railToolAutoBG");
    const railToolVector = document.getElementById("railToolVector");
    const railTabAdjust = document.getElementById("railTabAdjust");
    const railTabPresets = document.getElementById("railTabPresets");
    const railTabHist = document.getElementById("railTabHist");

    // --- Canvas & Containers ---
    const uploadZone = document.getElementById("uploadZone");
    const dropCard = document.getElementById("dropCard");
    const imageInput = document.getElementById("imageInput");
    const btnBrowse = document.getElementById("btnBrowse");
    const btnLoadDemo = document.getElementById("btnLoadDemo");
    const canvasContainer = document.getElementById("canvasContainer");
    
    // Split View Elements
    const splitViewBox = document.getElementById("splitViewBox");
    const compareContainer = document.getElementById("compareContainer");
    const imgOriginal = document.getElementById("imgOriginal");
    const compareOverlay = document.getElementById("compareOverlay");
    const imgProcessed = document.getElementById("imgProcessed");
    const compareSliderLine = document.getElementById("compareSliderLine");
    const compareRangeInput = document.getElementById("compareRangeInput");
    const compareToolbar = document.getElementById("compareToolbar");
    const btnSourceOrig = document.getElementById("btnSourceOrig");
    const btnSourcePrev = document.getElementById("btnSourcePrev");
    const badgeCompareLeft = document.getElementById("badgeCompareLeft");
    const badgeCompareRight = document.getElementById("badgeCompareRight");

    let currentHistory = [];
    let currentHistoryIndex = 0;
    let compareSourceMode = "auto";
    let origMetadata = null;
    let currentMetadata = null;

    function updateComparisonBase() {
        if (!currentHistory || currentHistory.length === 0) return;

        const origStep = currentHistory[0];
        const origUrl = origStep.url || `/static/uploads/${origStep.filename}`;

        const isCroppedOrResized = currentMetadata && origMetadata && (
            currentMetadata.width !== origMetadata.width || currentMetadata.height !== origMetadata.height
        );

        let usePrevious = false;
        if (compareSourceMode === "previous") {
            usePrevious = true;
        } else if (compareSourceMode === "original") {
            usePrevious = false;
        } else {
            // Auto mode: if image was cropped/resized, compare against previous step to prevent distortion
            usePrevious = Boolean(isCroppedOrResized && currentHistoryIndex > 0);
        }

        if (usePrevious && currentHistoryIndex > 0) {
            const prevStep = currentHistory[currentHistoryIndex - 1];
            const prevUrl = prevStep.url || `/static/uploads/${prevStep.filename}`;
            imgOriginal.onerror = function() {
                this.onerror = null;
                if (imgProcessed && imgProcessed.src) this.src = imgProcessed.src;
            };
            imgOriginal.src = prevUrl;
            if (badgeCompareLeft) badgeCompareLeft.textContent = "PREVIOUS";
            if (btnSourcePrev) btnSourcePrev.classList.add("active");
            if (btnSourceOrig) btnSourceOrig.classList.remove("active");
        } else {
            imgOriginal.onerror = function() {
                this.onerror = null;
                if (imgProcessed && imgProcessed.src) this.src = imgProcessed.src;
            };
            imgOriginal.src = origUrl;
            if (badgeCompareLeft) badgeCompareLeft.textContent = "ORIGINAL";
            if (btnSourceOrig) btnSourceOrig.classList.add("active");
            if (btnSourcePrev) btnSourcePrev.classList.remove("active");
        }
    }

    // Side by Side View Elements
    const sideViewBox = document.getElementById("sideViewBox");
    const imgSideOriginal = document.getElementById("imgSideOriginal");
    const imgSideProcessed = document.getElementById("imgSideProcessed");

    // Loader
    const canvasLoader = document.getElementById("canvasLoader");
    const canvasLoaderText = document.getElementById("canvasLoaderText");

    // --- Footer & History ---
    const btnUndo = document.getElementById("btnUndo");
    const btnResetAll = document.getElementById("btnResetAll");
    const stepCounter = document.getElementById("stepCounter");
    const historyTrail = document.getElementById("historyTrail");
    const metaRes = document.getElementById("metaRes");
    const metaSize = document.getElementById("metaSize");
    const metaColor = document.getElementById("metaColor");

    // --- Sidebar Tabs & Panels ---
    const tabButtons = document.querySelectorAll(".tab-btn");
    const toolPanels = document.querySelectorAll(".tool-panel");

    // --- Fine Adjustment Sliders ---
    const slideBrightness = document.getElementById("slideBrightness");
    const valBrightness = document.getElementById("valBrightness");
    const slideContrast = document.getElementById("slideContrast");
    const valContrast = document.getElementById("valContrast");
    const slideTemperature = document.getElementById("slideTemperature");
    const valTemperature = document.getElementById("valTemperature");
    const slideSaturation = document.getElementById("slideSaturation");
    const valSaturation = document.getElementById("valSaturation");
    const slideSharpen = document.getElementById("slideSharpen");
    const valSharpen = document.getElementById("valSharpen");
    const slideBlur = document.getElementById("slideBlur");
    const valBlur = document.getElementById("valBlur");
    const slideVignette = document.getElementById("slideVignette");
    const valVignette = document.getElementById("valVignette");
    const slideGamma = document.getElementById("slideGamma");
    const valGamma = document.getElementById("valGamma");
    const btnApplySliders = document.getElementById("btnApplySliders");
    const btnResetSliders = document.getElementById("btnResetSliders");

    // --- Transform & Crop ---
    const btnRotateCW = document.getElementById("btnRotateCW");
    const btnRotateCCW = document.getElementById("btnRotateCCW");
    const btnFlipH = document.getElementById("btnFlipH");
    const btnFlipV = document.getElementById("btnFlipV");
    const btnStartCrop = document.getElementById("btnStartCrop");
    const cropOverlay = document.getElementById("cropOverlay");
    const cropBox = document.getElementById("cropBox");
    const cropToolbar = document.getElementById("cropToolbar");
    const btnCancelCrop = document.getElementById("btnCancelCrop");
    const btnConfirmCrop = document.getElementById("btnConfirmCrop");

    // --- Histogram Canvas ---
    const histogramCanvas = document.getElementById("histogramCanvas");
    const btnRefreshHist = document.getElementById("btnRefreshHist");

    // --- Assistant Drawer & Floating Bar ---
    const assistantDrawer = document.getElementById("assistantDrawer");
    const btnCloseDrawer = document.getElementById("btnCloseDrawer");
    const chatLog = document.getElementById("chatLog");
    const chatForm = document.getElementById("chatForm");
    const userInput = document.getElementById("userInput");
    const quickPrompts = document.getElementById("quickPrompts");
    const btnClearChat = document.getElementById("btnClearChat");

    const floatingPromptForm = document.getElementById("floatingPromptForm");
    const floatingInput = document.getElementById("floatingInput");

    // --- Modals ---
    const exportModal = document.getElementById("exportModal");
    const btnCloseExport = document.getElementById("btnCloseExport");
    const btnCancelExport = document.getElementById("btnCancelExport");
    const btnConfirmExport = document.getElementById("btnConfirmExport");
    const qualityField = document.getElementById("qualityField");
    const exportQuality = document.getElementById("exportQuality");
    const qualityVal = document.getElementById("qualityVal");

    const shortcutsModal = document.getElementById("shortcutsModal");
    const btnCloseShortcuts = document.getElementById("btnCloseShortcuts");
    const toastContainer = document.getElementById("toastContainer");

    // --- State Variables ---
    let currentFilename = "";
    let naturalWidth = 0;
    let naturalHeight = 0;
    let isProcessing = false;
    let currentViewMode = "split"; // 'split' | 'side'

    // =========================================================================
    // 1. Session Restoration & Init
    // =========================================================================
    function checkAndRestoreSession() {
        fetch("/api/session")
            .then(res => res.json())
            .then(data => {
                if (data.success && data.has_session) {
                    loadActiveState(data);
                    showToast("Active session restored", "info");
                }
            })
            .catch(err => console.error("Session restore error:", err));
    }

    function loadActiveState(data) {
        currentFilename = data.filename;
        currentHistory = data.history || [];
        currentHistoryIndex = data.current_index !== undefined ? data.current_index : 0;

        if (data.metadata) {
            naturalWidth = data.metadata.width;
            naturalHeight = data.metadata.height;
            currentMetadata = data.metadata;
            if (currentHistoryIndex === 0 || !origMetadata) {
                origMetadata = data.metadata;
            }
            updateMetadataUI(data.metadata);
        }

        activeFilename.innerText = data.filename;
        
        // Populate all image targets with fail-safe fallback
        const origUrl = data.original_url || (data.history && data.history.length > 0 ? `/static/uploads/${data.history[0].filename}` : data.url);
        const currentUrl = data.url;

        imgOriginal.onerror = function() {
            this.onerror = null;
            console.warn("Original image failed to load, falling back to processed URL");
            if (imgProcessed && imgProcessed.src && this.src !== imgProcessed.src) {
                this.src = imgProcessed.src;
            }
        };
        imgSideOriginal.onerror = function() {
            this.onerror = null;
            if (imgSideProcessed && imgSideProcessed.src && this.src !== imgSideProcessed.src) {
                this.src = imgSideProcessed.src;
            }
        };

        imgProcessed.src = currentUrl;
        imgSideProcessed.src = currentUrl;
        imgSideOriginal.src = origUrl;

        updateComparisonBase();

        // Show workspace
        uploadZone.style.display = "none";
        canvasContainer.style.display = "flex";
        navViewControls.style.display = "flex";
        btnOpenExport.style.display = "flex";

        // Reset split slider to 50%
        compareRangeInput.value = 50;
        compareContainer.style.setProperty("--slider-pos", "50%");

        renderHistory(data.history || [], data.current_index || 0);
        renderHistogram();

        // Restore saved chat
        const savedChat = sessionStorage.getItem("lumina_chat");
        if (savedChat && chatLog) {
            chatLog.innerHTML = savedChat;
            chatLog.scrollTop = chatLog.scrollHeight;
        }
    }

    checkAndRestoreSession();

    // =========================================================================
    // 2. Upload, Demo & Clipboard Paste Support (Ctrl + V)
    // =========================================================================
    if (btnBrowse) btnBrowse.addEventListener("click", () => imageInput.click());

    imageInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
            uploadFile(e.target.files[0]);
        }
    });

    // Drag and Drop
    ["dragenter", "dragover"].forEach(evt => {
        uploadZone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropCard.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach(evt => {
        uploadZone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropCard.classList.remove("dragover");
        });
    });

    uploadZone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        if (dt && dt.files.length > 0) {
            uploadFile(dt.files[0]);
        }
    });

    // Native Clipboard Paste Handler (Ctrl + V)
    window.addEventListener("paste", (e) => {
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        for (let item of items) {
            if (item.type.indexOf("image") !== -1) {
                const blob = item.getAsFile();
                uploadFile(blob);
                showToast("Pasted image from clipboard", "info");
                break;
            }
        }
    });

    // Demo Image Loader
    btnLoadDemo.addEventListener("click", () => {
        if (isProcessing) return;
        setLoader(true, "Loading demo image...");

        fetch("/demo", { method: "POST" })
            .then(res => res.json())
            .then(data => {
                setLoader(false);
                if (data.success) {
                    loadActiveState(data);
                    appendChat("bot", "Sample photo loaded. You can now tweak adjustment sliders, click preset filters, or type an edit command below!");
                    showToast("Sample photo loaded", "success");
                } else {
                    showToast(data.error || "Failed to load demo", "error");
                }
            })
            .catch(err => {
                setLoader(false);
                showToast("Failed to load demo image", "error");
            });
    });

    function uploadFile(file) {
        if (isProcessing) return;
        setLoader(true, "Uploading image...");

        const fd = new FormData();
        fd.append("image", file);

        fetch("/upload", {
            method: "POST",
            body: fd
        })
            .then(res => res.json())
            .then(data => {
                setLoader(false);
                if (data.success) {
                    loadActiveState(data);
                    appendChat("bot", `Image uploaded successfully (${data.metadata.width}×${data.metadata.height}px). What adjustments would you like to make?`);
                    showToast("Image loaded onto canvas", "success");
                } else {
                    showToast(data.error || "Upload failed", "error");
                }
            })
            .catch(err => {
                setLoader(false);
                showToast("Connection error uploading image", "error");
            });
    }

    // =========================================================================
    // 3. New Canvas & Reset State
    // =========================================================================
    btnNewCanvas.addEventListener("click", () => {
        if (!currentFilename) return;
        if (!confirm("Start new canvas? This will clear your current working history.")) return;

        fetch("/api/reset-session", { method: "POST" })
            .then(res => res.json())
            .then(() => {
                currentFilename = "";
                sessionStorage.removeItem("lumina_chat");

                uploadZone.style.display = "flex";
                canvasContainer.style.display = "none";
                navViewControls.style.display = "none";
                btnOpenExport.style.display = "none";
                activeFilename.innerText = "No file open";

                imgOriginal.src = "";
                imgProcessed.src = "";
                imgSideOriginal.src = "";
                imgSideProcessed.src = "";
                showToast("Canvas cleared", "info");
            });
    });

    btnResetAll.addEventListener("click", () => {
        executeCommand("reset");
    });

    btnUndo.addEventListener("click", () => {
        executeCommand("undo");
    });

    // =========================================================================
    // 4. View Mode Toggling (Split, Side-by-Side, Hold Spacebar)
    // =========================================================================
    compareRangeInput.addEventListener("input", (e) => {
        compareContainer.style.setProperty("--slider-pos", `${e.target.value}%`);
    });

    if (btnSourceOrig) {
        btnSourceOrig.addEventListener("click", () => {
            compareSourceMode = "original";
            updateComparisonBase();
            showToast("Comparing with original photo", "info");
        });
    }

    if (btnSourcePrev) {
        btnSourcePrev.addEventListener("click", () => {
            compareSourceMode = "previous";
            updateComparisonBase();
            showToast("Comparing with previous step", "info");
        });
    }

    btnViewSplit.addEventListener("click", () => {
        currentViewMode = "split";
        btnViewSplit.classList.add("active");
        btnViewSide.classList.remove("active");
        btnViewHold.classList.remove("active");

        splitViewBox.style.display = "flex";
        sideViewBox.style.display = "none";
    });

    btnViewSide.addEventListener("click", () => {
        currentViewMode = "side";
        btnViewSide.classList.add("active");
        btnViewSplit.classList.remove("active");
        btnViewHold.classList.remove("active");

        splitViewBox.style.display = "none";
        sideViewBox.style.display = "grid";
    });

    // Hold to compare mode (Spacebar or Mouse Hold)
    let isHoldingOriginal = false;
    const startHold = () => {
        isHoldingOriginal = true;
        compareContainer.classList.add("hold-active");
        btnViewHold.classList.add("active");
    };
    const endHold = () => {
        isHoldingOriginal = false;
        compareContainer.classList.remove("hold-active");
        btnViewHold.classList.remove("active");
    };

    btnViewHold.addEventListener("mousedown", startHold);
    window.addEventListener("mouseup", endHold);

    window.addEventListener("keydown", (e) => {
        // Spacebar hold to compare when not focused in an input
        if (e.code === "Space" && document.activeElement.tagName !== "INPUT" && !isHoldingOriginal && currentFilename) {
            e.preventDefault();
            startHold();
        }
        // Ctrl + Z (Undo)
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !e.shiftKey) {
            e.preventDefault();
            btnUndo.click();
        }
        // Ctrl + S (Export)
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
            e.preventDefault();
            if (currentFilename) btnOpenExport.click();
        }
    });

    window.addEventListener("keyup", (e) => {
        if (e.code === "Space" && document.activeElement.tagName !== "INPUT" && isHoldingOriginal) {
            endHold();
        }
    });

    // Assistant Drawer Toggle
    btnToggleAssistant.addEventListener("click", () => {
        assistantDrawer.classList.toggle("collapsed");
        btnToggleAssistant.classList.toggle("active", !assistantDrawer.classList.contains("collapsed"));
    });

    if (btnCloseDrawer) {
        btnCloseDrawer.addEventListener("click", () => {
            assistantDrawer.classList.add("collapsed");
            btnToggleAssistant.classList.remove("active");
        });
    }

    // =========================================================================
    // 5. Sidebar Tabs Switcher
    // =========================================================================
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.getAttribute("data-tab");
            tabButtons.forEach(b => b.classList.remove("active"));
            toolPanels.forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            const activePanel = document.getElementById(`panel-${target}`);
            if (activePanel) activePanel.classList.add("active");

            if (target === "histogram") renderHistogram();
        });
    });

    // =========================================================================
    // 6. Interactive Adjustment Sliders
    // =========================================================================
    slideBrightness.addEventListener("input", e => valBrightness.innerText = e.target.value);
    slideContrast.addEventListener("input", e => valContrast.innerText = (e.target.value / 100).toFixed(1) + "x");
    if (slideTemperature) slideTemperature.addEventListener("input", e => valTemperature.innerText = (e.target.value > 0 ? "+" : "") + e.target.value);
    slideSaturation.addEventListener("input", e => valSaturation.innerText = (e.target.value / 100).toFixed(1) + "x");
    slideSharpen.addEventListener("input", e => valSharpen.innerText = (e.target.value / 100).toFixed(1) + "x");
    slideBlur.addEventListener("input", e => valBlur.innerText = e.target.value + " px");
    slideVignette.addEventListener("input", e => valVignette.innerText = e.target.value + "%");
    slideGamma.addEventListener("input", e => valGamma.innerText = (e.target.value / 100).toFixed(1));

    btnResetSliders.addEventListener("click", () => {
        slideBrightness.value = 0; valBrightness.innerText = "0";
        slideContrast.value = 100; valContrast.innerText = "1.0x";
        if (slideTemperature) { slideTemperature.value = 0; valTemperature.innerText = "0"; }
        slideSaturation.value = 100; valSaturation.innerText = "1.0x";
        slideSharpen.value = 100; valSharpen.innerText = "1.0x";
        slideBlur.value = 0; valBlur.innerText = "0 px";
        slideVignette.value = 0; valVignette.innerText = "0%";
        slideGamma.value = 100; valGamma.innerText = "1.0";
    });

    btnApplySliders.addEventListener("click", () => {
        if (!currentFilename) {
            showToast("Open an image first", "info");
            return;
        }

        const b = parseInt(slideBrightness.value);
        const c = parseFloat((slideContrast.value / 100).toFixed(1));
        const t = slideTemperature ? parseInt(slideTemperature.value) : 0;
        const s = parseFloat((slideSaturation.value / 100).toFixed(1));
        const sh = parseFloat((slideSharpen.value / 100).toFixed(1));
        const bl = parseInt(slideBlur.value);
        const v = parseInt(slideVignette.value);
        const g = parseFloat((slideGamma.value / 100).toFixed(1));

        if (b !== 0) executeAction("brightness", { val: b });
        else if (c !== 1.0) executeAction("contrast", { factor: c });
        else if (t !== 0) executeAction("temperature", { mode: t > 0 ? "warm" : "cool", intensity: Math.abs(t) });
        else if (s !== 1.0) executeAction("saturation", { factor: s });
        else if (sh !== 1.0) executeAction("sharpen", { strength: sh });
        else if (bl > 0) executeAction("blur", { ksize: bl });
        else if (v > 0) executeAction("vignette", { intensity: v / 100 });
        else if (g !== 1.0) executeAction("gamma", { gamma: g });
        else showToast("Adjust a slider before applying", "info");
    });

    // Preset Tiles Click Handler
    document.querySelectorAll(".preset-tile").forEach(tile => {
        tile.addEventListener("click", () => {
            if (!currentFilename) {
                showToast("Open an image first", "info");
                return;
            }
            if (tile.id === "btnSideManualEraser") {
                startManualEraser();
                return;
            }
            const action = tile.getAttribute("data-action");
            if (!action) return;
            const param = tile.getAttribute("data-param");
            let params = {};
            if (action === "colormap") params = { colormap: param || "ocean" };
            else if (action === "color_splash") params = { color: param || "red" };
            else if (action === "remove_bg_color") params = { color: param || "white" };
            executeAction(action, params);
        });
    });

    // Transform Actions
    btnRotateCW.addEventListener("click", () => executeAction("rotate", { angle: 90 }));
    btnRotateCCW.addEventListener("click", () => executeAction("rotate", { angle: -90 }));
    btnFlipH.addEventListener("click", () => executeAction("flip", { mode: "horizontal" }));
    btnFlipV.addEventListener("click", () => executeAction("flip", { mode: "vertical" }));

    // Preset Crops
    document.querySelectorAll(".crop-pill").forEach(pill => {
        pill.addEventListener("click", () => {
            const area = pill.getAttribute("data-crop");
            const pct = parseInt(pill.getAttribute("data-pct"));
            executeAction("crop", { area_type: area, percent: pct });
        });
    });

    // =========================================================================
    // 7. Interactive Crop Tool
    // =========================================================================
    btnStartCrop.addEventListener("click", enterCropMode);
    btnCancelCrop.addEventListener("click", exitCropMode);
    btnConfirmCrop.addEventListener("click", applyCropCoords);

    function enterCropMode() {
        if (!currentFilename) return;
        isCropMode = true;
        cropOverlay.style.display = "block";
        cropToolbar.style.display = "flex";
    }

    function exitCropMode() {
        isCropMode = false;
        cropOverlay.style.display = "none";
        cropToolbar.style.display = "none";
    }

    function applyCropCoords() {
        const overlayW = cropOverlay.clientWidth;
        const overlayH = cropOverlay.clientHeight;
        if (!overlayW || !overlayH) return;

        const x1 = Math.round((cropBox.offsetLeft / overlayW) * naturalWidth);
        const y1 = Math.round((cropBox.offsetTop / overlayH) * naturalHeight);
        const x2 = Math.round(((cropBox.offsetLeft + cropBox.offsetWidth) / overlayW) * naturalWidth);
        const y2 = Math.round(((cropBox.offsetTop + cropBox.offsetHeight) / overlayH) * naturalHeight);

        exitCropMode();
        executeAction("crop", { x1: x1, y1: y1, x2: x2, y2: y2 });
    }

    // Drag crop box
    let isDraggingCrop = false;
    let cropStart = null;

    cropBox.addEventListener("mousedown", (e) => {
        e.preventDefault();
        isDraggingCrop = true;
        cropStart = {
            x: e.clientX,
            y: e.clientY,
            left: cropBox.offsetLeft,
            top: cropBox.offsetTop
        };
    });

    window.addEventListener("mousemove", (e) => {
        if (!isDraggingCrop || !cropStart) return;
        const dx = e.clientX - cropStart.x;
        const dy = e.clientY - cropStart.y;
        const maxL = cropOverlay.clientWidth - cropBox.offsetWidth;
        const maxT = cropOverlay.clientHeight - cropBox.offsetHeight;

        cropBox.style.left = Math.max(0, Math.min(maxL, cropStart.left + dx)) + "px";
        cropBox.style.top = Math.max(0, Math.min(maxT, cropStart.top + dy)) + "px";
    });

    window.addEventListener("mouseup", () => {
        isDraggingCrop = false;
        cropStart = null;
    });

    // =========================================================================
    // 8. Manual Background Eraser Engine
    // =========================================================================
    const btnStartEraser = document.getElementById("btnStartEraser");
    const btnSideManualEraser = document.getElementById("btnSideManualEraser");
    const eraserOverlay = document.getElementById("eraserOverlay");
    const eraserCanvas = document.getElementById("eraserCanvas");
    const eraserCursor = document.getElementById("eraserCursor");
    const eraserToolbar = document.getElementById("eraserToolbar");
    const eraserSize = document.getElementById("eraserSize");
    const eraserSizeVal = document.getElementById("eraserSizeVal");
    const btnEraserUndo = document.getElementById("btnEraserUndo");
    const btnEraserClear = document.getElementById("btnEraserClear");
    const btnCancelEraser = document.getElementById("btnCancelEraser");
    const btnConfirmEraser = document.getElementById("btnConfirmEraser");

    let isEraserMode = false;
    let isDrawingEraser = false;
    let eraserCtx = null;
    let eraserHistory = [];
    let lastEraserPoint = null;

    if (btnStartEraser) btnStartEraser.addEventListener("click", startManualEraser);
    if (btnSideManualEraser) btnSideManualEraser.addEventListener("click", startManualEraser);
    if (btnCancelEraser) btnCancelEraser.addEventListener("click", exitManualEraser);
    if (btnEraserUndo) btnEraserUndo.addEventListener("click", undoEraserStroke);
    if (btnEraserClear) btnEraserClear.addEventListener("click", clearEraserCanvas);
    if (btnConfirmEraser) btnConfirmEraser.addEventListener("click", applyManualEraserCutout);

    if (eraserSize) {
        eraserSize.addEventListener("input", (e) => {
            const val = e.target.value;
            eraserSizeVal.innerText = `${val}px`;
            updateEraserCursorSize(val);
        });
    }

    function updateEraserCursorSize(diameter) {
        if (!eraserCursor) return;
        eraserCursor.style.width = `${diameter}px`;
        eraserCursor.style.height = `${diameter}px`;
    }

    function startManualEraser() {
        if (!currentFilename) {
            showToast("Open an image first", "info");
            return;
        }

        // Switch to split view to ensure alignment with canvas bounds
        if (currentViewMode !== "split") {
            btnViewSplit.click();
        }

        isEraserMode = true;
        eraserOverlay.style.display = "block";
        eraserToolbar.style.display = "flex";
        compareSliderLine.style.display = "none";
        compareRangeInput.style.display = "none";
        compareOverlay.style.display = "none";

        compareContainer.classList.add("has-transparency");

        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
            eraserCanvas.width = img.naturalWidth;
            eraserCanvas.height = img.naturalHeight;
            eraserCtx = eraserCanvas.getContext("2d", { willReadFrequently: true });
            eraserCtx.clearRect(0, 0, eraserCanvas.width, eraserCanvas.height);
            eraserCtx.drawImage(img, 0, 0);

            eraserHistory = [
                eraserCtx.getImageData(0, 0, eraserCanvas.width, eraserCanvas.height)
            ];

            updateEraserCursorSize(eraserSize.value);
            showToast("Manual Eraser active. Brush over background to cut out.", "info");
        };
        img.src = imgProcessed.src;
    }

    function exitManualEraser() {
        isEraserMode = false;
        eraserOverlay.style.display = "none";
        eraserToolbar.style.display = "none";
        if (eraserCursor) eraserCursor.style.display = "none";
        compareSliderLine.style.display = "block";
        compareRangeInput.style.display = "block";
        compareOverlay.style.display = "block";
        eraserHistory = [];
    }

    function undoEraserStroke() {
        if (eraserHistory.length > 1) {
            eraserHistory.pop();
            const prevState = eraserHistory[eraserHistory.length - 1];
            eraserCtx.putImageData(prevState, 0, 0);
            showToast("Undid last eraser stroke", "info");
        } else {
            showToast("No eraser strokes to undo", "info");
        }
    }

    function clearEraserCanvas() {
        if (eraserHistory.length > 0) {
            const initialState = eraserHistory[0];
            eraserCtx.putImageData(initialState, 0, 0);
            eraserHistory = [initialState];
            showToast("Eraser reset to start state", "info");
        }
    }

    function applyManualEraserCutout() {
        if (!eraserCanvas || !eraserCtx) return;

        setLoader(true, "Saving transparent cutout...");
        const dataUrl = eraserCanvas.toDataURL("image/png");

        fetch("/api/save-canvas", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image_data: dataUrl })
        })
            .then(res => res.json())
            .then(data => {
                exitManualEraser();
                handleProcessingResult(data);
                showToast("Background erased and saved as PNG", "success");
            })
            .catch(err => {
                setLoader(false);
                console.error("Save canvas error:", err);
                showToast("Failed to save cutout", "error");
            });
    }

    if (eraserOverlay) {
        eraserOverlay.addEventListener("mouseenter", () => {
            if (isEraserMode && eraserCursor) eraserCursor.style.display = "block";
        });

        eraserOverlay.addEventListener("mouseleave", () => {
            if (eraserCursor) eraserCursor.style.display = "none";
            isDrawingEraser = false;
            lastEraserPoint = null;
        });

        eraserOverlay.addEventListener("mousemove", (e) => {
            if (!isEraserMode) return;
            const rect = eraserCanvas.getBoundingClientRect();
            const relX = e.clientX - rect.left;
            const relY = e.clientY - rect.top;

            if (eraserCursor) {
                eraserCursor.style.left = `${relX}px`;
                eraserCursor.style.top = `${relY}px`;
            }

            if (isDrawingEraser && eraserCtx) {
                drawEraserStroke(e);
            }
        });

        eraserOverlay.addEventListener("mousedown", (e) => {
            if (!isEraserMode || !eraserCtx) return;
            isDrawingEraser = true;
            const coords = getCanvasCoords(e);
            lastEraserPoint = coords;
            eraseAt(coords.x, coords.y);
        });

        window.addEventListener("mouseup", () => {
            if (isDrawingEraser && eraserCtx) {
                isDrawingEraser = false;
                lastEraserPoint = null;
                if (eraserHistory.length > 15) eraserHistory.shift();
                eraserHistory.push(eraserCtx.getImageData(0, 0, eraserCanvas.width, eraserCanvas.height));
            }
        });

        // Touch support for mobile/touch screens
        eraserOverlay.addEventListener("touchstart", (e) => {
            if (!isEraserMode || !eraserCtx) return;
            e.preventDefault();
            isDrawingEraser = true;
            const touch = e.touches[0];
            const coords = getCanvasCoords(touch);
            lastEraserPoint = coords;
            eraseAt(coords.x, coords.y);
        }, { passive: false });

        eraserOverlay.addEventListener("touchmove", (e) => {
            if (!isEraserMode || !isDrawingEraser || !eraserCtx) return;
            e.preventDefault();
            const touch = e.touches[0];
            drawEraserStroke(touch);
        }, { passive: false });

        eraserOverlay.addEventListener("touchend", () => {
            if (isDrawingEraser && eraserCtx) {
                isDrawingEraser = false;
                lastEraserPoint = null;
                if (eraserHistory.length > 15) eraserHistory.shift();
                eraserHistory.push(eraserCtx.getImageData(0, 0, eraserCanvas.width, eraserCanvas.height));
            }
        });
    }

    function getCanvasCoords(e) {
        const rect = eraserCanvas.getBoundingClientRect();
        const scaleX = eraserCanvas.width / (rect.width || 1);
        const scaleY = eraserCanvas.height / (rect.height || 1);
        return {
            x: (e.clientX - rect.left) * scaleX,
            y: (e.clientY - rect.top) * scaleY
        };
    }

    function eraseAt(x, y) {
        const radius = (parseInt(eraserSize.value) / 2) * (eraserCanvas.width / (eraserCanvas.clientWidth || 1));
        eraserCtx.save();
        eraserCtx.globalCompositeOperation = "destination-out";
        eraserCtx.beginPath();
        eraserCtx.arc(x, y, Math.max(1, radius), 0, Math.PI * 2, false);
        eraserCtx.fill();
        eraserCtx.restore();
    }

    function drawEraserStroke(e) {
        const currentPoint = getCanvasCoords(e);
        if (!lastEraserPoint) {
            lastEraserPoint = currentPoint;
            eraseAt(currentPoint.x, currentPoint.y);
            return;
        }

        const lineWidth = parseInt(eraserSize.value) * (eraserCanvas.width / (eraserCanvas.clientWidth || 1));
        eraserCtx.save();
        eraserCtx.globalCompositeOperation = "destination-out";
        eraserCtx.lineWidth = Math.max(2, lineWidth);
        eraserCtx.lineCap = "round";
        eraserCtx.lineJoin = "round";
        eraserCtx.beginPath();
        eraserCtx.moveTo(lastEraserPoint.x, lastEraserPoint.y);
        eraserCtx.lineTo(currentPoint.x, currentPoint.y);
        eraserCtx.stroke();
        eraserCtx.restore();

        lastEraserPoint = currentPoint;
    }

    // =========================================================================
    // 9. Histogram Canvas Visualizer
    // =========================================================================
    btnRefreshHist.addEventListener("click", renderHistogram);

    function renderHistogram() {
        if (!currentFilename || !histogramCanvas) return;

        fetch("/api/histogram")
            .then(res => res.json())
            .then(data => {
                if (!data.success || !data.histogram) return;
                drawHistogram(data.histogram);
            })
            .catch(err => console.error("Histogram error:", err));
    }

    function drawHistogram(hist) {
        const ctx = histogramCanvas.getContext("2d");
        const w = histogramCanvas.width;
        const h = histogramCanvas.height;

        ctx.clearRect(0, 0, w, h);

        const drawCurve = (bins, color) => {
            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.5;
            const step = w / bins.length;

            bins.forEach((val, i) => {
                const y = h - (val / 100) * (h - 10) - 5;
                if (i === 0) ctx.moveTo(0, y);
                else ctx.lineTo(i * step, y);
            });
            ctx.stroke();
        };

        ctx.globalCompositeOperation = "screen";
        drawCurve(hist.r, "#ef4444");
        drawCurve(hist.g, "#10b981");
        drawCurve(hist.b, "#3b82f6");
        ctx.globalCompositeOperation = "source-over";
    }

    // =========================================================================
    // 9. NLP Chat Assistant & Floating Command Bar
    // =========================================================================
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;
        executeCommand(text);
        userInput.value = "";
    });

    if (floatingPromptForm) {
        floatingPromptForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const text = floatingInput.value.trim();
            if (!text) return;
            executeCommand(text);
            floatingInput.value = "";
        });
    }

    quickPrompts.addEventListener("click", (e) => {
        const chip = e.target.closest(".prompt-chip");
        if (!chip) return;
        const prompt = chip.getAttribute("data-prompt");
        executeCommand(prompt);
    });

    btnClearChat.addEventListener("click", () => {
        sessionStorage.removeItem("lumina_chat");
        chatLog.innerHTML = `<div class="chat-bubble bot"><p>Conversation cleared. Ready for your edit requests!</p></div>`;
        showToast("Chat cleared", "info");
    });

    function executeCommand(prompt) {
        appendChat("user", prompt);
        setLoader(true, `Processing: "${prompt}"...`);

        fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: prompt })
        })
            .then(res => res.json())
            .then(handleProcessingResult)
            .catch(handleProcessingError);
    }

    function executeAction(action, params = {}) {
        appendChat("user", `Apply ${action}`);
        setLoader(true, `Running ${action}...`);

        fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: action, params: params })
        })
            .then(res => res.json())
            .then(handleProcessingResult)
            .catch(handleProcessingError);
    }

    function handleProcessingResult(data) {
        setLoader(false);
        if (data.reply) appendChat("bot", data.reply);

        if (data.success && data.url) {
            currentFilename = data.url.split("/").pop();
            imgProcessed.src = data.url;
            imgSideProcessed.src = data.url;

            if (data.history) {
                currentHistory = data.history;
                currentHistoryIndex = data.current_index !== undefined ? data.current_index : data.history.length - 1;
                renderHistory(data.history, currentHistoryIndex);
            }

            if (data.metadata) {
                naturalWidth = data.metadata.width;
                naturalHeight = data.metadata.height;
                currentMetadata = data.metadata;
                if (currentHistoryIndex === 0) {
                    origMetadata = data.metadata;
                }
                updateMetadataUI(data.metadata);
            }

            const origUrl = data.original_url || (currentHistory.length > 0 ? `/static/uploads/${currentHistory[0].filename}` : data.url);
            imgSideOriginal.onerror = function() {
                this.onerror = null;
                if (imgSideProcessed && imgSideProcessed.src) this.src = imgSideProcessed.src;
            };
            imgSideOriginal.src = origUrl;

            updateComparisonBase();

            renderHistogram();
            showToast("Transformation applied", "success");
        }
    }

    function handleProcessingError(err) {
        setLoader(false);
        console.error("Processing error:", err);
        appendChat("bot", "An error occurred while contacting the processing server.");
        showToast("Error processing command", "error");
    }

    function appendChat(role, text) {
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${role}`;

        let cleanText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');

        bubble.innerHTML = `<p>${cleanText}</p>`;
        chatLog.appendChild(bubble);
        chatLog.scrollTop = chatLog.scrollHeight;
        sessionStorage.setItem("lumina_chat", chatLog.innerHTML);
    }

    // =========================================================================
    // 10. Export Modal & Shortcuts Dialog
    // =========================================================================
    btnOpenExport.addEventListener("click", () => exportModal.style.display = "flex");
    btnCloseExport.addEventListener("click", () => exportModal.style.display = "none");
    btnCancelExport.addEventListener("click", () => exportModal.style.display = "none");

    document.querySelectorAll("input[name='exportFormat']").forEach(radio => {
        radio.addEventListener("change", (e) => {
            const fmt = e.target.value;
            qualityField.style.display = (fmt === "jpg" || fmt === "webp") ? "block" : "none";
        });
    });

    exportQuality.addEventListener("input", e => qualityVal.innerText = `${e.target.value}%`);

    btnConfirmExport.addEventListener("click", () => {
        const fmt = document.querySelector("input[name='exportFormat']:checked").value;
        const q = exportQuality.value;
        exportModal.style.display = "none";
        window.location.href = `/api/export?format=${fmt}&quality=${q}`;
        showToast(`Exporting as ${fmt.toUpperCase()}...`, "success");
    });

    btnShortcuts.addEventListener("click", () => shortcutsModal.style.display = "flex");
    btnCloseShortcuts.addEventListener("click", () => shortcutsModal.style.display = "none");

    window.addEventListener("click", (e) => {
        if (e.target === exportModal) exportModal.style.display = "none";
        if (e.target === shortcutsModal) shortcutsModal.style.display = "none";
    });

    // =========================================================================
    // 11. UI Helpers
    // =========================================================================
    function setLoader(active, text = "Processing...") {
        isProcessing = active;
        canvasLoaderText.innerText = text;
        canvasLoader.classList.toggle("active", active);
    }

    function updateMetadataUI(meta) {
        if (!meta) return;
        metaRes.innerText = `${meta.width} × ${meta.height} px`;
        metaSize.innerText = `${meta.size_kb} KB`;
        if (meta.has_alpha) {
            metaColor.innerText = "RGBA (Alpha)";
            compareContainer.classList.add("has-transparency");
            document.querySelectorAll(".side-card-body").forEach(el => el.classList.add("has-transparency"));
        } else {
            metaColor.innerText = meta.channels === 1 ? "Grayscale" : "BGR (3ch)";
            compareContainer.classList.remove("has-transparency");
            document.querySelectorAll(".side-card-body").forEach(el => el.classList.remove("has-transparency"));
        }
    }

    function renderHistory(history, currentIndex) {
        stepCounter.innerText = `${history.length} step${history.length === 1 ? "" : "s"}`;
        historyTrail.innerHTML = "";

        history.forEach((item, idx) => {
            const chip = document.createElement("span");
            chip.className = `crumb-chip ${idx === currentIndex ? "active" : ""}`;
            let actName = item.action.replace("Applied", "").replace("✨ **Success!**", "").trim();
            if (actName.length > 18) actName = actName.substring(0, 16) + "..";
            chip.innerText = actName;
            historyTrail.appendChild(chip);
        });

        historyTrail.scrollLeft = historyTrail.scrollWidth;
    }

    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast-item ${type}`;
        toast.innerHTML = `<span>${message}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(8px)";
            setTimeout(() => toast.remove(), 250);
        }, 2800);
    }

    // =========================================================================
    // 12. Theme Management (Light & Dark Studio Modes)
    // =========================================================================
    function initTheme() {
        const savedTheme = localStorage.getItem("lumina_theme") || "dark";
        applyTheme(savedTheme);
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        if (theme === "light") {
            if (themeIcon) themeIcon.className = "fa-solid fa-sun text-amber";
            if (themeText) themeText.innerText = "Light";
        } else {
            if (themeIcon) themeIcon.className = "fa-solid fa-moon";
            if (themeText) themeText.innerText = "Dark";
        }
        localStorage.setItem("lumina_theme", theme);
    }

    if (btnToggleTheme) {
        btnToggleTheme.addEventListener("click", () => {
            const current = document.documentElement.getAttribute("data-theme") || "dark";
            const next = current === "dark" ? "light" : "dark";
            applyTheme(next);
            showToast(`Switched to ${next.toUpperCase()} Studio Mode`, "info");
        });
    }

    initTheme();

    // =========================================================================
    // 13. Canvas Viewport Zoom Controller
    // =========================================================================
    let currentZoom = 1.0;

    function updateZoom(newZoom) {
        currentZoom = Math.min(3.0, Math.max(0.4, parseFloat(newZoom.toFixed(2))));
        if (zoomVal) zoomVal.innerText = `${Math.round(currentZoom * 100)}%`;
        if (compareContainer) {
            compareContainer.style.transform = `scale(${currentZoom})`;
            compareContainer.style.transformOrigin = "center center";
            compareContainer.style.transition = "transform 0.15s ease";
        }
        if (sideViewBox) {
            sideViewBox.style.transform = `scale(${currentZoom})`;
            sideViewBox.style.transformOrigin = "center center";
            sideViewBox.style.transition = "transform 0.15s ease";
        }
    }

    if (btnZoomIn) btnZoomIn.addEventListener("click", () => updateZoom(currentZoom + 0.15));
    if (btnZoomOut) btnZoomOut.addEventListener("click", () => updateZoom(currentZoom - 0.15));
    if (btnZoomFit) btnZoomFit.addEventListener("click", () => updateZoom(1.0));
    if (zoomVal) zoomVal.addEventListener("click", () => updateZoom(1.0));

    // Ctrl + MouseWheel Zoom over canvas
    if (canvasContainer) {
        canvasContainer.addEventListener("wheel", (e) => {
            if (e.ctrlKey) {
                e.preventDefault();
                const delta = e.deltaY < 0 ? 0.1 : -0.1;
                updateZoom(currentZoom + delta);
            }
        }, { passive: false });
    }

    // =========================================================================
    // 14. Left Vertical Toolrail Actions
    // =========================================================================
    const railBtns = document.querySelectorAll(".rail-btn");

    function setRailActive(targetBtn) {
        railBtns.forEach(b => b.classList.remove("active"));
        if (targetBtn) targetBtn.classList.add("active");
    }

    if (railToolSelect) {
        railToolSelect.addEventListener("click", () => {
            setRailActive(railToolSelect);
            if (currentViewMode !== "split" && btnViewSplit) btnViewSplit.click();
            showToast("Selection & Split Slider active", "info");
        });
    }

    if (railToolCrop) {
        railToolCrop.addEventListener("click", () => {
            setRailActive(railToolCrop);
            if (btnStartCrop) btnStartCrop.click();
        });
    }

    if (railToolEraser) {
        railToolEraser.addEventListener("click", () => {
            setRailActive(railToolEraser);
            startManualEraser();
        });
    }

    if (railToolAutoBG) {
        railToolAutoBG.addEventListener("click", () => {
            setRailActive(railToolAutoBG);
            executeAction("remove_bg");
        });
    }

    if (railToolVector) {
        railToolVector.addEventListener("click", () => {
            setRailActive(railToolVector);
            executeAction("vectorize");
        });
    }

    if (railTabAdjust) {
        railTabAdjust.addEventListener("click", () => {
            setRailActive(railTabAdjust);
            const btn = document.querySelector(".tab-btn[data-tab='adjust']");
            if (btn) btn.click();
        });
    }

    if (railTabPresets) {
        railTabPresets.addEventListener("click", () => {
            setRailActive(railTabPresets);
            const btn = document.querySelector(".tab-btn[data-tab='filters']");
            if (btn) btn.click();
        });
    }

    if (railTabHist) {
        railTabHist.addEventListener("click", () => {
            setRailActive(railTabHist);
            const btn = document.querySelector(".tab-btn[data-tab='histogram']");
            if (btn) btn.click();
        });
    }

    // =========================================================================
    // 15. Desktop Application Menu Bar Actions
    // =========================================================================
    const menuActions = [
        ["menuNew", () => btnNewCanvas && btnNewCanvas.click()],
        ["menuOpen", () => imageInput && imageInput.click()],
        ["menuDemo", () => btnLoadDemo && btnLoadDemo.click()],
        ["menuExport", () => btnOpenExport && btnOpenExport.click()],
        ["menuExportSVG", () => { window.location.href = "/api/export?format=svg"; showToast("Exporting SVG vector...", "success"); }],
        ["menuUndo", () => btnUndo && btnUndo.click()],
        ["menuRevert", () => btnResetAll && btnResetAll.click()],
        ["menuCrop", () => btnStartCrop && btnStartCrop.click()],
        ["menuEraser", () => startManualEraser()],
        ["menuAIBG", () => executeAction("remove_bg")],
        ["menuKeyWhite", () => executeAction("remove_bg_color", { color: "white" })],
        ["menuMakePNG", () => executeAction("make_png")],
        ["menuMakeJPG", () => executeAction("make_jpg")],
        ["menuVectorize", () => executeAction("vectorize")],
        ["menuRotateCW", () => btnRotateCW && btnRotateCW.click()],
        ["menuFlipH", () => btnFlipH && btnFlipH.click()],
        ["menuViewSplit", () => btnViewSplit && btnViewSplit.click()],
        ["menuViewSide", () => btnViewSide && btnViewSide.click()],
        ["menuZoomIn", () => updateZoom(currentZoom + 0.15)],
        ["menuZoomOut", () => updateZoom(currentZoom - 0.15)],
        ["menuZoomFit", () => updateZoom(1.0)]
    ];

    menuActions.forEach(([id, handler]) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener("click", handler);
    });

    document.querySelectorAll("[data-menu-action]").forEach(btn => {
        btn.addEventListener("click", () => {
            const act = btn.getAttribute("data-menu-action");
            if (act) executeAction(act);
        });
    });
});
