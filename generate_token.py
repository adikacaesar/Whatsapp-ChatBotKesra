import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# --- UPDATE: SCOPE HANYA 2 INI SAJA (HAPUS FEEDS) ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def main():
    creds = None
    
    # 1. Hapus token lama agar bersih
    if os.path.exists('token.json'):
        try:
            os.remove('token.json')
            print("🗑️ Token lama dihapus untuk pembaruan izin.")
        except:
            pass

    print("🔄 Membuka Browser untuk Login Google...")
    
    # 2. Cek apakah credentials.json ada
    if not os.path.exists('credentials.json'):
        print("❌ Error: File 'credentials.json' tidak ditemukan!")
        print("👉 Harap download dari Google Cloud Console > Credentials > Download JSON.")
        return

    # 3. Proses Login
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    
    # Menjalankan server lokal untuk auth
    creds = flow.run_local_server(port=0)

    # 4. Simpan Token Baru
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    print("\n✅ SUKSES! File 'token.json' baru telah dibuat.")
    print("🚀 Sekarang Anda bisa menjalankan 'python server.py'.")

if __name__ == '__main__':
    main()