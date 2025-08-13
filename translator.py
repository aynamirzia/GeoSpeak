from flask import Flask, request, render_template
import google.generativeai as genai
import fitz  # PyMuPDF for PDF text extraction
import pytesseract
from PIL import Image
import os


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

# Configure Gemini API
genai.configure(api_key="AIzaSyCgfOtpqPq8Tvzt_rdaYS3lSmBG1Iyhq5o")
model = genai.GenerativeModel("gemini-2.5-flash")

# Make uploads folder if not exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def extract_pdf_text(file_path):
    """Extract text from a PDF file, with OCR fallback for scanned pages."""
    text = ""
    pdf_document = fitz.open(file_path)

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        page_text = page.get_text()

        # If page text is empty, try OCR
        if not page_text.strip():
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_text = pytesseract.image_to_string(img)

        text += page_text + "\n"

    return text

@app.route("/pdf_translator", method=["POST"])
def pdf_translator():
    if "pdf_file" not in request.files:
        return jsonify({"error": "No PDF file provided"}), 400

    pdf_file = request.files["pdf_file"]
    if pdf_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    target_language = request.form.get("target_lang", "Urdu")

    # Save file
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_file.filename)
    pdf_file.save(file_path)

    # Extract text
    pdf_text = extract_pdf_text(file_path)
    if not pdf_text.strip():
        return jsonify({"error": "Could not extract text from PDF"}), 400

    # Translate
    prompt = f"Translate the following PDF content to {target_language}:\n\n{pdf_text[:10000]}"
    response = model.generate_content(prompt)
    translated_text = response.text

    return jsonify({
        "target_language": target_language,
        "original_preview": pdf_text[:500],
        "translated_text": translated_text
    })


@app.route("/pdf", methods=["GET", "POST"])
def translate_text():
    user_input = ""
    translated_text = ""
    target_language = "Urdu"

    if request.method == "POST":
        target_language = request.form.get("target_lang", "Urdu")

        # Text translation
        if "message" in request.form and request.form["message"].strip():
            user_input = request.form["message"]
            prompt = f"Translate the following text to {target_language}:\n\n{user_input}"
            response = model.generate_content(prompt)
            translated_text = response.text

        # PDF translation
        elif "pdf_file" in request.files:
            pdf_file = request.files["pdf_file"]
            if pdf_file.filename != "":
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_file.filename)
                pdf_file.save(file_path)

                # Extract text (with OCR fallback)
                pdf_text = extract_pdf_text(file_path)

                if not pdf_text.strip():
                    translated_text = "Could not extract text from the PDF."
                else:
                    user_input = f"(PDF content preview) {pdf_text[:500]}..."
                    prompt = f"Translate the following PDF content to {target_language}:\n\n{pdf_text[:10000]}"
                    response = model.generate_content(prompt)
                    translated_text = response.text

    return render_template(
        "index.html",
        user_input=user_input,
        translated_text=translated_text,
        target_language=target_language
    )


if __name__ == "__main__":
    app.run(debug=True)
