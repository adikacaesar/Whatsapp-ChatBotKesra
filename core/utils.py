from datetime import datetime

# Kamus Bulan Indonesia
BULAN_INDO = {
    'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
}

def parse_tanggal_indo(teks_tanggal):
    """Mengubah teks '10 November 2025' menjadi object datetime Python"""
    try:
        parts = teks_tanggal.split() # ['10', 'November', '2025']
        if len(parts) < 3: return None
        
        tgl = int(parts[0])
        bulan_str = parts[1].lower()
        tahun = int(parts[2])
        
        bulan_angka = BULAN_INDO.get(bulan_str)
        if not bulan_angka: return None
        
        return datetime(tahun, bulan_angka, tgl)
    except:
        return None