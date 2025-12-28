from datetime import datetime, timedelta
from core.config import TAB_RKM
from core.utils import parse_tanggal_indo

class ScheduleMixin:
    """Bagian Otak untuk Jadwal & Filter Tanggal (Versi WhatsApp)"""

    def tampilkan_menu_jadwal(self, chat_id):
        """Menampilkan pilihan filter waktu"""
        text = (
            "📅 **MENU CEK JADWAL**\n"
            "Pilih rentang waktu:\n\n"
            "1️⃣ Hari Ini\n"
            "2️⃣ Minggu Ini\n"
            "3️⃣ Bulan Ini\n"
            "4️⃣ Semua Jadwal\n"
            "5️⃣ Cari Tanggal Manual\n\n"
            "🔙 Ketik *Batal* untuk kembali."
        )
        self.kirim_pesan(chat_id, text)

    def menu_jadwal_handler(self, chat_id, text, session):
        """Menangani input angka pilihan user di menu jadwal"""
        
        # === A. PILIH FILTER ===
        if text == '1': # HARI INI
            self.filter_jadwal(chat_id, session['nama'], 'hari_ini')
        
        elif text == '2': # MINGGU INI
            self.filter_jadwal(chat_id, session['nama'], 'minggu_ini')
        
        elif text == '3': # BULAN INI
            self.filter_jadwal(chat_id, session['nama'], 'bulan_ini')
        
        elif text == '4': # SEMUA
            self.filter_jadwal(chat_id, session['nama'], 'semua')
        
        elif text == '5': # CARI MANUAL
            session['state'] = 'SEARCHING_DATE'
            self.kirim_pesan(chat_id, "🔍 **CARI TANGGAL**\nKetik tanggal yang dicari (Cth: 10 November 2025):")
            # Kita return agar tidak langsung balik ke menu utama
            return 
        
        elif text.lower() == 'batal':
            self.tampilkan_menu_utama(chat_id, session['nama'], "🔙 Kembali ke Menu.")
        
        else:
            self.kirim_pesan(chat_id, "⚠️ Pilih angka 1-5 atau ketik 'batal'.")
            return # Jangan ubah state, biarkan user mencoba lagi

        # Jika sukses filter (selain cari manual), kembalikan ke Menu Utama
        if text in ['1', '2', '3', '4']:
            # Beri jeda sedikit agar pesan jadwal terbaca dulu sebelum menu muncul
            import time
            time.sleep(1)
            self.tampilkan_menu_utama(chat_id, session['nama'], "👇 Menu Utama:")

    def filter_jadwal(self, chat_id, nama_user, mode):
        """Logika inti penyaringan jadwal"""
        self.kirim_pesan(chat_id, "🔄 Sedang mengambil data...")
        
        # Refresh Data dari Google Sheet
        self.db_rkm = self.google.ambil_data(TAB_RKM)
        
        # Ambil semua milik user ini dulu
        semua_jadwal = [r for r in self.db_rkm if r.get('Peserta') == nama_user]
        
        sekarang = datetime.now()
        hasil = []
        judul = ""

        if mode == 'hari_ini':
            judul = "HARI INI"
            for j in semua_jadwal:
                t = parse_tanggal_indo(j['Tanggal'])
                if t and t.date() == sekarang.date(): hasil.append(j)
        
        elif mode == 'minggu_ini':
            judul = "MINGGU INI"
            # Cari awal dan akhir minggu (Senin - Minggu)
            start = sekarang - timedelta(days=sekarang.weekday())
            end = start + timedelta(days=6)
            for j in semua_jadwal:
                t = parse_tanggal_indo(j['Tanggal'])
                if t and start.date() <= t.date() <= end.date(): hasil.append(j)

        elif mode == 'bulan_ini':
            judul = "BULAN INI"
            for j in semua_jadwal:
                t = parse_tanggal_indo(j['Tanggal'])
                if t and t.month == sekarang.month and t.year == sekarang.year: hasil.append(j)
        
        elif mode == 'semua':
            judul = "SELURUH WAKTU"
            hasil = semua_jadwal

        # Tampilkan Hasil
        if hasil:
            pesan = f"📅 **JADWAL {judul}:**\n"
            for j in hasil:
                status = "✅ Selesai" if j.get('Bukti Kehadiran') else "⏳ Belum Lapor"
                # Format pesan per jadwal
                pesan += f"🔹 {j['Kegiatan']}\n"
                pesan += f"   🕒 {j['Tanggal']}\n"
                pesan += f"   📍 {status}\n\n"
            
            self.kirim_pesan(chat_id, pesan)
        else:
            self.kirim_pesan(chat_id, f"✅ Tidak ada jadwal ditemukan untuk **{judul}**.")

    def cari_tanggal_manual(self, chat_id, text, session):
        """Pencarian jadwal berdasarkan keyword tanggal user"""
        self.kirim_pesan(chat_id, "🔍 Mencari...")
        
        self.db_rkm = self.google.ambil_data(TAB_RKM)
        keyword = text.lower()
        
        # Filter sederhana: apakah keyword ada di kolom Tanggal?
        hasil = [r for r in self.db_rkm if r.get('Peserta') == session['nama'] and keyword in str(r['Tanggal']).lower()]
        
        if hasil:
            pesan = f"🔍 **HASIL PENCARIAN '{text}':**\n"
            for j in hasil:
                status = "✅" if j.get('Bukti Kehadiran') else "⏳"
                pesan += f"- {j['Kegiatan']} ({j['Tanggal']}) {status}\n"
            self.kirim_pesan(chat_id, pesan)
        else:
            self.kirim_pesan(chat_id, f"❌ Tidak ditemukan jadwal pada tanggal '{text}'.")
        
        # Kembali ke menu utama
        self.tampilkan_menu_utama(chat_id, session['nama'])