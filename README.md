🤖 WhatsApp ChatBot Kesra (Versi WAHA)

Bot asisten virtual berbasis WhatsApp untuk manajemen kegiatan dan presensi pegawai di lingkungan Kesra.

Dibangun menggunakan Python (Flask) dan terintegrasi dengan WAHA (WhatsApp HTTP API) serta Google Workspace untuk penyimpanan data dan berkas.

🚀 Fitur Utama
👤 Fitur Pegawai

📍 Presensi Kegiatan: Lapor kehadiran rapat atau kegiatan lapangan dengan bukti foto (otomatis upload ke Google Drive).

🖼️ Izin & Sakit: Input alasan izin atau upload foto surat sakit.

📅 Cek Jadwal: Melihat agenda kegiatan mendatang secara real-time.

🔔 Notifikasi Otomatis: Pengingat jadwal rapat/apel setiap pagi.

🛠️ Fitur Admin

📢 Broadcast Pesan: Kirim pengumuman massal ke seluruh nomor pegawai terdaftar.

📝 Manajemen Jadwal: Tambah agenda kegiatan baru langsung melalui chat WhatsApp.

📂 Upload Surat Resmi: Upload surat tugas/undangan (PDF/Gambar) ke folder Drive khusus via chat.

⚙️ Config Notifikasi: Pengaturan waktu untuk pengingat otomatis.

⚙️ Teknologi yang Digunakan

Core Logic: Python, Flask, APScheduler (untuk cron jobs).

WhatsApp Engine: WAHA (WhatsApp HTTP API) via Docker — https://waha.devlike.pro/

Database: Google Sheets (via Google Sheets API).

File Storage: Google Drive (via Google Drive API).

📋 Prasyarat Sistem

Sebelum memulai, pastikan environment Anda memiliki:

Python 3.9+ terinstall: https://www.python.org/downloads/

Docker Desktop (wajib untuk menjalankan server WAHA): https://www.docker.com/products/docker-desktop

Koneksi Internet stabil (diperlukan untuk webhook dan API Google).

📦 Instalasi & Penggunaan

Ikuti langkah-langkah berikut untuk menjalankan bot di komputer lokal (localhost).

1. Siapkan Server WAHA

Jalankan perintah berikut di terminal/CMD untuk menyalakan engine WhatsApp:

docker run -it --rm -p 3000:3000/tcp --name waha devlikeapro/waha

Catatan: Tunggu hingga terminal menampilkan QR Code, lalu scan menggunakan WhatsApp (Linked Devices) yang akan dijadikan nomor bot.

2. Clone Repository

Buka terminal baru, lalu clone project ini:

git clone https://github.com/adikacaesar/Whatsapp-ChatBotKesra.git

cd Whatsapp-ChatBotKesra

3. Setup Environment

Salin file .env.example menjadi .env:

cp .env.example .env
Atau pada Windows (Command Prompt): copy .env.example .env

Buka file .env dan sesuaikan konfigurasinya:

WAHA_BASE_URL=http://localhost:3000

WAHA_API_KEY=isi_jika_waha_menggunakan_auth
SPREADSHEET_NAME=Nama_Google_Sheet_Anda
ID_FOLDER_DRIVE=ID_Folder_Drive_Utama
ID_FOLDER_SURAT=ID_Folder_Surat_Resmi

4. Setup Google Credentials (⚠️ Penting)

File token.json atau credentials.json (akses Google API) tidak disertakan dalam repository ini demi keamanan.

Pastikan Anda memiliki file token.json yang valid (hasil generate dari Google Cloud Console).

Salin/paste file token.json tersebut ke dalam folder root project ini.

5. Install Dependencies

Install library Python yang dibutuhkan:

pip install -r requirements.txt

6. Jalankan Server Bot

Jalankan aplikasi Flask:

python server.py

📝 Catatan Konfigurasi Webhook

Agar bot dapat membalas pesan, Anda perlu menghubungkan WAHA dengan script Python (Flask) Anda.

Pastikan server.py berjalan (biasanya di port 5000).

Buka Dashboard WAHA di browser: http://localhost:3000/dashboard

Masuk ke menu Webhooks.

Set URL Webhook ke salah satu opsi berikut:

http://host.docker.internal:5000/webhook
 (jika WAHA via Docker)

http://localhost:5000/webhook
 (jika non-Docker / akses lokal)

Pastikan event message.any atau message dicentang.

Developed by Adika Caesar Prijatna