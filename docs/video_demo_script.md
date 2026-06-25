# Script Video Demo & Presentasi

Target durasi: 12–15 menit. Format: presentasi PPT + demo live code.

> Catatan: naskah ini boleh dibaca natural, tidak perlu persis kata per kata. Yang penting alur, istilah, dan poin teknisnya tersampaikan.

---

## 0:00–2:00 — Pembukaan

Pembicara: Fahyi Nashaqi

“Assalamualaikum warahmatullahi wabarakatuh. Selamat pagi/siang, kami dari kelompok Data Lakehouse Indonesia. Anggota kelompok kami adalah saya, Fahyi Nashaqi dengan NRP 5026241171, dan rekan saya Gelar Ridho Ramadhan dengan NRP 5026241045.

Pada video ini, kami akan mempresentasikan final project Data Engineering dengan judul Data Lakehouse Platform untuk analisis demografi dan ekonomi provinsi di Indonesia.

Latar belakang dari project ini adalah data provinsi Indonesia sebenarnya tersedia dari beberapa sumber resmi dan terbuka, seperti Wikidata dan Badan Pusat Statistik. Namun, data tersebut masih tersebar. Wikidata menyediakan metadata provinsi seperti nama, kode ISO, luas wilayah, koordinat, dan ibu kota. Sementara itu, BPS menyediakan data ekonomi dan demografi seperti PDRB dan jumlah penduduk.

Masalahnya, kalau data tersebut masih terpisah, analisis regional menjadi kurang praktis dan sulit direplikasi. Karena itu, kami membangun pipeline data lakehouse yang mengintegrasikan data dari Wikidata dan BPS ke dalam satu arsitektur Bronze, Silver, dan Gold Layer.

Tujuan akhirnya adalah menghasilkan data yang bersih, terstruktur, dan siap digunakan untuk query analitik, seperti analisis PDRB per kapita, tren pertumbuhan ekonomi, populasi, dan ketimpangan antarprovinsi.”

Transisi:

“Selanjutnya saya akan menjelaskan sumber data dan arsitektur lakehouse yang kami gunakan.”

---

## 2:00–5:00 — Arsitektur & Data

Pembicara: Fahyi Nashaqi

“Untuk sumber data, project ini menggunakan dua sumber utama.

Sumber pertama adalah Wikidata SPARQL API. Dari Wikidata, kami mengambil data referensi provinsi Indonesia, seperti nama provinsi, nama dalam bahasa Inggris, kode ISO, luas wilayah, koordinat, ibu kota, dan Wikidata QID. Data ini digunakan sebagai dimensi provinsi pada Gold Layer.

Sumber kedua adalah API Badan Pusat Statistik atau BPS. Dari BPS, kami mengambil data PDRB dan populasi per provinsi untuk periode 2019 sampai 2023. Untuk PDRB, kami menggunakan dua indikator, yaitu PDRB atas dasar harga berlaku dan PDRB atas dasar harga konstan. Untuk populasi, data dari BPS kami konversi dari satuan ribu jiwa menjadi jiwa.

Arsitektur yang kami gunakan adalah Medallion Architecture. Ada tiga layer utama.

Pertama, Bronze Layer. Layer ini menyimpan data mentah dari sumber asli dalam format CSV. Pada tahap ini, data juga diberi metadata ingestion seperti timestamp, nama sumber data, operator ID, manifest JSON, dan checksum.

Kedua, Silver Layer. Di layer ini data dibersihkan dan distandardisasi. Misalnya, tipe data numerik dikonversi, nama provinsi dinormalisasi, dan duplikasi dari Wikidata dibersihkan. Output Silver disimpan dalam format Parquet dan dilengkapi versioning sederhana menggunakan Delta Log.

Ketiga, Gold Layer. Di layer ini data sudah dimodelkan untuk kebutuhan analitik menggunakan star schema. Tabel utamanya adalah fact_economics, yang berisi data PDRB, populasi, dan PDRB per kapita. Tabel fact ini terhubung dengan dim_province, dim_year, dan dim_indicator.

Pada slide ERD Gold Layer, bisa dilihat bahwa fact_economics menjadi pusat analisis. Tabel ini memiliki foreign key ke dim_province dan dim_year. Dengan model seperti ini, query analitik menjadi lebih mudah, misalnya untuk membandingkan PDRB per provinsi, melihat tren per tahun, atau mengelompokkan provinsi berdasarkan wilayah.”

