import os
import requests
import time
import logging
import base64
import json 
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

# --- IMPORT MODULE BUATAN SENDIRI ---
from core.config import WAHA_BASE_URL, WAHA_SESSION, WAHA_API_KEY
from core.services import GoogleService
from handlers.main_handler import BotHandler

# --- SETUP LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

print("🚀 Memulai Server Bot Kesra (Fase 1 - Final)...")
google_service = GoogleService()
bot = BotHandler(google_service)

# ==========================================
# 0. MEMORI ANTI-DUPLIKAT
# ==========================================
PROCESSED_MSG_IDS = []

# ==========================================
# 1. FUNGSI KIRIM PESAN
# ==========================================
def kirim_pesan_via_waha(chat_id, text):
    url = f"{WAHA_BASE_URL}/api/sendText"
    headers = {"X-Api-Key": WAHA_API_KEY, "Content-Type": "application/json"}
    payload = {"session": WAHA_SESSION, "chatId": chat_id, "text": text}
    
    try:
        # Delay sedikit biar manusiawi
        time.sleep(0.5) 
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        logger.error(f"❌ Error WAHA: {e}")

# Inject fungsi kirim ke dalam Bot Handler
bot.kirim_pesan = kirim_pesan_via_waha

# ==========================================
# 2. HELPER: DOWNLOAD MEDIA (Versi Lama Kamu - Robust)
# ==========================================
def download_media(source, mime_type):
    try:
        if not os.path.exists("temp_download"): os.makedirs("temp_download")
        
        ext = "bin"
        if "image" in mime_type: ext = "jpg"
        elif "pdf" in mime_type: ext = "pdf"
        elif "png" in mime_type: ext = "png"
        elif "spreadsheet" in mime_type or "excel" in mime_type: ext = "xlsx"
        
        # Nama file unik
        filename = f"temp_download/file_{int(time.time())}_{os.urandom(4).hex()}.{ext}"
        
        # A. URL HTTP
        if source.startswith("http"):
            response = requests.get(source)
            if response.status_code == 200:
                with open(filename, 'wb') as f: f.write(response.content)
                return filename

        # B. BASE64
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
# 3. SCHEDULER (Diaktifkan Kembali)
# ==========================================
def setup_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Jakarta")
    try:
        # Load config dari Google Sheets
        configs = google_service.ambil_config_notif()
        for conf in configs:
            if conf.get('Status') == 'ON':
                jam, menit = str(conf['Waktu']).split(':')
                scheduler.add_job(
                    func=bot.jalankan_notifikasi_pagi,
                    trigger='cron',
                    hour=int(jam),
                    minute=int(menit),
                    args=[{'pesan': conf['Pesan'], 'target': conf['Target']}],
                    id=f"job_{jam}_{menit}"
                )
        scheduler.start()
        print("⏰ Scheduler berjalan.")
    except Exception as e:
        print(f"⚠️ Scheduler Error (Mungkin sheet kosong): {e}")

# Panggil setup scheduler (bisa dimatikan kalau error)
setup_scheduler()

# ==========================================
# 4. ROUTE WEBHOOK (LOGIKA UTAMA)
# ==========================================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data: return "OK", 200

    # Handling Payload yang kadang nested, kadang tidak (Robustness Kodingan Lama)
    payload = data.get('payload', data)

    # 1. Filter Dasar
    if payload.get('fromMe'): return "OK", 200
    
    chat_id = payload.get('from') # Format: 628xxx@c.us
    if not chat_id: return "OK", 200 
    
    # Abaikan Status & Grup (Sementara)
    if 'status@broadcast' in chat_id or '@g.us' in chat_id:
        return "OK", 200

    # --- FILTER ANTI-DUPLIKAT ---
    msg_id = payload.get('id', '')
    if msg_id and msg_id in PROCESSED_MSG_IDS:
        return "OK", 200
    
    if msg_id:
        PROCESSED_MSG_IDS.append(msg_id)
        if len(PROCESSED_MSG_IDS) > 1000: PROCESSED_MSG_IDS.pop(0)

    # -----------------------------------
    sender_name = payload.get('pushName') or payload.get('_data', {}).get('notifyName', 'User')

    # --- DETEKSI FILE ---
    mimetype = payload.get('mimetype') or payload.get('_data', {}).get('mimetype')
    is_file = False
    if mimetype:
        is_file = ('application' in mimetype) or ('image' in mimetype) or ('pdf' in mimetype)

    if is_file:
        print(f"📁 Mendeteksi Lampiran dari {sender_name}...")
        
        media_source = payload.get('mediaUrl') or payload.get('body')
        
        # Fallback cek _data jika body kosong
        if not media_source or (len(str(media_source)) < 50 and not str(media_source).startswith('http')):
             media_source = payload.get('_data', {}).get('body')

        if media_source:
            local_path = download_media(media_source, mimetype)
            if local_path:
                caption = payload.get('caption', '')
                if not caption: caption = payload.get('_data', {}).get('caption', '')
                
                bot.handle_incoming_file(chat_id, local_path, mimetype, caption)
                return "OK", 200
            else:
                print("❌ Gagal simpan file.")
    
    # --- PESAN TEKS BIASA ---
    else:
        body = payload.get('body', '')
        
        # Pastikan body valid
        if body and not str(body).startswith('data:') and len(body) < 2000:
            print(f"📩 {sender_name}: {body}")
            
            # [PENTING] PERUBAHAN UTAMA DI SINI
            # Kita panggil handle_text_message dengan 4 ARGUMEN
            # Argumen ke-4 adalah nomor_pengirim (sama dengan chat_id di WAHA)
            bot.handle_text_message(chat_id, body, sender_name, chat_id)

    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)