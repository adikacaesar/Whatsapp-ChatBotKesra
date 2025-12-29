# [File: handlers/auth.py]
from core.config import TAB_PEGAWAI

class AuthMixin:
    """
    Logika Login & Registrasi (Versi Strict Mode)
    User wajib mendaftarkan nomor HP sebelum bisa mengakses Menu Utama.
    """

    def proses_login(self, chat_id, text, nomor_pengirim):
        """
        Flow Login Strict:
        1. Cek ID di Database Master.
        2. Kalau Valid -> Cek Status Registrasi Kontak.
        3. Belum Daftar? -> Ubah State jadi AWAITING_PHONE_REGISTRATION -> STOP.
        4. Sudah Daftar? -> Langsung Masuk Menu Utama.
        """
        id_input = text.strip()
        
        # --- 1. VALIDASI DATA PEGAWAI (Master Data) ---
        found_user = None
        for p in self.db_pegawai:
            # Bandingkan sebagai string untuk keamanan
            if str(p.get('ID_Pegawai', '')).strip() == id_input:
                found_user = p
                break
        
        if not found_user:
            self.kirim_pesan(chat_id, f"❌ ID **{id_input}** tidak ditemukan di database pegawai.")
            return

        # --- 2. SIAPKAN SESI ---
        nama_user = found_user.get('Nama', 'Pegawai')
        jabatan = str(found_user.get('Jabatan 1', '')).strip()

        # Simpan sesi awal (State default sementara)
        self.sessions[chat_id] = {
            'id': id_input,
            'nama': nama_user,
            'jabatan': jabatan,
            'nomor_wa_asli': nomor_pengirim # Cadangan info pengirim asli
        }

        # --- 3. CEK STATUS REGISTRASI ---
        # Apakah ID ini sudah ada di sheet 'kontak_pegawai'?
        sudah_reg = self.google.cek_kontak_terdaftar(id_input)
        
        if not sudah_reg:
            # --- SKENARIO A: BELUM DAFTAR (BLOCKING) ---
            # Paksa user masuk ke mode input nomor
            self.sessions[chat_id]['state'] = 'AWAITING_PHONE_REGISTRATION'
            
            pesan = (
                f"👋 Halo **{nama_user}** ({jabatan})\n\n"
                "⚠️ **AKSES DITAHAN**\n"
                "ID Anda belum terdaftar untuk notifikasi otomatis.\n\n"
                "👉 **Silakan ketik Nomor WhatsApp Anda sekarang.**\n"
                "*(Contoh: 08123456789)*"
            )
            self.kirim_pesan(chat_id, pesan)
            return  # <--- BERHENTI DI SINI (JANGAN TAMPILKAN MENU)

        else:
            # --- SKENARIO B: SUDAH DAFTAR (LANGSUNG MENU) ---
            self.sessions[chat_id]['state'] = 'MAIN_MENU'
            
            # Langsung tampilkan menu tanpa basa-basi
            self.tampilkan_menu_utama(chat_id, nama_user, pesan_tambahan="")

    def proses_input_nomor_wa(self, chat_id, text):
        """
        Menangani input manual nomor WA (Contoh: 0812xxx).
        Dipanggil saat state == 'AWAITING_PHONE_REGISTRATION'.
        """
        session = self.sessions.get(chat_id)
        if not session:
            self.kirim_pesan(chat_id, "⚠️ Sesi habis. Silakan Login ulang.")
            return

        # Bersihkan input (hapus spasi atau strip)
        raw_nomor = text.strip().replace('-', '').replace(' ', '')
        
        # Validasi sederhana: harus angka
        if not raw_nomor.isdigit():
            self.kirim_pesan(chat_id, "❌ Format salah. Harap masukkan hanya angka (Contoh: 0812xxx).")
            return

        # --- FORMATTING NOMOR (08 -> 628... @c.us) ---
        nomor_final = raw_nomor
        if nomor_final.startswith('0'):
            nomor_final = '62' + nomor_final[1:]
        elif nomor_final.startswith('8'):
            nomor_final = '62' + nomor_final
        
        # Tambahkan suffix WAHA jika belum ada
        if '@c.us' not in nomor_final:
            nomor_final += '@c.us'

        # Simpan ke Excel
        self.kirim_pesan(chat_id, "⏳ Menyimpan nomor...")
        id_pegawai = session['id']
        
        sukses = self.google.simpan_kontak_baru(id_pegawai, nomor_final)

        if sukses:
            # Update State jadi Main Menu (Pintu Terbuka)
            self.sessions[chat_id]['state'] = 'MAIN_MENU'
            self.kirim_pesan(chat_id, "✅ **Terima Kasih!** Nomor berhasil disimpan.")
            
            # Langsung masuk menu utama
            self.tampilkan_menu_utama(chat_id, session['nama'])
        else:
            self.kirim_pesan(chat_id, "❌ Gagal menyimpan ke database. Hubungi Admin.")

    def proses_logout(self, chat_id):
        """Menghapus sesi user"""
        if chat_id in self.sessions:
            nama = self.sessions[chat_id]['nama']
            del self.sessions[chat_id]
            self.kirim_pesan(chat_id, f"👋 Sampai jumpa, {nama}!\nAnda berhasil logout.")
        else:
            self.kirim_pesan(chat_id, "Anda belum login.")