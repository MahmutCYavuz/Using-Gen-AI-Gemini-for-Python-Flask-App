import os
from flask import Flask, render_template, request, redirect, url_for, session
import markdown
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import docx
from PyPDF2 import PdfReader
import re
from transformers import pipeline


# Çevresel değişkenleri yükle
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # Gizli anahtar .env dosyasından alınır

# OpenAI istemcisini oluştur
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

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
def extract_text_from_files(files):
    input_text1 = ""
    input_text2 = ""
    for i, file in enumerate(files):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        elif filename.endswith('.docx'):
            text = extract_text_from_docx(file_path)
        else:
            continue

        # İlk dosya input_text1'e, ikinci dosya input_text2'ye atanır
        if i == 0:
            input_text1 += text
        elif i == 1:
            input_text2 += text

    return input_text1, input_text2

# NER modeli yükleme
ner_model = pipeline("ner", model="savasy/bert-base-turkish-ner-cased", aggregation_strategy="simple")

# Metni temizleme ve normalize etme fonksiyonu
def clean_text(text):
    """
    Metni normalize eder ve gereksiz karakterleri temizler.
    """
    text = re.sub(r'\s+', ' ', text)  # Birden fazla boşluk yerine tek bir boşluk koyar
    text = re.sub(r'[^\w\s.,:]', '', text)  # Gereksiz karakterleri kaldırır
    return text

# Hassas verileri maskelemek için fonksiyon
def redact_sensitive_info(text):
    """
    Hassas bilgileri NER modeli ve regex ile maskeleyen fonksiyon.
    """
    # Regex ile maskeleme kuralları
    MASKING_RULES = [
        (r'\b(DAVACI|DAVALI|VEKİLİ|Av\.|HUKUK BÜROSU)\s+([A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s*){1,3}\b', r'\1: ********'),
        (r'\b(0\d{3})[-\s]*\d{3}[-\s]*\d{2}[-\s]*\d{2}\b|\b(0\d{3})[-\s]*\d{7}\b', r'\1 *** ** **'),  # Telefon numaraları
        (r'\b\S+\s+(Sokak|Sok|Cadde|Cd\.|Mh\.|Mah\.|Mahalle|Apartman|Blok|No|Kat|Daire)\b.*', '**** adres ****'),  # Adres
        (r'\b([A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+){1,3}(San\.|Tic\.|Ltd\.|A\.Ş\.|Şti\.)\b', '******** ********'),  # Şirket isimleri
        (r'\b(TCKN|T\.C\. Kimlik No):?\s*\d{11}\b', 'TCKN: ***********'),  # TCKN
        (r'\b(VKN|Vergi No):?\s*\d{10}\b', 'VKN: **********'),  # VKN
        (r'\b[A-ZÇĞİÖŞÜ]+(?:\s[A-ZÇĞİÖŞÜ]+)?/[A-ZÇĞİÖŞÜ]+(?:\s[A-ZÇĞİÖŞÜ]+)?\b', '********/********'),  # Şehir/ilçe isimleri
        (r'\b[A-ZÇĞİÖŞÜ]+[\s][A-ZÇĞİÖŞÜ]+\s+\([A-ZÇĞİÖŞÜ]+\)\s+HUKUK\s+MAHKEMESİ\b', '******** Mahkemesi'),  # Mahkeme isimleri
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '********@*****.***') # E-posta adreslerinin maskelenmesi
    ]

    # Regex ile metin maskeleme
    for pattern, replacement in MASKING_RULES:
        text = re.sub(pattern, replacement, text)

    # NER modeli ile kişisel isim tespiti ve maskeleme
    entities = ner_model(text)
    for entity in entities:
        if entity['entity_group'] == 'PER':
            name = entity['word']
            # İsimleri maskele
            text = re.sub(rf'\b{re.escape(name)}\b', '********', text, flags=re.IGNORECASE)
     # Hassas kelimeleri maskele
    sensitive_words = ['Neova Katılım Sigorta', 'Neova Katılım', 'Neova','AcnTurk', 'AKSigorta', 'Allianz', 'Anadolu', 'Arex', 'Atradius', 'Atlas', 'Aveon Global', 'Axa', 'Bereket', 'BNP Paribas Cardif', 'BUPA Acıbadem', 'CHUBB', 'Coface', 'Corpus', 'Doga', 'Emaa', 'Ethica', 'Euler Hermes', 'Eureko', 'Fiba', 'Generali', 'Global World', 'GRI', 'GIG', 'HDI', 'HDI Katılım', 'Hepiyi', 'Koru', 'Magdeburger', 'Mapfre', 'Medisa', 'Neova Katılım', 'Orient', 'Quick', 'Prive', 'Ray', 'Sompo', 'Şeker', 'Mellce', 'Turkcell Dijital', 'Türk Nippon', 'Türk P ve I', 'Türkiye Katılım', 'Unico', 'VHV Allgemeine', 'Zurich','Artun']
    for word in sensitive_words:
        # Kelime grubunu tam olarak eşleştir
        text = re.sub(rf'\b{re.escape(word)}\b', '********', text, flags=re.IGNORECASE)

    # Debug: Maskeleme sonrası metni yazdır
    print("Maskeleme sonrası metin:", text)

    return text


