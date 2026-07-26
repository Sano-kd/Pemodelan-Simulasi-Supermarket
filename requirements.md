# Penjelasan Program Simulasi Monte Carlo - Persediaan Supermarket

 app.py

### `# IMPORT LIBRARY`
|   Library   |                          Kegunaan                                  |
|-------------|--------------------------------------------------------------------|
| `streamlit` | Membuat tampilan web interaktif (dashboard, tombol, tabel, dll)    |
| `pandas`    | Mengolah data dalam bentuk tabel (DataFrame)                       |
| `plotly.express` & `plotly.graph_objects` | Membuat grafik interaktif (bar, line, pie, scatter) |
| `StringIO`  | Menyimpan file CSV di memori (tanpa simpan ke disk) untuk download |
| `time`      | Memberi jeda/animasi pada progress bar                             |
| `os`        | Cek keberadaan file dataset di folder                              |

### `# IMPORT FUNGSI DARI UTILS.PY`
Fungsi-fungsi dari `utils.py` yang dipakai oleh `app.py` — semacam "mesin" di belakang layar.

### `# KONFIGURASI HALAMAN STREAMLIT`
`st.set_page_config(...)` — mengatur judul tab, icon, layout lebar, dan sidebar default terbuka.

### `# KONSTANTA WARNA (LIGHT & DARK MODE)`
Menyimpan kode warna hex untuk mode terang dan gelap, dipakai di seluruh halaman.

### `# FUNGSI: TERAPKAN CSS KUSTOM`
`apply_custom_css(dark_mode)` — menyuntikkan CSS ke halaman agar tampilan lebih rapi, card, tabel, tab, dll sesuai tema.

### `# FUNGSI: INISIALISASI SESSION STATE`
`init_session()` — menyiapkan penyimpanan sementara (`st.session_state`) agar data tidak hilang saat interaksi (pindah halaman, klik tombol).

### `# FUNGSI: DAPATKAN WARNA TEKS`
`get_text_color()` — mengembalikan warna teks sesuai mode (gelap/terang) untuk grafik.

### `# FUNGSI: NAVIGASI SIDEBAR`
`sidebar_nav()` — menu samping kiri: pindah halaman, toggle dark mode, upload dataset.

### `# FUNGSI: MUAT DATASET`
`load_dataset()` — ambil data dari session_state atau dari file Excel default.

### `# HALAMAN: DASHBOARD`
`page_dashboard()` — Halaman utama: menampilkan ringkasan (total produk, supplier, penjualan) + grafik penjualan per bulan, distribusi kategori, scatter stok vs penjualan.

### `# HALAMAN: DATA PRODUK`
`page_data_produk()` — Tabel lengkap produk dengan fitur search dan filter (kategori, supplier, nama produk) + tombol download CSV.

### `# HALAMAN: SIMULASI MONTE CARLO`
`page_simulasi()` — Inti program: pilih produk, supplier, periode → jalankan simulasi → tampilkan 6 tahap (probabilitas, LCG, mapping, persediaan, ringkasan, visualisasi).

### `# HALAMAN: LAPORAN`
`page_laporan()` — Menampilkan hasil simulasi dalam format laporan lengkap + tombol download PDF.

### `# DAFTAR HALAMAN`
Dictionary yang memetakan nama menu ke fungsi halaman, agar `main()` bisa memanggil halaman yang aktif.

### `# FUNGSI UTAMA (MAIN)`
`main()` — urutan eksekusi: init session → terapkan CSS → sidebar → tampilkan halaman.

### `# JALANKAN APLIKASI`
`if __name__ == '__main__'` — entry point program.

---

## 🔧 utils.py

### `# IMPORT LIBRARY`
|        Library     |                          Kegunaan                                    |
|--------------------|----------------------------------------------------------------------|
| `pandas`           | Baca Excel, olah data dalam DataFrame                                |
| `matplotlib` (Agg) | Backend grafik (hanya untuk kompatibilitas, tanpa tampilkan jendela) |
| `FPDF`             | Generate laporan PDF                                                 |
| `tempfile`         | Simpan file PDF sementara di folder temporary                        |
| `os`               | Operasi path file                                                    |

### `# KONFIGURASI MAPPING & KOLOM`
`COLUMN_MAPPING` — memperbaiki nama kolom yang typo di dataset.  
`REQUIRED_COLUMNS` — daftar kolom wajib; jika tidak ada, diisi `None`.

### `# FUNGSI: LOAD DATA DARI EXCEL`
`load_data(filepath)` — baca file Excel, rename kolom typo, tambah kolom yang hilang, konversi kolom Date ke datetime.

### `# FUNGSI: HITUNG STATISTIK RINGKASAN`
`get_summary_stats(df)` — menghitung total produk, supplier, penjualan, nilai stok, produk terlaris, stok terendah.

### `# FUNGSI: PENJUALAN PER BULAN`
`get_monthly_sales(df)` — grup penjualan per bulan untuk grafik bar.

### `# FUNGSI: DISTRIBUSI KATEGORI`
`get_category_distribution(df)` — total penjualan per kategori untuk pie chart.

### `# FUNGSI: TABEL PROBABILITAS & INTERVAL`
`compute_probability_table(series)` — hitung frekuensi → probabilitas → prob kumulatif → interval angka acak (contoh: `01-15`, `16-40`, dll) dari data historis penjualan.

### `# FUNGSI: GENERATE BILANGAN ACAK (LCG)`
`lcg_generate(n, a=34, c=11, m=99, z0=37)` — Linear Congruential Generator: rumus `Z = (a*Z + c) mod m` untuk menghasilkan bilangan acak 0–98 sebanyak `n` kali.

### `# KELAS: SIMULASI MONTE CARLO`
`MonteCarloSimulation` — kelas utama yang menjalankan seluruh simulasi.

|            Method           |                        Kegunaan                         |
|-----------------------------|---------------------------------------------------------|
| `__init__`                  | Simpan data produk & supplier yang dipilih              |
| `compute_probability_table` | Hitung tabel probabilitas untuk produk tertentu         |
| `simulate_inventory`        | Proses utama: generate LCG → mapping ke interval → hitung penjualan & sisa stok per hari            |
| `run`                       | Bungkus `simulate_inventory`, kembalikan 3 output utama |
| `run_multiple`              | Jalankan simulasi berkali-kali untuk analisis statistik |

### `# FUNGSI: BUAT LAPORAN PDF`
`generate_pdf_report(...)` — buat file PDF dengan FPDF: judul, tabel probabilitas, tabel hasil simulasi, ringkasan parameter, interpretasi.

### `# FUNGSI: GENERATE INTERPRETASI TEKS`
`generate_interpretation(...)` — buat kalimat naratif otomatis: "Berdasarkan simulasi Monte Carlo untuk produk X selama Y hari, diperoleh estimasi...".
