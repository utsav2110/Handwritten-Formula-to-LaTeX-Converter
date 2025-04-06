from flask import Flask, render_template, request, send_from_directory, url_for
import os
import easyocr
import cv2
import google.generativeai as genai
from flask import send_from_directory
import uuid
import subprocess
from PIL import Image
from dotenv import load_dotenv
import PyPDF2
import fitz  # PyMuPDF

# Add user-agent detection
from user_agents import parse

load_dotenv()
api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

reader = easyocr.Reader(['en'])
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return "No file uploaded", 400

    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400

    # Get user agent
    user_agent_string = request.headers.get('User-Agent')
    user_agent = parse(user_agent_string)
    is_mobile = user_agent.is_mobile

    # Create a unique filename for the uploaded file
    file_extension = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)

    if file_extension == '.pdf':
        try:
            pdf_document = fitz.open(filepath)
            all_latex_codes = []
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # Increase resolution
                img_data = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Process each page as an image
                prompt = f"Extract all handwritten math expressions from this image. Convert this handwritten math expression to LaTeX format. Format: Each formula must be in $$...$$ and placed on a new line. Do NOT use ``` or \\[ \\]. Output only LaTeX equations.\n"
                try:
                    response = model.generate_content([img_data, prompt])
                    page_latex = response.text.strip()
                    if page_latex:
                        all_latex_codes.append(page_latex)
                except Exception as e:
                    return f"Error processing page {page_num + 1}: {str(e)}", 500
            
            pdf_document.close()
            latex_code = "\n".join(all_latex_codes)
        except Exception as e:
            return f"Error processing PDF: {str(e)}", 500
    else:
        # Handle single image processing
        img = Image.open(filepath)
        prompt = f"Extract all handwritten math expressions from this image. Convert this handwritten math expression to LaTeX format. Format: Each formula must be in $$...$$ and placed on a new line. Do NOT use ``` or \\[ \\]. Output only LaTeX equations.\n"
        try:
            response = model.generate_content([img, prompt])
            latex_code = response.text.strip()
        except Exception as e:
            return f"Error from Gemini: {str(e)}", 500

    # Common processing for both PDF and image
    if not latex_code.strip().startswith("$"):
        latex_code = f"${latex_code.strip()}$"

    # Create LaTeX document
    full_latex_code = f"""\\documentclass{{article}}
    \\usepackage{{amsmath}}
    \\usepackage{{amssymb}}

    \\begin{{document}}

    {latex_code}

    \\end{{document}}
    """

    # Save and process LaTeX file
    tex_filename = f"{uuid.uuid4().hex}.tex"
    tex_path = os.path.join(app.config['UPLOAD_FOLDER'], tex_filename)
    
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(full_latex_code)

    pdf_filename = tex_filename.replace('.tex', '.pdf')
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)

    try:
        subprocess.run(["pdflatex", "-output-directory", app.config['UPLOAD_FOLDER'], tex_path], check=True)
    except subprocess.CalledProcessError:
        return "PDF conversion failed!", 500

    return render_template('index.html',
                       latex_code=latex_code,
                       latex_file=tex_filename,
                       pdf_file=pdf_filename,
                       pdf_url=url_for('static', filename=f'uploads/{pdf_filename}'),
                       image_url=url_for('static', filename=f'uploads/{unique_filename}'),
                       is_mobile=is_mobile)

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
