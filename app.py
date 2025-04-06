from flask import Flask, render_template, request, send_from_directory, url_for
import os
import google.generativeai as genai
from flask import send_from_directory
import uuid
from PIL import Image
from dotenv import load_dotenv
from pdf2image import convert_from_path
from user_agents import parse

load_dotenv()
api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-pro-latest")
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

    user_agent_string = request.headers.get('User-Agent')
    user_agent = parse(user_agent_string)
    is_mobile = user_agent.is_mobile

    file_extension = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)

    if file_extension == '.pdf':
        try:
            images = convert_from_path(filepath)
            all_latex_codes = []
            
            for page_num, img in enumerate(images):
                prompt = f"Extract all handwritten math expressions from this image. Convert this handwritten math expression to LaTeX format. Format: Each formula must be in $$...$$ and placed on a new line. Do NOT use ``` or \\[ \\]. Output only LaTeX equations.\n"
                try:
                    response = model.generate_content([img, prompt])
                    page_latex = response.text.strip()
                    if page_latex:
                        all_latex_codes.append(page_latex)
                except Exception as e:
                    return f"Error processing page {page_num + 1}: {str(e)}", 500
            
            latex_code = "\n".join(all_latex_codes)
        except Exception as e:
            return f"Error processing PDF: {str(e)}", 500
    else:
        img = Image.open(filepath)
        prompt = f"Extract all handwritten math expressions from this image. Convert this handwritten math expression to LaTeX format. Format: Each formula must be in $$...$$ and placed on a new line. Do NOT use ``` or \\[ \\]. Output only LaTeX equations.\n"
        try:
            response = model.generate_content([img, prompt])
            latex_code = response.text.strip()
        except Exception as e:
            return f"Error from Gemini: {str(e)}", 500

    if not latex_code.strip().startswith("$"):
        latex_code = f"${latex_code.strip()}$"

    full_latex_code = f"""\\documentclass{{article}}
    \\usepackage{{amsmath}}
    \\usepackage{{amssymb}}

    \\begin{{document}}

    {latex_code}

    \\end{{document}}
    """

    tex_filename = f"{uuid.uuid4().hex}.tex"
    tex_path = os.path.join(app.config['UPLOAD_FOLDER'], tex_filename)
    
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(full_latex_code)

    return render_template('index.html',
                       latex_code=latex_code,
                       latex_file=tex_filename,
                       image_url=url_for('static', filename=f'uploads/{unique_filename}'),
                       is_mobile=is_mobile)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)