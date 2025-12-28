import os
import time
from core.config import TAB_PEGAWAI, TAB_RKM, ID_FOLDER_SURAT

class AdminActionMixin:
    """Bagian 4: Pemrosesan Data Admin - Versi WAHA"""

    def admin_finalisasi_simpan(self, chat_id, session):
        data = session['temp_rapat']
        peserta_raw = data['peserta_list']
        
        if not peserta_raw:
            self.kirim_pesan(chat_id, "⚠️ Belum ada peserta!")
            session['state'] = 'ADMIN_INPUT_PESERTA'
            return

        self.kirim_pesan(chat_id, "⏳ **Memproses data...**")

        self.db_pegawai = self.google.ambil_data(TAB_PEGAWAI)
        final_targets = []
        cols_jabatan = ['Jabatan 1', 'Jabatan 2', 'Jabatan 3', 'Jabatan 4']

        # --- LOGIKA PENCARIAN PESERTA ---
        for p in peserta_raw:
            target_str = p['target'].strip().lower()
            role_str = p['status']
            found = False
            
            for pegawai in self.db_pegawai:
                # 1. Cek Nama
                nama_db = str(pegawai.get('Nama', '')).strip().lower()
                if target_str in nama_db:
                    final_targets.append({'data': pegawai, 'role': role_str})
                    found = True
                    continue 
                
                # 2. Cek Jabatan
                for col in cols_jabatan:
                    jab_db = str(pegawai.get(col, '')).strip().lower()
                    if target_str == jab_db:
                        final_targets.append({'data': pegawai, 'role': role_str})
                        found = True
                        break 
            
            if not found:
                self.kirim_pesan(chat_id, f"⚠️ Peringatan: '{p['target']}' tidak ditemukan.")

        if not final_targets:
            self.kirim_pesan(chat_id, "❌ Gagal. Tidak ada target valid.")
            return

        # --- SIMPAN KE EXCEL ---
        sheet = self.google.sheet_client.open(self.google.NAMA_SPREADSHEET)
        ws_rkm = sheet.worksheet(TAB_RKM)
        
        rows_to_add = []
        notif_count = 0
        added_signatures = set()

        for item in final_targets:
            pegawai = item['data']
            role = item['role']
            
            # Cek Duplikasi (Agar satu orang tidak diundang 2x di rapat yang sama)
            signature = f"{pegawai['ID_Pegawai']}_{pegawai['Nama']}"
            if signature in added_signatures: continue
            added_signatures.add(signature)
            
            id_unik = f"{data['id']}_{pegawai['ID_Pegawai']}"

            row = [
                data['tanggal'], data['jam'], data['id'],
                data['kegiatan'], data['lokasi'],
                pegawai['Nama'], role,
                "", "", "FALSE", id_unik, "", ""
            ]
            rows_to_add.append(row)
            
            # --- KIRIM NOTIFIKASI VIA WAHA ---
            if pegawai.get('Chat_ID'):
                try:
                    msg = f"📅 **UNDANGAN BARU**\nKegiatan: {data['kegiatan']}\nWaktu: {data['tanggal']} {data['jam']}\nLokasi: {data['lokasi']}"
                    self.kirim_pesan(pegawai['Chat_ID'], msg)
                    notif_count += 1
                except: pass

        try:
            ws_rkm.append_rows(rows_to_add)
            self.kirim_pesan(chat_id,
                f"✅ **SUKSES!**\nTotal Undangan: {len(rows_to_add)}\nNotifikasi: {notif_count}"
            )
            self.tampilkan_menu_utama(chat_id, session['nama'])
        except Exception as e:
            self.kirim_pesan(chat_id, f"❌ Error Excel: {e}")

    def admin_proses_file_surat(self, chat_id, file_path, mime_type, session):
        """
        Handler baru untuk menerima file yang SUDAH didownload oleh server.py
        file_path: Lokasi file lokal (temp)
        """
        id_kegiatan = session['selected_id_surat']
        user_name = session['nama']
        
        self.kirim_pesan(chat_id, "⏳ **Mengupload surat resmi...**")

        try:
            # Tentukan ekstensi
            ext = "jpg"
            if "pdf" in mime_type: ext = "pdf"
            elif "png" in mime_type: ext = "png"
            
            timestamp = int(time.time())
            nama_drive = f"SURAT_{id_kegiatan}_{timestamp}.{ext}"
            
            # --- UPLOAD KE DRIVE (FOLDER KHUSUS SURAT) ---
            link = self.google.upload_file_bebas(
                file_path, 
                nama_drive, 
                mime_type, 
                target_folder_id=ID_FOLDER_SURAT 
            )

            # Hapus file lokal setelah upload (kebersihan server)
            if os.path.exists(file_path): os.remove(file_path)

            if link:
                sukses, msg = self.google.update_surat_resmi_by_id(id_kegiatan, link)
                if sukses:
                    self.kirim_pesan(chat_id, f"✅ **SURAT RESMI TERSIMPAN!**\n🆔 {id_kegiatan}\n📎 {link}")
                    self.tampilkan_menu_utama(chat_id, user_name)
                else:
                    self.kirim_pesan(chat_id, f"⚠️ Gagal Excel: {msg}")
            else:
                self.kirim_pesan(chat_id, "❌ Gagal Upload Drive.")

        except Exception as e:
            self.kirim_pesan(chat_id, f"❌ Error Upload: {e}")