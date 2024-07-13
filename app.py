from flask import Flask, render_template, request, redirect, url_for, session
import markdown
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Çevresel değişkenleri yükle
load_dotenv()

genai.configure(api_key=os.getenv('API_KEY'))

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # Gizli anahtar .env dosyasından alınır

@app.route("/", methods=["GET", "POST"])
def index():
    result1 = ""
    
    if request.method == 'POST':
        input_text = request.form['input_text']
        model = genai.GenerativeModel('gemini-pro')
        try:
            responseFirst = model.generate_content(
                # 'aşağıdaki davada davacı avukatı gibi davran ve savun. Bu dava metnini aşağıda yazacağım. Hukuki Dava metnine benzemeyen promptlara "Sadece hukuki davalara cevap veriyorum!" cevabını ilet. Dava Metni:' + input_text)
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
    app.run(debug=True, port=5001)
