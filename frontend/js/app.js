// ============================================================
// SYNIA — FRONTEND
// ============================================================

// FastAPI local
const API_URL = "http://127.0.0.1:8000";


// ============================================================
// VARIABLES
// ============================================================

let selectedFiles = [];
let lastResponse = null;


// ============================================================
// INITIALISATION
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    console.log(">>> SYNIA FRONTEND INITIALISÉ");

    initializeNavigation();
    initializeFileUpload();
    initializeButtons();

    loadHistory();
});


// ============================================================
// NAVIGATION
// ============================================================

function initializeNavigation() {

    const navItems = document.querySelectorAll(".nav-item");
    const pages = document.querySelectorAll(".page");

    navItems.forEach(item => {

        item.addEventListener("click", () => {

            const pageName = item.dataset.page;

            if (!pageName) {
                return;
            }

            showPage(pageName);

        });

    });
}


function showPage(pageName) {

    console.log(">>> PAGE :", pageName);

    const pages = document.querySelectorAll(".page");
    const navItems = document.querySelectorAll(".nav-item");

    pages.forEach(page => {

        page.classList.remove("active");

        if (page.id === pageName) {
            page.classList.add("active");
        }

    });

    navItems.forEach(item => {

        item.classList.remove("active");

        if (item.dataset.page === pageName) {
            item.classList.add("active");
        }

    });

}


// ============================================================
// FILE UPLOAD
// ============================================================

function initializeFileUpload() {

    const fileInput = document.getElementById("fileInput");
    const uploadZone = document.getElementById("uploadZone");

    if (!fileInput) {
        console.error("fileInput introuvable");
        return;
    }

    fileInput.addEventListener("change", event => {

        const files = Array.from(event.target.files);

        addFiles(files);

    });


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

            const files = Array.from(event.dataTransfer.files);

            addFiles(files);

        });

    }

}


// ============================================================
// AJOUT DES FICHIERS
// ============================================================

function addFiles(files) {

    const allowedExtensions = [
        ".pdf",
        ".docx",
        ".txt"
    ];

    const MAX_SIZE = 20 * 1024 * 1024; // 20 MB

    files.forEach(file => {

        const extension =
            "." + file.name.split(".").pop().toLowerCase();

        if (!allowedExtensions.includes(extension)) {

            showError(
                `Format non supporté : ${file.name}`
            );

            return;
        }


        if (file.size > MAX_SIZE) {

            showError(
                `Le fichier ${file.name} dépasse 20 MB.`
            );

            return;
        }


        // éviter les doublons
        const alreadyExists = selectedFiles.some(
            existingFile =>
                existingFile.name === file.name &&
                existingFile.size === file.size
        );

        if (alreadyExists) {
            return;
        }


        selectedFiles.push(file);

    });


    displaySelectedFiles();

}


// ============================================================
// AFFICHER LES FICHIERS SÉLECTIONNÉS
// ============================================================

function displaySelectedFiles() {

    const container =
        document.getElementById("filePreviewList");

    if (!container) {
        return;
    }


    container.innerHTML = "";


    if (selectedFiles.length === 0) {

        container.innerHTML = `
            <div class="empty-files">
                Aucun fichier sélectionné
            </div>
        `;

        return;
    }


    selectedFiles.forEach((file, index) => {

        const fileElement = document.createElement("div");

        fileElement.className = "file-preview";


        fileElement.innerHTML = `

            <div class="file-info">

                <span class="file-name">
                    ${escapeHtml(file.name)}
                </span>

                <span class="file-size">
                    ${formatFileSize(file.size)}
                </span>

            </div>

            <button
                type="button"
                class="remove-file"
                data-index="${index}"
            >
                ×
            </button>

        `;


        container.appendChild(fileElement);

    });


    // Boutons supprimer

    const removeButtons =
        container.querySelectorAll(".remove-file");


    removeButtons.forEach(button => {

        button.addEventListener("click", () => {

            const index =
                parseInt(button.dataset.index);

            selectedFiles.splice(index, 1);

            displaySelectedFiles();

        });

    });

}


// ============================================================
// BOUTONS
// ============================================================

