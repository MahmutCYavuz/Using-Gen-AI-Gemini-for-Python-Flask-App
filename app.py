import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import markdown
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import docx
from PyPDF2 import PdfReader
import re
from transformers import pipeline
from itsdangerous import URLSafeTimedSerializer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# import logger



# Çevresel değişkenleri yükle
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # Gizli anahtar .env dosyasından alınır
email_key = os.getenv('EMAIL_KEY')
sender = os.getenv('SENDER_EMAIL')
<<<<<<< Updated upstream

=======
>>>>>>> Stashed changes
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
    texts = []
    for file in files:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        elif filename.endswith('.docx'):
            text = extract_text_from_docx(file_path)
        else:
            continue

        texts.append(text)

    return texts

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
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '********@*****.***'), # E-posta adreslerinin maskelenmesi
        (r'0[-\s]*\d{3}[-\s]*\d{3}[-\s]*\d{2}[-\s]*\d{2}','0-*** *** ** **'),
         (r'\bEMRAH ÇELİK\b', '******** ********'),
        (r'\b441\d{6}76\b', '**********'),
        (r'\b35PFK25\b', '********'),
        (r'\bBM07186\b', '********'),
        (r'\bNM0FXXTTFFBM07186\b', '********'),
        (r'\bHasan\b', '********'),
        (r'\bAv\. Fatih\b', '********'),
        (r'\bAv\. Rıdvan\b', '********'),
        (r'\bMurat\b', '********'),
        (r'\b0-232 251 51 60\b', '********'),
        (r'\b35 PFK\b', '********'),
        (r'\b35 NN\b', '********'),
        (r'\bGazi Mah\. .*? Gaziemir/İZMİR\b', '******** ********'),
        (r'\bKozyatağı Mah\. .*? Kadıköy / İstanbul\b', '******** ********') 
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
    sensitive_words = ['Neova Katılım Sigorta', 'Neova Katılım', 'Neova','AcnTurk', 'AKSigorta', 'Allianz', 'Anadolu', 'Arex', 'Atradius', 'Atlas', 'Aveon Global', 'Axa', 'Bereket', 'BNP Paribas Cardif', 'BUPA Acıbadem', 'CHUBB', 'Coface', 'Corpus', 'Doga', 'Emaa', 'Ethica', 'Euler Hermes', 'Eureko', 'Fiba', 'Generali', 'Global World', 'GRI', 'GIG', 'HDI', 'HDI Katılım', 'Hepiyi', 'Koru', 'Magdeburger', 'Mapfre', 'Medisa', 'Neova Katılım', 'Orient', 'Quick', 'Prive','Papağan', 'Ray', 'Sompo', 'Şeker', 'Mellce', 'Turkcell Dijital', 'Türk Nippon', 'Türk P ve I', 'Türkiye Katılım', 'Unico', 'VHV Allgemeine', 'Zurich','Artun']
    for word in sensitive_words:
        # Kelime grubunu tam olarak eşleştir
        text = re.sub(rf'\b{re.escape(word)}\b', '********', text, flags=re.IGNORECASE)

    # Debug: Maskeleme sonrası metni yazdır
    print("Maskeleme sonrası metin:", text)

    return text

serializer = URLSafeTimedSerializer(app.secret_key)

@app.route("/", methods = ["GET", "POST"])
def login_page():
        
    if request.method == 'POST':            
        email = request.form['email']  # Formdan email al

        if not email:
            flash("Lütfen geçerli bir e-posta adresi girin.", "error")
            return redirect(url_for('login_page'))

        try:
            token = serializer.dumps(email, salt="email-confirm")
            confirmation_link = url_for("confirm_email", token=token, _external=True)

            # E-posta gönder
            subject = "E-Posta Doğrulama"
            body = f"Lütfen e-posta adresinizi doğrulamak için aşağıdaki bağlantıya tıklayın:\n\n{confirmation_link}"
            send_email(email, subject, body)
            flash("Doğrulama e-postası başarıyla gönderildi. Lütfen gelen kutunuzu kontrol edin.", "success")
            flash("Bu sayfayı kapatabilirsiniz")
        except Exception as e:
            flash(f"E-posta gönderim hatası: {e}", "error")
    return render_template('login.html')

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        # Token çözümleme ve email doğrulama
        email = serializer.loads(token, salt='email-confirm', max_age=3600)  # Token geçerliliği: 1 saat
        session["email"] = email

        #logger.log_user_login(email)
        #flash(f"E-posta adresiniz başarıyla doğrulandı: {email}", "success")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Token geçersiz veya süresi dolmuş: {e}", "error")
        return redirect(url_for('login_page'))


