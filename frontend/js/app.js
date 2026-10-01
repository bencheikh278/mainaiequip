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


// ============================================================
// SIDEBAR
// ============================================================

navItems.forEach(item => {

    item.addEventListener("click", () => {

        showPage(item.dataset.page);

    });

});


// ============================================================
// HOME -> ANALYSE
// ============================================================

const goAnalyseButton = document.getElementById("goAnalyse");

if (goAnalyseButton) {

    goAnalyseButton.addEventListener("click", () => {

        showPage("analyse");

    });

}


// ============================================================
// HISTORY BUTTON
// ============================================================

const historyButton = document.querySelector(".text-button");

if (historyButton) {

    historyButton.addEventListener("click", () => {

        showPage("historique");

    });

}


// ============================================================
// FILE SELECTION
// ============================================================

if (fileInput) {

    fileInput.addEventListener("change", () => {

        addFiles(fileInput.files);

        fileInput.value = "";

    });

}


// ============================================================
// ADD FILES
// ============================================================

function addFiles(fileList) {

    hideError();

    const maxSize = 20 * 1024 * 1024;

    Array.from(fileList).forEach(file => {

        // ----------------------------------------------------
        // EMPTY FILE
        // ----------------------------------------------------

        if (file.size === 0) {

            showError(
                `Le fichier "${file.name}" est vide.`
            );

            return;
        }


        // ----------------------------------------------------
        // SIZE
        // ----------------------------------------------------

        if (file.size > maxSize) {

            showError(
                `"${file.name}" dépasse la limite de 20 Mo.`
            );

            return;
        }


        // ----------------------------------------------------
        // EXTENSION
        // ----------------------------------------------------

        const point = file.name.lastIndexOf(".");

        const extension =
            point >= 0
                ? file.name.slice(point).toLowerCase()
                : "";

        if (![".pdf", ".docx", ".txt"].includes(extension)) {

            showError(
                `"${file.name}" n'est pas un format supporté. ` +
                `Formats acceptés : PDF, DOCX, TXT.`
            );

            return;
        }


        // ----------------------------------------------------
        // DUPLICATE IN CURRENT SELECTION
        // ----------------------------------------------------

        const dejaPresent = selectedFiles.some(
            existingFile =>
                existingFile.name === file.name &&
                existingFile.size === file.size
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

    if (!filePreviewList) {
        return;
    }

    filePreviewList.innerHTML = "";

    selectedFiles.forEach((file, index) => {

        const item = document.createElement("div");

        item.className = "file-preview show";

        item.innerHTML = `

            <div class="file-preview-left">

                <div class="file-preview-icon">

                    <img
                        src="assets/icons/nice.png"
                        alt=""
                    >

                </div>

                <div>

                    <strong>
                        ${escapeHtml(file.name)}
                    </strong>

                    <span>
                        ${formatSize(file.size)}
                    </span>

                </div>

            </div>


            <button
                class="remove-file"
                type="button"
                data-index="${index}"
            >

                <img
                    src="assets/icons/x.png"
                    alt="Supprimer"
                >

            </button>

        `;

        filePreviewList.appendChild(item);

    });


    filePreviewList
        .querySelectorAll(".remove-file")
        .forEach(button => {

            button.addEventListener("click", () => {

                const index =
                    Number(button.dataset.index);

                selectedFiles.splice(index, 1);

                renderFileList();

            });

        });


    if (analyseBtn) {

        analyseBtn.disabled =
            selectedFiles.length === 0;

    }
}


// ============================================================
// DRAG & DROP
// ============================================================

if (uploadZone) {

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

        const files =
            event.dataTransfer.files;

        if (!files.length) {
            return;
        }

        addFiles(files);

    });

}


// ============================================================
// RESET FILES
// ============================================================

function resetFile() {

    selectedFiles = [];

    renderFileList();

}


// ============================================================
// ANALYSE BUTTON
// ============================================================

if (analyseBtn) {

    analyseBtn.addEventListener(
        "click",
        analyseDocument
    );

}


// ============================================================
// ANALYSE DOCUMENT
// ============================================================

async function analyseDocument() {

    if (!selectedFiles.length) {

        showError(
            "Veuillez sélectionner au moins un fichier."
        );

        return;
    }


    const formData = new FormData();


    selectedFiles.forEach(file => {

        formData.append(
            "fichiers",
            file
        );

    });


    // --------------------------------------------------------
    // UI
    // --------------------------------------------------------

    analyseBtn.disabled = true;

    analyseBtn.innerHTML =
        "Analyse en cours...";

    if (loading) {
        loading.classList.add("show");
    }

    hideError();


    try {

        console.log(
            ">>> Envoi des fichiers :",
            selectedFiles.map(file => file.name)
        );


        // ----------------------------------------------------
        // API
        // ----------------------------------------------------

        const response = await fetch(
            `${API_URL}/api/analyse`,
            {
                method: "POST",
                body: formData
            }
        );


        // ----------------------------------------------------
        // JSON
        // ----------------------------------------------------

        let data;

        try {

            data = await response.json();

        } catch (error) {

            throw new Error(
                "Le serveur a retourné une réponse invalide."
            );

        }


        console.log(
            ">>> Réponse API :",
            data
        );


        // ----------------------------------------------------
        // ERROR
        // ----------------------------------------------------

        if (!response.ok) {

            throw new Error(
                extraireMessageErreur(data) ||
                "Erreur pendant l'analyse."
            );

        }


        // ----------------------------------------------------
        // CHECK RESPONSE
        // ----------------------------------------------------

        if (!data) {

            throw new Error(
                "Aucune réponse reçue du serveur."
            );

        }


        if (!data.synthese) {

            console.warn(
                "La réponse ne contient pas de synthèse.",
                data
            );

        }


        // ----------------------------------------------------
        // SAVE RESPONSE
        // ----------------------------------------------------

        lastResponse = data;


        // ----------------------------------------------------
        // DISPLAY
        // ----------------------------------------------------

        displayResult(data);


        // ----------------------------------------------------
        // RESULT PAGE
        // ----------------------------------------------------

        showPage("result");


    } catch (error) {

        console.error(
            "!!! ERREUR FRONTEND !!!",
            error
        );

        showError(
            error.message ||
            "Impossible de contacter le serveur."
        );

    } finally {

        if (loading) {
            loading.classList.remove("show");
        }

        analyseBtn.disabled =
            selectedFiles.length === 0;

        analyseBtn.innerHTML = `
            Analyser maintenant

            <img
                src="assets/icons/goto.png"
                alt=""
            >
        `;

    }

}


// ============================================================
// DISPLAY RESULT
//
// IMPORTANT:
// L'interface affiche UNIQUEMENT:
//
// 01 - Synthèse des interventions réalisées
// 02 - Recommandations
//
// Elle n'affiche pas les analyses détaillées des équipements.
// ============================================================

function displayResult(data) {

    if (!resultContent) {
        return;
    }

    resultContent.innerHTML = "";


    console.log(
        ">>> AFFICHAGE RESULTAT"
    );

    console.log(
        ">>> Synthèse :",
        data.synthese
    );


    const synthese =
        data.synthese || {};



    // ========================================================
    // 01 - SYNTHESE DES INTERVENTIONS REALISEES
    // ========================================================

    const syntheses =
        Array.isArray(
            synthese.synthese_interventions
        )
            ? synthese.synthese_interventions
            : [];


    let syntheseHTML = "";


    if (!syntheses.length) {

        syntheseHTML = `
            <p class="empty-result">
                Aucune synthèse des interventions réalisées
                n'a été produite.
            </p>
        `;

    } else {

        syntheses.forEach(item => {

            let equipement = "";
            let resume = "";


            // ------------------------------------------------
            // CAS 1 :
            // { equipement, resume }
            // ------------------------------------------------

            if (
                typeof item === "object" &&
                item !== null
            ) {

                equipement =
                    item.equipement ||
                    item.nom ||
                    "Équipement";

                resume =
                    item.resume ||
                    item.synthese ||
                    item.description ||
                    item.intervention ||
                    "";

            }


            // ------------------------------------------------
            // CAS 2 :
            // simple string
            // ------------------------------------------------

            else {

                resume = String(item);

            }


            syntheseHTML += `

                <div class="synthesis-equipment">

                    ${
                        equipement
                            ? `
                                <h3>
                                    ${escapeHtml(
                                        equipement
                                    )}
                                </h3>
                            `
                            : ""
                    }

                    <p>
                        ${escapeHtml(
                            resume
                        )}
                    </p>

                </div>

            `;

        });

    }


    addResultItem(
        resultContent,
        "01",
        "Synthèse des interventions réalisées",
        syntheseHTML
    );



    // ========================================================
    // 02 - RECOMMANDATIONS
    // ========================================================

    const recommandations =
        Array.isArray(
            synthese.recommandations
        )
            ? synthese.recommandations
            : [];


    let recommendationsHTML = "";


    if (!recommandations.length) {

        recommendationsHTML = `
            <p class="empty-result">
                Aucune recommandation future
                n'a été générée.
            </p>
        `;

    } else {


        recommandations.forEach(
            recommandation => {


                // =================================================
                // FORMAT ACTUEL DE TON AGENT :
                //
                // {
                //   equipement: "...",
                //   action: "...",
                //   priorite: "moyenne"
                // }
                // =================================================

                if (
                    typeof recommandation === "object" &&
                    recommandation !== null
                ) {

                    const equipement =
                        recommandation.equipement ||
                        "Équipement";

                    const action =
                        recommandation.action ||
                        "";

                    const priorite =
                        recommandation.priorite ||
                        "moyenne";

                    const justification =
                        recommandation.justification ||
                        "";


                    const priorityClass =
                        getPriorityClass(
                            priorite
                        );


                    recommendationsHTML += `

                        <div
                            class="recommendation-group"
                        >

                            <h3
                                class="recommendation-equipment"
                            >
                                ${escapeHtml(
                                    equipement
                                )}
                            </h3>


                            <div
                                class="recommendation-actions"
                            >

                                <div
                                    class="priority-box"
                                >

                                    <span
                                        class="priority-label ${priorityClass}"
                                    >
                                        ${escapeHtml(
                                            priorite
                                        )}
                                    </span>


                                    <div
                                        class="priority-action"
                                    >

                                        <strong>
                                            Action recommandée
                                        </strong>

                                        <p>
                                            ${escapeHtml(
                                                action
                                            )}
                                        </p>

                                    </div>


                                    ${
                                        justification
                                            ? `
                                                <div
                                                    class="priority-justification"
                                                >

                                                    <strong>
                                                        Justification
                                                    </strong>

                                                    <p>
                                                        ${escapeHtml(
                                                            justification
                                                        )}
                                                    </p>

                                                </div>
                                            `
                                            : ""
                                    }

                                </div>

                            </div>

                        </div>

                    `;

                }

            }
        );

    }


    addResultItem(
        resultContent,
        "02",
        "Recommandations",
        `
            <div class="recommendations-container">

                ${recommendationsHTML}

                <div class="recommendation-note">
                    Les recommandations sont des actions
                    futures proposées par SYNIA.
                    Elles doivent être validées par un
                    responsable de maintenance.
                </div>

            </div>
        `
    );

}


// ============================================================
// RESULT ITEM
// ============================================================

function addResultItem(
    container,
    index,
    label,
    value
) {

    const item =
        document.createElement("div");

    item.className =
        "result-item";


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
// PRIORITY CLASS
// ============================================================

function getPriorityClass(priorite) {

    const p =
        String(priorite || "")
            .toLowerCase();


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


// ============================================================
// ERROR MESSAGE
// ============================================================

function extraireMessageErreur(data) {

    if (!data) {
        return "";
    }


    const detail =
        data.detail;


    if (!detail) {
        return "";
    }


    if (typeof detail === "string") {
        return detail;
    }


    if (Array.isArray(detail)) {

        return detail
            .map(item =>
                item.msg ||
                item.detail ||
                ""
            )
            .filter(Boolean)
            .join(" ");

    }


    return String(detail);

}


// ============================================================
// HISTORY
// ============================================================

async function chargerHistorique() {

    if (!historyRows) {
        return;
    }


    historyRows.innerHTML = `
        <div class="history-row">
            <span>Chargement...</span>
        </div>
    `;


    try {

        const response =
            await fetch(
                `${API_URL}/api/historique`
            );


        const data =
            await response.json();


        const items =
            data.historique || [];


        if (!items.length) {

            historyRows.innerHTML = `
                <div class="history-row">
                    <span>
                        Aucune analyse pour le moment.
                    </span>
                </div>
            `;

            return;
        }


        historyRows.innerHTML =
            items.map(item => `

                <div class="history-row">

                    <div class="history-document">

                        <img
                            src="assets/icons/nice.png"
                            alt=""
                        >

                        <span>
                            ${escapeHtml(
                                item.fichier
                            )}
                        </span>

                    </div>


                    <span>
                        ${escapeHtml(
                            item.analyse_le ||
                            item.date ||
                            "--"
                        )}
                    </span>


                    <span class="history-success">
                        Analysé
                    </span>

                </div>

            `).join("");


    } catch (error) {

        console.error(
            "Erreur historique :",
            error
        );


        historyRows.innerHTML = `
            <div class="history-row">
                <span>
                    Impossible de charger l'historique.
                </span>
            </div>
        `;

    }

}


// ============================================================
// RECENT ANALYSES
// ============================================================

async function chargerDernieresAnalyses() {

    if (!recentAnalyses) {
        return;
    }


    try {

        const response =
            await fetch(
                `${API_URL}/api/historique`
            );


        const data =
            await response.json();


        const items =
            (data.historique || [])
                .slice(0, 3);


        if (!items.length) {

            recentAnalyses.innerHTML = `
                <div class="recent-item">

                    <div class="recent-main">

                        <span>
                            Aucune analyse pour le moment.
                        </span>

                    </div>

                </div>
            `;

            return;
        }


        recentAnalyses.innerHTML =
            items.map(item => `

                <div class="recent-item">

                    <div class="document-mini-icon">

                        <img
                            src="assets/icons/nice.png"
                            alt=""
                        >

                    </div>


                    <div class="recent-main">

                        <strong>
                            ${escapeHtml(
                                item.fichier
                            )}
                        </strong>

                        <span>
                            ${escapeHtml(
                                item.analyse_le ||
                                item.date ||
                                "--"
                            )}
                        </span>

                    </div>


                    <span class="recent-status">
                        Terminé
                    </span>

                </div>

            `).join("");


    } catch (error) {

        console.error(
            "Erreur dernières analyses :",
            error
        );


        recentAnalyses.innerHTML = `
            <div class="recent-item">

                <div class="recent-main">

                    <span>
                        Impossible de charger les analyses.
                    </span>

                </div>

            </div>
        `;

    }

}


// ============================================================
// EXPORT JSON
// ============================================================

const exportJsonBtn =
    document.getElementById(
        "exportJsonBtn"
    );


if (exportJsonBtn) {

    exportJsonBtn.addEventListener(
        "click",
        () => {

            if (!lastResponse) {

                showError(
                    "Aucune analyse disponible."
                );

                return;
            }


            const blob =
                new Blob(
                    [
                        JSON.stringify(
                            lastResponse,
                            null,
                            2
                        )
                    ],
                    {
                        type:
                            "application/json"
                    }
                );


            const url =
                URL.createObjectURL(blob);


            const link =
                document.createElement("a");


            link.href = url;

            link.download =
                "synia_analyse.json";


            document.body.appendChild(link);

            link.click();

            link.remove();


            URL.revokeObjectURL(url);

        }
    );

}


// ============================================================
// DOWNLOAD
// ============================================================

const downloadBtn =
    document.getElementById(
        "downloadBtn"
    );


if (downloadBtn) {

    downloadBtn.addEventListener(
        "click",
        () => {

            window.print();

        }
    );

}


// ============================================================
// NEW ANALYSIS
// ============================================================

const newAnalysisBtn =
    document.getElementById(
        "newAnalysisBtn"
    );


if (newAnalysisBtn) {

    newAnalysisBtn.addEventListener(
        "click",
        () => {

            resetFile();


            if (resultContent) {
                resultContent.innerHTML = "";
            }


            showPage("analyse");

        }
    );

}


// ============================================================
// ERROR DISPLAY
// ============================================================

function showError(message) {

    if (!errorMessage) {
        return;
    }


    const span =
        errorMessage.querySelector(
            "span"
        );


    if (span) {

        span.textContent =
            message;

    }


    errorMessage.classList.add(
        "show"
    );

}


function hideError() {

    if (!errorMessage) {
        return;
    }


    errorMessage.classList.remove(
        "show"
    );

}


// ============================================================
// FORMAT SIZE
// ============================================================

function formatSize(bytes) {

    if (bytes < 1024) {

        return `${bytes} octets`;

    }


    if (bytes < 1024 * 1024) {

        return `${(
            bytes / 1024
        ).toFixed(1)} KB`;

    }


    return `${(
        bytes /
        (1024 * 1024)
    ).toFixed(1)} MB`;

}


// ============================================================
// HTML ESCAPE
// ============================================================

function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }


    return String(value)
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );

}


// ============================================================
// INITIAL LOAD
// ============================================================

chargerDernieresAnalyses();