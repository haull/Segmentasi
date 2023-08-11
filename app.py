from flask import Flask, render_template, request, redirect, url_for
import os
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import numpy as np
os.environ["OMP_NUM_THREADS"] = '1'
import scipy.stats as stats

# Set tampilan desimal menjadi 6 digit
pd.set_option('display.float_format', '{:.6f}'.format)

app = Flask(__name__)
# Set folder untuk menyimpan file yang diunggah (misalnya di folder uploads)
app.config['UPLOAD_FOLDER'] = 'uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Variabel global untuk menyimpan DataFrame setelah proses cleaning
df1 = None
df2 = None
recency_df = None
frequency_df = None
monetary_df = None
menu_member = None
common_menu = None
df_seleksi = None
df_seleksi2 = None
data_uploaded = False
data_cleaned = False
integrated_data1 = None
integrated_data2 = None
scaled = None
merged_result_table = None
clustering_result = None

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    global df1, df2, data_uploaded
    if request.method == 'POST':
        # Periksa apakah file-file sudah diunggah oleh pengguna
        if 'file1' not in request.files or 'file2' not in request.files:
            return redirect(request.url)

        file1 = request.files['file1']
        file2 = request.files['file2']
        
        # Periksa apakah file-file yang diunggah kosong
        if file1.filename == '' or file2.filename == '':
            return redirect(request.url)

        # Periksa apakah file-file memiliki ekstensi xlsx
        if file1 and file1.filename.endswith('.xlsx') and file2 and file2.filename.endswith('.xlsx'):
            # Simpan file-file di folder uploads
            file1.save(os.path.join(app.config['UPLOAD_FOLDER'], file1.filename))
            file2.save(os.path.join(app.config['UPLOAD_FOLDER'], file2.filename))
            
            # Baca file-file sebagai DataFrame pandas
            df1 = pd.read_excel(os.path.join(app.config['UPLOAD_FOLDER'], file1.filename))
            df2 = pd.read_excel(os.path.join(app.config['UPLOAD_FOLDER'], file2.filename))

            data_uploaded = True
            # Redirect ke endpoint cleaning dengan menyertakan nama file yang diunggah sebagai parameter
            return redirect(url_for('read', filename1=file1.filename, filename2=file2.filename))
        else:
            return 'Hanya file dengan ekstensi .xlsx yang diizinkan.'

    return render_template('upload.html', data_uploaded=data_uploaded)

def calculate_common_menu(dataframe):
    produk = dataframe[['ID Member', 'Deskripsi Produk', 'Jumlah Barang']]
    common_menu = produk.copy()
    common_menu['Total'] = common_menu.groupby(['Deskripsi Produk', 'ID Member'])['Jumlah Barang'].transform('sum')
    idx = common_menu.groupby('ID Member')['Total'].idxmax()
    common_by_member = common_menu.loc[idx, ['ID Member', 'Deskripsi Produk']]
    return common_by_member

@app.route('/read')
def read():
    global df1, df2, data_uploaded
    # Periksa apakah DataFrame df1 dan df2 sudah berhasil diupload
    if df1 is not None and df2 is not None:
        data_uploaded = True
        # Ubah DataFrame menjadi bentuk HTML dan kirimkan ke template
        df1_html = df1.head().to_html(classes="table table-bordered")
        df2_html = df2.head().to_html(classes="table table-bordered")
        dimensi1 = df1.shape
        dimensi2 = df2.shape
        return render_template('read.html', df1_html=df1_html, df2_html=df2_html, dimensi1 = dimensi1, dimensi2 = dimensi2)
    else:
        return 'Tidak ada data yang diunggah atau belum dilakukan proses pembacaan data.'
  
