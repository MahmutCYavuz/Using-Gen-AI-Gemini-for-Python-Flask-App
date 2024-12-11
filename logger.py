import pyodbc
from datetime import datetime


conn = pyodbc.connect(    
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=MOZDEMIRNB\OZDEMIRSQLSERVER;'
    'DATABASE=LOGDATABASE;'
    'Trusted_Connection=yes;')

cursor = conn.cursor()

def log_user_activity(email, file_path=None, masked_data=None):
    
    try:
        query = """
        INSERT INTO UserLogs (Email, LoginTime, FilePath, MaskedData)
        VALUES (?, ?, ?, ?)
        """
        current_time = datetime.now()  # Mevcut zamanı al
        cursor.execute(query, (email, current_time, file_path, masked_data))
        conn.commit()
        print(f"Log başarıyla eklendi: {email}")
    except Exception as e:
        print(f"Log ekleme hatası: {e}")


def log_user_login(email):
    try:
        query = """
        INSERT INTO UserLogs (Email, LoginTime, FilePath, MaskedData)
        VALUES (?, ?, NULL, NULL)
        """
        current_time = datetime.now()  # Mevcut zamanı al
        cursor.execute(query, (email, current_time))
        conn.commit()
        print(f"Kullanıcı girişi loglandı: {email}")
    except Exception as e:
        print(f"Kullanıcı giriş loglama hatası: {e}")
