from core.config import TAB_RKM

class AdminWizardMixin:
    """Bagian 3: Interaksi Chat Admin (Wizard & Menu Pilihan) - Versi WAHA"""

    # ==========================================
    # FITUR 1: TAMBAH JADWAL BARU (WIZARD)
    # ==========================================

    def admin_menu_init(self, chat_id, session):
        jabatan = session.get('jabatan', '').lower()
        if 'kabag' not in jabatan and 'ketua' not in jabatan and 'kepala' not in jabatan:
            self.kirim_pesan(chat_id, "⛔ Akses Ditolak. Menu ini khusus Pimpinan.")
            return

        session['temp_rapat'] = {'peserta_list': []}
        session['state'] = 'ADMIN_INPUT_TANGGAL'
        self.kirim_pesan(chat_id, "📅 **TAMBAH JADWAL BARU**\n1️⃣ **Masukkan TANGGAL Rapat:**\n(Contoh: 25 Januari 2026)")

    def admin_terima_tanggal(self, chat_id, text, session):
        session['temp_rapat']['tanggal'] = text
        session['state'] = 'ADMIN_INPUT_JAM'
        self.kirim_pesan(chat_id, "2️⃣ **Masukkan JAM Rapat:**\n(Contoh: 09:00 WIB)")

    def admin_terima_jam(self, chat_id, text, session):
        session['temp_rapat']['jam'] = text
        session['state'] = 'ADMIN_INPUT_ID'
        self.kirim_pesan(chat_id, "3️⃣ **Buat ID Rapat:**\n(Contoh: RPT-001)")

    def admin_terima_id(self, chat_id, text, session):
        session['temp_rapat']['id'] = text
        session['state'] = 'ADMIN_INPUT_NAMA_KEGIATAN'
        self.kirim_pesan(chat_id, "4️⃣ **Masukkan NAMA KEGIATAN:**\n(Contoh: Rapat Koordinasi)")

    def admin_terima_nama(self, chat_id, text, session):
        session['temp_rapat']['kegiatan'] = text
        session['state'] = 'ADMIN_INPUT_LOKASI'
        self.kirim_pesan(chat_id, "5️⃣ **Masukkan LOKASI:**\n(Contoh: Aula Barat)")

    def admin_terima_lokasi(self, chat_id, text, session):
        session['temp_rapat']['lokasi'] = text
        session['state'] = 'ADMIN_INPUT_PESERTA'
        jml = len(session['temp_rapat']['peserta_list']) + 1
        self.kirim_pesan(chat_id, f"📍 Lokasi disimpan.\n6️⃣ **Masukkan PESERTA ke-{jml}:**\n(Nama Orang / Jabatan / Grup)\n👉 Ketik **SELESAI** jika sudah.")

    def admin_terima_peserta(self, chat_id, text, session):
        if text.upper() == 'SELESAI':
            # Pindah ke AdminActionMixin untuk simpan
            self.admin_finalisasi_simpan(chat_id, session)
            return
        session['temp_rapat']['temp_nama_input'] = text
        session['state'] = 'ADMIN_INPUT_STATUS_PESERTA'
        self.kirim_pesan(chat_id, f"👤 Peserta: **{text}**\n❓ **Status/Peran?** (Peserta, Tamu, dll)")

    def admin_terima_status(self, chat_id, text, session):
        nama_input = session['temp_rapat']['temp_nama_input']
        session['temp_rapat']['peserta_list'].append({'target': nama_input, 'status': text})
        
        session['state'] = 'ADMIN_INPUT_PESERTA'
        jml = len(session['temp_rapat']['peserta_list']) + 1
        self.kirim_pesan(chat_id, f"✅ **{nama_input}** ditambahkan.\n👉 **Masukkan PESERTA ke-{jml}:**\n(Atau ketik **SELESAI**)")


    # ==========================================
    # FITUR 2: UPLOAD SURAT RESMI (PILIH EVENT)
    # ==========================================

    def admin_upload_surat_init(self, chat_id, session):
        # 1. Validasi Admin
        jabatan = session.get('jabatan', '').lower()
        if 'kabag' not in jabatan and 'ketua' not in jabatan and 'kepala' not in jabatan:
            self.kirim_pesan(chat_id, "⛔ Akses Ditolak.")
            return

        self.kirim_pesan(chat_id, "🔄 Mengambil daftar kegiatan...")
        self.db_rkm = self.google.ambil_data(TAB_RKM)
        
        # 2. Ambil Daftar Kegiatan UNIK
        kegiatan_unik = {}
        for row in self.db_rkm:
            id_keg = str(row.get('ID Kegiatan', ''))
            nama_keg = row.get('Kegiatan', '')
            tgl = row.get('Tanggal', '')
            
            # Hanya ambil yang punya ID dan belum masuk list
            if id_keg and id_keg not in kegiatan_unik:
                kegiatan_unik[id_keg] = f"{nama_keg} ({tgl})"

        if not kegiatan_unik:
            self.kirim_pesan(chat_id, "⚠️ Belum ada kegiatan di RKM.")
            return

        # 3. Tampilkan Menu Pilihan
        session['temp_surat_list'] = [] 
        pesan = "📂 **PILIH KEGIATAN UNTUK UPLOAD SURAT:**\n\n"
        
        nomor = 1
        for id_keg, info in kegiatan_unik.items():
            pesan += f"**{nomor}.** [{id_keg}] {info}\n"
            session['temp_surat_list'].append(id_keg) # Simpan ID ke list sementara
            nomor += 1
            
        pesan += "\nKetik **Nomor** kegiatan yang dimaksud.\nAtau ketik 'batal'."
        
        session['state'] = 'ADMIN_SELECT_EVENT_FOR_LETTER'
        self.kirim_pesan(chat_id, pesan)

    def admin_terima_pilihan_surat(self, chat_id, text, session):
        if not text.isdigit():
            self.kirim_pesan(chat_id, "⚠️ Ketik nomor urutnya saja.")
            return

        idx = int(text) - 1
        daftar_id = session.get('temp_surat_list', [])
        
        if 0 <= idx < len(daftar_id):
            id_terpilih = daftar_id[idx]
            session['selected_id_surat'] = id_terpilih
            
            # Ganti status agar siap menerima file
            session['state'] = 'ADMIN_UPLOAD_LETTER_FILE'
            
            self.kirim_pesan(chat_id,
                f"✅ Kegiatan Terpilih: **{id_terpilih}**\n\n"
                "📤 **Silakan Kirim File Surat Resmi.**\n"
                "Bisa berupa:\n"
                "- Foto (JPG/PNG)\n"
                "- File Dokumen (PDF)\n\n"
                "Silakan upload sekarang."
            )
        else:
            self.kirim_pesan(chat_id, "❌ Nomor tidak ada di daftar.")