@app.route('/select_attributes')
def select_attributes():
    global df1, df2, df_seleksi, data_uploaded, df_seleksi2

    # Check if data has been loaded through the 'read' function
    # Check if data has not been loaded through the 'read' function
    if data_uploaded:
        # Continue with data processing and attribute selection
        if df1 is not None and df2 is not None:
            df_seleksi = df1.copy()
            seleksi2 = df2.copy()
            data_uploaded = True
            # Lakukan proses pembersihan data sesuai dengan kebutuhan
            # Mengubah format tanggal menjadi date
            df_seleksi['Tanggal'] = pd.to_datetime(df_seleksi['Tanggal'], format='%Y-%m-%d', errors='coerce')

            # Menampilkan data yang hanya pada periode promosi terakhir yaitu Juli-Desember 2022
            start_date = '2022-07-01'
            end_date = '2022-12-30'
            df_seleksi = df_seleksi.loc[(df_seleksi['Tanggal'] >= start_date) & (df_seleksi['Tanggal'] <= end_date)]
            # Menghapus row yang bukan member
            df_seleksi = df_seleksi.drop(df_seleksi[df_seleksi['ID Member'] == 0].index)
            df_seleksi = df_seleksi.drop(df_seleksi[df_seleksi['Jumlah dibatalkan'] == 1].index)
            to_drop = ['No Faktur', 'Nama Outlet', 'Nama Kasir', 'Jam', 'Harga Per Barang', 'Diskon Per Barang', 'Diskon Transaksi', 'Pajak', 'Subtotal', 'Status', 'Metode Pembayaran', 'Tipe Diskon Transaksi', 'Jumlah dibatalkan', 'Tipe Diskon Per Barang']
            df_seleksi = df_seleksi.drop(to_drop, axis=1)
            if df_seleksi is not None and seleksi2 is not None:
                
                selected = df_seleksi.head(10).copy()
                df_seleksi2 = seleksi2.head(10).copy()
                dimensi3 = df_seleksi.shape
                dimensi4 = seleksi2.shape
            else:
                selected = None
        else:
            selected = None
            error_message = "Tidak ada data yang dipilih atau belum dilakukan pemilihan atribut."
            return render_template('error.html', error_message=error_message)

        return render_template('selected_results.html', selected=selected, df_seleksi2 = df_seleksi2, dimensi3 = dimensi3, dimensi4 = dimensi4)
    else:
        # If data is not loaded, redirect to the 'read' page to upload files
        return redirect(url_for('read'))
    
@app.route('/cleaning')
def cleaning():
    global df_seleksi, df2

    if df_seleksi is not None and df2 is not None:
        
        periksa1 = df_seleksi.isnull().sum()
        periksa2 = df2.isnull().sum()

        periksa1_table = df_seleksi.isnull().sum().head().to_frame().to_html(classes="table table-bordered table-sm table-left-align", header=False)
        periksa2_table = df2.isnull().sum().head().to_frame().to_html(classes="table table-bordered table-sm table-left-align", header=False)


        return render_template('cleaning.html', periksa1_table=periksa1_table, periksa2_table=periksa2_table,)
    else:
        return 'Tidak ada data yang diunggah atau belum dilakukan pembersihan data.'
     
    # Simpan hasil pembersihan data dalam variabel cleaning_result
    # cleaning_result = rfm.head(5).to_html(classes="table table-bordered")
        # cleaning_result = "Tidak ada data yang diunggah atau belum dilakukan pembersihan data."
    
    # return render_template('cleaning.html', cleaning_result=cleaning_result)

