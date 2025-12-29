# --- Import Config ---
from core.config import TAB_PEGAWAI, TAB_RKM

# --- Import Semua Logika (Mixin) ---
from .auth import AuthMixin
from .schedule import ScheduleMixin
from .notification import NotificationMixin
from .common import CommonMixin

# Pecahan Report (User)
from .report_menu import ReportMenuMixin
from .report_action import ReportActionMixin

# Pecahan Admin (Manajemen)
from .admin_wizard import AdminWizardMixin
from .admin_action import AdminActionMixin
from .admin_config import AdminConfigMixin 

class BotHandler(
    AuthMixin, 
    ScheduleMixin, 
    NotificationMixin, 
    CommonMixin, 
    ReportMenuMixin,
    ReportActionMixin,
    AdminWizardMixin,
    AdminActionMixin,
    AdminConfigMixin 
):
    """
    Router Utama Bot Kesra (Versi WAHA).
    Menerima input chat_id & text, lalu mengarahkannya ke fungsi yang tepat.
    """
    
    def __init__(self, google_service):
        self.google = google_service
        self.sessions = {} 
        
        print("🔄 Memuat Database...")
        self.db_pegawai = self.google.ambil_data(TAB_PEGAWAI)
        self.db_rkm = self.google.ambil_data(TAB_RKM)
        print("✅ Database Siap!")

    # --- FUNGSI UTAMA (ROUTER TEKS) ---
    def handle_text_message(self, chat_id, text, sender_name, nomor_pengirim):
        """
        Logic Utama: Menentukan arah pesan user.
        Menggabungkan Logic Login Strict + Routing Menu Lama.
        """
        text = text.strip()
        
        # Ambil sesi user (jika ada)
        session = self.sessions.get(chat_id)
        state = session.get('state') if session else None

        # ==================================================
        # 1. GLOBAL COMMANDS (Bisa diakses kapan saja)
        # ==================================================
        if text.lower() == "batal":
             if session:
                 self.tampilkan_menu_utama(chat_id, session['nama'], "❌ Aksi dibatalkan.")
             else:
                 self.kirim_pesan(chat_id, "✅ Siap. Silakan Login dengan ID Pegawai.")
             return

        if text.upper() == "LOGOUT":
            self.proses_logout(chat_id)
            return

        # ==================================================
        # 2. LOGIC LOGIN (JIKA BELUM ADA SESI)
        # ==================================================
        if not session:
            # Jika user mengirim ANGKA -> Asumsi mencoba Login ID
            if text.isdigit():
                # Memanggil auth.py (Strict Mode)
                self.proses_login(chat_id, text, nomor_pengirim)
            else:
                self.kirim_pesan(chat_id, "🔒 **Bot Terkunci.**\nSilakan ketik **ID Pegawai** Anda (Angka NIP/Absen) untuk masuk.")
            return

        # ==================================================
        # 3. LOGIC INPUT NOMOR WA (Strict Mode)
        # ==================================================
        # Jika user tertahan di fase registrasi, semua input teks dianggap nomor HP
        if state == 'AWAITING_PHONE_REGISTRATION':
            self.proses_input_nomor_wa(chat_id, text)
            return

        # ==================================================
        # 4. ROUTING BERDASARKAN STATE (MENU)
        # ==================================================
        
        # A. MENU UTAMA
        if state == 'MAIN_MENU':
            if text == '1':
                session['state'] = 'SUBMENU_JADWAL'
                self.tampilkan_menu_jadwal(chat_id)
            elif text == '2':
                self.menu_upload_init(chat_id, session)
            elif text == '3':
                # Cek akses admin
                jabatan = session.get('jabatan', '').lower()
                if 'kabag' in jabatan or 'ketua' in jabatan or 'kepala' in jabatan:
                    self.admin_menu_init(chat_id, session)
                else:
                     self.kirim_pesan(chat_id, "⛔ Menu ini khusus Admin/Pimpinan.")
            elif text == '4':
                # Cek akses admin
                jabatan = session.get('jabatan', '').lower()
                if 'kabag' in jabatan or 'ketua' in jabatan or 'kepala' in jabatan:
                    self.admin_upload_surat_init(chat_id, session)
                else:
                     self.kirim_pesan(chat_id, "⛔ Menu ini khusus Admin/Pimpinan.")
            elif text == '5':
                 # Cek akses admin
                jabatan = session.get('jabatan', '').lower()
                if 'kabag' in jabatan or 'ketua' in jabatan or 'kepala' in jabatan:
                    self.menu_config_notif(chat_id, session)
                else:
                     self.kirim_pesan(chat_id, "⛔ Menu ini khusus Admin/Pimpinan.")
            else:
                self.tampilkan_menu_utama(chat_id, session['nama'], "⚠️ Pilih menu 1 - 5.")
        
        # B. SUBMENU JADWAL
        elif state == 'SUBMENU_JADWAL':
            self.menu_jadwal_handler(chat_id, text, session)
        elif state == 'SEARCHING_DATE':
            self.cari_tanggal_manual(chat_id, text, session)
        
        # C. ALUR LAPORAN (User)
        elif state == 'SELECTING_RAPAT':
            self.proses_pilih_rapat(chat_id, text, session)
        elif state == 'SELECTING_STATUS':
            self.proses_pilih_status(chat_id, text, session)
        elif state == 'AWAITING_REASON_IZIN':
            self.proses_terima_alasan_izin(chat_id, text, session)
        elif state == 'AWAITING_PHOTO' or state == 'AWAITING_PHOTO_SAKIT':
            if text.upper() == 'SELESAI':
                if hasattr(self, 'proses_selesai_upload_foto'):
                    self.proses_selesai_upload_foto(chat_id, session)
                else:
                    self.proses_selesai_upload(chat_id, session)
            else:
                self.kirim_pesan(chat_id, "📸 Silakan kirim FOTO. Ketik **SELESAI** jika sudah.")
        elif state == 'AWAITING_FINAL_CAPTION':
            self.proses_simpan_akhir(chat_id, text, session)
        
        # D. ALUR ADMIN: TAMBAH JADWAL
        elif state == 'ADMIN_INPUT_TANGGAL':
            self.admin_terima_tanggal(chat_id, text, session)
        elif state == 'ADMIN_INPUT_JAM':
            self.admin_terima_jam(chat_id, text, session)
        elif state == 'ADMIN_INPUT_ID':
            self.admin_terima_id(chat_id, text, session)
        elif state == 'ADMIN_INPUT_NAMA_KEGIATAN':
            self.admin_terima_nama(chat_id, text, session)
        elif state == 'ADMIN_INPUT_LOKASI':
            self.admin_terima_lokasi(chat_id, text, session)
        elif state == 'ADMIN_INPUT_PESERTA':
            self.admin_terima_peserta(chat_id, text, session)
        elif state == 'ADMIN_INPUT_STATUS_PESERTA':
            self.admin_terima_status(chat_id, text, session)

        # E. ALUR ADMIN: UPLOAD SURAT
        elif state == 'ADMIN_SELECT_EVENT_FOR_LETTER':
            self.admin_terima_pilihan_surat(chat_id, text, session)
        elif state == 'ADMIN_UPLOAD_LETTER_FILE':
             self.kirim_pesan(chat_id, "📂 Silakan kirim file (PDF/Gambar) sekarang.")

        # F. ALUR ADMIN: CONFIG NOTIFIKASI
        elif state == 'CONFIG_MENU':
            self.config_process_menu(chat_id, text, session)
        elif state == 'CONFIG_ADD_TIME':
            self.config_add_time(chat_id, text, session)
        elif state == 'CONFIG_SELECT_TARGET':
            self.config_select_target(chat_id, text, session)
        elif state == 'CONFIG_ADD_MSG':
            self.config_add_msg(chat_id, text, session)
        elif state == 'CONFIG_CONFIRM_TEST':
            self.config_confirm_test(chat_id, text, session)
        elif state == 'CONFIG_DELETE':
            self.config_delete(chat_id, text, session)
        elif state == 'BROADCAST_INPUT':
            self.broadcast_process(chat_id, text, session)
            
        else:
            self.tampilkan_menu_utama(chat_id, session['nama'], "⚠️ Perintah tidak dikenali.")

    # --- ROUTER FILE (FOTO/DOKUMEN) ---
    def handle_incoming_file(self, chat_id, file_path, mime_type, caption):
        """
        Dipanggil ketika user mengirim file (Foto/PDF).
        """
        if chat_id in self.sessions:
            state = self.sessions[chat_id]['state']
            
            # 1. Alur Laporan User (Foto Absen / Sakit)
            if state in ['AWAITING_PHOTO', 'AWAITING_PHOTO_SAKIT']:
                self.proses_terima_foto(chat_id, file_path, mime_type, caption, self.sessions[chat_id])
            
            # 2. Alur Admin Upload Surat (Bisa PDF/Foto)
            elif state == 'ADMIN_UPLOAD_LETTER_FILE':
                self.admin_proses_file_surat(chat_id, file_path, mime_type, self.sessions[chat_id])
            
            else:
                self.kirim_pesan(chat_id, "⚠️ Saya tidak sedang menunggu file. Pilih menu dulu.")
        else:
            self.kirim_pesan(chat_id, "🔒 Silakan Login dulu dengan ID Pegawai.")