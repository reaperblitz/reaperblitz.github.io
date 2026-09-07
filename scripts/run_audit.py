import sys
import os
import subprocess
import requests
from pypdf import PdfReader

# Discord Webhook fetched from GitHub Actions Secrets
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_discord_embed(title, description, color=3447003, fields=None):
    """Sends structured embed messages to Discord."""
    if not DISCORD_WEBHOOK_URL:
        print("[WARNING] DISCORD_WEBHOOK_URL not found in environment. Skipping Discord logging.")
        return

    embed = {
        "title": title,
        "description": description[:2000],  # Discord limit
        "color": color
    }
    if fields:
        embed["fields"] = fields

    payload = {"embeds": [embed]}
    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to post to Discord: {e}")

def extract_pdf_text(pdf_path):
    """Parses text from a PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for idx, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        if page_text:
            text += f"\n--- Page {idx} ---\n" + page_text.strip()
    return text

def query_ollama_cli(prompt, model_name="trained-curriculum-ai"):
    """Queries Ollama directly using the CLI binary installed in the runner environment."""
    try:
        process = subprocess.run(
            ["ollama", "run", model_name, prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True
        )
        return process.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_details = e.stderr.strip() if e.stderr else str(e)
        raise RuntimeError(f"Ollama CLI error: {error_details}")

def save_report(file_name, report_content):
    """Saves the audit findings to the reports/ directory."""
    os.makedirs("reports", exist_ok=True)
    report_filename = f"reports/audit_{os.path.splitext(file_name)[0]}.md"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(f"# Curriculum Audit Report: {file_name}\n\n")
        f.write(report_content)
    print(f"Saved audit report to {report_filename}")

def main():
    if len(sys.argv) < 2:
        print("Error: No file path provided.")
        print("Usage: python run_audit.py <path_to_curriculum_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    file_name = os.path.basename(pdf_path)

    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' not found.")
        sys.exit(1)

    # Step 1: Send initial status update to Discord
    send_discord_embed(
        title="📑 AI Compliance Audit Initiated",
        description=f"Auditing file: `{file_name}`",
        color=3447003  # Blue
    )

    # Step 2: Extract PDF Text
    try:
        print(f"Extracting text from: {pdf_path}")
        curriculum_text = extract_pdf_text(pdf_path)
        if not curriculum_text.strip():
            raise ValueError("No readable text could be extracted from the PDF.")
    except Exception as e:
        error_msg = f"Failed to extract text from `{file_name}`: {str(e)}"
        print(f"[ERROR] {error_msg}")
        send_discord_embed(title="❌ Audit Error", description=error_msg, color=15158332)
        sys.exit(1)

    # Step 3: Construct evaluation prompt
    prompt = f"""You are a Curriculum Auditor AI.
Review the following curriculum content against your pre-trained accreditation criteria and examples.

CURRICULUM FILE: {file_name}

CONTENT:
{curriculum_text[:5000]}

Provide a structured report covering:
1. Overall Compliance Status (PASS, FAIL, or NEEDS REVISION)
2. Identified Non-Compliance Issues or Gaps
3. Actionable Recommendations

Use Thai language.
"""

    # Step 4: Query Model & Handle Output
    print(f"Executing CLI model '{model_name if 'model_name' in locals() else 'trained-curriculum-ai'}'...")
    try:
        audit_output = query_ollama_cli(prompt)

        # Save markdown report to disk
        save_report(file_name, audit_output)

        # Step 5: Post findings to Discord
        send_discord_embed(
            title=f"📊 Compliance Audit Complete: {file_name}",
            description=audit_output,
            color=3066993  # Green
        )
        print("Audit completed successfully.")

    except Exception as e:
        error_msg = f"Audit execution failed: {str(e)}"
        print(f"[ERROR] {error_msg}")
        send_discord_embed(title="❌ Audit Execution Failed", description=error_msg, color=15158332)
        sys.exit(1)

if __name__ == "__main__":
    main()
