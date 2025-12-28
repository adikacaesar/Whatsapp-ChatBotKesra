from datetime import datetime
import pytz 
from core.config import TAB_RKM, TAB_PEGAWAI
from core.utils import parse_tanggal_indo

class NotificationMixin:
    """Khusus menangani Notifikasi Otomatis (Cron Jobs) - Versi WAHA"""

    def jalankan_notifikasi_pagi(self, data=None):
        """
        Fungsi ini dipanggil oleh APScheduler dari server.py
        data: Dictionary berisi {'pesan': '...', 'target': '...'}
        """
        if not data:
            data = {'pesan': 'Cek Agenda', 'target': 'ALL'}

        pesan_custom = data.get('pesan', 'Cek Agenda Hari Ini')
        target_group = data.get('target', 'ALL').upper() # ALL, KABAG, STAFF
        
        print(f"⏰ MENJALANKAN NOTIFIKASI... Target: {target_group} | Msg: {pesan_custom}")
        
        # 1. Refresh Data Terbaru dari Excel
        try:
            db_rkm = self.google.ambil_data(TAB_RKM)
            db_pegawai = self.google.ambil_data(TAB_PEGAWAI)
        except Exception as e:
            print(f"❌ Gagal ambil data notif: {e}")
            return
        
        # 2. Cek Tanggal Hari Ini (WIB)
        zona_wib = pytz.timezone('Asia/Jakarta')
        sekarang_date = datetime.now(zona_wib).date()
        sekarang_str = sekarang_date.strftime('%d-%m-%Y')

        count_sent = 0

        # 3. Looping Semua Pegawai di Database
        for p in db_pegawai:
            chat_id = p.get('Chat_ID')
            nama_user = p.get('Nama')

            # Skip jika tidak punya Chat ID (Belum daftar)
            if not chat_id: continue

            # --- LOGIKA FILTER TARGET (ROLE BASED) ---
            jabatan = str(p.get('Jabatan 1', '')).lower()
            is_pimpinan = 'kabag' in jabatan or 'ketua' in jabatan or 'kepala' in jabatan
            
            kirim = False
            if target_group == 'ALL': kirim = True
            elif target_group == 'KABAG' and is_pimpinan: kirim = True
            elif target_group == 'STAFF' and not is_pimpinan: kirim = True
            
            if not kirim: continue # Skip orang ini

            # --- CARI JADWAL HARI INI ---
            jadwal_hari_ini = []
            for baris in db_rkm:
                if baris.get('Peserta') == nama_user:
                    # Parse tanggal dari string Excel
                    tgl_obj = parse_tanggal_indo(baris['Tanggal'])
                    if tgl_obj and tgl_obj.date() == sekarang_date:
                        status = "✅" if baris.get('Bukti Kehadiran') else "⏳"
                        jadwal_hari_ini.append(f"- {baris['Kegiatan']} ({status})")

            # --- SUSUN PESAN ---
            if jadwal_hari_ini:
                pesan = (
                    f"🔔 **{pesan_custom}**\n"
                    f"Halo {nama_user}, agenda hari ini ({sekarang_str}):\n\n"
                    + "\n".join(jadwal_hari_ini)
                    + "\n\nSemangat! 💪"
                )
            else:
                # Opsi: Kirim pesan penyemangat walaupun kosong
                # Jika tidak ingin spam, bisa di-comment bagian ini
                pesan = (
                    f"🔔 **{pesan_custom}**\n"
                    f"Halo {nama_user}, hari ini ({sekarang_str}) **TIDAK ADA JADWAL** kegiatan.\n"
                    "Bisa fokus mengerjakan laporan lain. 👍"
                )

            # --- KIRIM VIA WAHA (Method self.kirim_pesan diwariskan dari server.py) ---
            try:
                self.kirim_pesan(chat_id, pesan)
                count_sent += 1
            except Exception as e:
                print(f"⚠️ Gagal kirim ke {nama_user}: {e}")

        print(f"✅ Selesai. Terkirim ke {count_sent} orang.")