@app.route('/build')
def build_data():
    global df_seleksi, common_menu,recency_df, frequency_df, monetary_df, menu_member  # Gunakan variabel global rfm
    # Ambil nama file dari parameter URL
    if df_seleksi is not None:
        # Calculate common_menu data
        common_menu = calculate_common_menu(df_seleksi)
        #pembangunan recency
        # mengetahui tanggal terakhir pada dataset
        maks_tgl = df_seleksi['Tanggal'].max()
        recency_df = df_seleksi.groupby(['ID Member'],as_index=False)['Tanggal'].max()
        recency_df.columns = ['ID Member','LastPurchaseDate']

        #calculate how often he is purchasing with reference to latest date in days..

        recency_df['Recency'] = recency_df.LastPurchaseDate.apply(lambda x : (maks_tgl - x).days)
        recency_df.drop(columns=['LastPurchaseDate'],inplace=True)

        #check frequency of customer means how many transaction has been done..

        frequency_df = df_seleksi.copy()
        frequency_df.drop_duplicates(subset=['ID Member','Jumlah Barang'], keep="first", inplace=True) 
        frequency_df = frequency_df.groupby('ID Member',as_index=False)['Jumlah Barang'].sum()
        frequency_df.columns = ['ID Member','Frequency']
        
        #check summed up spend of a customer with respect to latest date..

        monetary_df=df_seleksi.groupby('ID Member',as_index=False)['Jumlah Harga'].sum()
        monetary_df.columns = ['ID Member','Monetary']

        monetary_df = df_seleksi.groupby('ID Member')['Jumlah Harga'].sum().reset_index()
        # Rename the 'Amount' column to 'Monetary'
        monetary_df = monetary_df.rename(columns={'Jumlah Harga': 'Monetary'})

        #Combine all together all dataframe in so we have recency, frequency and monetary values together..

        #combine first recency and frequency..
        
        if recency_df is not None and frequency_df is not None and monetary_df is not None:
            recency_df = recency_df.head(5).copy()  # Ambil 5 data pertama untuk contoh
            frequency_df = frequency_df.head(5).copy()
            monetary_df = monetary_df.head(5).copy()
            menu_member = common_menu.head(5).copy()
    else:
        error_message = "Tidak ada data yang dipilih atau belum dilakukan pemilihan atribut."
        return render_template('error.html', error_message=error_message)

    return render_template('build_results.html', recency_df=recency_df, frequency_df = frequency_df, monetary_df = monetary_df, menu_member = menu_member)

@app.route('/integration')
def integration():
    global recency_df, frequency_df, monetary_df, common_menu, df_seleksi2, menu_member, integrated_data1, integrated_data2

    # Pastikan data sudah tersedia sebelum melakukan integrasi
    if recency_df is not None and frequency_df is not None and monetary_df is not None and menu_member is not None and df_seleksi2 is not None:
        # Gabungkan recency_df, frequency_df, dan monetary_df berdasarkan kolom 'ID Member'
        integrated_data1 = pd.merge(recency_df, frequency_df, on='ID Member')
        integrated_data1 = pd.merge(integrated_data1, monetary_df, on='ID Member')

        # Gabungkan common_menu dengan df_seleksi2 berdasarkan kolom 'ID Member'
        integrated_data2 = pd.merge(menu_member, df_seleksi2, on='ID Member')
        integrated_data1.head(5).copy()
        integrated_data2.head(5).copy()
        return render_template('integration_results.html', integrated_data1=integrated_data1, integrated_data2=integrated_data2)
    else:
        error_message = "Data belum lengkap. Lakukan pemrosesan sebelum melakukan integrasi."
        return render_template('error.html', error_message=error_message)

@app.route('/transformation')
def transformation():
    global integrated_data1, scaled
    
    if integrated_data1 is not None:
        # Normalisasi dengan Z-Score
        rfm = integrated_data1.copy()
        # Membuat DataFrame baru dengan memilih kolom tertentu
        scaled = (rfm - rfm.mean()) / rfm.std(ddof=0)
        
        return render_template('transformation_results.html', scaled=scaled)
    else:
        error_message = "Data belum tersedia. Lakukan pemrosesan sebelum melakukan transformasi."
        return render_template('error.html', error_message=error_message)


