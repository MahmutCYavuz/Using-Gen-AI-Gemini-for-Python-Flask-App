import os
from flask import Flask, render_template, request, redirect, url_for, session
import markdown
import google.generativeai as genai
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import docx
from PyPDF2 import PdfReader
import re
# from transformers import pipeline

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
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text()
    except Exception as e:
        print(f"Error reading PDF file: {e}")
    return text


def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])



# Hugging Face'den Türkçe NER modeli yükleniyor
# ner_model = pipeline("ner", model="savasy/bert-base-turkish-ner-cased", aggregation_strategy="simple")

# def redact_sensitive_info(text):
#     # NER modeli ile isim ve soyisimleri bul
#     entities = ner_model(text)

#     # Bulunan isim ve soyisimleri ayrı ayrı ve birlikte topla
#     names = set()
#     full_names = set()

#     for entity in entities:
#         if entity['entity_group'] == 'PER':
#             names.add(entity['word'])
#             full_names.add(entity['word'])

#     # İsim ve soyisimleri birlikte ve ayrı ayrı maskele
#     for full_name in full_names:
#         # Tam ismi maskele
#         pattern = re.compile(rf'\b{full_name}(\w*)\b', re.IGNORECASE)
#         text = pattern.sub(lambda m: '****' + m.group(1), text)

#         # İsim ve soyisimleri ayrı ayrı maskele
#         for name in full_name.split():
#             pattern = re.compile(rf'\b{name}(\w*)\b', re.IGNORECASE)
#             text = pattern.sub(lambda m: '****' + m.group(1), text)

    # # Kimlik numarasını tespit edip maskeleme
    # id_pattern = r'\b\d{11}\b'
    # text = re.sub(id_pattern, lambda m: '***********' if int(m.group()) % 2 == 0 else m.group(), text)

    # # Telefon numaralarını tespit edip maskeleme (10 haneli numaralar)
    # phone_pattern = r'\b\d{10}\b'
    # text = re.sub(phone_pattern, '**********', text)

    # # Adres tespit ve maskeleme
    # address_pattern = r'\b\S+ (Sokak|Sk|Sok|Cadde|Cd|Mahalle|Mahallesi|Mah|Mh|Apartman|Apartmanı|Apt|Blok|No|Kapı|Daire|D|No)\b.*'
    # text = re.sub(address_pattern, '**** adres ****', text)

    # return text


# def mask_sensitive_data(text):
    # TCKN Maskeleme
    masked_text = re.sub(r'\b(T?C?K?N?:?\s*)(\d{3})\d{6}(\d{2})\b', r'\1\2******\3', text)

    # Telefon Numarası Maskeleme
    masked_text = re.sub(r'\b(Tel:?\s*)(0?\d{3})\s*(\d{3})\s*(\d{2})\s*(\d{2})\b', r'\1\2 *** ** **', masked_text)
    masked_text = re.sub(r'\b(\d{1,4})\s*(\d{3})\s*(\d{2})\s*(\d{2})\b', r'\1 *** ** **', masked_text)

    # VKN Maskeleme
    masked_text = re.sub(r'\b(V?K?N?:?\s*)(\d{3})\d{5}(\d{2})\b', r'\1\2*****\3', masked_text)

    # Adres Bilgisi Maskeleme
    masked_text = re.sub(r'(No:)\s*\d+(/\d+)?', r'\1 **', masked_text)
    masked_text = re.sub(r'(Daire:)\s*\d+', r'\1 **', masked_text)
    masked_text = re.sub(r'(Kat:)\s*\d+', r'\1 **', masked_text)

    # İsim Maskeleme (Avukatlar ve diğer özel isimler için)
    def mask_name(match):
        prefix = match.group(1) if match.group(1) else ""
        first_name = match.group(2)
        last_name = match.group(3)
        return f"{prefix}{first_name[0]}{'*' * (len(first_name) - 1)} {last_name[0]}{'*' * (len(last_name) - 1)}"

    masked_text = re.sub(r'\b(Av\.|Avukat\s+)?([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)\s+([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü]+)\b', mask_name, masked_text)

    # Şirket İsmi Maskeleme
    sirket_turleri = r'(A\.Ş\.|LTD\.\s*ŞTİ\.|Limited Şirketi|Anonim Şirketi)'
    masked_text = re.sub(rf'\b([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü]+)(\s+[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü]+)*\s+{sirket_turleri}\b', 
                         lambda m: m.group(1) + ' ' + '*' * len(m.group(0).split(m.group(1))[1].split(m.group(-1))[0]) + m.group(-1), 
                         masked_text)

    # E-mail Maskeleme
    masked_text = re.sub(r'\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', 
                         lambda m: f"{m.group(1)[0]}{'*' * (len(m.group(1)) - 1)}@{m.group(2)}", 
                         masked_text)

    return masked_text


@app.route("/", methods=["GET", "POST"])
def index():
    result1 = {}
    
    if request.method == 'POST':
        input_text = request.form.get('input_text', '').strip()
        file = request.files.get('file')
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            if filename.rsplit('.', 1)[1].lower() == 'pdf':
                file_content = extract_text_from_pdf(file_path)
            elif filename.rsplit('.', 1)[1].lower() == 'docx':
                file_content = extract_text_from_docx(file_path)
            
            input_text = file_content + "\n\n" + input_text
        
        if not input_text:
            return "Geçersiz istek: Metin veya dosya gerekli", 400
        
        model = genai.GenerativeModel('gemini-pro')
        try:
            prompt = """Her bölümü verdiğim başlıklar altında yazdır,
                aşağıdaki davada dilekçeyi özetle 'DİLEKÇE ÖZETİ',
                ardından yaşanılan durumları kronolojik olarak sırala 'DAVANIN KRONOLOJİSİ',
                ardından Dilekçedeki argumanları dogrulayacak emsal yargıtay kararlarını çıkar 'EMSAL YARGITAY KARARI',
                içeriğini yazdır,'DİLEKÇE İÇERİĞİ',
                davacı argümanlarını oluştur,'DAVACININ ARGÜMANLARI',
                bu metin içeriğinde gözümden kaçırdığım ve mahkemede beni zorlayacak argümanları listele 'GÖZDEN KAÇAN ARGÜMANLAR',
                Bu dava metnini aşağıda yazacağım. Hukuki Dava metnine benzemeyen promptlara "Sadece hukuki davalara cevap veriyorum!" cevabını ilet. Dava Metni:""" + input_text
            
            response = model.generate_content(prompt)
            
            # Yanıtı bölümlere ayır
            sections = ['DİLEKÇE ÖZETİ', 'DAVANIN KRONOLOJİSİ', 'EMSAL YARGITAY KARARI', 'DİLEKÇE İÇERİĞİ', 'DAVACININ ARGÜMANLARI', 'GÖZDEN KAÇAN ARGÜMANLAR']
            result1 = {}
            current_section = ''
            for line in response.text.split('\n'):
                if any(section in line for section in sections):
                    current_section = next(section for section in sections if section in line)
                    result1[current_section] = ''
                elif current_section:
                    result1[current_section] += line + '\n'

            # Her bölümü Markdown'a çevir
            for section in result1:
                result1[section] = markdown.markdown(result1[section])
            
            print("Result1:", result1)  # Debug için
        
        except Exception as e:
            result1 = {"Hata": f"Hata oluştu: {e}"}
        
        return render_template('index.html', result1=result1)
    
    return render_template('index.html', result1=None)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

