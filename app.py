import os
from flask import Flask, render_template, request, redirect, url_for, session
import markdown
import openai 
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import docx
from PyPDF2 import PdfReader
import re
from transformers import pipeline


# Çevresel değişkenleri yükle
load_dotenv()

# genai.configure(api_key=os.getenv('API_KEY'))
openai.api_key = os.getenv('OPENAI_API_KEY')  # Bu satırı ekleyin

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

# Load the Turkish NER model from Hugging Face

ner_model = pipeline("ner", model="savasy/bert-base-turkish-ner-cased", aggregation_strategy="simple")

# PDF metnini temizleme ve normalize etme
def clean_text(text):
    # Birden fazla boşluğu tek bir boşluk yap
    text = re.sub(r'\s+', ' ', text)
    # Gereksiz karakterleri kaldırma
    text = re.sub(r'[^\w\s.,:]', '', text)
    return text


# Function to mask sensitive data
def redact_sensitive_info(text):
    # Anahtar kelimelerden sonra gelen isimleri maskeleme fonksiyonu
    def mask_after_keywords(match):
        return f"{match.group(1)}: ********"

    # 1. Kural: DAVACI, DAVALI, VEKİLİ, Av., HUKUK BÜROSU kelimelerinden sonra gelen isimler maskelenecek
    text = re.sub(r'\b(DAVACI|DAVALI|VEKİLİ|Av\.|HUKUK BÜROSU)\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü]+\b', mask_after_keywords, text)
    entities = ner_model(text)

    # Bulunan isim ve soyisimleri ayrı ayrı ve birlikte topla
    names = set()
    full_names = set()

    for entity in entities:
        if entity['entity_group'] == 'PER':
            names.add(entity['word'])
            full_names.add(entity['word'])

    # İsim ve soyisimleri birlikte ve ayrı ayrı maskele
    for full_name in full_names:
        # Tam ismi maskele
        pattern = re.compile(rf'\b{full_name}(\w*)\b', re.IGNORECASE)
        text = pattern.sub(lambda m: '****' + m.group(1), text)

        # İsim ve soyisimleri ayrı ayrı maskele
        for name in full_name.split():
            pattern = re.compile(rf'\b{name}(\w*)\b', re.IGNORECASE)
            text = pattern.sub(lambda m: '****' + m.group(1), text)
    # 2. Kural: Özel olarak "DAVACI:" ve "DAVALI:" ifadesinden sonra gelen isimler maskelenecek
    # DAVACI ve DAVALI'dan sonra gelen isimleri doğru şekilde maskeleme
    text = re.sub(r"(DAVACI|DAVALI)\s*:\s*[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü]+)*", r"\1: ******** ******** **** **** **** **** **** ****** ******* ****************** ", text)
    text = re.sub(r'(DAVACI|DAVALI|VEKİLİ|Av\.|HUKUK BÜROSU)\s*:\s*[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü]+)*', r'\1: ******** ******** **** ***** ****** **** *********** ', text)
    text = re.sub(r'(DAVALI:\s*)(.*?)(\(VKN:\s*\d{10}\))', r'\1 ****** \3', text)
    text = re.sub(r'(SAN\s+ve\s+TİC\.?\s+A\.Ş\.?|Ltd\.?\s+Şti\.?|A\.Ş\.?|Tic\.?|Şti\.?|SAN\.?)', '******', text)
    text = re.sub(r'(\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü]+\s+(SAN\.?\s+ve\s+TİC\.?\s+A\.Ş\.?|Ltd\.?\s+Şti\.?|Şti\.?|A\.Ş\.?|Tic\.?))', '******', text)
    text = re.sub(r'(DAVACI|DAVALI)\s*:\s*(.*?)(?=\s|$)', r'\1: ******** *********** ******* ******* ******* ****** ***** **** ***** *************************', text)
     # DAVACI, DAVALI, VEKİLİ, Av., HUKUK BÜROSU kelimelerinden sonra gelen isimleri maskeleme


    #text = re.sub(r"(DAVACI|DAVALI)\s*:\s*[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü]+\b", r"\1: ******** ********", text)

    # 3. Kural: Telefon numaralarını tespit edip maskeleme (10 haneli numaralar, boşluklu ve boşluksuz)
    phone_pattern = r'\b(0\d{3})\s*\d{3}\s*\d{2}\s*\d{2}\b|\b(0\d{3})\d{7}\b'
    text = re.sub(phone_pattern, r'\1 *** ** **', text)

    # 4. Kural: Adres tespit ve maskeleme (adres ifadeleri: Sokak, Cadde, Mahalle, No vb.)
    address_pattern = r'\b\S+\s+(Sokak|Sok|Cadde|Cad.|Cd.|Mh.|Mah.|Mahalle|Mahallesi|Apartman|Apartmanı|Blok|No|Kat|Daire|Daire:)\b.*'
    text = re.sub(address_pattern, '**** adres ****', text)

    # 5. Kural: Şirket isimlerini maskeleme (örnek: HİSTAŞ HİSAR İNŞ. TUR. SAN ve TİC. A.Ş.)
    company_pattern = r'\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)+\s+(San\.|Tic\.|Ltd\.|A\.Ş\.|Şti\.)\b'
    text = re.sub(company_pattern, '******** ********', text)

    # 6. Kural: Mahkeme isimlerini maskeleme (örnek: Sulh Hukuk Mahkemesi)
    court_pattern = r'\b([A-ZÇĞİÖŞÜÜ]+)\s+([A-ZÇĞİÖŞÜÜ]+)\s+\([A-ZÇĞİÖŞÜÜ]+\)\s+[HUKUK]\s+[MAHKEMESİ]\b'
    text = re.sub(court_pattern, '******** ********', text)

    # 7. Kural: Şehir ve ilçe isimlerini maskeleme (örnek: Beşiktaş/İst.)
    
    city_pattern = r'\b([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)/([A-ZÇĞİÖŞÜ]+)\b'
    text = re.sub(city_pattern, '********/********', text)

    # 8. Kural: TCKN ve VKN numaralarını maskeleme
    text = re.sub(r'TCKN:\s*\d{11}', 'TCKN: ***********', text)
    text = re.sub(r'VKN:\s*\d{10}', 'VKN: **********', text)
    
    # mernis no

    # 9. Kural: Doğum tarihlerini tespit edip maskeleme (dd/mm/yyyy veya dd-mm-yyyy formatında)
    date_pattern = r'\b\d{2}[/-]\d{2}[/-]\d{4}\b'
    text = re.sub(date_pattern, '****/****/****', text)

    # 10. Kural: Dava esas ve karar numaralarını maskele (örn: 2022/1809 E.)
    #text = re.sub(r'\b(\d{4}/\d{4,6}\s*(E|K))\b', '****/**** **', text)

    # 11. Ekstra Pattern'ler:
    # İsimler, adresler, davacı/davalı ve avukat bilgileri, mahkeme isimleri gibi bilgileri ekliyoruz
    patterns = [
        #r"\b[A-ZÇĞİÖŞÜÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜÜ][a-zçğıöşü]+)*\b",  # İsimler
        r"\b[A-ZÇĞİÖŞÜÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜÜ][a-zçğıöşü]+)*\s+(Mah\.|Cad\.|Sok\.)\s*\d+",  # Adresler
        r"DAVACI:\s+(.*?)\s*(?=(DAVALI|Av\.))",  # Davacı ve tüm bilgileri (sonraki başlık bulunana kadar)
        r"DAVALI:\s+(.*?)\s*(?=(VEKİLİ|$))",  # Davalı ve tüm bilgileri (sonraki başlık bulunana kadar)
        r"Av\.\s+(.*?)\s*(?=\s|$)",  # Avukat ismi
        r"([A-ZÇĞİÖŞÜÜ]+)\s+([A-ZÇĞİÖŞÜÜ]+)\s+\([A-ZÇĞİÖŞÜÜ]+\)\s+[HUKUK]\s+[MAHKEMESİ]",  # Mahkeme adı (daha genel)
    ]

    for pattern in patterns:
        text = re.sub(pattern, '********', text)

    return text





