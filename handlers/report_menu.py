from core.config import TAB_RKM

class ReportMenuMixin:
    """Bagian 1: Navigasi Menu & Pilihan - Versi WAHA (Sinkronus)"""

    def menu_upload_init(self, chat_id, session):
        self.kirim_pesan(chat_id, "🔄 Sinkronisasi data...")
        self.db_rkm = self.google.ambil_data(TAB_RKM)
        
        # Cari jadwal yang pesertanya user ini & kolom bukti masih kosong
        jadwal_belum = [
            r for r in self.db_rkm 
            if r.get('Peserta') == session['nama'] and not r.get('Bukti Kehadiran')
        ]
        
        if not jadwal_belum:
            self.tampilkan_menu_utama(chat_id, session['nama'], "🎉 **LUAR BIASA!** Semua laporan selesai.")
            return

        session['temp_list'] = jadwal_belum
        session['state'] = 'SELECTING_RAPAT'
        
        pesan = "📝 **PERBARUI STATUS KEHADIRAN:**\nSilakan pilih kegiatan:\n\n"
        for i, j in enumerate(jadwal_belum):
            pesan += f"**{i+1}.** {j['Kegiatan']} ({j['Tanggal']})\n"
        pesan += "\n❌ Ketik 'batal' untuk kembali."
        self.kirim_pesan(chat_id, pesan)

    def proses_pilih_rapat(self, chat_id, text, session):
        if text.lower() == 'batal':
            self.tampilkan_menu_utama(chat_id, session['nama'], "🔙 Kembali.")
            return

        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(session['temp_list']):
                session['selected_rapat'] = session['temp_list'][idx]
                session['state'] = 'SELECTING_STATUS'
                
                # Reset penampung link
                session['collected_links'] = [] 
                
                rapat = session['selected_rapat']
                self.kirim_pesan(chat_id, 
                    f"✅ Kegiatan: **{rapat['Kegiatan']}**\n"
                    "Status kehadiran Anda?\n\n"
                    "1️⃣ **Hadir** (Upload Foto Kegiatan)\n"
                    "2️⃣ **Izin** (Tulis Alasan)\n"
                    "3️⃣ **Sakit** (Upload Surat Dokter)"
                )
            else:
                self.kirim_pesan(chat_id, "Nomor salah.")
        else:
            self.kirim_pesan(chat_id, "Ketik nomor.")

    def proses_pilih_status(self, chat_id, text, session):
        if text == '1': # HADIR
            session['state'] = 'AWAITING_PHOTO'
            session['jenis_laporan'] = "HADIR"
            self.kirim_pesan(chat_id, 
                "📸 **MODE MULTI-UPLOAD AKTIF**\n\n"
                "Silakan kirim FOTO kegiatan.\n"
                "Bisa kirim **banyak foto sekaligus** (Album).\n\n"
                "👉 Jika semua foto sudah terkirim, KETIK: **SELESAI**"
            )
        
        elif text == '2': # IZIN
            session['state'] = 'AWAITING_REASON_IZIN'
            self.kirim_pesan(chat_id, "📝 Silakan ketik **ALASAN** Anda izin:")
        
        elif text == '3': # SAKIT
            session['state'] = 'AWAITING_PHOTO_SAKIT'
            session['jenis_laporan'] = "SAKIT"
            self.kirim_pesan(chat_id, 
                "🏥 **UPLOAD SURAT DOKTER**\n\n"
                "Silakan kirim foto surat.\n"
                "👉 Jika sudah, KETIK: **SELESAI**"
            )
        
        elif text.lower() == 'batal':
            self.tampilkan_menu_utama(chat_id, session['nama'])
        else:
            self.kirim_pesan(chat_id, "Pilih angka 1, 2, atau 3.")