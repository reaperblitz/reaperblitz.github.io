import os
import sys
import subprocess
import requests
from pypdf import PdfReader

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
CURRICULUM_DIR = "curriculum"
MODEL_NAME = "trained-curriculum-ai"


def send_discord_embed(title, description, color=3447003, fields=None):
    """Sends structured embed messages to Discord."""
    if not DISCORD_WEBHOOK_URL:
        print("[WARNING] DISCORD_WEBHOOK_URL not set in environment. Skipping Discord logging.")
        return

    embed = {
        "title": title,
        "description": description[:2000] if description else "",
        "color": color
    }
    if fields:
        embed["fields"] = fields

    payload = {"embeds": [embed]}
    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to send Discord webhook: {e}")


def get_curriculum_file(directory_path):
    """Detects and returns the path of the file inside the curriculum directory."""
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"Directory '{directory_path}' does not exist.")

    files = [
        os.path.join(directory_path, f)
        for f in os.listdir(directory_path)
        if os.path.isfile(os.path.join(directory_path, f)) and not f.startswith(".")
    ]

    if not files:
        raise FileNotFoundError(f"No files found inside '{directory_path}/'.")

    # Pick the single target file present in the directory
    return files[0]


def extract_pdf_text(pdf_path):
    """Parses text from a PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for idx, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        if page_text:
            text += f"\n--- Page {idx} ---\n" + page_text.strip()
    return text


def query_ollama(prompt, model=MODEL_NAME):
    """Queries Ollama via CLI first, falling back to REST API if needed."""
    try:
        print(f"Executing CLI model '{model}'...")
        res = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True
        )
        return res.stdout.strip()
    except Exception as cli_err:
        print(f"[INFO] CLI call failed ({cli_err}). Retrying via local REST API...")
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        res = requests.post(url, json=payload, timeout=180)
        res.raise_for_status()
        return res.json().get("response", "")


def save_report(file_name, report_content):
    """Saves the generated audit report as markdown."""
    os.makedirs("reports", exist_ok=True)
    clean_name = os.path.splitext(file_name)[0]
    report_filename = f"reports/audit_{clean_name}.md"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(f"# Curriculum Audit Report: {file_name}\n\n")
        f.write(report_content)
    print(f"Saved audit report to {report_filename}")


def main():
    # Detect file in curriculum folder or accept direct argument
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        try:
            target_path = get_curriculum_file(CURRICULUM_DIR)
        except Exception as e:
            err_msg = f"Failed to locate file in '{CURRICULUM_DIR}': {e}"
            print(f"[ERROR] {err_msg}")
            send_discord_embed(title="❌ Audit Failed to Start", description=err_msg, color=15158332)
            sys.exit(1)

    file_name = os.path.basename(target_path)
    print(f"Auditing target file: {target_path}")

    # 1. Send status update to Discord
    send_discord_embed(
        title="📑 AI Compliance Audit Initiated",
        description=f"Auditing file: `{file_name}`",
        color=3447003  # Blue
    )

    # 2. Extract PDF Text
    try:
        print(f"Extracting text from: {target_path}")
        curriculum_text = extract_pdf_text(target_path)
        if not curriculum_text.strip():
            raise ValueError("No readable text could be extracted from the file.")
    except Exception as e:
        err_msg = f"Failed to extract text from `{file_name}`: {str(e)}"
        print(f"[ERROR] {err_msg}")
        send_discord_embed(title="❌ Audit Extraction Error", description=err_msg, color=15158332)
        sys.exit(1)

    # 3. Construct prompt
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

    # 4. Run Model Evaluation
    try:
        audit_output = query_ollama(prompt, MODEL_NAME)

        save_report(file_name, audit_output)

        send_discord_embed(
            title=f"📊 Compliance Audit Complete: {file_name}",
            description=audit_output,
            color=3066993  # Green
        )
        print("Audit execution completed successfully.")

    except Exception as e:
        err_msg = f"Audit execution failed: {str(e)}"
        print(f"[ERROR] {err_msg}")
        send_discord_embed(title="❌ Audit Execution Failed", description=err_msg, color=15158332)
        sys.exit(1)


if __name__ == "__main__":
    main()
