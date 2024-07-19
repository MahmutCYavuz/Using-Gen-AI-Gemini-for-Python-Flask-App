# GEN AI Lawyer Simulation

## Açıklama

GEN AI Lawyer Simulation, hukuki argümanları simüle etmek için AI kullanan Flask tabanlı bir web uygulamasıdır. Kullanıcılar hukuki metinleri girebilir ve uygulama bu metinleri işleyerek simüle edilmiş hukuki yanıtlar döndürür. Bu proje, veri saklama için MSSQL kullanır ve pürüzsüz animasyonlarla dinamik bir kullanıcı arayüzü sağlar.

## Özellikler

- **Kullanıcı Girişi ve AI Yanıtı**: Hukuki metin girin ve simüle edilmiş hukuki argümanları alın.
- **Dinamik Yükleme Animasyonu**: AI yanıtını beklerken görsel olarak çekici bir yükleme animasyonu.
- **Veritabanı Entegrasyonu**: Tüm kullanıcı girdileri ve yanıtları MSSQL veritabanında saklanır.

## Kullanılan Teknolojiler

- **Flask**: Python'da hafif bir WSGI web uygulama çerçevesi.
- **MSSQL**: Kullanıcı verilerini saklamak için Microsoft'un ilişkisel veritabanı yönetim sistemi.
- **SQLAlchemy**: Python için SQL araç takımı ve Object-Relational Mapping (ORM) kütüphanesi.
- **HTML/CSS**: Web sayfalarını yapılandırmak ve stil vermek için.
- **JavaScript**: Dinamik animasyonları uygulamak için.

## Başlangıç

### Gereksinimler

- Python 3.x
- MSSQL Server
- pip (Python paket yöneticisi)

### Kurulum

1. **Depoyu Klonlayın:**
   ```bash
   git clone https://github.com/username/GEN-AI-Lawyer-Simulation.git
   cd GEN-AI-Lawyer-Simulation
