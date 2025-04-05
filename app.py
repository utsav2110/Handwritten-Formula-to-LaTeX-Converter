from flask import Flask, render_template, request, send_from_directory, url_for
import os
import easyocr
import cv2
import google.generativeai as genai
from flask import send_from_directory
import uuid
import subprocess
from PIL import Image

# Configure Gemini API
genai.configure(api_key="") # Add your Gemini API key here
model = genai.GenerativeModel("gemini-1.5-pro-latest")

reader = easyocr.Reader(['en'])
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return "No file uploaded", 400

    file = request.files['image']
    if file.filename == '':
        return "No file selected", 400

    # Create a unique filename for the uploaded image
    image_filename = f"{uuid.uuid4().hex}{os.path.splitext(file.filename)[1]}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
    file.save(filepath)

    # ---- OCR Extract Text ----
    # result = reader.readtext(filepath, detail=0)
    # extracted_text = " ".join(result)
    # print("OCR Output:", extracted_text)

    # ---- Gemini Convert to LaTeX ----
    img = Image.open(filepath)
    prompt = f"Extract all handwritten math expressions from this image.Convert this handwritten math expression to LaTeX format. Format: Each formula must be in $$...$$ and placed on a new line.Do NOT use ``` or \\[ \\]. Output only LaTeX equations.\n"
    try:
        response = model.generate_content([img, prompt])
        latex_code = response.text.strip()
    except Exception as e:
        latex_code = f"Error from Gemini: {e}"

    # Wrap only if it's not already in math mode
    if latex_code.startswith("```"):
        latex_code = latex_code.replace("```latex", "").replace("```", "").strip()

    if not latex_code.strip().startswith("$"):
        latex_code = f"${latex_code.strip()}$"

    # Wrap in proper LaTeX structure
    full_latex_code = f"""\\documentclass{{article}}
    \\usepackage{{amsmath}}
    \\usepackage{{amssymb}}

    \\begin{{document}}

    {latex_code}

    \\end{{document}}
    """

    filename = f"{uuid.uuid4().hex}.tex"
    tex_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(full_latex_code)

    pdf_filename = filename.replace('.tex', '.pdf')
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)

    try:
        subprocess.run(["pdflatex", "-output-directory", app.config['UPLOAD_FOLDER'], tex_path], check=True)
    except subprocess.CalledProcessError:
        return "PDF conversion failed!", 500

    return render_template('index.html',
                       latex_code=latex_code,
                       latex_file=filename,
                       pdf_file=pdf_filename,
                       pdf_url=url_for('static', filename=f'uploads/{pdf_filename}'),
                       image_url=url_for('static', filename=f'uploads/{image_filename}'))

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/download_pdf/<filename>')
def download_pdf(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    # Ensure both uploads and static/uploads directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