function initializeButtons() {

    const analyseBtn =
        document.getElementById("analyseBtn");

    if (analyseBtn) {

        analyseBtn.addEventListener(
            "click",
            analyseDocument
        );

    }


    const newAnalysisBtn =
        document.getElementById("newAnalysisBtn");

    if (newAnalysisBtn) {

        newAnalysisBtn.addEventListener(
            "click",
            resetAnalysis
        );

    }


    const exportBtn =
        document.getElementById("exportJsonBtn");

    if (exportBtn) {

        exportBtn.addEventListener(
            "click",
            exportJSON
        );

    }


    const downloadBtn =
        document.getElementById("downloadBtn");

    if (downloadBtn) {

        downloadBtn.addEventListener(
            "click",
            downloadResult
        );

    }

}


// ============================================================
// ANALYSE DU DOCUMENT
// ============================================================

async function analyseDocument() {

    console.log("=================================");
    console.log(">>> DÉBUT ANALYSE");
    console.log("=================================");


    if (selectedFiles.length === 0) {

        showError(
            "Veuillez sélectionner au moins un fichier."
        );

        return;
    }


    const formData = new FormData();


    selectedFiles.forEach(file => {

        // IMPORTANT :
        // Le backend FastAPI attend "fichiers"

        formData.append("fichiers", file);

    });


    setLoading(true);
    clearError();


    try {

        console.log(">>> Envoi vers :", API_URL);
        console.log(">>> Nombre de fichiers :", selectedFiles.length);


        const response = await fetch(
            `${API_URL}/api/analyse`,
            {
                method: "POST",
                body: formData
            }
        );


        console.log(
            ">>> STATUS API :",
            response.status
        );


        // ====================================================
        // LIRE LA RÉPONSE JSON
        // ====================================================

        const data = await response.json();


        console.log("=================================");
        console.log(">>> RÉPONSE API");
        console.log(data);
        console.log("=================================");


        if (!response.ok) {

            throw new Error(
                data.detail ||
                data.message ||
                `Erreur HTTP ${response.status}`
            );

        }


        if (!data) {

            throw new Error(
                "La réponse du serveur est vide."
            );

        }


        // sauvegarder la réponse

        lastResponse = data;


        // afficher le résultat

        displayResult(data);


        // aller à la page résultat

        showPage("result");


        // actualiser l'historique

        loadHistory();


    } catch (error) {

        console.error(
            ">>> ERREUR ANALYSE :",
            error
        );


        showError(
            error.message ||
            "Une erreur est survenue pendant l'analyse."
        );


    } finally {

        setLoading(false);

    }

}


// ============================================================
// AFFICHAGE DU RÉSULTAT
// ============================================================

