function copyLatex() {
const textarea = document.querySelector("textarea");
textarea.select();
document.execCommand("copy");

const status = document.getElementById("copy-status");
status.innerText = "✅ LaTeX code copied!";
setTimeout(() => (status.innerText = ""), 2000);
}

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, unhighlight, false);
});

function highlight(e) {
    dropZone.classList.add('dragover');
}

function unhighlight(e) {
    dropZone.classList.remove('dragover');
}

dropZone.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    fileInput.files = files;
    showPreview(files[0]);
}

fileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    const preview = document.getElementById('preview');
    const fileName = document.getElementById('fileName');

    if (file) {
        fileName.textContent = file.name;
        
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                preview.src = e.target.result;
                preview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        } else {
            // Hide preview for PDFs
            preview.style.display = 'none';
        }
    }
});

function showPreview(file) {
    const preview = document.getElementById('preview');
    const fileName = document.getElementById('fileName');
    
    if (file) {
        fileName.textContent = file.name;
        
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                preview.src = e.target.result;
                preview.style.display = 'block';
            }
            reader.readAsDataURL(file);
        } else {
            preview.style.display = 'none';
        }
    }
}

// Theme toggling functionality
const themeToggle = document.getElementById('themeToggle');
const root = document.documentElement;

themeToggle.addEventListener('click', () => {
    const currentTheme = root.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    root.setAttribute('data-theme', newTheme);
    themeToggle.textContent = newTheme === 'light' ? '☀️' : '🌙';
    
    // Save theme preference
    localStorage.setItem('theme', newTheme);
});

// Load saved theme preference
const savedTheme = localStorage.getItem('theme') || 'light';
root.setAttribute('data-theme', savedTheme);
themeToggle.textContent = savedTheme === 'light' ? '☀️' : '🌙';

function printPreview() {
    const printWindow = window.open('', '_blank');
    const previewContent = document.getElementById('latexPreview').innerHTML;
    
    printWindow.document.write(`
        <html>
            <head>
                <title>LaTeX Preview</title>
                <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
                <style>
                    body { padding: 20px; font-size: 14pt; }
                    .preview-content { margin: 0 auto; max-width: 800px; }
                </style>
            </head>
            <body>
                <div class="preview-content">${previewContent}</div>
            </body>
        </html>
    `);
    
    printWindow.document.addEventListener('DOMContentLoaded', function() {
        MathJax.typesetPromise().then(() => {
            printWindow.print();
            printWindow.close();
        });
    });
}
