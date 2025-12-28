import os
import requests
import time
import logging
import base64
import json 
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

# --- IMPORT MODULE BUATAN SENDIRI ---
from core.config import WAHA_BASE_URL, WAHA_SESSION, WAHA_API_KEY, TAB_PEGAWAI
from core.services import GoogleService
from handlers.main_handler import BotHandler

# --- SETUP LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

print("🚀 Memulai Server Bot Kesra (Stabil)...")
google_service = GoogleService()
bot = BotHandler(google_service)

# ==========================================
# 0. MEMORI ANTI-DUPLIKAT (BARU)
# ==========================================
# Menyimpan 1000 ID pesan terakhir agar tidak diproses 2x
PROCESSED_MSG_IDS = []

# ==========================================
# 1. FUNGSI KIRIM PESAN
# ==========================================
def kirim_pesan_via_waha(chat_id, text):
    url = f"{WAHA_BASE_URL}/api/sendText"
    headers = {"X-Api-Key": WAHA_API_KEY, "Content-Type": "application/json"}
    payload = {"session": WAHA_SESSION, "chatId": chat_id, "text": text}
    try:
        # Sedikit delay untuk menjaga urutan pesan
        time.sleep(0.3)
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        logger.error(f"Error WAHA: {e}")

bot.kirim_pesan = kirim_pesan_via_waha

# ==========================================
# 2. HELPER: DOWNLOAD MEDIA
# ==========================================
def download_media(source, mime_type):
    try:
        if not os.path.exists("temp_download"): os.makedirs("temp_download")
        
        ext = "bin"
        if "image" in mime_type: ext = "jpg"
        elif "pdf" in mime_type: ext = "pdf"
        elif "png" in mime_type: ext = "png"
        
        filename = f"temp_download/file_{int(time.time())}_{os.urandom(4).hex()}.{ext}"
        
        # --- KASUS A: URL HTTP ---
        if source.startswith("http"):
            response = requests.get(source)
            if response.status_code == 200:
                with open(filename, 'wb') as f: f.write(response.content)
                return filename

        # --- KASUS B: BASE64 ---
        source = source.strip()
        if "," in source and "base64" in source[:50]:
            _, encoded = source.split(",", 1)
        else:
            encoded = source

        try:
            file_data = base64.b64decode(encoded)
            with open(filename, 'wb') as f: f.write(file_data)
            return filename
        except:
            return None

    except Exception as e:
        logger.error(f"❌ Error Simpan Media: {e}")
        return None

# ==========================================
# 3. SCHEDULER
# ==========================================
scheduler = BackgroundScheduler()
def setup_scheduler():
    scheduler.remove_all_jobs()
    # (Di sini Anda bisa mengaktifkan lagi logika scheduler jika file excel sudah siap)
    # Untuk saat ini kita pass dulu agar fokus ke chat
    pass 
    
bot.setup_scheduler = setup_scheduler
scheduler.start()

# ==========================================
# 4. ROUTE WEBHOOK (LOGIKA UTAMA)
# ==========================================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    payload = data.get('payload', data)

    # 1. Filter Dasar
    if payload.get('fromMe'): return "OK", 200
    
    chat_id = payload.get('from')
    if not chat_id: return "OK", 200 
    
    # --- [BARU] FILTER ANTI-DUPLIKAT ---
    msg_id = payload.get('id')
    # ID di WAHA biasanya formatnya: false_NomorHP@c.us_IDUNIK
    if msg_id and msg_id in PROCESSED_MSG_IDS:
        print(f"♻️ Skip pesan duplikat (ID: {msg_id[-8:]}...)")
        return "OK", 200
    
    # Jika pesan baru, simpan ID-nya
    if msg_id:
        PROCESSED_MSG_IDS.append(msg_id)
        # Jaga agar memori tidak penuh, buang yang lama jika > 1000
        if len(PROCESSED_MSG_IDS) > 1000:
            PROCESSED_MSG_IDS.pop(0)

    # -----------------------------------

    sender_name = payload.get('_data', {}).get('notifyName', 'User')

    # --- DETEKSI FILE ---
    has_media = payload.get('hasMedia', False)
    mimetype = payload.get('mimetype', '')
    msg_type = payload.get('type', '')
    
    is_file = has_media or (msg_type in ['image', 'document']) or ('image' in mimetype)

    if is_file:
        print(f"📁 Mendeteksi Lampiran dari {sender_name}...")
        
        media_source = payload.get('mediaUrl') or payload.get('url')
        
        # Cek Body & _data Body
        body = payload.get('body', '')
        if len(body) > 200: media_source = body
        
        if not media_source:
             hidden_body = payload.get('_data', {}).get('body', '')
             if len(hidden_body) > 200: media_source = hidden_body

        if media_source:
            local_path = download_media(media_source, mimetype)
            if local_path:
                caption = payload.get('caption', '')
                if not caption: caption = payload.get('_data', {}).get('caption', '')
                if len(caption) > 200: caption = ""

                bot.handle_incoming_file(chat_id, local_path, mimetype, caption)
                return "OK", 200
            else:
                print("❌ Gagal simpan file.")
        else:
            print("⚠️ File terdeteksi tapi kosong.")
    
    # --- PESAN TEKS BIASA ---
    else:
        body = payload.get('body', '')
        # Pastikan body bukan sampah Base64
        if body and not body.startswith('data:') and len(body) < 1000:
            print(f"📩 {sender_name}: {body}")
            bot.proses_pesan(chat_id, body, sender_name)

    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)