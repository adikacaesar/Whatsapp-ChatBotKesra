import os
from dotenv import load_dotenv

# Load file .env
load_dotenv()

# ==========================================
# KONFIGURASI BOT (WHATSAPP - WAHA)
# ==========================================

# --- 1. KONEKSI WHATSAPP (WAHA) ---
WAHA_BASE_URL = os.getenv("WAHA_BASE_URL", "http://localhost:3000")
WAHA_SESSION = os.getenv("WAHA_SESSION", "default")
WAHA_API_KEY = os.getenv("WAHA_API_KEY", "")

# --- 2. RAHASIA SPREADSHEET ---
NAMA_SPREADSHEET = os.getenv("SPREADSHEET_NAME", "DB_Kesra")
FILE_TOKEN = "token.json"

# --- 3. KONFIGURASI FOLDER GOOGLE DRIVE ---
ID_FOLDER_DRIVE = os.getenv("ID_FOLDER_DRIVE", "")
ID_FOLDER_SURAT = os.getenv("ID_FOLDER_SURAT", "")

# --- 4. NAMA TAB SHEET ---
TAB_PEGAWAI = "ID_Pegawai"
TAB_RKM = "RKM"
TAB_CONFIG_NOTIF = "Config_Notif"
TAB_KONTAK = "Kontak_Pegawai"