@app.route('/clustering', methods=['GET', 'POST'])
def clustering():
    global scaled,integrated_data1, integrated_data2,clustering_result,merged_result_table,cluster_means  # Gunakan variabel global df1
    if scaled is not None:
        integrated_data1.copy()
        integrated_data2.copy()
        # Initiating the KMeans Clustering model 
        kmeans = KMeans(n_clusters=3)
        # fit model and predict clusters
        integrated_data1["Clusters"] = kmeans.fit_predict(scaled)
        integrated_data1['Clusters'] = integrated_data1['Clusters'].astype(int)
        # Simpan hasil clustering dalam variabel clustering_result
        # Simpan hasil clustering dalam variabel clustering_result
        # Assuming rfm DataFrame contains the 'Clusters' attribute as a string data type
            
        clustering_result = integrated_data1.head(10)
        # Merge common_menu and rfm based on 'ID Member'
        karakteristik = pd.merge(integrated_data2, integrated_data1, on='ID Member', how='inner')
        # Simpan hasil merge dalam variabel merged_result

        # Hitung nilai rata-rata Recency, Frequency, dan Monetary untuk setiap cluster
        cluster_means = karakteristik.groupby('Clusters').mean()[['Recency', 'Frequency', 'Monetary']]

        # Tentukan kriteria untuk masing-masing label pada setiap kolom
        score = cluster_means['Frequency'] + cluster_means['Monetary'] - cluster_means['Recency']

        # Berikan label pada setiap cluster berdasarkan kriteria
        cluster_labels = []
        for cluster in cluster_means.index:
            recency = cluster_means.loc[cluster, 'Recency']
            frequency = cluster_means.loc[cluster, 'Frequency']
            monetary = cluster_means.loc[cluster, 'Monetary']
                
            if score.loc[cluster] == score.max():
                cluster_labels.append('Tinggi')
            elif score.loc[cluster] == score.min():
                cluster_labels.append('Rendah')
            else:
                cluster_labels.append('Sedang')

        # Tambahkan kolom label ke dalam dataframe hasil clustering
        karakteristik['Loyalitas'] = karakteristik['Clusters'].map(dict(zip(cluster_means.index, cluster_labels)))

        final_karaktertistik = karakteristik.copy()
        # Tampilkan hasil label untuk setiap cluster
        merged_result_table = final_karaktertistik.head(10)
        return render_template('clustering_results.html', clustering_result=clustering_result, merged_result_table=merged_result_table)
    else:
        return 'Tidak ada data yang diunggah atau belum dilakukan pembersihan data.'

@app.route('/loyalty_promo')
def loyalty_promo():
    global merged_result_table

    # Inisialisasi dictionary untuk menyimpan rekomendasi promosi untuk setiap cluster
    promotions_by_cluster = {}
    member_data = merged_result_table.copy()
    for index, row in member_data.iterrows():
        # Mendapatkan nilai rata-rata Recency, Frequency, dan Monetary untuk cluster ini
        recency = row['Recency']
        frequency = row['Frequency']
        monetary = row['Monetary']
        cluster = row['Loyalitas']

        # Rekomendasi promosi untuk masing-masing cluster berdasarkan nilai Recency, Frequency, dan Monetary
        if cluster == 'Tinggi':
            promotion = f"Berikan reward yang spesial untuk kelompok ini. Seperti potongan harga spesial untuk menu yang cenderung dibeli mereka yaitu Gula Aren Original, Lemon Tea Ice, Indomie Rebus Regular, Long Black, dan V-60 Japstyle."
        elif cluster == 'Sedang':
            promotion = f"Berikan promosi yang dapat meningkatkan nilai frequency, dan recency. Seperti promosi beli satu gratis satu untuk menu-menu favorit mereka yaitu Vietnam Drip Hot, Vanilla Milk Ice, Indomie Rebus Regular, Shake Presso Original, dan V-60 Japstyle."
        elif cluster == 'Rendah':
            promotion = f"Berikan promosi yang dapat menarik perhatian kelompok ini agar lebih sering mengunjungi tovi kohi. Seperti memberikan promosi penukaran kupon untuk setiap pembelian menu yang cenderung dibeli yaitu Lemon Tea Ice, V-60 Original, Americano Hot, Americano Ice, dan Dragon Tea."
        else:
            promotion = "Tidak ada rekomendasi promosi untuk cluster ini."

        # Simpan rekomendasi dalam dictionary dengan nama cluster sebagai kunci
        promotions_by_cluster[cluster] = promotion

    return render_template('recommendation_results.html', promotions_by_cluster=promotions_by_cluster)



def recommend_low_loyalty_promotions(clustering_result, merged_result_table):
    # Dictionary untuk menyimpan rekomendasi untuk setiap pelanggan
    recommendations = {}
    merged_result_table.copy()
    clustering_result.copy()
    # Filter data hanya untuk pelanggan dengan nilai loyalitas "Rendah"
    low_loyalty_customers = merged_result_table[merged_result_table['Loyalitas'] == 'Rendah']
    
    for index, row in merged_result_table.iterrows():
        # Cek apakah pelanggan memiliki item favorit yang sering dibeli
        favorite_menu = row['Deskripsi Produk']
        if favorite_menu:
            recommendation = f"Promo eksklusif untuk Anda! Dapatkan diskon 20% untuk {favorite_menu} pada pembelian berikutnya. Tunjukkan Pesan ini ke kasir untuk claim promosi"
        else:
            # Jika tidak ada item favorit, berikan kampanye "Selamat Datang Kembali"
            recommendation = "Kami merindukan Anda! Aktifkan kembali minat Anda dengan diskon 15% untuk pembelian berikutnya. Tunjukkan Pesan ini ke kasir untuk claim promosi"
        
        # Simpan rekomendasi dalam dictionary dengan ID Member sebagai kunci
        recommendations[row['ID Member']] = recommendation
    
    return recommendations

