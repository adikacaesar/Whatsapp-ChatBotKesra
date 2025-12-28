class AuthMixin:
    """
    Logika untuk Login dan Logout (Versi WhatsApp/WAHA).
    File ini tidak lagi membutuhkan library 'telegram'.
    """

    def proses_login(self, chat_id, text):
        # 1. Cek apakah user mengirim angka (ID Pegawai)
        if text.isdigit():
            id_input = int(text)
            
            # 2. Cari di database pegawai (self.db_pegawai dimuat di server.py nanti)
            found_user = None
            for p in self.db_pegawai:
                # Bandingkan sebagai string agar aman
                if str(p['ID_Pegawai']) == str(id_input):
                    found_user = p
                    break
            
            if found_user:
                # --- LOGIN BERHASIL ---
                
                # Ambil Jabatan (Default kosong jika tidak ada)
                jabatan_user = str(found_user.get('Jabatan 1', '')).strip() 
                
                # Simpan ke memori sesi (RAM)
                self.sessions[chat_id] = {
                    'id': id_input,
                    'nama': found_user['Nama'],
                    'jabatan': jabatan_user, # PENTING: Untuk menu admin
                    'state': 'MAIN_MENU'
                }
                
                # Simpan Chat ID ke Excel (Agar user tidak perlu login ulang nanti)
                # Fungsi ini ada di GoogleSheetsService
                self.google.simpan_chat_id(id_input, chat_id)
                
                # Tampilkan Menu Utama
                # (Fungsi ini nanti kita ambil dari CommonMixin yang akan dimigrasi)
                self.tampilkan_menu_utama(chat_id, found_user['Nama'])
                
            else:
                # Jika ID tidak ditemukan di Excel
                self.kirim_pesan(chat_id, "❌ ID Pegawai tidak ditemukan. Silakan cek kembali.")
        else:
            # Jika input bukan angka
            self.kirim_pesan(
                chat_id,
                "🔒 **Anda belum login.**\n"
                "Silakan ketik **ID Pegawai** Anda (Angka) untuk masuk."
            )

    def proses_logout(self, chat_id):
        if chat_id in self.sessions:
            nama = self.sessions[chat_id]['nama']
            
            # Hapus dari sesi
            del self.sessions[chat_id]
            
            self.kirim_pesan(chat_id, f"👋 Sampai jumpa, {nama}!\nAnda berhasil logout.")