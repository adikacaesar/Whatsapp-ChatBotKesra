import time
from core.config import TAB_KONTAK, TAB_PEGAWAI

class AdminConfigMixin:
    """
    Menu 5: Konfigurasi Notifikasi & Broadcast (Versi Hybrid WAHA)
    Fitur: Wizard Config, Target Selection, Test Mode, & Broadcast Fixed.
    """

    def menu_config_notif(self, chat_id, session):
        """Menampilkan Dashboard Konfigurasi"""
        items = self.google.ambil_config_notif()
        
        pesan = "⚙️ **PENGATURAN NOTIFIKASI & BROADCAST**\n\n"
        pesan += "Daftar Jadwal Otomatis:\n"
        
        if not items:
            pesan += "_(Belum ada jadwal)_\n"
        else:
            for i in items:
                # Format: [Waktu] [Target] : Pesan
                waktu = i.get('Waktu', '??:??')
                target = i.get('Target', 'ALL')
                isi = i.get('Pesan', '-')
                pesan += f"🟢 **{waktu}** [{target}] : {isi}\n"
        
        pesan += "\n👇 **PILIHAN MENU:**\n"
        pesan += "1️⃣ Tambah Jadwal Baru\n"
        pesan += "2️⃣ Hapus Jadwal\n"
        pesan += "3️⃣ Kembali ke Menu Utama\n"
        pesan += "4️⃣ **BROADCAST PESAN (DADAKAN)**"

        session['state'] = 'CONFIG_MENU'
        self.kirim_pesan(chat_id, pesan)

    def config_process_menu(self, chat_id, text, session):
        """Router Pilihan Menu"""
        if text == '1': # Tambah
            session['state'] = 'CONFIG_ADD_TIME'
            self.kirim_pesan(chat_id, "⏰ **Masukkan JAM Notifikasi:**\n(Format HH:MM, contoh: 07:00)")
            
        elif text == '2': # Hapus
            session['state'] = 'CONFIG_DELETE'
            self.kirim_pesan(chat_id, "🗑️ **Ketik JAM yang mau dihapus:**\n(Persis seperti di list, contoh: 07:00)")
            
        elif text == '3': # Kembali
            self.tampilkan_menu_utama(chat_id, session['nama'])

        elif text == '4': # Broadcast
            session['state'] = 'BROADCAST_INPUT'
            self.kirim_pesan(chat_id, 
                "📢 **MODE BROADCAST MANUAL**\n\n"
                "Ketik pesan yang ingin Anda kirimkan ke **SEMUA PEGAWAI**.\n"
                "_(Ketik 'batal' untuk kembali)_"
            )
        else:
            self.kirim_pesan(chat_id, "⚠️ Pilih angka 1-4.")

    # ==========================================
    # A. WIZARD TAMBAH JADWAL (FITUR LAMA YG BAGUS)
    # ==========================================
    
    def config_add_time(self, chat_id, text, session):
        if ':' not in text:
            self.kirim_pesan(chat_id, "⚠️ Format salah. Gunakan HH:MM")
            return
        
        session['temp_config'] = {'waktu': text}
        session['state'] = 'CONFIG_SELECT_TARGET'
        
        self.kirim_pesan(chat_id, 
            "🎯 **PILIH TARGET PENERIMA:**\n\n"
            "Ketik angka/kode:\n"
            "1. **ALL** (Semua Pegawai)\n"
            "2. **KABAG** (Hanya Pimpinan)\n"
            "3. **STAFF** (Hanya Staff)"
        )

    def config_select_target(self, chat_id, text, session):
        # Normalisasi Input
        target = "ALL"
        if text == '1' or text.upper() == 'ALL': target = 'ALL'
        elif text == '2' or text.upper() == 'KABAG': target = 'KABAG'
        elif text == '3' or text.upper() == 'STAFF': target = 'STAFF'
        else:
            self.kirim_pesan(chat_id, "⚠️ Pilihan salah. Ketik 1, 2, atau 3.")
            return

        session['temp_config']['target'] = target
        session['state'] = 'CONFIG_ADD_MSG'
        self.kirim_pesan(chat_id, f"📝 **Target: {target}**. Sekarang masukkan isi pesan notifikasi:")

    def config_add_msg(self, chat_id, text, session):
        session['temp_config']['pesan'] = text
        session['state'] = 'CONFIG_CONFIRM_TEST'
        
        data = session['temp_config']
        self.kirim_pesan(chat_id, 
            f"📋 **KONFIRMASI JADWAL**\n"
            f"⏰ Jam: {data['waktu']}\n"
            f"🎯 Target: {data['target']}\n"
            f"💬 Pesan: {data['pesan']}\n\n"
            "👇 Pilih Tindakan:\n"
            "1️⃣ 🧪 **TEST DULU** (Kirim ke saya sekarang)\n"
            "2️⃣ 💾 **SIMPAN** (Masuk Database)"
        )

    def config_confirm_test(self, chat_id, text, session):
        data = session['temp_config']
        
        if text == '1': # TEST MODE
            self.kirim_pesan(chat_id, 
                f"🧪 **[TEST MODE]**\n"
                f"🔔 **{data['pesan']}**\n"
                f"Target: {data['target']}\n\n"
                "Oke, sudah dicek? Ketik **2** untuk SIMPAN permanen."
            )
            
        elif text == '2': # SIMPAN
            sukses = self.google.tambah_config_notif(data['waktu'], data['pesan'], data['target'])
            if sukses:
                self.kirim_pesan(chat_id, "✅ Berhasil disimpan ke Excel!")
                # Refresh Menu
                self.menu_config_notif(chat_id, session)
            else:
                self.kirim_pesan(chat_id, "❌ Gagal simpan ke Excel.")
        else:
            self.kirim_pesan(chat_id, "Pilih 1 atau 2.")

    def config_delete(self, chat_id, text, session):
        sukses = self.google.hapus_config_notif(text)
        if sukses:
            self.kirim_pesan(chat_id, f"✅ Jadwal {text} dihapus.")
        else:
            self.kirim_pesan(chat_id, "❌ Jam tidak ditemukan.")
        self.menu_config_notif(chat_id, session)

    # ==========================================
    # B. LOGIC BROADCAST (SUDAH DIPERBAIKI)
    # ==========================================
    def broadcast_process(self, chat_id, text, session):
        if text.lower() == 'batal':
            self.menu_config_notif(chat_id, session)
            return

        pesan_broadcast = text
        self.kirim_pesan(chat_id, "⏳ Mengirim pesan ke semua pegawai...")
        
        # 1. AMBIL DATA DARI SHEET KONTAK (CORRECT LOGIC)
        try:
            data_kontak = self.google.ambil_data(TAB_KONTAK)
        except Exception as e:
            self.kirim_pesan(chat_id, f"❌ Gagal mengambil data kontak: {e}")
            return

        count_sukses = 0
        
        # 2. LOOPING KIRIM PESAN
        for row in data_kontak:
            # Ambil Nomor WA
            target_wa = str(row.get('Nomor_WA', '')).strip()
            
            # Validasi nomor
            if target_wa and len(target_wa) > 5:
                # Jangan kirim ke diri sendiri (opsional)
                if target_wa == chat_id:
                    continue
                    
                # Kirim
                try:
                    self.kirim_pesan(target_wa, f"📢 *PENGUMUMAN*\n\n{pesan_broadcast}")
                    count_sukses += 1
                    time.sleep(1) # Jeda anti-spam
                except:
                    pass

        # 3. LAPORAN
        self.kirim_pesan(chat_id, 
            f"✅ **Broadcast Selesai.**\n"
            f"Terkirim ke {count_sukses} orang."
        )
        self.menu_config_notif(chat_id, session)