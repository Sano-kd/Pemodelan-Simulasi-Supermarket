import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO
import time
import os

from utils import (
    load_data, get_summary_stats, get_monthly_sales,
    get_category_distribution,
    MonteCarloSimulation, generate_pdf_report,
    generate_interpretation, lcg_generate
)

st.set_page_config(
    page_title='Monte Carlo - Simulasi Persediaan Supermarket',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

DEFAULT_DATASET = 'dataset_3_supplier_simulasi.xlsx'
LIGHT_BG = '#ffffff'
LIGHT_CARD = '#f8f9fa'
LIGHT_TEXT = '#1a1a2e'
DARK_BG = '#0e1117'
DARK_CARD = '#1e2230'
DARK_TEXT = '#e0e0e0'
PRIMARY = '#1f77b4'
SECONDARY = '#6c757d'
ACCENT = '#2ecc71'


def apply_custom_css(dark_mode):
    if dark_mode:
        bg = DARK_BG; card = DARK_CARD; text = DARK_TEXT; sidebar_bg = '#161a28'
    else:
        bg = LIGHT_BG; card = LIGHT_CARD; text = LIGHT_TEXT; sidebar_bg = '#f0f2f6'

    st.markdown(f'''
    <style>
        .stApp {{ background-color: {bg}; color: {text}; }}
        .main .block-container {{ padding-top: 1.5rem; padding-bottom: 1.5rem; }}
        section[data-testid="stSidebar"] {{ background-color: {sidebar_bg}; }}
        div[data-testid="metric-container"] {{
            background-color: {card}; border-radius: 12px; padding: 16px 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid {PRIMARY};
            margin-bottom: 10px;
        }}
        div[data-testid="metric-container"] > label {{ color: {text} !important; font-size: 0.85rem !important; font-weight: 500; }}
        div[data-testid="metric-container"] > div {{ color: {PRIMARY} !important; font-weight: 700 !important; font-size: 1.5rem !important; }}
        .stDataFrame {{ border: none !important; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .stDataFrame thead tr th {{ background-color: {PRIMARY} !important; color: white !important; font-weight: 600; }}
        h1, h2, h3 {{ color: {PRIMARY} !important; }}
        .card-custom {{
            background-color: {card}; border-radius: 12px; padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 16px;
        }}
        .stProgress > div > div > div {{ background-color: {PRIMARY}; }}
        .stTabs [data-baseweb="tab"] {{ border-radius: 8px 8px 0 0; padding: 8px 20px; font-weight: 500; }}
        .stTabs [aria-selected="true"] {{ background-color: {PRIMARY} !important; color: white !important; }}
        footer {{display: none}}
        #MainMenu {{visibility: hidden}}
    </style>
    ''', unsafe_allow_html=True)


def init_session():
    for key in ['page', 'dark_mode', 'data', 'sim_prob', 'sim_hasil',
                'sim_summary', 'sim_produk', 'sim_supplier', 'sim_days', 'sim_intervals',
                'sim_randoms', 'sim_lcg']:
        if key not in st.session_state:
            if key == 'page': st.session_state[key] = 'Dashboard'
            elif key == 'dark_mode': st.session_state[key] = False
            else: st.session_state[key] = None


def get_text_color():
    return DARK_TEXT if st.session_state.dark_mode else LIGHT_TEXT


def sidebar_nav():
    with st.sidebar:
        st.markdown('## Simulasi MC')
        st.markdown('---')
        menu_items = ['Dashboard', 'Data Produk', 'Simulasi Monte Carlo', 'Laporan']
        for label in menu_items:
            active = st.session_state.page == label
            if st.button(label, key=f'nav_{label}',
                         use_container_width=True,
                         type='primary' if active else 'secondary'):
                st.session_state.page = label
                st.rerun()
        st.markdown('---')
        st.session_state.dark_mode = st.toggle('Dark Mode', value=st.session_state.dark_mode)
        st.markdown('---')
        with st.expander('Dataset'):
            uploaded = st.file_uploader('Upload Excel', type=['xlsx', 'xls'], label_visibility='collapsed')
            if uploaded:
                try:
                    st.session_state.data = load_data(uploaded)
                    st.success('OK')
                except Exception as e:
                    st.error(f'Gagal: {e}')
            if st.button('Reset Dataset'):
                st.session_state.data = None
                st.rerun()


def load_dataset():
    if st.session_state.data is not None:
        return st.session_state.data
    if os.path.exists(DEFAULT_DATASET):
        st.session_state.data = load_data(DEFAULT_DATASET)
        return st.session_state.data
    return None


def page_dashboard():
    df = load_dataset()
    if df is None:
        st.warning('Dataset tidak ditemukan. Upload file Excel di sidebar.')
        return

    stats = get_summary_stats(df)

    st.markdown('#  Dashboard')
    st.markdown('---')

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric('Total Produk', stats['total_products'])
    with col2:
        st.metric('Total Supplier', stats['total_suppliers'])
    with col3:
        st.metric('Total Penjualan', f"{int(stats['total_units_sold']):,}")
    with col4:
        st.metric('Total Nilai Penjualan', f"Rp {int(stats['total_sales_value']):,}")
    with col5:
        st.metric('Total Nilai Persediaan', f"Rp {int(stats['total_stock_value']):,}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="card-custom"><b>🏆 Produk Terlaris:</b> {stats["top_product"]}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="card-custom"><b>⚠️ Stok Terendah:</b> {stats["lowest_stock_product"]}</div>', unsafe_allow_html=True)

    st.markdown('---')
    col1, col2 = st.columns(2)

    with col1:
        monthly = get_monthly_sales(df)
        fig = px.bar(monthly, x='Month', y='UnitsSold', title='Penjualan per Bulan',
                     color_discrete_sequence=[PRIMARY],
                     labels={'Month': 'Bulan', 'UnitsSold': 'Unit Terjual'})
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                          font_color=get_text_color())
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        cat_dist = get_category_distribution(df)
        fig = px.pie(cat_dist, values='TotalUnitsSold', names='Category',
                     title='Distribusi Kategori Produk',
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                          font_color=get_text_color())
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('---')
    fig = px.scatter(df, x='StockQuantity', y='UnitsSold', color='Category',
                     title='Stock Quantity vs Units Sold',
                     labels={'StockQuantity': 'Stok', 'UnitsSold': 'Unit Terjual'},
                     opacity=0.6)
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                      font_color=get_text_color())
    st.plotly_chart(fig, use_container_width=True)


