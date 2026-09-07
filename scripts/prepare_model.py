import os
import re
from pypdf import PdfReader

PDF_DIR = "pdf"
OUTPUT_MODELFILE = "Modelfile"
BASE_MODEL = "llama3.2:1b"


def clean_text_for_ollama(text: str) -> str:
    """Sanitizes extracted PDF text to strictly adhere to Ollama Modelfile syntax."""
    if not text:
        return ""
    # Remove null bytes and non-printable control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    # Replace triple quotes so they never accidentally close the SYSTEM block
    text = text.replace('"""', "'''")
    return text


def extract_text_from_all_descendants():
    """Recursively walks through PDF_DIR and extracts text from all descendant .pdf files."""
    if not os.path.exists(PDF_DIR):
        print(f"Error: Directory '{PDF_DIR}' does not exist.")
        return ""

    combined_text = []
    file_count = 0

    for root, _, files in os.walk(PDF_DIR):
        for file in files:
            if file.lower().endswith(".pdf"):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, start=PDF_DIR)

                print(
                    f" Extracting descendant [{file_count + 1}]: {relative_path}"
                )

                try:
                    reader = PdfReader(full_path)
                    file_text = ""
                    for page_idx, page in enumerate(reader.pages):
                        text = page.extract_text()
                        if text:
                            file_text += (
                                f"\n--- Page {page_idx + 1} ---\n"
                                + text.strip()
                            )

                    cleaned_text = clean_text_for_ollama(file_text)
                    if cleaned_text.strip():
                        document_block = (
                            f"=== START OF REFERENCE DOCUMENT: {relative_path} ===\n"
                            f"{cleaned_text}\n"
                            f"=== END OF REFERENCE DOCUMENT: {relative_path} ==="
                        )
                        combined_text.append(document_block)
                        file_count += 1
                except Exception as e:
                    print(f" Failed to process {relative_path}: {e}")

    print(f"\n Finished! Processed {file_count} total PDF document(s).")
    return "\n\n".join(combined_text)


def build_modelfile():
    all_pdf_context = extract_text_from_all_descendants()

    system_content = (
        "You are a Curriculum Auditor AI.\n\n"
        "Use the following official criteria, training guidelines, example reports, and reference materials "
        "extracted from the repository to evaluate any curriculum passed to you:\n\n"
        f"{all_pdf_context}\n\n"
        "INSTRUCTIONS:\n"
        "Evaluate input curriculum text strictly against the criteria and examples provided above. "
        "Output structured non-compliance findings."
    )

    # Secondary safety check against triple quotes
    system_content = clean_text_for_ollama(system_content)

    modelfile_content = f"""FROM {BASE_MODEL}
PARAMETER temperature 0.0
PARAMETER num_ctx 8192
SYSTEM \"\"\"
{system_content}
\"\"\"
"""

    with open(OUTPUT_MODELFILE, "w", encoding="utf-8") as f:
        f.write(modelfile_content)

    print(f" Successfully generated '{OUTPUT_MODELFILE}'!")


if __name__ == "__main__":
    build_modelfile()
