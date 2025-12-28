class CommonMixin:
    """
    Khusus menangani Start & Tampilan Menu Utama (Versi WhatsApp).
    """

    def start(self, chat_id, nama_pengirim):
        # Sapaan awal saat orang baru chat "Hi" atau "Halo"
        self.kirim_pesan(chat_id, f"Halo {nama_pengirim}!\nSilakan ketik **ID Pegawai** untuk Login.")

    def tampilkan_menu_utama(self, chat_id, nama_user, pesan_tambahan=""):
        # --- 1. RESET STATE ---
        # Penting: Saat kembali ke menu utama, kita lupakan proses sebelumnya
        if chat_id in self.sessions:
            self.sessions[chat_id]['state'] = 'MAIN_MENU'
            self.sessions[chat_id]['selected_rapat'] = None
            
            # Bersihkan sisa data temp jika ada
            if 'temp_rapat' in self.sessions[chat_id]:
                del self.sessions[chat_id]['temp_rapat']
        
        # --- 2. CEK JABATAN (ADMIN ATAU BUKAN) ---
        user_session = self.sessions.get(chat_id, {})
        jabatan = user_session.get('jabatan', '').lower()
        
        # Logika Admin: Kabag atau Ketua
        is_admin = 'kabag' in jabatan or 'ketua' in jabatan
        
        # --- 3. SUSUN TEKS MENU ---
        text = (f"{pesan_tambahan}\n\n" if pesan_tambahan else "")
        text += f"✅ Halo **{nama_user}**!\n"
        text += "1️⃣ Cek Jadwal\n"
        text += "2️⃣ Perbarui Status Jadwal (Upload Bukti)\n"
        
        if is_admin:
            text += "3️⃣ Tambah Jadwal (Admin)\n"
            text += "4️⃣ Upload Surat Resmi (Admin)\n"
            text += "5️⃣ Konfigurasi Notifikasi (Admin)"
        
        text += "\n\n(Ketik angka menu yang diinginkan)"
            
        # Kirim pesan via WAHA
        self.kirim_pesan(chat_id, text)