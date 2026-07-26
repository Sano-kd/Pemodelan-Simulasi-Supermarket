# ==============================
# IMPORT LIBRARY
# ==============================
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from fpdf import FPDF
import tempfile
import os

# ==============================
# KONFIGURASI MAPPING & KOLOM
# ==============================
COLUMN_MAPPING = {'Reorderevel': 'ReorderLevel', ', ': 'SalesValue'}
REQUIRED_COLUMNS = [
    'Date', 'ProductID', 'ProductName', 'Category', 'Supplier',
    'UnitPrice', 'StockQuantity', 'StockValue', 'ReorderLevel',
    'ReorderQuantity', 'UnitsSold', 'SalesValue', 'LastSoldDate',
    'LastRestockDate', 'NextRestockDate', 'DeliveryTimeDays', 'DeliveryStatus'
]

# ==============================
# FUNGSI: LOAD DATA DARI EXCEL
# ==============================
def load_data(filepath):
    df = pd.read_excel(filepath)
    df.rename(columns=COLUMN_MAPPING, inplace=True)
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df['Date'] = pd.to_datetime(df['Date'])
    return df


# ==============================
# FUNGSI: HITUNG STATISTIK RINGKASAN
# ==============================
def get_summary_stats(df):
    return {
        'total_products': df['ProductName'].nunique(),
        'total_suppliers': df['Supplier'].nunique(),
        'total_sales_value': df['SalesValue'].sum(),
        'total_stock_value': df['StockValue'].sum(),
        'total_units_sold': df['UnitsSold'].sum(),
        'top_product': df.groupby('ProductName')['UnitsSold'].sum().idxmax(),
        'lowest_stock_product': df.loc[df['StockQuantity'].idxmin(), 'ProductName'],
    }

# ==============================
# FUNGSI: PENJUALAN PER BULAN
# ==============================
def get_monthly_sales(df):
    df_month = df.copy()
    df_month['Month'] = df_month['Date'].dt.to_period('M').astype(str)
    return df_month.groupby('Month')['UnitsSold'].sum().reset_index()


# ==============================
# FUNGSI: DISTRIBUSI KATEGORI
# ==============================
def get_category_distribution(df):
    cat_dist = df.groupby('Category')['UnitsSold'].sum().reset_index()
    cat_dist.columns = ['Category', 'TotalUnitsSold']
    return cat_dist

# ==============================
# FUNGSI: TABEL PROBABILITAS & INTERVAL
# ==============================
def compute_probability_table(series):
    freq = series.value_counts().sort_index()
    total = len(series)
    prob = freq / total
    cum_prob = prob.cumsum()

    intervals = []
    prev_cum = 0.0
    for val, cp in cum_prob.items():
        lower = round(prev_cum * 100) + 1
        upper = round(cp * 100)
        interval_str = f'{lower:02d}' if lower == upper else f'{lower:02d}-{upper:02d}'
        intervals.append((lower, upper, int(val), interval_str))
        prev_cum = cp

    prob_df = pd.DataFrame({
        'Penjualan': freq.index,
        'Frekuensi': freq.values,
        'Probabilitas': prob.values,
        'ProbKumulatif': cum_prob.values,
        'IntervalAcak': [iv[3] for iv in intervals],
    }).reset_index(drop=True)

    return prob_df, intervals


# ==============================
# FUNGSI: GENERATE BILANGAN ACAK (LCG)
# ==============================
def lcg_generate(n, a=34, c=11, m=99, z0=37):
    z = z0
    results = []
    for _ in range(n):
        z_prev = z
        z = (a * z + c) % m
        calc = f'({a}\u00d7{z_prev}+{c}) mod {m} = {z}'
        results.append({
            'Hari': len(results) + 1,
            'Perhitungan': calc,
            'Z': z,
            'BilanganAcak': z,
        })
    return results


