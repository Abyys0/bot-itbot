from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot iBot está online! 🤖"

@app.route('/health')
def health():
    return {"status": "online", "bot": "iBot"}

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """Inicia servidor web em thread separada para manter bot ativo"""
    t = Thread(target=run)
    t.daemon = True
    t.start()