function displayResult(data) {

    console.log("=================================");
    console.log(">>> DISPLAY RESULT");
    console.log(">>> DATA :", data);
    console.log("=================================");


    const resultContent =
        document.getElementById("resultContent");


    if (!resultContent) {

        console.error(
            ">>> resultContent introuvable dans le HTML"
        );

        return;
    }


    resultContent.innerHTML = "";


    // ========================================================
    // VÉRIFICATION
    // ========================================================

    if (!data) {

        resultContent.innerHTML = `
            <div class="error-box">
                Aucune donnée reçue.
            </div>
        `;

        return;
    }


    const synthese = data.synthese;


    if (!synthese) {

        console.error(
            ">>> La propriété 'synthese' est absente"
        );

        resultContent.innerHTML = `

            <div class="error-box">

                <h3>Aucune synthèse reçue</h3>

                <pre>
${escapeHtml(JSON.stringify(data, null, 2))}
                </pre>

            </div>

        `;

        return;
    }


    // ========================================================
    // 1. SYNTHÈSE DES INTERVENTIONS
    // ========================================================

    const interventions =
        Array.isArray(synthese.synthese_interventions)
            ? synthese.synthese_interventions
            : [];


    let interventionsHTML = "";


    if (interventions.length === 0) {

        interventionsHTML = `

            <div class="empty-result">

                Aucune intervention réalisée trouvée.

            </div>

        `;

    } else {

        interventionsHTML = interventions
            .map((item, index) => {

                // Si l'IA retourne directement une chaîne

                if (typeof item === "string") {

                    return `

                        <div class="result-card">

                            <p>
                                ${escapeHtml(item)}
                            </p>

                        </div>

                    `;

                }


                // Nom équipement

                const equipement =
                    item.equipement ||
                    item.nom_equipement ||
                    item.equipment ||
                    "";


                // Texte de synthèse

                const texte =
                    item.resume ||
                    item.synthese ||
                    item.description ||
                    item.intervention ||
                    item.resultat ||
                    item.texte ||
                    item.action ||
                    "";


                return `

                    <div class="result-card">

                        ${
                            equipement
                                ? `
                                    <h3>
                                        ${escapeHtml(equipement)}
                                    </h3>
                                  `
                                : ""
                        }

                        <p>
                            ${escapeHtml(
                                texte ||
                                "Aucune information disponible."
                            )}
                        </p>

                    </div>

                `;

            })
            .join("");

    }


    // ========================================================
    // 2. RECOMMANDATIONS
    // ========================================================

    const recommandations =
        Array.isArray(synthese.recommandations)
            ? synthese.recommandations
            : [];


    let recommandationsHTML = "";


    if (recommandations.length === 0) {

        recommandationsHTML = `

            <div class="empty-result">

                Aucune recommandation générée.

            </div>

        `;

    } else {

        recommandationsHTML = recommandations
            .map((item, index) => {

                // Si l'IA retourne directement une chaîne

                if (typeof item === "string") {

                    return `

                        <div class="result-card">

                            <p>
                                ${escapeHtml(item)}
                            </p>

                        </div>

                    `;

                }


                const equipement =
                    item.equipement ||
                    item.nom_equipement ||
                    item.equipment ||
                    "";


                const action =
                    item.action ||
                    item.recommandation ||
                    item.description ||
                    item.texte ||
                    "";


                const priorite =
                    item.priorite ||
                    item.priority ||
                    "";


                const justification =
                    item.justification ||
                    "";


                return `

                    <div class="result-card">

                        ${
                            equipement
                                ? `
                                    <h3>
                                        ${escapeHtml(equipement)}
                                    </h3>
                                  `
                                : ""
                        }


                        ${
                            action
                                ? `
                                    <p>
                                        <strong>
                                            Recommandation :
                                        </strong>

                                        ${escapeHtml(action)}
                                    </p>
                                  `
                                : ""
                        }


                        ${
                            priorite
                                ? `
                                    <p>
                                        <strong>
                                            Priorité :
                                        </strong>

                                        ${escapeHtml(priorite)}
                                    </p>
                                  `
                                : ""
                        }


                        ${
                            justification
                                ? `
                                    <p>
                                        <strong>
                                            Justification :
                                        </strong>

                                        ${escapeHtml(
                                            justification
                                        )}
                                    </p>
                                  `
                                : ""
                        }

                    </div>

                `;

            })
            .join("");

    }


    // ========================================================
    // AFFICHAGE FINAL
    // ========================================================

    resultContent.innerHTML = `

        <section class="result-section">

            <h2>
                Synthèse des interventions réalisées
            </h2>

            <div class="result-list">

                ${interventionsHTML}

            </div>

        </section>


        <section class="result-section">

            <h2>
                Recommandations
            </h2>

            <div class="result-list">

                ${recommandationsHTML}

            </div>

        </section>

    `;


    console.log(
        ">>> AFFICHAGE DU RÉSULTAT TERMINÉ"
    );

}


// ============================================================
// HISTORIQUE
// ============================================================

async function loadHistory() {

    try {

        const response = await fetch(
            `${API_URL}/api/historique`
        );


        if (!response.ok) {

            console.warn(
                "Impossible de charger l'historique."
            );

            return;
        }


        const data = await response.json();


        console.log(
            ">>> HISTORIQUE :",
            data
        );


        displayHistory(data);


    } catch (error) {

        console.warn(
            "Erreur historique :",
            error
        );

    }

}


// ============================================================
// AFFICHER HISTORIQUE
// ============================================================

