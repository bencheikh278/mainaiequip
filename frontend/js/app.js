const API_URL = "http://127.0.0.1:8000";


// ============================================================
// ELEMENTS
// ============================================================

const pages = document.querySelectorAll(".page");
const navItems = document.querySelectorAll(".nav-item");
const fileInput = document.getElementById("fileInput");
const uploadZone = document.getElementById("uploadZone");
const filePreviewList = document.getElementById("filePreviewList");
const analyseBtn = document.getElementById("analyseBtn");
const loading = document.getElementById("loading");
const errorMessage = document.getElementById("errorMessage");
const resultContent = document.getElementById("resultContent");
const historyRows = document.getElementById("historyRows");
const recentAnalyses = document.getElementById("recentAnalyses");

let selectedFiles = [];
let lastResponse = null;


// ============================================================
// NAVIGATION
// ============================================================

function showPage(pageName) {

    pages.forEach(page => {
        page.classList.remove("active");
    });

    const target = document.getElementById(`page-${pageName}`);

    if (!target) {
        return;
    }

    target.classList.add("active");

    navItems.forEach(item => {

        item.classList.remove("active");

        if (item.dataset.page === pageName) {
            item.classList.add("active");
        }

    });

    if (pageName === "historique") {
        chargerHistorique();
    }

    if (pageName === "home") {
        chargerDernieresAnalyses();
    }

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}


// sidebar buttons

navItems.forEach(item => {

    item.addEventListener("click", () => {
        showPage(item.dataset.page);
    });

});


// home button

document
    .getElementById("goAnalyse")
    .addEventListener("click", () => {
        showPage("analyse");
    });


// history button

document
    .querySelector(".text-button")
    .addEventListener("click", () => {
        showPage("historique");
    });


// ============================================================
// FILE SELECTION
// ============================================================

fileInput.addEventListener("change", () => {

    addFiles(fileInput.files);

    fileInput.value = "";

});


function addFiles(fileList) {

    hideError();

    const maxSize = 20 * 1024 * 1024;

    Array.from(fileList).forEach(file => {

        if (file.size === 0) {

            showError(`Le fichier "${file.name}" est vide.`);

            return;
        }

        if (file.size > maxSize) {

            showError(`"${file.name}" dépasse la limite de 20 Mo.`);

            return;
        }

        const point = file.name.lastIndexOf(".");
        const extension = point >= 0
            ? file.name.slice(point).toLowerCase()
            : "";

        if (![".pdf", ".docx", ".txt"].includes(extension)) {

            showError(
                `"${file.name}" n'est pas un format supporté. Formats acceptés : PDF, DOCX, TXT.`
            );

            return;
        }

        const dejaPresent = selectedFiles.some(
            f => f.name === file.name && f.size === file.size
        );

        if (!dejaPresent) {
            selectedFiles.push(file);
        }

    });

    renderFileList();
}


// ============================================================
// RENDER FILE LIST
// ============================================================

function renderFileList() {

    filePreviewList.innerHTML = "";

    selectedFiles.forEach((file, index) => {

        const item = document.createElement("div");

        item.className = "file-preview show";

        item.innerHTML = `

            <div class="file-preview-left">

                <div class="file-preview-icon">
                    <img src="assets/icons/nice.png" alt="">
                </div>

                <div>
                    <strong>${escapeHtml(file.name)}</strong>
                    <span>${formatSize(file.size)}</span>
                </div>

            </div>

            <button
                class="remove-file"
                type="button"
                data-index="${index}"
            >
                <img src="assets/icons/x.png" alt="Supprimer">
            </button>
        `;

        filePreviewList.appendChild(item);

    });

    filePreviewList
        .querySelectorAll(".remove-file")
        .forEach(btn => {

            btn.addEventListener("click", () => {

                const idx = Number(btn.dataset.index);

                selectedFiles.splice(idx, 1);

                renderFileList();

            });

        });

    analyseBtn.disabled = selectedFiles.length === 0;
}


// ============================================================
// DRAG & DROP
// ============================================================

uploadZone.addEventListener("dragover", event => {

    event.preventDefault();

    uploadZone.classList.add("dragover");

});


uploadZone.addEventListener("dragleave", () => {

    uploadZone.classList.remove("dragover");

});


uploadZone.addEventListener("drop", event => {

    event.preventDefault();

    uploadZone.classList.remove("dragover");

    const files = event.dataTransfer.files;

    if (!files.length) {
        return;
    }

    addFiles(files);

});


// ============================================================
// RESET FILES
// ============================================================

function resetFile() {

    selectedFiles = [];

    renderFileList();
}


// ============================================================
// ANALYSE
// ============================================================

