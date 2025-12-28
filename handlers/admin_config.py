from core.config import TAB_PEGAWAI

class AdminConfigMixin:
    """
    Mixin khusus untuk menangani Konfigurasi Notifikasi & Broadcast.
    Versi WAHA (Tanpa Telegram JobQueue)
    """

    def menu_config_notif(self, chat_id, session):
        """Menampilkan Dashboard Konfigurasi"""
        items = self.google.ambil_config_notif()
        
        pesan = "⚙️ **PENGATURAN NOTIFIKASI & BROADCAST**\n\n"
        pesan += "Daftar Jadwal Otomatis:\n"
        
        if not items:
            pesan += "(Belum ada jadwal)\n"
        else:
            for i in items:
                status = i.get('Status', 'OFF')
                waktu = i.get('Waktu', '??:??')
                target = i.get('Target', 'ALL')
                isi = i.get('Pesan', '-')

                icon = "🟢" if status == 'ON' else "🔴"
                pesan += f"{icon} **{waktu}** [{target}] : {isi}\n"
        
        pesan += "\n👇 **PILIHAN MENU:**\n"
        pesan += "1️⃣ Tambah Jadwal Baru\n"
        pesan += "2️⃣ Hapus Jadwal\n"
        pesan += "3️⃣ Kembali ke Menu Utama\n"
        pesan += "4️⃣ BROADCAST PESAN (DADAKAN)"

        session['state'] = 'CONFIG_MENU'
        self.kirim_pesan(chat_id, pesan)

    def config_process_menu(self, chat_id, text, session):
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
                "Ketik pesan yang ingin Anda kirimkan ke SEMUA pegawai.\n"
                "(Ketik 'batal' untuk kembali)"
            )
        else:
            self.kirim_pesan(chat_id, "Pilih angka 1-4.")

    # --- WIZARD TAMBAH JADWAL ---
    
    def config_add_time(self, chat_id, text, session):
        if ':' not in text:
            self.kirim_pesan(chat_id, "⚠️ Format salah. Gunakan HH:MM")
            return
        
        session['temp_config'] = {'waktu': text}
        session['state'] = 'CONFIG_SELECT_TARGET'
        
        self.kirim_pesan(chat_id, 
            "🎯 **PILIH TARGET PENERIMA:**\n\n"
            "Ketik salah satu:\n"
            "• **ALL** (Semua Pegawai)\n"
            "• **KABAG** (Hanya Pimpinan/Kabag)\n"
            "• **STAFF** (Hanya Staff/Pelaksana)"
        )

    def config_select_target(self, chat_id, text, session):
        target = text.upper()
        if target not in ['ALL', 'KABAG', 'STAFF']:
            self.kirim_pesan(chat_id, "⚠️ Pilihan salah. Ketik: ALL, KABAG, atau STAFF.")
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
                f"📅 (Tanggal Hari Ini)\n\n"
                f"Halo {session['nama']}, (Isi Agenda)..."
            )
            self.kirim_pesan(chat_id, "Oke, sudah dicek? Ketik **2** untuk SIMPAN permanen.")
            
        elif text == '2': # SIMPAN
            sukses = self.google.tambah_config_notif(data['waktu'], data['pesan'], data['target'])
            if sukses:
                self.kirim_pesan(chat_id, "✅ Berhasil disimpan ke Excel!")
                
                # Reload Scheduler di Server (Hook)
                if hasattr(self, 'setup_scheduler'):
                    self.setup_scheduler()
                
                self.menu_config_notif(chat_id, session)
            else:
                self.kirim_pesan(chat_id, "❌ Gagal simpan ke Excel.")
        else:
            self.kirim_pesan(chat_id, "Pilih 1 atau 2.")

    def config_delete(self, chat_id, text, session):
        sukses = self.google.hapus_config_notif(text)
        if sukses:
            self.kirim_pesan(chat_id, f"✅ Jadwal {text} dihapus.")
            # Reload Scheduler di Server (Hook)
            if hasattr(self, 'setup_scheduler'):
                self.setup_scheduler()
        else:
            self.kirim_pesan(chat_id, "❌ Jam tidak ditemukan.")
        self.menu_config_notif(chat_id, session)

    # --- BROADCAST MANUAL ---
    def broadcast_process(self, chat_id, text, session):
        if text.lower() == 'batal':
            self.menu_config_notif(chat_id, session)
            return

        self.kirim_pesan(chat_id, "⏳ Mengirim pesan ke semua pegawai...")
        
        db_pegawai = self.google.ambil_data(TAB_PEGAWAI)
        count = 0
        
        for p in db_pegawai:
            cid = p.get('Chat_ID')
            if cid:
                try:
                    msg = f"📢 **PENGUMUMAN DARI ADMIN**\n\n{text}"
                    self.kirim_pesan(cid, msg)
                    count += 1
                except: pass
        
        self.kirim_pesan(chat_id, f"✅ Broadcast Selesai.\nTerkirim ke {count} orang.")
        self.menu_config_notif(chat_id, session)