Transisi:

“Setelah memahami arsitekturnya, saya akan masuk ke demo pipeline ETL, mulai dari menjalankan MinIO sampai membangun Gold Layer.”

---

## 5:00–8:00 — Demo ETL Pipeline

Pembicara: Fahyi Nashaqi

“Sekarang kita masuk ke demo ETL pipeline. Pertama, kita pastikan service MinIO berjalan menggunakan Docker Compose.”

Jalankan:

```bash
docker compose up -d
```

“MinIO digunakan sebagai object storage yang menyimpan data di Bronze, Silver, dan Gold Layer. Setelah MinIO aktif, kita jalankan ingestion Wikidata.”

Jalankan:

```bash
python3 src/01_ingestion_wikidata.py
```

“Script ini mengambil data provinsi dari Wikidata SPARQL API. Jika data berhasil diambil, script akan menyimpan file CSV ke Bronze Layer di MinIO. Script ini juga idempotent, jadi kalau data tidak berubah, proses upload akan dilewati agar tidak membuat duplikasi.”

Jalankan:

```bash
python3 src/02_ingestion_bps.py
```

“Berikutnya adalah ingestion BPS. Script ini mengambil data PDRB dan populasi dari API BPS untuk tahun 2019 sampai 2023. Output yang penting diperhatikan adalah jumlah record yang berhasil diambil. Untuk PDRB, pipeline menghasilkan 174 record. Untuk populasi, pipeline menghasilkan 170 record. Ini menunjukkan parser BPS sudah berhasil membaca data API, bukan menghasilkan 0 record.”

Jalankan:

```bash
python3 src/03_silver_transform.py
```

“Setelah Bronze selesai, kita masuk ke Silver Transform. Pada tahap ini data dibersihkan, nama provinsi dinormalisasi, tipe data dikonversi, dan output disimpan sebagai Parquet. Silver Layer juga membuat versioning menggunakan Delta Log.”

Jalankan:

```bash
python3 src/04_gold_transform.py
```

“Terakhir, kita jalankan Gold Transform. Script ini membangun tabel dim_province, dim_year, dim_indicator, dan fact_economics. Dari hasil run, dim_province berisi 38 provinsi aktif, dim_year berisi 5 tahun, dim_indicator berisi 3 indikator, dan fact_economics berisi 174 record. Output ‘All provinces matched successfully’ menunjukkan mapping nama provinsi dari BPS ke Wikidata berhasil.”

Transisi:

“Setelah data masuk ke Gold Layer, selanjutnya rekan saya Gelar akan mendemokan query analitik yang dijalankan di atas data lakehouse ini.”

---

## 8:00–12:00 — Demo Query Analitik

Pembicara: Gelar Ridho Ramadhan

“Terima kasih. Selanjutnya saya akan menjelaskan dan mendemokan query analitik yang digunakan dalam project ini.

Query-query ini dijalankan dari script Python menggunakan DuckDB. Tabel Gold Layer yang sudah berbentuk Parquet akan dibaca, lalu diregistrasikan sebagai tabel DuckDB. Selain itu, semua query juga sudah kami sediakan dalam bentuk file SQL di folder sql, sehingga bisa dijalankan juga melalui DBeaver atau DuckDB client.”

Jalankan:

```bash
python3 src/05_analytics.py
```

“Ada enam query analitik yang kami gunakan.

Query pertama adalah Top 5 Provinces by GDP atau PDRB per Capita. Query ini mencari provinsi dengan PDRB per kapita tertinggi pada tahun terbaru. Dari hasil query, Jakarta berada di posisi teratas. Ini masuk akal karena aktivitas ekonomi nasional sangat terkonsentrasi di wilayah ibu kota.

Query kedua adalah Average GDP by Island Group. Di sini kami mengelompokkan provinsi berdasarkan kelompok pulau seperti Jawa, Sumatera, Kalimantan, Sulawesi, Papua, Maluku, serta Bali dan Nusa Tenggara. Query ini membantu melihat perbandingan ekonomi antarwilayah. Dari hasilnya, Jawa menjadi kelompok dengan rata-rata PDRB yang besar karena memiliki pusat industri, perdagangan, dan populasi yang tinggi.