@app.route("/", methods=["GET", "POST"])
def index():
    result1 = {}
    message = None
    
    if request.method == 'POST':
        # Metin girişi
        input_text1 = request.form.get('input_text', '').strip()
        input_text2 = ""

        # Dosya yükleme
        files = request.files.getlist('file')
        if files and files[0].filename != '':
            input_text1, input_text2 = extract_text_from_files(files)

        # Eğer sadece metin girildiyse, input_text2'yi boş bırak
        if input_text1 and not input_text2:
            input_text2 = ""

        # Metinleri maskele
        masked_text1 = redact_sensitive_info(input_text1)
        masked_text2 = redact_sensitive_info(input_text2)

        # Debug: Maskeleme sonrası metinleri yazdır
        print("Masked Metin 1:", masked_text1)
        print("Masked Metin 2:", masked_text2)

        # Prompt oluştur
        prompt = f"""
        Aşağıdaki dava metinlerini analiz et ve Dilekçe Özetini ve Dilekçede bulunan dosyaları madde madde alt alta yazıp'DİLEKÇE ÖZETİ:' başlığı altında,
        Davanın Kronolojik sıralamasını ve olayları tarihleriyle birlikte gg/aa/yyyy şeklinde 'DAVANIN KRONOLOJİSİ:' başlığı altında,
        Davaya ilişkin geçmiş emsal yargıtay kararlarını internetten bul ve içeriğini 'EMSAL YARGITAY KARARLARI:' başlığı altında,
        Davacının bütün Argümanlarını 'DAVACININ ARGÜMANLARI:' başlığı altında,
        Gözden Kaçan ve Zorluk çıkarabilecek Argümanları 'GÖZDEN KAÇAN ARGÜMANLAR:' başlığı altında,
        Metinde 'Metin 2:' kelimesini görürsen eğer Poliçe ile Dava Metnini detaylıca karşılaştır ve 'POLİÇE KARŞILAŞTIRMASI:' başlığı altında yaz

        Her bölümü kesinlikle belirtilen başlıkla başlat ve içeriği bu başlığın altına yaz.

DİLEKÇE ÖZETİ:
DAVANIN KRONOLOJİSİ:
EMSAL YARGITAY KARARLARI:
DAVACININ ARGÜMANLARI:
GÖZDEN KAÇAN ARGÜMANLAR:
POLİÇE KARŞILAŞTIRMASI:
Eğer herhangi bir bölüm için bilgi yoksa, o bölüme "Yeterli bilgi bulunmamaktadır!" yaz. Hukuki olmayan metinlere "Sadece hukuki davalara cevap veriyorum!" cevabını ver. 
İşte analiz edilecek dava metinleri:
Metin 1:
{masked_text1}

Metin 2:
{masked_text2}
"""
        # OpenAI API çağrısı
        try:
            print("API çağrısı yapılıyor...")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sen yardımsever bir hukukçu asistanısın ve metni analiz edip bana yardımcı olacaksın."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000
            )
            print("API yanıtı alındı.")
            print("Yanıt içeriği:", response.choices[0].message.content)

            # Yanıtı bölümlere ayır
            sections = ['DİLEKÇE ÖZETİ:', 'DAVANIN KRONOLOJİSİ:', 'EMSAL YARGITAY KARARLARI:', 'DAVACININ ARGÜMANLARI:', 'GÖZDEN KAÇAN ARGÜMANLAR:', 'POLİÇE KARŞILAŞTIRMASI:']
            result1 = {}
            current_section = None
            content = ""

            for line in response.choices[0].message.content.split('\n'):
                if any(section in line for section in sections):
                    if current_section:
                        result1[current_section] = content.strip()
                        content = ""
                    current_section = next(section for section in sections if section in line)
                elif current_section:
                    content += line + "\n"

            if current_section:
                result1[current_section] = content.strip() if content.strip() else "Yeterli bilgi bulunmamaktadır!"

            # Her bölümü Markdown'a çevir
            for section in result1:
                if result1[section]:
                    result1[section] = markdown.markdown(result1[section])
                else:
                    result1[section] = ""
            
            print("Result1:", result1)
        
        except Exception as e:
            print("API çağrısı sırasında hata oluştu:", e)
            result1 = {"Hata": f"Hata oluştu: {e}"}
        
        return render_template('index.html', result1=result1, message=message)
    
    return render_template('index.html', result1=None, message=None)
if __name__ == '__main__':
    app.run(debug=True, port=5000)