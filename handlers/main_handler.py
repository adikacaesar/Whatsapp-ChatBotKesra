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

    # --- FUNGSI DUMMY (Akan ditimpa oleh server.py) ---
    def kirim_pesan(self, chat_id, text):
        """Fungsi ini akan di-override oleh server.py"""
        print(f"[MOCK SEND] Ke {chat_id}: {text}")

    # --- ROUTER PESAN TEKS ---
    def proses_pesan(self, chat_id, text, nama_pengirim):
        text = text.strip() if text else ""

        # 1. Cek Login
        if chat_id not in self.sessions:
            if text.lower() in ['hi', 'halo', 'p', 'start', 'menu']:
                self.start(chat_id, nama_pengirim)
            else:
                self.proses_login(chat_id, text)
            return

        # 2. Ambil Status User
        session = self.sessions[chat_id]
        state = session['state']
        
        # --- GLOBAL CANCEL ---
        if text.lower() == 'batal' and state != 'MAIN_MENU':
             self.tampilkan_menu_utama(chat_id, session['nama'], "❌ Aksi dibatalkan.")
             return

        # --- GLOBAL LOGOUT ---
        if text.lower() == 'logout':
            self.proses_logout(chat_id)
            return

        # --- ROUTING BERDASARKAN STATE ---
        
        # A. MENU UTAMA
        if state == 'MAIN_MENU':
            if text == '1':
                session['state'] = 'SUBMENU_JADWAL'
                self.tampilkan_menu_jadwal(chat_id)
            elif text == '2':
                self.menu_upload_init(chat_id, session)
            elif text == '3':
                self.admin_menu_init(chat_id, session)
            elif text == '4':
                self.admin_upload_surat_init(chat_id, session)
            elif text == '5':
                self.menu_config_notif(chat_id, session)
            else:
                self.kirim_pesan(chat_id, "⚠️ Ketik angka menu yang tersedia (1-5).")

        # B. SUBMENU JADWAL
        elif state == 'SUBMENU_JADWAL':
            self.menu_jadwal_handler(chat_id, text, session)
        elif state == 'SEARCHING_DATE':
            self.cari_tanggal_manual(chat_id, text, session)

        # C. ALUR LAPORAN
        elif state == 'SELECTING_RAPAT':
            self.proses_pilih_rapat(chat_id, text, session)
        elif state == 'SELECTING_STATUS':
            self.proses_pilih_status(chat_id, text, session)
        elif state == 'AWAITING_REASON_IZIN':
            self.proses_terima_alasan_izin(chat_id, text, session)
        elif state == 'AWAITING_PHOTO' or state == 'AWAITING_PHOTO_SAKIT':
            if text.upper() == 'SELESAI':
                self.proses_selesai_upload_foto(chat_id, session)
            else:
                self.kirim_pesan(chat_id, "⚠️ Sedang mode terima foto. Kirim foto atau ketik **SELESAI**.")
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

    # --- ROUTER FILE (FOTO/DOKUMEN) ---
    def handle_incoming_file(self, chat_id, file_path, mime_type, caption):
        """
        Dipanggil ketika user mengirim file (Foto/PDF).
        """
        if chat_id in self.sessions:
            state = self.sessions[chat_id]['state']
            
            # 1. Alur Laporan User (Foto Absen / Sakit)
            if state in ['AWAITING_PHOTO', 'AWAITING_PHOTO_SAKIT']:
                # Panggil report_action.py
                self.proses_terima_foto(chat_id, file_path, mime_type, caption, self.sessions[chat_id])
            
            # 2. Alur Admin Upload Surat (Bisa PDF/Foto)
            elif state == 'ADMIN_UPLOAD_LETTER_FILE':
                # Panggil admin_action.py
                self.admin_proses_file_surat(chat_id, file_path, mime_type, self.sessions[chat_id])
            
            else:
                self.kirim_pesan(chat_id, "⚠️ Maaf, saya sedang tidak meminta file/foto saat ini.")
        else:
            self.kirim_pesan(chat_id, "⚠️ Silakan Login dulu dengan ID Pegawai.")