def page_data_produk():
    df = load_dataset()
    if df is None:
        st.warning('Dataset tidak ditemukan.')
        return

    st.markdown('#  Data Produk')
    st.markdown('---')

    display_cols = [c for c in df.columns if c not in ['ProductID', 'LastSoldDate', 'LastRestockDate', 'NextRestockDate', 'DeliveryTimeDays']]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        search = st.text_input('🔍 Search Produk', placeholder='Cari nama produk...')
    with col2:
        cat_filter = st.selectbox('Filter Kategori', ['Semua'] + sorted(df['Category'].unique().tolist()))
    with col3:
        supp_filter = st.selectbox('Filter Supplier', ['Semua'] + sorted(df['Supplier'].unique().tolist()))
    with col4:
        prod_list = ['Semua'] + sorted(df['ProductName'].unique().tolist())
        prod_filter = st.selectbox('Filter Produk', prod_list)

    filtered = df.copy()
    if search:
        filtered = filtered[filtered['ProductName'].str.contains(search, case=False, na=False)]
    if cat_filter != 'Semua':
        filtered = filtered[filtered['Category'] == cat_filter]
    if supp_filter != 'Semua':
        filtered = filtered[filtered['Supplier'] == supp_filter]
    if prod_filter != 'Semua':
        filtered = filtered[filtered['ProductName'] == prod_filter]

    st.markdown(f'<div class="card-custom"><b>Total Baris:</b> {len(filtered):,}</div>', unsafe_allow_html=True)

    display = filtered[display_cols].copy()
    if 'Date' in display.columns:
        display['Date'] = display['Date'].dt.strftime('%Y-%m-%d')
    st.dataframe(display, use_container_width=True, height=500)
    csv_buffer = StringIO()
    filtered.to_csv(csv_buffer, index=False)
    st.download_button('📥 Download CSV', csv_buffer.getvalue(), 'data_produk_filtered.csv', 'text/csv')