@app.route("/", methods=["GET", "POST"])
def index():
    result1 = {}
    message = None
    
    if request.method == 'POST':
        input_text1 = ""
        input_text2 = ""
        files = request.files.getlist('file')  # Birden fazla dosya al

        if len(files) > 0:
            file1 = files[0]
            if file1 and allowed_file(file1.filename):
                filename1 = secure_filename(file1.filename)
                file_path1 = os.path.join(app.config['UPLOAD_FOLDER'], filename1)
                file1.save(file_path1)
                
                if filename1.rsplit('.', 1)[1].lower() == 'pdf':
                    input_text1 = extract_text_from_pdf(file_path1)
                elif filename1.rsplit('.', 1)[1].lower() == 'docx':
                    input_text1 = extract_text_from_docx(file_path1)

                # Metni temizle ve konsola yazdır
                input_text1 = redact_sensitive_info(input_text1)
                print("Dosya 1 İçeriği (Redacted):", input_text1)

        if len(files) > 1:
            file2 = files[1]
            if file2 and allowed_file(file2.filename):
                filename2 = secure_filename(file2.filename)
                file_path2 = os.path.join(app.config['UPLOAD_FOLDER'], filename2)
                file2.save(file_path2)
                
                if filename2.rsplit('.', 1)[1].lower() == 'pdf':
                    input_text2 = extract_text_from_pdf(file_path2)
                elif filename2.rsplit('.', 1)[1].lower() == 'docx':
                    input_text2 = extract_text_from_docx(file_path2)

                # Metni temizle ve konsola yazdır
                input_text2 = redact_sensitive_info(input_text2)
                print("Dosya 2 İçeriği (Redacted):", input_text2)

        # Prompt oluştur
        prompt = """
        Aşağıdaki dava metinlerini analiz et ve Dilekçe Özetini ve Dilekçede bulunan dosyaları madde madde alt alta yazıp'DİLEKÇE ÖZETİ:' başlığı altında,
        Davanın Kronolojik sıralamasını ve olayları tarihleriyle birlikte gg/aa/yyyy şeklinde 'DAVANIN KRONOLOJİSİ:' başlığı altında,
        Davaya ilişkin geçmiş emsal yargıtay kararlarını internetten bul ve içeriğini 'EMSAL YARGITAY KARARLARI:' başlığı altında,
        Davacının bütün Argümanlarını 'DAVACININ ARGÜMANLARI:' başlığı altında,
        Gözden Kaçan ve Zorluk çıkarabilecek Argümanları 'GÖZDEN KAÇAN ARGÜMANLAR:' başlığı altında,
        Metinde 'Dosya 2 İçeriği (Redacted)' kelimesini görürsen eğer Poliçe ile Dava Metnini karşılaştır ve 'POLİÇE KARŞILAŞTIRMASI:' başlığı altında yaz

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
""" + input_text1 + "\n\nMetin 2:\n" + input_text2

        # OpenAI API çağrısı
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",  # veya "gpt-4" kullanabilirsiniz
                messages=[
                    {"role": "system", "content": ""},
                    {"role": "user", "content": prompt}
                ]   
            )
            # Yanıtı bölümlere ayır
            sections = ['DİLEKÇE ÖZETİ:', 'DAVANIN KRONOLOJİSİ:', 'EMSAL YARGITAY KARARLARI:', 'DAVACININ ARGÜMANLARI:', 'GÖZDEN KAÇAN ARGÜMANLAR:','POLİÇE KARŞILAŞTIRMASI:']
            result1 = {}
            current_section = None
            content = ""

            for line in response.choices[0].message['content'].split('\n'):  # OpenAI yanıtını işle
                if any(section in line for section in sections):
                    if current_section:
                        result1[current_section] = content.strip()
                        content = ""
                    current_section = next(section for section in sections if section in line)
                elif current_section:
                    content += line + "\n"
            
            if current_section:
                result1[current_section] = content.strip()

            # Her bölümü Markdown'a çevir
            for section in result1:
                if result1[section]:
                    result1[section] = markdown.markdown(result1[section])
                else:
                    result1[section] = ""
            
            print("Result1:", result1)  # Debug için
        
        except Exception as e:
            result1 = {"Hata": f"Hata oluştu: {e}"}
        
        return render_template('index.html', result1=result1, message=message)
    
    return render_template('index.html', result1=None, message=None)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