def send_email(email, subject, body):
    smtp_server = "webmail.neova.com.tr"
    port = 587
    sender_email = sender
    password = email_key

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, email, message.as_string())
        print("E-posta başarıyla gönderildi.")
    except Exception as e:
        print(f"E-posta gönderilirken bir hata oluştu: {e}")
        raise e
    finally:
        server.quit()


@app.route("/index", methods=["GET", "POST"])
def index():
    result1 = {}
    message = None

    

    if "email" not in session:
        flash("Lütfen giriş yapın!", "warning")
        return redirect(url_for("login_page"))
    
    if request.method == 'POST':
        
        # Dosya yükleme
        files = request.files.getlist('file')
        # print(files)
        # for file in files:
        #     # print(file + "123456")
        #     print(file)
        #     if allowed_file(file.filename):
        #         filename = secure_filename(file.filename)
        #         file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        #          # Dosyayı kaydet
        #         try:
        #             file.save(file_path)
        #             # flash(f"Dosya başarıyla kaydedildi: {filename}", "success")
        #         except Exception as e:
        #             flash(f"Dosya kaydedilirken hata oluştu: {e}", "error")
        #             continue


        texts = extract_text_from_files(files)

        # Metinleri maskele
        masked_texts = [redact_sensitive_info(text) for text in texts]
        #Herbir maskelenmiş veri için log satırı oluştur.
        # for index, masked_data in enumerate(masked_texts):
        #     logger.log_user_activity(email=session["email"], masked_data=masked_data)

    
        # Kullanıcıdan gelen metin
        user_input = request.form.get('input_text', '').strip()

        if len(masked_texts)>1:
                prompt=f"""
        Sana yollanan metinlerden biri poliçe metni biri dava dilekçesi metni Bu metinleri analiz etmeni isteyeceğim.

        Dava dilekçesini analiz et ve şu sorulara yanıt ver:

Dava dilekçesinde belirtilen taraflar kimlerdir ve sigorta poliçesiyle ilişkileri nedir?
Davacı hangi gerekçelerle talepte bulunuyor ve bu gerekçeler poliçe kapsamında mı?
Dava konusu olay, poliçe kapsamındaki teminatlarla uyumlu mu? Poliçede istisna olarak belirtilen bir durum var mı?
Olayın gerçekleşme tarihi ile dava açma tarihi arasındaki ilişkiyi değerlendir. Zamanaşımı süresi aşılmış mı?
Davacının sunduğu deliller ve hukuki dayanaklar nelerdir? Bu dayanakların poliçe ve yasal düzenlemelerle uyumluluğunu analiz et.
Davacının taleplerinin sigorta şirketinin yükümlülükleriyle uyumluluğunu değerlendir.
Analizi net ve detaylı bir şekilde yanıtla. Yukarıdaki soruların cevaplarını'DİLEKÇE ÖZETİ:' başlığı altında,

        Aşağıdaki dava dilekçesini analiz ederek olayların kronolojik sırasını çıkar. Lütfen şu bilgileri belirt:

Olayların tarihi ve sırasıyla açıklaması.
Dava konusu olayın gerçekleşme tarihi.
Sigortalının veya diğer tarafların sigorta şirketine başvuru tarihi ve verilen yanıtlar.
Davanın açılma tarihi ve diğer hukuki süreçler.
Süreçte belirtilen herhangi bir zamanaşımı, yasal süre veya kritik tarihler.
Her bir aşamayı kısa ve net şekilde kronolojik sıraya göre 'DAVANIN KRONOLOJİSİ:' başlığı altında,

        Belirtilen dava konusu için Yargıtay'ın verdiği emsal kararları bul:

Dava konusu: [Dava konusunu açıkça belirt, örn. 'Sigorta poliçesindeki teminat kapsamı dışındaki zararlar nedeniyle açılan tazminat davaları']
Aranan hukuki çerçeve: [İlgili kanun ve maddeleri belirt, örn. 'Türk Ticaret Kanunu madde 1423']
Emsal karar kriterleri:
Yargıtay dairesi ve karar numarası (varsa).
Karar metninde dava konusu ile doğrudan bağlantılı olan hususlar.
Davalı ve davacı lehine oluşturulan argümanlar.
Dava sonucuna etkisi olan önemli hukuki değerlendirmeler.
Lütfen kararların kısa özetlerini ve davanın bağlamıyla ilişkisini sun. Ayrıca, verilen emsal kararların hangi tarihte alındığını belirt. 'EMSAL YARGITAY KARARLARI:' başlığı altında,

        Aşağıdaki dava dilekçesini analiz ederek davacının argümanlarını çıkar:

Davacının ileri sürdüğü iddialar nelerdir?
İddialarını desteklemek için hangi olaylar veya durumlara atıfta bulunuyor?
Hukuki dayanakları nelerdir? (Belirtilen yasa, madde, sözleşme hükümleri vb.)
Davacı hangi hakları veya tazminatları talep ediyor?
Sunulan deliller nelerdir ve davacı bu delillerle hangi iddialarını destekliyor?
Analizi kısa ve net bir şekilde sun, ancak detayları kaybetme. 'DAVACININ ARGÜMANLARI:' başlığı altında,

        Aşağıdaki dava dilekçesini analiz et ve gözden kaçmış olabilecek argümanları veya önemli noktaları tespit et.

Davacının veya davalının dilekçesinde eksik veya zayıf bir hukuki argüman var mı?
Dava dilekçesinde belirtilmeyen ancak davanın sonucu üzerinde etkili olabilecek başka önemli bir olgu veya durum var mı?
Hukuki dayanaklardan herhangi birisi atlanmış olabilir mi? (Özellikle dava konusu ile ilgili ek kanun, madde veya hukuki ilkeler)
Davacının iddialarını desteklemek için kullanmadığı ancak eklenmesi gereken deliller var mı?
Dava dilekçesinde daha güçlü bir argüman yaratabilecek potansiyel açıklamalar veya yönler var mı?
Lütfen gözden kaçmış olabilecek her bir noktayı net bir şekilde belirt. 'GÖZDEN KAÇAN ARGÜMANLAR:' başlığı altında,

        "Sigorta poliçesini ve dava dilekçesini aşağıdaki kriterlere göre analiz et:

Poliçe kapsamı ve şartları ile dava dilekçesindeki talepler arasında uyum var mı?
Poliçedeki teminat istisnaları, dava konusu olay açısından geçerli mi?
Sigorta süresi, prim ödemeleri ve tarafların yükümlülükleri dava dilekçesiyle çelişiyor mu?
Dava dilekçesindeki yasal dayanaklar poliçe hükümlerine uygun mu?
Süre aşımı veya yasal bir engel var mı?
Lütfen her bir kriteri ayrı ayrı değerlendir ve detaylı bir analiz sun." 'POLİÇE KARŞILAŞTIRMASI:' başlığı altında,

        'Kullanıcı Sorusu'nun cevabını metni doğru bir şekilde analiz ederek soruyu soru işaretiyle ve cevabını 'KULLANICI SORUSU:' başlığı altında,

        Her bölümü kesinlikle belirtilen başlıkla başlat ve içeriği bu başlığın altına yaz.
        
DİLEKÇE ÖZETİ:
DAVANIN KRONOLOJİSİ:
EMSAL YARGITAY KARARLARI:
DAVACININ ARGÜMANLARI:
GÖZDEN KAÇAN ARGÜMANLAR:
POLİÇE KARŞILAŞTIRMASI:
KULLANICI SORUSU:
Eğer herhangi bir bölüm için bilgi yoksa, o bölüme "Yeterli bilgi bulunmamaktadır!" yaz.
İşte analiz edilecek metinler:
""" + "\n\n".join([f"Metin {i+1}:\n{masked_text}" for i, masked_text in enumerate(masked_texts)])
                print("Prompt (Çoklu Metin): Oluşturuldu")

        elif len(masked_texts)==1:
            prompt=f"""
        Sana yollanan metin bir dava dilekçe metni. Bu metni analiz etmeni isteyeceğim.

        Dava dilekçesini analiz et ve şu sorulara yanıt ver:

Dava dilekçesinde belirtilen taraflar kimlerdir ve sigorta poliçesiyle ilişkileri nedir?
Davacı hangi gerekçelerle talepte bulunuyor ve bu gerekçeler poliçe kapsamında mı?
Dava konusu olay, poliçe kapsamındaki teminatlarla uyumlu mu? Poliçede istisna olarak belirtilen bir durum var mı?
Olayın gerçekleşme tarihi ile dava açma tarihi arasındaki ilişkiyi değerlendir. Zamanaşımı süresi aşılmış mı?
Davacının sunduğu deliller ve hukuki dayanaklar nelerdir? Bu dayanakların poliçe ve yasal düzenlemelerle uyumluluğunu analiz et.
Davacının taleplerinin sigorta şirketinin yükümlülükleriyle uyumluluğunu değerlendir.
Analizi net ve detaylı bir şekilde yanıtla. Yukarıdaki soruların cevaplarını'DİLEKÇE ÖZETİ:' başlığı altında,

        Aşağıdaki dava dilekçesini analiz ederek olayların kronolojik sırasını çıkar. Lütfen şu bilgileri belirt:

Olayların tarihi ve sırasıyla açıklaması.
Dava konusu olayın gerçekleşme tarihi.
Sigortalının veya diğer tarafların sigorta şirketine başvuru tarihi ve verilen yanıtlar.
Davanın açılma tarihi ve diğer hukuki süreçler.
Süreçte belirtilen herhangi bir zamanaşımı, yasal süre veya kritik tarihler.
Her bir aşamayı kısa ve net şekilde kronolojik sıraya göre 'DAVANIN KRONOLOJİSİ:' başlığı altında,

        Belirtilen dava konusu için Yargıtay'ın verdiği emsal kararları bul:

Dava konusu: [Dava konusunu açıkça belirt, örn. 'Sigorta poliçesindeki teminat kapsamı dışındaki zararlar nedeniyle açılan tazminat davaları']
Aranan hukuki çerçeve: [İlgili kanun ve maddeleri belirt, örn. 'Türk Ticaret Kanunu madde 1423']
Emsal karar kriterleri:
Yargıtay dairesi ve karar numarası (varsa).
Karar metninde dava konusu ile doğrudan bağlantılı olan hususlar.
Davalı ve davacı lehine oluşturulan argümanlar.
Dava sonucuna etkisi olan önemli hukuki değerlendirmeler.
Lütfen kararların kısa özetlerini ve davanın bağlamıyla ilişkisini sun. Ayrıca, verilen emsal kararların hangi tarihte alındığını belirt. 'EMSAL YARGITAY KARARLARI:' başlığı altında,

        Aşağıdaki dava dilekçesini analiz ederek davacının argümanlarını çıkar:

Davacının ileri sürdüğü iddialar nelerdir?
İddialarını desteklemek için hangi olaylar veya durumlara atıfta bulunuyor?
Hukuki dayanakları nelerdir? (Belirtilen yasa, madde, sözleşme hükümleri vb.)
Davacı hangi hakları veya tazminatları talep ediyor?
Sunulan deliller nelerdir ve davacı bu delillerle hangi iddialarını destekliyor?
Analizi kısa ve net bir şekilde sun, ancak detayları kaybetme. 'DAVACININ ARGÜMANLARI:' başlığı altında,

        Aşağıdaki dava dilekçesini analiz et ve gözden kaçmış olabilecek argümanları veya önemli noktaları tespit et.

Davacının veya davalının dilekçesinde eksik veya zayıf bir hukuki argüman var mı?
Dava dilekçesinde belirtilmeyen ancak davanın sonucu üzerinde etkili olabilecek başka önemli bir olgu veya durum var mı?
Hukuki dayanaklardan herhangi birisi atlanmış olabilir mi? (Özellikle dava konusu ile ilgili ek kanun, madde veya hukuki ilkeler)
Davacının iddialarını desteklemek için kullanmadığı ancak eklenmesi gereken deliller var mı?
Dava dilekçesinde daha güçlü bir argüman yaratabilecek potansiyel açıklamalar veya yönler var mı?
Lütfen gözden kaçmış olabilecek her bir noktayı net bir şekilde belirt. 'GÖZDEN KAÇAN ARGÜMANLAR:' başlığı altında,

        'Poliçe dosyası yüklenmemiştir. Poliçe Karşılaştırması yapmak istiyorsanız lütfen ilgili dava dilekçesiyle birlikte Poliçe dosyasını da yükleyiniz' 'POLİÇE KARŞILAŞTIRMASI:' başlığı altında,

        'Kullanıcı Sorusu'nun cevabını metni doğru bir şekilde analiz ederek soruyu soru işaretiyle ve cevabını 'KULLANICI SORUSU:' başlığı altında,

        Her bölümü kesinlikle belirtilen başlıkla başlat ve içeriği bu başlığın altına yaz.
        
DİLEKÇE ÖZETİ:
DAVANIN KRONOLOJİSİ:
EMSAL YARGITAY KARARLARI:
DAVACININ ARGÜMANLARI:
GÖZDEN KAÇAN ARGÜMANLAR:
POLİÇE KARŞILAŞTIRMASI:
KULLANICI SORUSU:
Eğer herhangi bir bölüm için bilgi yoksa, o bölüme "Yeterli bilgi bulunmamaktadır!" yaz.
İşte analiz edilecek metinler:
            """ +"\n\n".join(masked_texts[0])

                
        print('Promtum:', prompt) #debug
        # Prompt oluştur
