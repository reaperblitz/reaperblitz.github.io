// Configuration
const GITHUB_OWNER = "your-github-username";
const GITHUB_REPO = "your-repo-name";
const WORKFLOW_ID = "review.yml";

// NOTE: For production, invoke this via a backend worker (e.g., Cloudflare Worker)
// to avoid exposing your GitHub Personal Access Token in client-side code.
const GITHUB_PAT = "your_github_personal_access_token"; 

async function startAudit() {
    const fileInput = document.getElementById("curriculumFile");
    const statusCard = document.getElementById("statusCard");
    const statusText = document.getElementById("statusText");

    if (!fileInput.files.length) {
        alert("Please select a curriculum file first.");
        return;
    }

    const fileName = fileInput.files[0].name;

    statusCard.classList.remove("hidden");
    statusText.innerText = `Triggering GitHub Action audit for: ${fileName}...`;

    try {
        const response = await fetch(
            `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`,
            {
                method: "POST",
                headers: {
                    "Accept": "application/vnd.github+json",
                    "Authorization": `Bearer ${GITHUB_PAT}`,
                    "X-GitHub-Api-Version": "2022-11-28",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    ref: "main",
                    inputs: {
                        curriculum_file: `curriculums/${fileName}`
                    }
                })
            }
        );

        if (response.status === 204) {
            statusText.innerText = " Audit triggered successfully! Check Discord for real-time progress and findings.";
        } else {
            const errData = await response.json();
            statusText.innerText = ` Failed to trigger audit: ${errData.message}`;
        }
    } catch (err) {
        statusText.innerText = ` Error: ${err.message}`;
    }
}
