import os
import json
import gspread
import io
import time
from datetime import datetime
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

# Import Config
from .config import (
    FILE_TOKEN, NAMA_SPREADSHEET, 
    TAB_PEGAWAI, TAB_RKM, TAB_KONTAK, TAB_CONFIG_NOTIF,
    ID_FOLDER_DRIVE, ID_FOLDER_SURAT
)

class GoogleService:
    def __init__(self):
        print("🔌 Menghubungkan ke Google Services...")
        
        # 1. Load Credentials dari Token
        self.creds = self.get_creds()
        
        if not self.creds:
            print("❌ Gagal login: Credential kosong.")
            return

        # 2. Build Service Google Drive
        try:
            self.drive_service = build('drive', 'v3', credentials=self.creds)
        except Exception as e:
            print(f"❌ Error Build Drive: {e}")

        # 3. Build Service Spreadsheet (Gspread)
        try:
            self.sheet_client = gspread.authorize(self.creds)
            # Cek Koneksi ke Sheet
            self.spreadsheet = self.sheet_client.open(NAMA_SPREADSHEET)
            print(f"✅ Terhubung ke Spreadsheet: {NAMA_SPREADSHEET}")
        except Exception as e:
            print(f"❌ Gagal buka Spreadsheet: {e}")

    def get_creds(self):
        """Load Token JSON"""
        if os.path.exists(FILE_TOKEN):
            try:
                with open(FILE_TOKEN, 'r') as token:
                    info = json.load(token)
                    return UserCredentials.from_authorized_user_info(info)
            except Exception as e:
                print(f"❌ Error baca token.json: {e}")
                return None
        else:
            print("❌ ERROR: token.json hilang! Jalankan 'python generate_token.py' dulu.")
            return None

    # ==================================================
    # 1. DATABASE UTAMA (READ/WRITE)
    # ==================================================

    def ambil_data(self, nama_tab):
        """Mengambil seluruh data dari sheet sebagai list of dict"""
        try:
            worksheet = self.spreadsheet.worksheet(nama_tab)
            return worksheet.get_all_records()
        except Exception as e:
            print(f"❌ Error ambil data {nama_tab}: {e}")
            return []

    # ==================================================
    # 2. SISTEM LOGIN & KONTAK (FASE 1 - WAHA)
    # ==================================================

    def cek_kontak_terdaftar(self, id_pegawai):
        """Cek apakah ID Pegawai sudah punya kontak WA"""
        try:
            worksheet = self.spreadsheet.worksheet(TAB_KONTAK)
            # Cari di kolom A atau seluruh sheet
            cell = worksheet.find(str(id_pegawai))
            return cell is not None
        except gspread.exceptions.WorksheetNotFound:
            print(f"⚠️ Sheet '{TAB_KONTAK}' belum dibuat! Harap buat manual di Excel.")
            return False
        except:
            return False

    def simpan_kontak_baru(self, id_pegawai, nomor_wa):
        """Simpan Kontak Baru"""
        try:
            worksheet = self.spreadsheet.worksheet(TAB_KONTAK)
            waktu = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            worksheet.append_row([str(id_pegawai), str(nomor_wa), waktu])
            return True
        except Exception as e:
            print(f"❌ Gagal simpan kontak: {e}")
            return False

    # ==================================================
    # 3. UPLOAD GOOGLE DRIVE (FASE 2)
    # ==================================================

    def upload_ke_drive(self, filepath, nama_file_baru):
        """Upload File Fisik (Foto/PDF) ke Drive"""
        print(f"📤 Uploading: {nama_file_baru}...")
        try:
            file_metadata = {'name': nama_file_baru, 'parents': [ID_FOLDER_DRIVE]}
            
            # Gunakan Resumable=True untuk file besar
            media = MediaFileUpload(filepath, resumable=True)
            
            file = self.drive_service.files().create(
                body=file_metadata, 
                media_body=media, 
                fields='id, webViewLink'
            ).execute()
            
            # Set Permission Public (Optional, agar bisa dilihat)
            self._set_public_permission(file.get('id'))
            
            return file.get('webViewLink')
        except Exception as e:
            print(f"❌ GAGAL UPLOAD DRIVE: {e}")
            return None

    def upload_text_ke_drive(self, nama_file, isi_teks):
        """Buat File Txt Langsung di Drive (Untuk Izin)"""
        print(f"📤 Uploading Teks: {nama_file}...")
        try:
            file_metadata = {'name': nama_file, 'parents': [ID_FOLDER_DRIVE]}
            fh = io.BytesIO(isi_teks.encode('utf-8'))
            media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=False)
            
            file = self.drive_service.files().create(
                body=file_metadata, 
                media_body=media, 
                fields='id, webViewLink'
            ).execute()

            self._set_public_permission(file.get('id'))
            return file.get('webViewLink')
        except Exception as e:
            print(f"❌ GAGAL UPLOAD TEXT: {e}")
            return None

    def _set_public_permission(self, file_id):
        """Helper: Agar file bisa dibuka siapa saja yg punya link"""
        try:
            self.drive_service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'},
                fields='id'
            ).execute()
        except:
            pass

    # ==================================================
    # 4. UPDATE DATA KEHADIRAN (FASE 2)
    # ==================================================

    def update_bukti(self, nama_peserta, nama_kegiatan, tanggal_kegiatan, link_bukti, jenis_laporan="HADIR"):
        """Update Kolom Bukti & Status di RKM"""
        try:
            worksheet = self.spreadsheet.worksheet(TAB_RKM)
            
            # Ambil semua data untuk pencarian manual
            all_values = worksheet.get_all_values()
            header = all_values[0]
            
            # Cari Index Kolom
            try:
                idx_peserta = header.index('Peserta')
                idx_kegiatan = header.index('Kegiatan')
                idx_tanggal = header.index('Tanggal')
                
                col_bukti = header.index('Bukti Kehadiran') + 1
                col_status = header.index('Status') + 1
            except ValueError as ve:
                return False, f"Kolom Excel Wajib Hilang: {ve}"

            # Loop cari baris
            target_row = -1
            for i, row in enumerate(all_values):
                if i == 0: continue # Skip header
                
                # Pencocokan String (Case Insensitive & Strip)
                r_nama = str(row[idx_peserta]).strip()
                r_kegiatan = str(row[idx_kegiatan]).strip()
                
                # Cek Nama & Kegiatan dulu
                if r_nama.lower() == str(nama_peserta).strip().lower() and r_kegiatan.lower() == str(nama_kegiatan).strip().lower():
                    # Cek Tanggal (Optional/Loose Check)
                    # Jika tanggal di excel kosong atau cocok, dianggap benar
                    if not tanggal_kegiatan or str(row[idx_tanggal]).strip() == str(tanggal_kegiatan).strip():
                        target_row = i + 1
                        break
            
            if target_row != -1:
                # Update Cell
                worksheet.update_cell(target_row, col_status, jenis_laporan)
                worksheet.update_cell(target_row, col_bukti, link_bukti)
                return True, "Sukses"
            
            return False, "Data kegiatan tidak ditemukan di Excel."

        except Exception as e:
            return False, str(e)

    # ==================================================
    # 5. FITUR ADMIN (CONFIG & SURAT)
    # ==================================================

    def update_surat_resmi_by_id(self, id_kegiatan, link_surat):
        """Untuk Menu 4 Admin: Upload Surat Resmi"""
        try:
            worksheet = self.spreadsheet.worksheet(TAB_RKM)
            cell = worksheet.find(str(id_kegiatan)) 
            
            if cell:
                header = worksheet.row_values(1)
                col_surat = header.index('Surat Resmi') + 1
                worksheet.update_cell(cell.row, col_surat, link_surat)
                return True, "Sukses"
            return False, "ID Kegiatan tidak ditemukan."
        except Exception as e:
            return False, str(e)

    def ambil_config_notif(self):
        """Untuk Menu 5 Admin"""
        try:
            return self.ambil_data(TAB_CONFIG_NOTIF)
        except: 
            return []

    def tambah_config_notif(self, waktu, pesan, target="ALL"):
        try:
            ws = self.spreadsheet.worksheet(TAB_CONFIG_NOTIF)
            ws.append_row([waktu, pesan, "ON", target])
            return True
        except: return False

    def hapus_config_notif(self, waktu_target):
        try:
            ws = self.spreadsheet.worksheet(TAB_CONFIG_NOTIF)
            cell = ws.find(waktu_target)
            if cell:
                ws.delete_rows(cell.row)
                return True
            return False
        except: return False