def page_simulasi():
    df = load_dataset()
    if df is None:
        st.warning('Dataset tidak ditemukan.')
        return

    st.markdown('# Simulasi Monte Carlo')
    st.markdown('---')

    product_list = sorted(df['ProductName'].unique().tolist())
    col1, col2, col3 = st.columns(3)
    with col1:
        produk = st.selectbox('Pilih Produk', product_list, key='sim_produk_select')
    with col2:
        supp_list = ['Semua Supplier'] + sorted(df[df['ProductName'] == produk]['Supplier'].unique().tolist())
        supplier = st.selectbox('Pilih Supplier', supp_list, key='sim_supplier_select')
    with col3:
        days = st.selectbox('Periode Simulasi (hari)', [10, 30, 60], index=1, key='sim_days_select')

    run = st.button('🚀 Jalankan Simulasi', type='primary', use_container_width=True)

    if run:
        supplier = None if supplier == 'Semua Supplier' else supplier
        prod_data = df[df['ProductName'] == produk]
        if supplier:
            prod_data = prod_data[prod_data['Supplier'] == supplier]
        if len(prod_data) == 0:
            label = f'{produk}' + (f' - {supplier}' if supplier else '')
            st.error(f'Tidak ada data untuk {label}')
            return

        progress = st.progress(0, text='Menyiapkan data...')
        time.sleep(0.2)

        progress.progress(20, text='Menghitung distribusi probabilitas...')

        mc = MonteCarloSimulation(df, produk, supplier)
        prob_df, intervals, rand_nums, hasil_df, summary, lcg_data = mc.simulate_inventory(days)

        progress.progress(60, text='Menyusun hasil...')
        time.sleep(0.3)

        st.session_state.sim_prob = prob_df
        st.session_state.sim_hasil = hasil_df
        st.session_state.sim_summary = summary
        st.session_state.sim_produk = produk
        st.session_state.sim_supplier = supplier
        st.session_state.sim_days = days
        st.session_state.sim_intervals = intervals
        st.session_state.sim_randoms = rand_nums
        st.session_state.sim_lcg = lcg_data

        progress.progress(100, text='Selesai!')
        time.sleep(0.3)
        progress.empty()
        st.balloons()

    if st.session_state.sim_prob is not None:
        prob_df = st.session_state.sim_prob
        hasil_df = st.session_state.sim_hasil
        summary = st.session_state.sim_summary
        produk = st.session_state.sim_produk
        days = st.session_state.sim_days
        lcg_data = st.session_state.sim_lcg

        st.markdown('---')
        st.markdown('## Tahap 1: Distribusi Probabilitas')
        st.dataframe(prob_df, use_container_width=True)

        st.markdown('---')
        st.markdown('## Tahap 2: Generate Bilangan Acak (LCG)')
        lcg_df = pd.DataFrame({
            'Hari': [d['Hari'] for d in lcg_data],
            'Perhitungan': [d['Perhitungan'] for d in lcg_data],
            'Z (LCG)': [d['Z'] for d in lcg_data],
            'Bilangan Acak (0-98)': [d['BilanganAcak'] for d in lcg_data],
        })
        st.dataframe(lcg_df, use_container_width=True)

        st.markdown('---')
        st.markdown('## Tahap 3: Mapping & Simulasi Penjualan')
        map_df = pd.DataFrame({
            'Hari': list(range(1, days + 1)),
            'Bilangan Acak': [d['BilanganAcak'] for d in lcg_data],
            'Interval': [
                next((iv[3] for iv in st.session_state.sim_intervals if iv[0] <= d['BilanganAcak'] <= iv[1]), '-')
                for d in lcg_data
            ],
            'Hasil Penjualan': hasil_df['Penjualan'].tolist(),
        })
        st.dataframe(map_df, use_container_width=True)

        st.markdown('---')
        st.markdown('## Tahap 4: Simulasi Persediaan')
        st.dataframe(hasil_df[['Hari', 'Penjualan', 'Persediaan', 'HargaJual']], use_container_width=True)

        st.markdown('---')
        st.markdown('## Tahap 5: Ringkasan Simulasi')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric('Persediaan Awal', f'{int(summary["PersediaanAwal"]):,} unit')
        with col2:
            st.metric('Total Penjualan', f'{int(summary["TotalPenjualan"]):,} unit')
        with col3:
            st.metric('Sisa Persediaan', f'{int(summary["SisaPersediaan"]):,} unit')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric('Harga Jual per Produk', f'Rp {summary["HargaJualPerProduk"]:,.2f}')
        with col2:
            st.metric('Total Pendapatan', f'Rp {int(summary["TotalPendapatan"]):,}')
        with col3:
            pct = summary['SisaPersediaan'] / summary['PersediaanAwal'] * 100
            st.metric('Sisa Stok vs Awal', f'{pct:.1f}%')
            st.progress(max(0, min(1, pct / 100)))

        st.markdown('---')
        st.markdown('## Visualisasi')

        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(hasil_df, x='Hari', y='Penjualan', markers=True,
                          title='Penjualan per Hari',
                          color_discrete_sequence=[PRIMARY])
            fig.update_traces(line=dict(width=2))
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                              font_color=get_text_color())
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(hasil_df, x='Hari', y='Persediaan', title='Sisa Persediaan per Hari',
                         color='Persediaan', color_continuous_scale='Blues')
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                              font_color=get_text_color())
            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.histogram(hasil_df, x='Penjualan', nbins=12, title='Distribusi Hasil Simulasi',
                               color_discrete_sequence=[PRIMARY])
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                              font_color=get_text_color())
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = go.Figure(data=[go.Table(
                header=dict(values=['Parameter', 'Nilai'], fill_color=PRIMARY, font=dict(color='white')),
                cells=dict(values=[
                    ['Persediaan Awal', 'Total Penjualan', 'Sisa Persediaan', 'Harga Jual/Unit', 'Total Pendapatan'],
                    [f'{int(summary["PersediaanAwal"]):,}',
                     f'{int(summary["TotalPenjualan"]):,}',
                     f'{int(summary["SisaPersediaan"]):,}',
                     f'Rp {summary["HargaJualPerProduk"]:,.2f}',
                     f'Rp {int(summary["TotalPendapatan"]):,}']
                ]))
            ])
            fig.update_layout(title='Ringkasan Parameter', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        csv = StringIO()
        hasil_df.to_csv(csv, index=False)
        st.download_button('📥 Download CSV Hasil', csv.getvalue(),
                           f'mc_{produk}_{days}hari.csv', 'text/csv')

        st.markdown('---')
        st.markdown('## Tahap 6: Laporan')

        if st.button('🔄 Reset Simulasi'):
            for k in ['sim_prob', 'sim_hasil', 'sim_summary', 'sim_produk',
                      'sim_supplier', 'sim_days', 'sim_intervals', 'sim_randoms', 'sim_lcg']:
                st.session_state[k] = None
            st.rerun()


def page_laporan():
    if st.session_state.sim_hasil is None:
        st.warning('Belum ada hasil simulasi. Jalankan simulasi terlebih dahulu.')
        st.info('➡️ Buka menu **Simulasi Monte Carlo**')
        return

    hasil_df = st.session_state.sim_hasil
    summary = st.session_state.sim_summary
    prob_df = st.session_state.sim_prob
    produk = st.session_state.sim_produk
    days = st.session_state.sim_days

    st.markdown('#  Laporan Simulasi')
    st.markdown('---')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric('Produk', produk)
    with col2:
        st.metric('Periode', f'{days} Hari')
    with col3:
        st.metric('Tanggal', pd.Timestamp.now().strftime('%d-%m-%Y'))

    st.markdown('---')
    st.markdown('### Tabel Distribusi Probabilitas')
    st.dataframe(prob_df, use_container_width=True)

    st.markdown('### Tabel Hasil Simulasi')
    st.dataframe(hasil_df, use_container_width=True)

    st.markdown('---')
    st.markdown('### Ringkasan Parameter')
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric('Persediaan Awal', int(summary['PersediaanAwal']))
    with col2:
        st.metric('Total Penjualan', int(summary['TotalPenjualan']))
    with col3:
        st.metric('Sisa Persediaan', int(summary['SisaPersediaan']))
    with col4:
        st.metric('Harga/Unit', f'Rp {summary["HargaJualPerProduk"]:,.0f}')
    with col5:
        st.metric('Total Pendapatan', f'Rp {int(summary["TotalPendapatan"]):,}')

    st.markdown('---')
    st.markdown('### Grafik')
    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(hasil_df, x='Hari', y='Penjualan', markers=True,
                      title='Penjualan per Hari', color_discrete_sequence=[PRIMARY])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(hasil_df, x='Hari', y='Persediaan', title='Sisa Persediaan',
                     color='Persediaan', color_continuous_scale='Blues')
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('---')
    st.markdown('### Interpretasi')
    interp = generate_interpretation(produk, days, summary)
    st.info(interp)

    st.markdown('---')
    csv = StringIO()
    hasil_df.to_csv(csv, index=False)
    st.download_button('📥 Download CSV', csv.getvalue(),
                       f'mc_{produk}_{days}hari.csv', 'text/csv')

    with st.spinner('Membuat PDF...'):
        pdf_path = generate_pdf_report(produk, f'{days} Hari',
                                       summary['HargaJualPerProduk'],
                                       prob_df, hasil_df, summary)
        with open(pdf_path, 'rb') as f:
            st.download_button('📄 Download PDF', f.read(),
                               f'laporan_mc_{produk}.pdf', 'application/pdf')


pages = {
    'Dashboard': page_dashboard,
    'Data Produk': page_data_produk,
    'Simulasi Monte Carlo': page_simulasi,
    'Laporan': page_laporan,
}


def main():
    init_session()
    apply_custom_css(st.session_state.dark_mode)
    sidebar_nav()
    pages.get(st.session_state.page, page_dashboard)()


if __name__ == '__main__':
    main()