function displayHistory(data) {

    const historyRows =
        document.getElementById("historyRows");


    if (!historyRows) {
        return;
    }


    historyRows.innerHTML = "";


    let history = [];


    if (Array.isArray(data)) {

        history = data;

    } else if (Array.isArray(data.historique)) {

        history = data.historique;

    } else if (Array.isArray(data.rapports)) {

        history = data.rapports;

    }


    if (history.length === 0) {

        historyRows.innerHTML = `

            <tr>

                <td colspan="5">

                    Aucun rapport analysé.

                </td>

            </tr>

        `;

        return;
    }


    history.forEach(item => {

        const row =
            document.createElement("tr");


        const fichier =
            item.fichier ||
            item.nom ||
            "—";


        const date =
            item.analyse_le ||
            item.date ||
            "—";


        row.innerHTML = `

            <td>
                ${escapeHtml(fichier)}
            </td>

            <td>
                ${escapeHtml(date)}
            </td>

        `;


        historyRows.appendChild(row);

    });

}


// ============================================================
// EXPORT JSON
// ============================================================

function exportJSON() {

    if (!lastResponse) {

        showError(
            "Aucun résultat à exporter."
        );

        return;
    }


    const json =
        JSON.stringify(
            lastResponse,
            null,
            2
        );


    const blob =
        new Blob(
            [json],
            {
                type: "application/json"
            }
        );


    const url =
        URL.createObjectURL(blob);


    const link =
        document.createElement("a");


    link.href = url;

    link.download =
        "synia_resultat.json";


    document.body.appendChild(link);

    link.click();

    link.remove();


    URL.revokeObjectURL(url);

}


// ============================================================
// TÉLÉCHARGER / IMPRIMER LE RÉSULTAT
// ============================================================

function downloadResult() {

    if (!lastResponse) {

        showError(
            "Aucun résultat disponible."
        );

        return;
    }


    /*
       Pour le moment, on utilise
       l'impression du navigateur.

       Dans la fenêtre d'impression :
       choisir "Enregistrer au format PDF".
    */

    window.print();

}


// ============================================================
// NOUVELLE ANALYSE
// ============================================================

function resetAnalysis() {

    selectedFiles = [];

    lastResponse = null;


    const fileInput =
        document.getElementById("fileInput");


    if (fileInput) {

        fileInput.value = "";

    }


    const resultContent =
        document.getElementById("resultContent");


    if (resultContent) {

        resultContent.innerHTML = "";

    }


    displaySelectedFiles();

    clearError();

    showPage("upload");

}


// ============================================================
// LOADING
// ============================================================

function setLoading(isLoading) {

    const loading =
        document.getElementById("loading");


    const analyseBtn =
        document.getElementById("analyseBtn");


    if (loading) {

        loading.style.display =
            isLoading
                ? "flex"
                : "none";

    }


    if (analyseBtn) {

        analyseBtn.disabled =
            isLoading;

    }

}


// ============================================================
// ERREURS
// ============================================================

function showError(message) {

    console.error(
        ">>> ERREUR :",
        message
    );


    const errorMessage =
        document.getElementById("errorMessage");


    if (!errorMessage) {
        return;
    }


    errorMessage.textContent =
        message;


    errorMessage.style.display =
        "block";

}


function clearError() {

    const errorMessage =
        document.getElementById("errorMessage");


    if (!errorMessage) {
        return;
    }


    errorMessage.textContent = "";

    errorMessage.style.display =
        "none";

}


// ============================================================
// UTILITAIRES
// ============================================================

function formatFileSize(bytes) {

    if (bytes === 0) {
        return "0 Bytes";
    }


    const units = [
        "Bytes",
        "KB",
        "MB",
        "GB"
    ];


    const index =
        Math.floor(
            Math.log(bytes) /
            Math.log(1024)
        );


    return (
        parseFloat(
            (
                bytes /
                Math.pow(1024, index)
            ).toFixed(2)
        )
        +
        " " +
        units[index]
    );

}


// ============================================================
// PROTECTION HTML
// ============================================================

function escapeHtml(value) {

    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}