#         prompt = f"""
#         Aşağıdaki dava metinlerini analiz et ve Dilekçe Özetini ve Dilekçede bulunan dosyaları madde madde alt alta yazıp'DİLEKÇE ÖZETİ:' başlığı altında,
#         Davanın Kronolojik sıralamasını ve olayları tarihleriyle birlikte gg/aa/yyyy şeklinde 'DAVANIN KRONOLOJİSİ:' başlığı altında,
#         Davaya ilişkin geçmiş emsal yargıtay kararlarını internetten bul ve içeriğini 'EMSAL YARGITAY KARARLARI:' başlığı altında,
#         Davacının bütün Argümanlarını 'DAVACININ ARGÜMANLARI:' başlığı altında,
#         Gözden Kaçan ve Zorluk çıkarabilecek Argümanları 'GÖZDEN KAÇAN ARGÜMANLAR:' başlığı altında,
#         Metinde 'Metin 2:' kelimesini görürsen eğer Poliçe ile Dava Metnini detaylıca karşılaştır ve 'POLİÇE KARŞILAŞTIRMASI:' başlığı altında yaz,
#         'Kullanıcı Sorusu'nun cevabını metni doğru bir şekilde analiz ederek soruyu ve cevabını 'KULLANICI SORUSU:' başlığı altında yaz.

