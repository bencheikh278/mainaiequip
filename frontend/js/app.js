const API_URL = "http://127.0.0.1:8000";


// ============================================================
// ELEMENTS
// ============================================================

const pages =
    document.querySelectorAll(".page");

const navItems =
    document.querySelectorAll(".nav-item");

const fileInput =
    document.getElementById("fileInput");

const uploadZone =
    document.getElementById("uploadZone");

const filePreview =
    document.getElementById("filePreview");

const fileName =
    document.getElementById("fileName");

const fileSize =
    document.getElementById("fileSize");

const removeFile =
    document.getElementById("removeFile");

const analyseBtn =
    document.getElementById("analyseBtn");

const loading =
    document.getElementById("loading");

const errorMessage =
    document.getElementById("errorMessage");

const resultContent =
    document.getElementById("resultContent");

let lastResponse = null;



// ============================================================
// NAVIGATION
// ============================================================

function showPage(pageName) {

    pages.forEach(page => {

        page.classList.remove("active");

    });


    const target =
        document.getElementById(
            `page-${pageName}`
        );


    if (!target) {
        return;
    }


    target.classList.add("active");


    navItems.forEach(item => {

        item.classList.remove("active");


        if (
            item.dataset.page === pageName
        ) {

            item.classList.add("active");

        }

    });


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}



// sidebar buttons

navItems.forEach(item => {

    item.addEventListener(
        "click",
        () => {

            showPage(
                item.dataset.page
            );

        }
    );

});



// home button

document
    .getElementById("goAnalyse")
    .addEventListener(
        "click",
        () => {

            showPage("analyse");

        }
    );



// history button

document
    .querySelector(".text-button")
    .addEventListener(
        "click",
        () => {

            showPage("historique");

        }
    );



// ============================================================
// FILE SELECTION
// ============================================================

fileInput.addEventListener(
    "change",
    handleFile
);


function handleFile() {

    hideError();


    if (!fileInput.files.length) {

        resetFile();

        return;
    }


    const file =
        fileInput.files[0];


    const maxSize =
        20 * 1024 * 1024;


    if (file.size > maxSize) {

        showError(
            "Le fichier dépasse la limite de 20 Mo."
        );

        resetFile();

        return;
    }


    fileName.textContent =
        file.name;


    fileSize.textContent =
        formatSize(file.size);


    filePreview.classList.add(
        "show"
    );


    analyseBtn.disabled = false;
}



// ============================================================
// DRAG & DROP
// ============================================================

uploadZone.addEventListener(
    "dragover",
    event => {

        event.preventDefault();

        uploadZone.classList.add(
            "dragover"
        );

    }
);


uploadZone.addEventListener(
    "dragleave",
    () => {

        uploadZone.classList.remove(
            "dragover"
        );

    }
);


uploadZone.addEventListener(
    "drop",
    event => {

        event.preventDefault();

        uploadZone.classList.remove(
            "dragover"
        );


        const files =
            event.dataTransfer.files;


        if (!files.length) {
            return;
        }


        fileInput.files =
            files;


        handleFile();

    }
);



// ============================================================
// REMOVE FILE
// ============================================================

removeFile.addEventListener(
    "click",
    () => {

        resetFile();

    }
);


function resetFile() {

    fileInput.value = "";

    filePreview.classList.remove(
        "show"
    );

    fileName.textContent = "";

    fileSize.textContent = "";

    analyseBtn.disabled = true;
}



// ============================================================
// ANALYSE
// ============================================================

analyseBtn.addEventListener(
    "click",
    analyseDocument
);