Query ketiga adalah Year-over-Year GDP Growth Rate untuk provinsi di Jawa. Query ini memakai fungsi window LAG untuk membandingkan PDRB tahun berjalan dengan tahun sebelumnya. Dari hasilnya, terlihat bahwa pada tahun 2020 banyak provinsi mengalami pertumbuhan negatif, yang dapat dikaitkan dengan dampak pandemi. Setelah itu, pertumbuhan kembali positif pada tahun-tahun berikutnya.

Query keempat adalah National Population Trend with Average GDP Per Capita. Query ini menjumlahkan populasi nasional dari data provinsi dan menghitung rata-rata PDRB per kapita per tahun. Dari hasilnya, populasi meningkat dari tahun ke tahun, sedangkan rata-rata PDRB per kapita sempat terdampak pada 2020 lalu meningkat kembali.

Query kelima adalah Provinces Above versus Below National Average GDP Per Capita. Query ini membandingkan setiap provinsi dengan rata-rata nasional. Hasilnya menunjukkan bahwa jumlah provinsi di bawah rata-rata lebih banyak dibandingkan yang di atas rata-rata. Ini menunjukkan adanya ketimpangan ekonomi antarprovinsi.

Query keenam adalah Population Density versus GDP Per Capita. Query ini membandingkan kepadatan penduduk dengan PDRB per kapita. Contohnya, Jakarta memiliki kepadatan penduduk sangat tinggi sekaligus PDRB per kapita tertinggi. Namun, kepadatan tinggi tidak selalu otomatis berarti PDRB per kapita tinggi, sehingga relasi ini perlu dianalisis lebih lanjut.”

Transisi:

“Setelah query utama, saya akan menjelaskan fitur bonus dan pembagian tugas kelompok.”

---

## 12:00–14:00 — Bonus, Pembagian Tugas, Closing

Pembicara: Fahyi Nashaqi

“Selain pipeline utama, project ini juga memiliki beberapa fitur tambahan.

Pertama adalah custom metadata. Pada proses ingestion, setiap data yang masuk ke Bronze Layer diberi metadata seperti ingestion timestamp, source name, operator ID, serta manifest JSON. Ini berguna untuk audit dan tracking asal data.

Kedua adalah idempotency menggunakan checksum. Setiap dataframe dihitung checksum MD5-nya. Jika data terbaru sama dengan data sebelumnya, pipeline tidak akan mengupload ulang data tersebut. Dengan begitu, pipeline aman dijalankan berkali-kali tanpa menghasilkan duplikasi yang tidak perlu.

Ketiga adalah versioning di Silver Layer. Setiap kali data Silver ditulis, pipeline membuat Delta Log sederhana yang menyimpan informasi versi, timestamp, schema, jumlah record, dan checksum. Ini membantu melacak perubahan data antar-run.

Keempat adalah perbandingan format CSV dan Parquet. Dari script bonus comparison, terlihat bahwa Parquet lebih efisien dari sisi ukuran file dan lebih cocok untuk analisis karena formatnya columnar.

Kelima adalah query explanation menggunakan DuckDB. Script bonus explain menampilkan query plan dan menunjukkan bagaimana engine melakukan filter dan projection sedekat mungkin dengan data yang dibutuhkan.

Untuk pembagian tugas, Fahyi mengerjakan bagian ingestion Wikidata dan BPS, termasuk perbaikan parser API, metadata ingestion, idempotency, serta query 1 sampai 3 dan demo ingestion.

Saya, Gelar, mengerjakan bagian transformasi Silver dan Gold, desain star schema, quality checks, query 4 sampai 6, dokumentasi, dan presentasi.

Sebagai penutup, project ini berhasil mengintegrasikan data provinsi Indonesia dari Wikidata dan BPS menjadi data lakehouse yang analytics-ready. Data mentah masuk ke Bronze, dibersihkan di Silver, dimodelkan di Gold, lalu dianalisis menggunakan DuckDB.

Demikian presentasi dan demo dari kelompok kami. Terima kasih.”

---

## Catatan Penting Saat Rekaman

- Jika memakai DBeaver, gunakan file `.sql` di folder `sql/`.
- Jika memakai Python, `src/05_analytics.py` sudah mengeksekusi SQL yang sama.
- Saat demo MinIO, buka `http://localhost:9001` dan tunjukkan bucket/prefix `bronze/`, `silver/`, dan `gold/`.
- BPS 2023 memiliki nilai populasi kosong untuk empat DOB Papua baru pada endpoint yang digunakan:
  - Papua Barat Daya
  - Papua Selatan
  - Papua Tengah
  - Papua Pegunungan

