import os
import time
from core.config import TAB_RKM

class ReportActionMixin:
    """Bagian 2: Eksekusi Upload & Simpan"""

    # --- HANDLER FOTO LOOPING ---
    async def proses_terima_foto(self, update, session):
        chat_id = update.message.chat_id
        rapat = session['selected_rapat']
        jenis = session.get('jenis_laporan', 'HADIR')
        
        caption_foto = update.message.caption or ""
        label_file = "Bukti" if jenis == "HADIR" else "SuratSakit"
        
        # Penanganan Error Upload
        try:
            # 1. Download File dari Telegram/WA ke Server
            # (Ingat: di server.py file sudah di-download ke path lokal yang dikirim via 'update')
            # Namun karena struktur Anda custom di server.py, kita asumsikan 'update' di sini
            # membawa path file lokal jika dipanggil dari server.py.
            # Tapi kode di bawah ini memakai logika download Telegram 'get_file'.
            # JIKA MENGGUNAKAN SERVER.PY SAYA (WAHA), LOGIKANYA SEDIKIT BERBEDA:
            
            # --- ADAPTASI KODE UNTUK WAHA (SERVER.PY) ---
            # Di server.py, 'update' berisi argumen: chat_id, file_path, mime_type, caption
            # Maka method ini harus menerima argumen tersebut, BUKAN object 'update' Telegram.
            pass
            
            # KARENA ANDA SUDAH MENIMPA FILE LAMA DENGAN VERSI TELEGRAM DI TAHAPAN SEBELUMNYA,
            # MARI KEMBALIKAN KE VERSI WAHA YANG BENAR:
            
        except Exception as e:
            print(f"Error Handler: {e}")

    # --- VERSI WAHA YANG BENAR (TIMPA FILE report_action.py DENGAN INI) ---
    def proses_terima_foto(self, chat_id, file_path, mime_type, caption, session):
        """
        Menerima file yang sudah didownload oleh server.py.
        """
        rapat = session['selected_rapat']
        jenis = session.get('jenis_laporan', 'HADIR')
        
        caption_foto = caption or ""
        label_file = "Bukti" if jenis == "HADIR" else "SuratSakit"
        
        try:
            timestamp = int(time.time())
            nama_drive = f"{label_file}_{session['nama']}_{rapat['Kegiatan'][:10]}_{timestamp}.jpg"
            
            # Upload ke Drive
            link = self.google.upload_ke_drive(file_path, nama_drive)
            
            # --- BAGIAN PENTING: CLEANUP YANG AMAN ---
            try:
                if os.path.exists(file_path): 
                    # Beri jeda 0.5 detik agar Windows melepas lock file
                    time.sleep(0.5)
                    os.remove(file_path)
            except Exception as e_del:
                print(f"⚠️ Gagal hapus temp file (Abaikan): {e_del}")
            # -----------------------------------------

            if link:
                if caption_foto:
                    data_simpan = f"{link} (Note: {caption_foto})"
                else:
                    data_simpan = link
                
                session['collected_links'].append(data_simpan)
                
                jml = len(session['collected_links'])
                self.kirim_pesan(chat_id, f"✅ Foto ke-{jml} diterima.\n(Ketik **SELESAI** jika sudah semua)")
            else:
                self.kirim_pesan(chat_id, "❌ Gagal Upload Drive (Cek Log Server).")
        except Exception as e:
            self.kirim_pesan(chat_id, f"❌ Error Sistem: {e}")

    # --- HANDLER SELESAI UPLOAD ---
    def proses_selesai_upload_foto(self, chat_id, session):
        if not session.get('collected_links'):
            self.kirim_pesan(chat_id, "⚠️ Belum ada foto yang diterima! Kirim foto dulu.")
            return

        session['state'] = 'AWAITING_FINAL_CAPTION'
        self.kirim_pesan(chat_id, 
            "🆗 Foto tersimpan sementara.\n\n"
            "Apakah ada **Keterangan Tambahan** untuk laporan ini?\n"
            "(Contoh: 'Hadir mewakili Pak Kabag' atau ketik 'skip' jika tidak ada)"
        )

    # --- FINALISASI SIMPAN EXCEL ---
    def proses_simpan_akhir(self, chat_id, text, session):
        keterangan_tambahan = text
        if keterangan_tambahan.lower() == 'skip':
            keterangan_tambahan = ""

        rapat = session['selected_rapat']
        jenis = session.get('jenis_laporan', 'HADIR')
        links = session['collected_links']

        self.kirim_pesan(chat_id, "⏳ Menggabungkan data & update Excel...")

        gabungan_link = "\n".join(links)
        if keterangan_tambahan:
            gabungan_link += f"\n\n[Keterangan: {keterangan_tambahan}]"

        # Panggil Service
        if jenis == "HADIR":
            sukses, msg = self.google.update_bukti(session['nama'], rapat['Kegiatan'], rapat['Tanggal'], gabungan_link, jenis_laporan="HADIR")
        else:
            sukses, msg = self.google.update_bukti(session['nama'], rapat['Kegiatan'], rapat['Tanggal'], gabungan_link, jenis_laporan="SAKIT")

        if sukses:
            self.kirim_pesan(chat_id, f"✅ **LAPORAN SUKSES!**\n{len(links)} Foto berhasil ditautkan.")
            self.tampilkan_menu_utama(chat_id, session['nama'])
        else:
            self.kirim_pesan(chat_id, f"⚠️ Gagal Update Excel: {msg}")

    # --- KHUSUS IZIN (TEXT ONLY) ---
    def proses_terima_alasan_izin(self, chat_id, text, session):
        alasan = text
        rapat = session['selected_rapat']
        self.kirim_pesan(chat_id, "⏳ Menyimpan catatan izin...")
        
        nama_file = f"IZIN_{session['nama']}_{rapat['Kegiatan'][:10]}.txt"
        link = self.google.upload_text_ke_drive(nama_file, f"Alasan Izin: {alasan}\nOleh: {session['nama']}")
        
        if link:
            sukses, msg = self.google.update_bukti(session['nama'], rapat['Kegiatan'], rapat['Tanggal'], link, jenis_laporan="IZIN")
            if sukses:
                self.kirim_pesan(chat_id, f"✅ Izin Tercatat.")
                self.tampilkan_menu_utama(chat_id, session['nama'])
            else:
                self.kirim_pesan(chat_id, f"⚠️ Gagal Excel: {msg}")