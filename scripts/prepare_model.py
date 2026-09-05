import os
from pypdf import PdfReader

PDF_DIR = "pdf"
OUTPUT_MODELFILE = "Modelfile"
BASE_MODEL = "llama3.2:1b"  # Fast model for GitHub Actions CPU runner

def extract_text_from_all_descendants():
    """Recursively walks through PDF_DIR and extracts text from all descendant .pdf files."""
    if not os.path.exists(PDF_DIR):
        print(f"Error: Directory '{PDF_DIR}' does not exist.")
        return ""

    combined_text = []
    file_count = 0

    # Walk through root folder and all subdirectories
    for root, subdirs, files in os.walk(PDF_DIR):
        for file in files:
            # Check for both lower/upper case .pdf extensions
            if file.lower().endswith(".pdf"):
                full_path = os.path.join(root, file)
                # Compute relative path to display clean document headers
                relative_path = os.path.relpath(full_path, start=PDF_DIR)
                
                print(f" Extracting descendant [{file_count + 1}]: {relative_path}")
                
                try:
                    reader = PdfReader(full_path)
                    file_text = ""
                    for page_idx, page in enumerate(reader.pages):
                        text = page.extract_text()
                        if text:
                            file_text += f"\n--- Page {page_idx + 1} ---\n" + text.strip()

                    if file_text.strip():
                        document_block = (
                            f"=== START OF REFERENCE DOCUMENT: {relative_path} ===\n"
                            f"{file_text}\n"
                            f"=== END OF REFERENCE DOCUMENT: {relative_path} ==="
                        )
                        combined_text.append(document_block)
                        file_count += 1
                except Exception as e:
                    print(f" Failed to process {relative_path}: {e}")

    print(f"\n Finished! Processed {file_count} total PDF document(s).")
    return "\n\n".join(combined_text)


def build_modelfile():
    # 1. Gather text from all subfolders
    all_pdf_context = extract_text_from_all_descendants()

    # 2. Build the System Prompt
    system_prompt = f"""You are a Curriculum Auditor AI.

Use the following official criteria, training guidelines, example reports, and reference materials extracted from the repository to evaluate any curriculum passed to you:

{all_pdf_context}

INSTRUCTIONS:
Evaluate input curriculum text strictly against the criteria and examples provided above. Output structured non-compliance findings."""

    # Escape triple-quotes to prevent breaking Ollama syntax
    system_prompt_clean = system_prompt.replace('"""', '\"\"\"')

    # 3. Write out the Ollama Modelfile
    modelfile_content = f"""FROM {BASE_MODEL}
PARAMETER temperature 0.0
PARAMETER num_ctx 8192
SYSTEM \"\"\"{system_prompt_clean}\"\"\"
"""

    with open(OUTPUT_MODELFILE, "w", encoding="utf-8") as f:
        f.write(modelfile_content)

    print(f" Successfully generated '{OUTPUT_MODELFILE}' from all descendant PDFs!")


if __name__ == "__main__":
    build_modelfile()