# ==============================
# KELAS: SIMULASI MONTE CARLO
# ==============================
class MonteCarloSimulation:
    def __init__(self, df, product_name, supplier_name=None):
        self.product_name = product_name
        self.supplier_name = supplier_name
        mask = df['ProductName'] == product_name
        if supplier_name:
            mask &= (df['Supplier'] == supplier_name)
        self.product_data = df[mask].copy()
        if len(self.product_data) == 0:
            raise ValueError(f'Tidak ada data untuk produk "{product_name}"' + (f' dengan supplier "{supplier_name}"' if supplier_name else ''))
        self.product_info = self.product_data.iloc[0]

    # ==============================
    # FUNGSI DALAM KELAS: TABEL PROBABILITAS
    # ==============================
    def compute_probability_table(self):
        return compute_probability_table(self.product_data['UnitsSold'])

    # ==============================
    # FUNGSI DALAM KELAS: SIMULASI PERSEDIAAN
    # ==============================
    def simulate_inventory(self, days):
        prob_df, intervals = self.compute_probability_table()

        lcg_data = lcg_generate(days)
        random_numbers = [d['BilanganAcak'] for d in lcg_data]

        simulated_demand = []
        for rn in random_numbers:
            matched = False
            for lower, upper, val, _ in intervals:
                if lower <= rn <= upper:
                    simulated_demand.append(val)
                    matched = True
                    break
            if not matched:
                simulated_demand.append(int(prob_df['Penjualan'].iloc[-1]))

        initial_stock = int(self.product_data['StockQuantity'].sum())
        unit_price = float(self.product_info['UnitPrice'])

        records = []
        current_stock = initial_stock
        for day in range(1, days + 1):
            d = simulated_demand[day - 1]
            current_stock -= d
            records.append({
                'Hari': day,
                'BilanganAcak': random_numbers[day - 1],
                'Penjualan': d,
                'Persediaan': current_stock,
                'HargaJual': round(d * unit_price, 2),
            })

        hasil_df = pd.DataFrame(records)
        total_penjualan = int(hasil_df['Penjualan'].sum())
        sisa_persediaan = int(initial_stock - total_penjualan)
        total_pendapatan = round(float(hasil_df['HargaJual'].sum()), 2)

        summary = {
            'PersediaanAwal': initial_stock,
            'TotalPenjualan': total_penjualan,
            'SisaPersediaan': sisa_persediaan,
            'HargaJualPerProduk': unit_price,
            'TotalPendapatan': total_pendapatan,
        }

        return prob_df, intervals, random_numbers, hasil_df, summary, lcg_data

    # ==============================
    # FUNGSI DALAM KELAS: JALANKAN SIMULASI
    # ==============================
    def run(self, days):
        prob_df, intervals, rand_nums, hasil_df, summary, lcg_data = self.simulate_inventory(days)
        return prob_df, hasil_df, summary

    # ==============================
    # FUNGSI DALAM KELAS: SIMULASI BERULANG
    # ==============================
    def run_multiple(self, days, n_simulations):
        results = []
        for _ in range(n_simulations):
            _, _, summary = self.run(days)
            results.append(summary)
        return pd.DataFrame(results)


# ==============================
# FUNGSI: BUAT LAPORAN PDF
# ==============================
def generate_pdf_report(product_name, periode, unit_price, prob_df, hasil_df, summary):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 12, 'Laporan Simulasi Monte Carlo', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.ln(4)

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(52, 73, 94)
    pdf.cell(0, 7, f'Produk: {product_name}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 7, f'Periode: {periode}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 7, f'Harga per Unit: Rp {unit_price:,.2f}', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 9, '1. Distribusi Probabilitas', new_x='LMARGIN', new_y='NEXT')

    cols_p = list(prob_df.columns)
    col_w = max(14, int(180 / len(cols_p)))
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_fill_color(41, 128, 185)
    pdf.set_text_color(255, 255, 255)
    for c in cols_p:
        pdf.cell(col_w, 6, c[:12], border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(52, 73, 94)
    for _, row in prob_df.iterrows():
        for c in cols_p:
            pdf.cell(col_w, 5, str(row[c])[:12], border=1, align='C')
        pdf.ln()
    pdf.ln(3)

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 9, '2. Hasil Simulasi', new_x='LMARGIN', new_y='NEXT')

    cols_h = list(hasil_df.columns)
    col_w = max(16, int(180 / len(cols_h)))
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_fill_color(41, 128, 185)
    pdf.set_text_color(255, 255, 255)
    for c in cols_h:
        pdf.cell(col_w, 6, c[:12], border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(52, 73, 94)
    for _, row in hasil_df.iterrows():
        for c in cols_h:
            pdf.cell(col_w, 5, str(row[c])[:12], border=1, align='C')
        pdf.ln()
    pdf.ln(3)

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 9, '3. Ringkasan Parameter', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(52, 73, 94)
    labels = {
        'PersediaanAwal': 'Persediaan Awal',
        'TotalPenjualan': 'Total Penjualan',
        'SisaPersediaan': 'Sisa Persediaan',
        'HargaJualPerProduk': 'Harga Jual per Produk',
        'TotalPendapatan': 'Total Pendapatan',
    }
    for k, v in summary.items():
        pdf.cell(0, 7, f'{labels.get(k, k)}: {v}', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(5)

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 9, '4. Interpretasi', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(52, 73, 94)
    pdf.multi_cell(0, 7, generate_interpretation(product_name, periode, summary))

    pdf_path = os.path.join(tempfile.gettempdir(), f'mc_report_{product_name.replace(" ", "_")}.pdf')
    pdf.output(pdf_path)
    return pdf_path


# ==============================
# FUNGSI: GENERATE INTERPRETASI TEKS
# ==============================
def generate_interpretation(product_name, days, summary):
    if isinstance(days, str):
        day_str = days
        n_days = int(''.join(filter(str.isdigit, days.split()[0]))) if any(c.isdigit() for c in days) else 30
    else:
        n_days = int(days)
        day_str = f'{n_days} Hari'
    avg = summary["TotalPenjualan"] / n_days
    return (
        f'Berdasarkan simulasi Monte Carlo untuk produk {product_name} '
        f'selama {day_str}, diperoleh estimasi total permintaan sebanyak '
        f'{int(summary["TotalPenjualan"])} unit dengan rata-rata '
        f'{avg:.2f} '
        f'unit per hari. Persediaan awal {int(summary["PersediaanAwal"]):,} unit, '
        f'sisa persediaan {int(summary["SisaPersediaan"]):,} unit. '
        f'Total pendapatan Rp {int(summary["TotalPendapatan"]):,} '
        f'dengan harga jual Rp {summary["HargaJualPerProduk"]:,.2f} per unit.'
    )