#         Her bölümü kesinlikle belirtilen başlıkla başlat ve içeriği bu başlığın altına yaz.
        
# DİLEKÇE ÖZETİ:
# DAVANIN KRONOLOJİSİ:
# EMSAL YARGITAY KARARLARI:
# DAVACININ ARGÜMANLARI:
# GÖZDEN KAÇAN ARGÜMANLAR:
# POLİÇE KARŞILAŞTIRMASI:
# KULLANICI SORUSU:
# Eğer herhangi bir bölüm için bilgi yoksa, o bölüme "Yeterli bilgi bulunmamaktadır!" yaz. Hukuki olmayan metinlere "Sadece hukuki davalara cevap veriyorum!" cevabını ver. 
# İşte analiz edilecek dava metinleri:
# """ + "\n\n".join([f"Metin {i+1}:\n{masked_text}" for i, masked_text in enumerate(masked_texts)])
        # Kullanıcıdan gelen metni prompt'a ekle
        if user_input:
            prompt += f"\n\nKullanıcı Sorusu:\n{user_input}"
        else:
            user_input = "Kullanıcı özel bir soru sormamıştır"
            prompt += f"\n\nKullanıcı Sorusu:\n{user_input}"

            #Debug amaçlı:
            #print('Promt:',prompt)
        # OpenAI API çağrısı
        try:
            print("API çağrısı yapılıyor...")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sen Türkiye Cumhuriyeti Hukukundan son derece iyi anlayan zeki bir yardımcısın."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.4,  # Yanıtların tutarlılığını artırmak için temperature ayarı
                top_p=0.9  # Yanıtların çeşitliliğini kontrol etmek için top_p ayarı
            )
            print("API yanıtı alındı.")
            print("Yanıt içeriği:", response.choices[0].message.content)

            # Yanıtı bölümlere ayır
            sections = ['DİLEKÇE ÖZETİ:', 'DAVANIN KRONOLOJİSİ:', 'EMSAL YARGITAY KARARLARI:', 'DAVACININ ARGÜMANLARI:', 'GÖZDEN KAÇAN ARGÜMANLAR:', 'POLİÇE KARŞILAŞTIRMASI:','KULLANICI SORUSU:']
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
            
            # print("Result1:", result1)
        
        except Exception as e:
            print("API çağrısı sırasında hata oluştu:", e)
            result1 = {"Hata": f"Hata oluştu: {e}"}
        
        return render_template('index.html', result1=result1, message=message,  email=session["email"])
    
    return render_template('index.html', result1=None, message=None,  email=session["email"])
if __name__ == '__main__':
    app.run(debug=True, port=5000)