async function analyseDocument() {

    if (!fileInput.files.length) {

        showError(
            "Veuillez sélectionner un fichier."
        );

        return;
    }


    const file =
        fileInput.files[0];


    const formData =
        new FormData();


    formData.append(
        "fichier",
        file
    );


    // interface

    analyseBtn.disabled = true;

    analyseBtn.innerHTML =
        "Analyse en cours...";

    loading.classList.add(
        "show"
    );

    hideError();


    try {

        console.log(
            "Envoi du fichier :",
            file.name
        );


        const response =
            await fetch(
                `${API_URL}/api/analyse`,
                {
                    method: "POST",
                    body: formData
                }
            );


        const data =
            await response.json();


        console.log(
            "Réponse API :",
            data
        );


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Erreur pendant l'analyse."
            );

        }


        lastResponse = data;


        displayResult(
            data
        );


        showPage("result");


    } catch (error) {

        console.error(error);


        showError(
            error.message ||
            "Impossible de contacter le serveur."
        );

    } finally {

        loading.classList.remove(
            "show"
        );


        analyseBtn.disabled = false;

        analyseBtn.innerHTML =
            `
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
// ============================================================

function displayResult(data) {

    resultContent.innerHTML = "";


    const analyse =
        data.analyse || {};


    const synthese =
        data.synthese || {};


    // --------------------------------------------------------
    // Équipements
    // --------------------------------------------------------

    const equipements =
        analyse.equipements || [];


    equipements.forEach(
        (equipement, index) => {

            addResultItem(
                resultContent,
                index + 1,
                "Équipement",
                `
                    <strong>
                        ${escapeHtml(
                            equipement.nom ||
                            "Non identifié"
                        )}
                    </strong>

                    <br>

                    ${escapeHtml(
                        equipement.type ||
                        "Type non précisé"
                    )}
                `
            );


            // anomalies

            if (
                equipement.anomalies &&
                equipement.anomalies.length
            ) {

                const anomalies =
                    equipement.anomalies
                        .map(anomalie => {

                            const niveau =
                                anomalie.niveau ||
                                "Non précisé";


                            return `
                                <div class="result-list-item">

                                    ${escapeHtml(
                                        anomalie.description
                                    )}

                                    <span>
                                        (${escapeHtml(
                                            niveau
                                        )})
                                    </span>

                                </div>
                            `;

                        })
                        .join("");


                addResultItem(
                    resultContent,
                    "--",
                    "Anomalies",
                    `
                        <div class="result-list">
                            ${anomalies}
                        </div>
                    `
                );

            }


            // causes

            if (
                equipement.causes &&
                equipement.causes.length
            ) {

                const causes =
                    equipement.causes
                        .map(cause => {

                            return `
                                <div class="result-list-item">
                                    ${escapeHtml(cause)}
                                </div>
                            `;

                        })
                        .join("");


                addResultItem(
                    resultContent,
                    "--",
                    "Causes",
                    `
                        <div class="result-list">
                            ${causes}
                        </div>
                    `
                );

            }


            // interventions

            if (
                equipement.interventions &&
                equipement.interventions.length
            ) {

                const interventions =
                    equipement.interventions
                        .map(intervention => {

                            return `
                                <div class="result-list-item">
                                    ${escapeHtml(
                                        intervention
                                    )}
                                </div>
                            `;

                        })
                        .join("");


                addResultItem(
                    resultContent,
                    "--",
                    "Interventions réalisées",
                    `
                        <div class="result-list">
                            ${interventions}
                        </div>
                    `
                );

            }


            // results

            if (
                equipement.resultats &&
                equipement.resultats.length
            ) {

                const results =
                    equipement.resultats
                        .map(resultat => {

                            return `
                                <div class="result-list-item">
                                    ${escapeHtml(resultat)}
                                </div>
                            `;

                        })
                        .join("");


                addResultItem(
                    resultContent,
                    "--",
                    "Résultats",
                    `
                        <div class="result-list">
                            ${results}
                        </div>
                    `
                );

            }

        }
    );



    // --------------------------------------------------------
    // Synthèse
    // --------------------------------------------------------

    if (
        synthese.synthese_interventions &&
        synthese.synthese_interventions.length
    ) {

        synthese
            .synthese_interventions
            .forEach(item => {

                addResultItem(
                    resultContent,
                    "06",
                    "Synthèse de l'intervention",
                    `
                        <strong>
                            ${escapeHtml(
                                item.equipement
                            )}
                        </strong>

                        <br>

                        ${escapeHtml(
                            item.resume
                        )}
                    `
                );

            });

    }



    // --------------------------------------------------------
    // Recommendations
    // --------------------------------------------------------

    if (
        synthese.recommandations &&
        synthese.recommandations.length
    ) {

        const recommendations =
            synthese
                .recommandations
                .map(reco => {

                    const priority =
                        (reco.priorite || "")
                        .toLowerCase();


                    let priorityClass =
                        "priority-medium";


                    if (
                        priority.includes("haute") ||
                        priority.includes("high")
                    ) {

                        priorityClass =
                            "priority-high";
                    }


                    if (
                        priority.includes("basse") ||
                        priority.includes("low")
                    ) {

                        priorityClass =
                            "priority-low";
                    }


                    return `
                        <div class="priority-box">

                            <span
                                class="priority-label ${priorityClass}"
                            >
                                ${escapeHtml(
                                    reco.priorite
                                )}
                            </span>

                            <div class="priority-action">

                                <strong>
                                    ${escapeHtml(
                                        reco.equipement
                                    )}
                                </strong>

                                <br>

                                ${escapeHtml(
                                    reco.action
                                )}

                            </div>

                            <div class="priority-justification">

                                ${escapeHtml(
                                    reco.justification
                                )}

                            </div>

                        </div>
                    `;

                })
                .join("");


        addResultItem(
            resultContent,
            "07",
            "Recommandations",
            recommendations
        );

    }

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


    container.appendChild(
        item
    );

}



// ============================================================
// EXPORT JSON
// ============================================================

document
    .getElementById("exportJsonBtn")
    .addEventListener(
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
                URL.createObjectURL(
                    blob
                );


            const link =
                document.createElement(
                    "a"
                );


            link.href = url;

            link.download =
                "synia_analyse.json";


            document.body.appendChild(
                link
            );

            link.click();

            link.remove();


            URL.revokeObjectURL(
                url
            );

        }
    );



// ============================================================
// DOWNLOAD
// ============================================================

document
    .getElementById("downloadBtn")
    .addEventListener(
        "click",
        () => {

            window.print();

        }
    );



// ============================================================
// NEW ANALYSIS
// ============================================================

document
    .getElementById("newAnalysisBtn")
    .addEventListener(
        "click",
        () => {

            resetFile();

            resultContent.innerHTML = "";

            showPage(
                "analyse"
            );

        }
    );



// ============================================================
// ERROR
// ============================================================

function showError(message) {

    const span =
        errorMessage.querySelector(
            "span"
        );


    span.textContent =
        message;


    errorMessage.classList.add(
        "show"
    );
}


function hideError() {

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
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}