import os
from flask import Flask, render_template, request, redirect, url_for, session
import markdown
import google.generativeai as genai
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import docx
import PyPDF2

# Çevresel değişkenleri yükle
load_dotenv()

genai.configure(api_key=os.getenv('API_KEY'))

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # Gizli anahtar .env dosyasından alınır

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfFileReader(file)
        for page_num in range(reader.numPages):
            page = reader.getPage(page_num)
            text += page.extractText()
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

@app.route("/", methods=["GET", "POST"])
def index():
    result1 = ""
    
    if request.method == 'POST':
        if 'input_text' in request.form:
            input_text = request.form['input_text']
        else:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                if filename.rsplit('.', 1)[1].lower() == 'pdf':
                    input_text = extract_text_from_pdf(file_path)
                elif filename.rsplit('.', 1)[1].lower() == 'docx':
                    input_text = extract_text_from_docx(file_path)
            else:
                input_text = ""
        
        model = genai.GenerativeModel('gemini-pro')
        try:
            responseFirst = model.generate_content(
                'aşağıdaki davada davacı argümanlarını oluştur bu metin içeriğinde gözümden kaçırdığım ve mahkemede beni zorlayacak argümanları listeler misin? Bu dava metnini aşağıda yazacağım. Hukuki Dava metnine benzemeyen promptlara "Sadece hukuki davalara cevap veriyorum!" cevabını ilet. Dava Metni:' + input_text)
            result1 = markdown.markdown(responseFirst.text)
        except Exception as e:
            result1 = f"Hata oluştu: {e}"
        
        session['result1'] = result1

        # Sayfayı temiz bir şekilde yeniden yönlendirin
        return redirect(url_for('index'))
    
    # GET isteğinde session'daki sonucu alın
    if 'result1' in session:
        result1 = session.pop('result1', '')

    return render_template('index.html', result1=result1)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