# Function to recommend promotions for medium loyalty customers
def recommend_medium_loyalty_promotions(merged_result_table,clustering_result ):
    recommendations = []
    merged_result_table.copy()
    clustering_result.copy()
    for index, row in merged_result_table.iterrows():
        customer_id = row['ID Member']
        customer_name = row['Nama']
        favorite_items = row['Deskripsi Produk']
        
        # Recommendation 1: Offer a discount on their next purchase based on their average monetary value
        discount_percentage = int(row['Monetary'] * 0.1)  # 10% discount based on average monetary value
        promotion1 = f"Halo {customer_name}, Selamat mendapatkan {discount_percentage}% diskon pada pembelian berikutnya. Gunakan Kode 'LOYAL10' saat membayar di kasir. Ayo ke Tovi Kohi Sekarang Juga!"
        recommendations.append(promotion1)
        
        # Recommendation 2: Send a personalized offer for their most frequent item
        most_frequent_item = row['Deskripsi Produk'].split(',')[0]  # Assuming items are separated by comma
        promotion2 = f"Halo {customer_name}, Kami memiliki penawaran khusus hanya untuk Anda! Dapatkan diskon 20% untuk menu {most_frequent_item}. Gunakan Kode 'FREQ20' dan manjakan diri Anda dengan menu favorit Anda!"
        recommendations.append(promotion2)
    
    return recommendations

# Function to recommend promotions for high loyalty customers
def recommend_high_loyalty_promotions(merged_result_table,clustering_result):
    recommendations = []
    merged_result_table.copy()
    clustering_result.copy()
    for index, row in merged_result_table.iterrows():
        customer_id = row['ID Member']
        customer_name = row['Nama']
        favorite_items = row['Deskripsi Produk']
        
        # Recommendation 1: Offer a personalized discount on their next purchase based on their average monetary value
        discount_percentage = int(row['Monetary'] * 0.15)  # 15% discount based on average monetary value
        promotion1 = f"Halo {customer_name}, sebagai member Kami yang berharga, kami senang untuk menawarkan Anda {discount_percentage}% diskon pada pembelian berikutnya. Gunakan kode 'LOYAL15' saat membayar di kasir. Belanja sekarang dan nikmati diskon eksklusif!"
        recommendations.append(promotion1)
        
        # Recommendation 2: Invite them to a special loyalty event with their favorite items
        promotion2 = f"Pelanggan yang terhormat {customer_name}, Anda diundang ke tempat kami. Nikmati malam yang menyenangkan dengan potongan 50% menu favorit Anda: {favorite_items}. Jangan lewatkan promosi spesial ini! Tunjukkan Pesan ini ke kasir untuk claim promosi."
        recommendations.append(promotion2)
    
    return recommendations

@app.route('/promotion_recommendations')
def promotion_recommendations():
    # Assume you have the DataFrame for each loyalty cluster (low_loyalty_customers, medium_loyalty_customers, high_loyalty_customers)
    # You can pass these DataFrames to the respective promotion recommendation functions

    # Get promotion recommendations for low loyalty customers
    low_loyalty_promotions = recommend_low_loyalty_promotions(merged_result_table,clustering_result)

    # Get promotion recommendations for medium loyalty customers
    medium_loyalty_promotions = recommend_medium_loyalty_promotions(merged_result_table,clustering_result)

    # Get promotion recommendations for high loyalty customers
    high_loyalty_promotions = recommend_high_loyalty_promotions(merged_result_table,clustering_result)

    return render_template('recommendation_results.html',
                           low_loyalty_promotions=low_loyalty_promotions,
                           medium_loyalty_promotions=medium_loyalty_promotions,
                           high_loyalty_promotions=high_loyalty_promotions)


if __name__ == '__main__':
    app.run(debug=True)