analyseBtn.addEventListener("click", analyseDocument);


async function analyseDocument() {

    if (!selectedFiles.length) {

        showError("Veuillez sélectionner au moins un fichier.");

        return;
    }

    const formData = new FormData();

    selectedFiles.forEach(file => {
        formData.append("fichiers", file);
    });

    // interface

    analyseBtn.disabled = true;
    analyseBtn.innerHTML = "Analyse en cours...";
    loading.classList.add("show");

    hideError();

    try {

        console.log(
            "Envoi des fichiers :",
            selectedFiles.map(f => f.name)
        );

        const response = await fetch(
            `${API_URL}/api/analyse`,
            {
                method: "POST",
                body: formData
            }
        );

        let data = {};

        try {
            data = await response.json();
        } catch (parseError) {
            throw new Error(
                "Impossible de contacter le serveur ou de lire la réponse."
            );
        }

        console.log("Réponse API :", data);

        if (!response.ok) {

            throw new Error(
                extraireMessageErreur(data) || "Erreur pendant l'analyse."
            );

        }

        lastResponse = data;

        displayResult(data);

        showPage("result");

    } catch (error) {

        console.error(error);

        showError(
            error.message || "Impossible de contacter le serveur."
        );

    } finally {

        loading.classList.remove("show");

        analyseBtn.disabled = false;

        analyseBtn.innerHTML = `
            Analyser maintenant

            <img src="assets/icons/goto.png" alt="">
        `;

    }

}


// ============================================================
// PRIORITY CLASS
// ============================================================

function getPriorityClass(priorite) {

    const p = (priorite || "").toLowerCase();

    if (
        p.includes("élev") ||
        p.includes("elev") ||
        p.includes("haute") ||
        p.includes("high")
    ) {
        return "priority-high";
    }

    if (
        p.includes("faible") ||
        p.includes("basse") ||
        p.includes("low")
    ) {
        return "priority-low";
    }

    return "priority-medium";
}


function extraireMessageErreur(data) {

    const detail = data && data.detail;

    if (!detail) {
        return "";
    }

    if (typeof detail === "string") {
        return detail;
    }

    if (Array.isArray(detail)) {
        return detail
            .map(item => item.msg || item.detail || "")
            .filter(Boolean)
            .join(" ");
    }

    return String(detail);
}


// ============================================================
// DISPLAY RESULT
// (uniquement synthèse + recommandations)
// ============================================================

function displayResult(data) {

    resultContent.innerHTML = "";

    const synthese = data.synthese || {};

    const syntheses =
        Array.isArray(synthese.synthese_interventions)
            ? synthese.synthese_interventions
            : [];

    let syntheseHTML = "";

    if (!syntheses.length) {

        syntheseHTML = "<p>Aucune synthèse n'a pu être produite.</p>";

    } else {

        syntheses.forEach(item => {

            syntheseHTML += `
                <div class="synthesis-equipment">
                    <h3>${escapeHtml(item.equipement || "")}</h3>
                    <p>${escapeHtml(item.resume || "")}</p>
                </div>
            `;

        });

    }

    addResultItem(
        resultContent,
        "01",
        "Synthèse de l'intervention",
        syntheseHTML
    );

    const recommandations =
        Array.isArray(synthese.recommandations)
            ? synthese.recommandations
            : [];

    let recommendationsHTML = "";

    recommandations.forEach(groupe => {

        const actions = Array.isArray(groupe.actions)
            ? groupe.actions
            : [];

        if (!actions.length) {
            return;
        }

        recommendationsHTML += `
            <div class="recommendation-group">

                <h3 class="recommendation-equipment">
                    ${escapeHtml(groupe.equipement || "")}
                </h3>

                <div class="recommendation-actions">
        `;

        actions.forEach(action => {

            const priorityClass = getPriorityClass(action.priorite);

            recommendationsHTML += `

                <div class="priority-box">

                    <span class="priority-label ${priorityClass}">
                        ${escapeHtml(action.priorite || "moyenne")}
                    </span>

                    <div class="priority-action">
                        <strong>Action recommandée</strong>
                        <p>${escapeHtml(action.action || "")}</p>
                    </div>

                    <div class="priority-justification">
                        <strong>Justification</strong>
                        <p>${escapeHtml(action.justification || "")}</p>
                    </div>

                </div>

            `;

        });

        recommendationsHTML += `
                </div>
            </div>
        `;

    });

    if (!recommendationsHTML.trim()) {
        recommendationsHTML = "<p>Aucune recommandation future n'a été générée.</p>";
    }

    addResultItem(
        resultContent,
        "02",
        "Recommandations",
        `
            <div class="recommendations-container">
                ${recommendationsHTML}

                <div class="recommendation-note">
                    Les recommandations doivent être validées par un responsable de maintenance.
                </div>
            </div>
        `
    );

}


