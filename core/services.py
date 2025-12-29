import os
import json
import gspread
import io
import time
from datetime import datetime
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from .config import *

class GoogleService:
    def __init__(self):
        self.creds = self.get_creds()
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.sheet_client = gspread.authorize(self.creds)
        self.NAMA_SPREADSHEET = NAMA_SPREADSHEET

    def get_creds(self):
        if os.path.exists(FILE_TOKEN):
            with open(FILE_TOKEN, 'r') as token:
                info = json.load(token)
                return UserCredentials.from_authorized_user_info(info)
        else:
            print("❌ ERROR: token.json hilang!")
            return None

    def ambil_data(self, nama_tab):
        try:
            sheet = self.sheet_client.open(self.NAMA_SPREADSHEET)
            worksheet = sheet.worksheet(nama_tab)
            return worksheet.get_all_records()
        except Exception as e:
            print(f"❌ Error ambil data {nama_tab}: {e}")
            return []

    def simpan_chat_id(self, id_pegawai, chat_id):
        """Fitur Lama (Telegram) - Tetap disimpan untuk backward compatibility"""
        try:
            sheet = self.sheet_client.open(self.NAMA_SPREADSHEET)
            worksheet = sheet.worksheet(TAB_PEGAWAI)
            cell = worksheet.find(str(id_pegawai))
            if cell:
                header = worksheet.row_values(1)
                if 'Chat_ID' in header:
                    col_index = header.index('Chat_ID') + 1 
                    worksheet.update_cell(cell.row, col_index, str(chat_id))
                    return True
            return False
        except Exception as e:
            print(f"❌ Error Simpan Chat ID: {e}")
            return False

    def upload_ke_drive(self, filepath, nama_file_baru):
        """Upload foto absen - MODE STABIL (Resumable=False)"""
        print(f"📤 Uploading Foto Absen: {nama_file_baru}...")
        try:
            file_metadata = {'name': nama_file_baru, 'parents': [ID_FOLDER_DRIVE]}
            
            with open(filepath, 'rb') as f:
                media = MediaIoBaseUpload(f, mimetype='image/jpeg', resumable=False)
                file = self.drive_service.files().create(
                    body=file_metadata, 
                    media_body=media, 
                    fields='id, webViewLink'
                ).execute()
                
            return file.get('webViewLink')
        except Exception as e:
            print(f"❌ GAGAL UPLOAD DRIVE: {e}")
            return None

    def upload_file_bebas(self, filepath, nama_file_baru, mime_type, target_folder_id=None):
        """Upload file bebas - MODE STABIL (Resumable=False)"""
        print(f"📤 Uploading File: {nama_file_baru} ({mime_type})...")
        folder_tujuan = target_folder_id if target_folder_id else ID_FOLDER_DRIVE
        
        try:
            file_metadata = {'name': nama_file_baru, 'parents': [folder_tujuan]}
            
            with open(filepath, 'rb') as f:
                media = MediaIoBaseUpload(f, mimetype=mime_type, resumable=False)
                file = self.drive_service.files().create(
                    body=file_metadata, 
                    media_body=media, 
                    fields='id, webViewLink'
                ).execute()
                
            return file.get('webViewLink')
        except Exception as e:
            print(f"❌ GAGAL UPLOAD FILE: {e}")
            return None

    def upload_text_ke_drive(self, nama_file, isi_teks):
        print(f"📤 Uploading Catatan: {nama_file}...")
        try:
            file_metadata = {'name': nama_file, 'parents': [ID_FOLDER_DRIVE]}
            fh = io.BytesIO(isi_teks.encode('utf-8'))
            media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=False)
            file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
            return file.get('webViewLink')
        except Exception as e:
            print(f"❌ GAGAL UPLOAD TEXT: {e}")
            return None

    def update_bukti(self, nama_user, kegiatan, tanggal, link_bukti, jenis_laporan="HADIR"):
        try:
            sheet = self.sheet_client.open(self.NAMA_SPREADSHEET)
            worksheet = sheet.worksheet(TAB_RKM)
            all_values = worksheet.get_all_values()
            header = all_values[0]
            
            try:
                idx_peserta = header.index('Peserta')
                idx_kegiatan = header.index('Kegiatan')
                idx_tanggal = header.index('Tanggal')
                col_bukti = header.index('Bukti Kehadiran') + 1
                col_timestamp = header.index('Timestamp') + 1
            except ValueError as ve:
                return False, f"Kolom Wajib tidak ditemukan: {ve}"
            
            col_ket_izin = None
            if 'Keterangan Izin' in header:
                col_ket_izin = header.index('Keterangan Izin') + 1

            row_found = -1
            for i, row in enumerate(all_values):
                if i == 0: continue
                if row[idx_peserta] == nama_user and row[idx_kegiatan] == kegiatan and row[idx_tanggal] == tanggal:
                    row_found = i + 1
                    break
            
            if row_found != -1:
                waktu_sekarang = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                if jenis_laporan == "HADIR":
                    worksheet.update_cell(row_found, col_bukti, link_bukti)
                    if col_ket_izin: worksheet.update_cell(row_found, col_ket_izin, "-")
                else:
                    worksheet.update_cell(row_found, col_bukti, jenis_laporan)
                    if col_ket_izin: worksheet.update_cell(row_found, col_ket_izin, link_bukti)

                worksheet.update_cell(row_found, col_timestamp, waktu_sekarang)
                return True, "Sukses"
            return False, "Data presensi tidak ditemukan."
        except Exception as e:
            return False, str(e)

    def update_surat_resmi_by_id(self, id_kegiatan, link_surat):
        try:
            sheet = self.sheet_client.open(self.NAMA_SPREADSHEET)
            worksheet = sheet.worksheet(TAB_RKM)
            all_values = worksheet.get_all_values()
            header = all_values[0]
            
            try:
                idx_id_kegiatan = header.index('ID Kegiatan')
                col_surat = header.index('Surat Resmi') + 1 
            except ValueError:
                return False, "Kolom 'ID Kegiatan' atau 'Surat Resmi' tidak ditemukan!"

            row_updates = []
            for i, row in enumerate(all_values):
                if i == 0: continue
                if str(row[idx_id_kegiatan]).strip() == str(id_kegiatan).strip():
                    cell_address = gspread.utils.rowcol_to_a1(i+1, col_surat)
                    row_updates.append({'range': cell_address, 'values': [[link_surat]]})

            if row_updates:
                worksheet.batch_update(row_updates)
                return True, f"Berhasil update {len(row_updates)} baris."
            return False, "ID Kegiatan tidak ditemukan."
        except Exception as e:
            return False, str(e)
            
    # =========================================================
    #  FITUR TAMBAHAN: CONFIG NOTIFIKASI
    # =========================================================
    
    def ambil_config_notif(self):
        try:
            sheet = self.sheet_client.open(self.NAMA_SPREADSHEET)
            worksheet = sheet.worksheet(TAB_CONFIG_NOTIF)
            return worksheet.get_all_records()
        except Exception as e:
            print(f"⚠️ Error ambil config: {e}")
            return []

    def tambah_config_notif(self, waktu, pesan, target="ALL"):
        try:
            sheet = self.sheet_client.open(self.NAMA_SPREADSHEET)
            worksheet = sheet.worksheet(TAB_CONFIG_NOTIF)
            worksheet.append_row([waktu, pesan, "ON", target])
            return True
        except Exception as e:
            print(f"❌ Gagal tambah config: {e}")
            return False

    def hapus_config_notif(self, waktu_target):
        try:
            sheet = self.sheet_client.open(self.NAMA_SPREADSHEET)
            worksheet = sheet.worksheet(TAB_CONFIG_NOTIF)
            cell = worksheet.find(waktu_target)
            if cell:
                worksheet.delete_rows(cell.row)
                return True
            return False
        except Exception as e:
            print(f"❌ Gagal hapus config: {e}")
            return False

    # ==========================================
    #  [BARU] FASE 1: KONTAK & VALIDASI (WAHA)
    # ==========================================

    def cek_kontak_terdaftar(self, id_pegawai):
        """
        Mengecek apakah ID Pegawai ini sudah punya Nomor WA di sheet kontak_pegawai.
        Return: True jika ada, False jika belum.
        """
        try:
            sheet = self.sheet_client.open(self.NAMA_SPREADSHEET)
            worksheet = sheet.worksheet(TAB_KONTAK)
            cell = worksheet.find(str(id_pegawai))
            return cell is not None
        except gspread.exceptions.WorksheetNotFound:
            print(f"⚠️ Sheet '{TAB_KONTAK}' belum dibuat! Harap buat manual di Excel.")
            return False
        except Exception:
            return False

    def simpan_kontak_baru(self, id_pegawai, nomor_wa):
        """
        Menyimpan pasangan ID Pegawai & Nomor WA ke sheet kontak_pegawai.
        """
        try:
            sheet = self.sheet_client.open(self.NAMA_SPREADSHEET)
            worksheet = sheet.worksheet(TAB_KONTAK)
            
            waktu = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Format Data: [ID, Nomor WA, Updated At]
            worksheet.append_row([str(id_pegawai), str(nomor_wa), waktu])
            return True
        except Exception as e:
            print(f"❌ Gagal simpan kontak: {e}")
            return False