// ============================================================
// RESULT ITEM
// ============================================================

function addResultItem(container, index, label, value) {

    const item = document.createElement("div");

    item.className = "result-item";

    item.innerHTML = `

        <div class="result-index">
            ${index}
        </div>

        <div class="result-label">
            ${label}
        </div>

        <div class="result-value">
            ${value}
        </div>

    `;

    container.appendChild(item);

}


// ============================================================
// CHARGER L'HISTORIQUE (PAGE HISTORIQUE)
// ============================================================

async function chargerHistorique() {

    if (!historyRows) {
        return;
    }

    historyRows.innerHTML =
        `<div class="history-row"><span>Chargement...</span></div>`;

    try {

        const response = await fetch(`${API_URL}/api/historique`);

        const data = await response.json();

        const items = data.historique || [];

        if (!items.length) {

            historyRows.innerHTML =
                `<div class="history-row"><span>Aucune analyse pour le moment.</span></div>`;

            return;
        }

        historyRows.innerHTML = items
            .map(item => `
                <div class="history-row">

                    <div class="history-document">

                        <img src="assets/icons/nice.png" alt="">

                        <span>${escapeHtml(item.fichier)}</span>

                    </div>

                    <span>
                        ${escapeHtml(item.analyse_le || item.date || "--")}
                    </span>

                    <span class="history-success">
                        Analysé
                    </span>

                </div>
            `)
            .join("");

    } catch (error) {

        console.error(error);

        historyRows.innerHTML =
            `<div class="history-row"><span>Impossible de charger l'historique.</span></div>`;
    }
}


// ============================================================
// CHARGER LES DERNIÈRES ANALYSES (PAGE ACCUEIL)
// ============================================================

async function chargerDernieresAnalyses() {

    if (!recentAnalyses) {
        return;
    }

    try {

        const response = await fetch(`${API_URL}/api/historique`);

        const data = await response.json();

        const items = (data.historique || []).slice(0, 3);

        if (!items.length) {

            recentAnalyses.innerHTML = `
                <div class="recent-item">
                    <div class="recent-main">
                        <span>Aucune analyse pour le moment.</span>
                    </div>
                </div>
            `;

            return;
        }

        recentAnalyses.innerHTML = items
            .map(item => `
                <div class="recent-item">

                    <div class="document-mini-icon">
                        <img src="assets/icons/nice.png" alt="">
                    </div>

                    <div class="recent-main">

                        <strong>${escapeHtml(item.fichier)}</strong>

                        <span>
                            ${escapeHtml(item.analyse_le || item.date || "--")}
                        </span>

                    </div>

                    <span class="recent-status">
                        Terminé
                    </span>

                </div>
            `)
            .join("");

    } catch (error) {

        console.error(error);

        recentAnalyses.innerHTML = `
            <div class="recent-item">
                <div class="recent-main">
                    <span>Impossible de charger les analyses.</span>
                </div>
            </div>
        `;
    }
}


// ============================================================
// EXPORT JSON
// ============================================================

document
    .getElementById("exportJsonBtn")
    .addEventListener("click", () => {

        if (!lastResponse) {

            showError("Aucune analyse disponible.");

            return;
        }

        const blob = new Blob(
            [JSON.stringify(lastResponse, null, 2)],
            { type: "application/json" }
        );

        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");

        link.href = url;

        link.download = "synia_analyse.json";

        document.body.appendChild(link);

        link.click();

        link.remove();

        URL.revokeObjectURL(url);

    });


// ============================================================
// DOWNLOAD
// ============================================================

document
    .getElementById("downloadBtn")
    .addEventListener("click", () => {

        window.print();

    });


// ============================================================
// NEW ANALYSIS
// ============================================================

document
    .getElementById("newAnalysisBtn")
    .addEventListener("click", () => {

        resetFile();

        resultContent.innerHTML = "";

        showPage("analyse");

    });


// ============================================================
// ERROR
// ============================================================

function showError(message) {

    const span = errorMessage.querySelector("span");

    span.textContent = message;

    errorMessage.classList.add("show");
}


function hideError() {

    errorMessage.classList.remove("show");

}


// ============================================================
// FORMAT SIZE
// ============================================================

function formatSize(bytes) {

    if (bytes < 1024) {
        return `${bytes} octets`;
    }

    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}


// ============================================================
// HTML ESCAPE
// ============================================================

function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// ============================================================
// CHARGEMENT INITIAL
// ============================================================

chargerDernieresAnalyses();