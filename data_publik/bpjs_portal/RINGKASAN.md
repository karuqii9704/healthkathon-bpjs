# Data Publik Portal BPJS Kesehatan

Diambil 2026-10-10 dari https://data.bpjs-kesehatan.go.id/bpjs-portal/action/dash-publik.cbi?page=1 (dashboard Tableau publik dan publikasi).

## Kepesertaan JKN per segmen (rekap 30 September 2026)

| Segmen | Jumlah peserta | Porsi |
|---|---:|---:|
| PBI APBN | 115,499,151 | 40.8% |
| PBI APBD | 61,592,653 | 21.8% |
| PPU - PN | 21,351,422 | 7.5% |
| PPU - BU | 47,024,587 | 16.6% |
| PBPU - Pekerja Mandiri | 32,040,621 | 11.3% |
| Bukan Pekerja | 5,315,733 | 1.9% |
| **Total** | **282,824,167** | 100% |

### Relevansi untuk PayRay

- Segmen sasaran PayRay, **PPU – Badan Usaha: 47,024,587 peserta (16.6%)**. Total PPU (PN + BU) 68,376,009 (24.2%).
- PBPU – Pekerja Mandiri: 32,040,621 (11.3%), segmen tujuan modus misklasifikasi PPU → PBPU.
- Rasio PBPU : PPU-BU = 1 : 1.47.
- Portal TIDAK menyediakan jumlah badan usaha, nilai iuran, atau tunggakan. Angka-angka itu tetap perlu
  dicari dari Laporan Keuangan/Pengelolaan Program BPJS Kesehatan atau LHP BPK (placeholder slide 4).

## Fasilitas kesehatan kerja sama (data 30/09/2026)

| Kelompok | Jenis | Jumlah |
|---|---|---:|
| Sarana Penunjang | Optik | 1,289 |
| Sarana Penunjang | Laboratorium | 560 |
| Sarana Penunjang | Apotik | 5,378 |
| FKTP | Puskesmas | 10,212 |
| FKTP | Klinik Pratama | 8,138 |
| FKTP | Dokter Umum | 4,321 |
| FKTP | Dokter gigi | 1,191 |
| FKRTL | Rumah sakit | 2,785 |
| FKRTL | Klinik Utama | 437 |

## Publikasi & artikel (16)

Teks lengkap ada di `artikel/`.

- 2025-12-02 — PELUNCURAN DATA SAMPEL BPJS KESEHATAN 2025 (2015-2024) (`artikel/2025-12-02_peluncuran-data-sampel-bpjs-kesehatan-2025-2015-2024.txt`)
- 2024-12-18 — PELUNCURAN DATA SAMPEL BPJS KESEHATAN 2024 (2015-2023) (`artikel/2024-12-18_peluncuran-data-sampel-bpjs-kesehatan-2024-2015-2023.txt`)
- 2023-12-18 — PELUNCURAN DATA SAMPEL BPJS KESEHATAN 2023 (2015-2022) (`artikel/2023-12-18_peluncuran-data-sampel-bpjs-kesehatan-2023-2015-2022.txt`)
- 2023-01-09 — DJSN & BPJS Kesehatan Luncurkan Buku Statistik JKN 2016-2021 (`artikel/2023-01-09_djsn-bpjs-kesehatan-luncurkan-buku-statistik-jkn-2016-2021.txt`)
- 2022-12-14 — PELUNCURAN DATA SAMPEL BPJS KESEHATAN 2015-2021 (`artikel/2022-12-14_peluncuran-data-sampel-bpjs-kesehatan-2015-2021.txt`)
- 2022-03-24 — DASHBOARD EVALUASI PENYAKIT KRONIS (DETAK) (`artikel/2022-03-24_dashboard-evaluasi-penyakit-kronis-detak.txt`)
- 2021-12-23 — PELUNCURAN DATA SAMPEL BPJS KESEHATAN 2015-2020 (`artikel/2021-12-23_peluncuran-data-sampel-bpjs-kesehatan-2015-2020.txt`)
- 2021-08-31 — EVALUASI SISTEM PEMBAYARAN FASILITAS KESEHATAN TINGKAT PERTAMA ERA JAMINAN KESEHATAN NASIONAL: Biaya Riil Layanan di Rawat Jalan Tingkat Pertama Sebagai Dasar Perhitungan Besaran Kapitasi Program JKN (`artikel/2021-08-31_evaluasi-sistem-pembayaran-fasilitas-kesehatan-tingkat-pertama-era-jam.txt`)
- 2021-08-30 — Evaluasi Sistem Pembayaran FKTP Era JKN: Dampak KBK Terhadap Kinerja Puskesmas dan Efisiensi (`artikel/2021-08-30_evaluasi-sistem-pembayaran-fktp-era-jkn-dampak-kbk-terhadap-kinerja-pu.txt`)
- 2021-08-27 — DAMPAK PROGRAM JKN-KIS  TERHADAP  KEMISKINAN (`artikel/2021-08-27_dampak-program-jkn-kis-terhadap-kemiskinan.txt`)
- 2021-08-26 — STUDI EVALUASI PENYELENGGARAAN SISTEM RUJUKAN BERJENJANG ERA JKN-KIS (`artikel/2021-08-26_studi-evaluasi-penyelenggaraan-sistem-rujukan-berjenjang-era-jkn-kis.txt`)
- 2021-08-25 — OPTIMALISASI STRATEGIC PURCHASING  BPJS KESEHATAN (`artikel/2021-08-25_optimalisasi-strategic-purchasing-bpjs-kesehatan.txt`)
- 2021-05-24 — DAMPAK PROGRAM JKN-KIS PADA PEREKONOMIAN INDONESIA (`artikel/2021-05-24_dampak-program-jkn-kis-pada-perekonomian-indonesia.txt`)
- 2020-12-20 — PELUNCURAN DATA SAMPEL BPJS KESEHATAN 2015-2018 (`artikel/2020-12-20_peluncuran-data-sampel-bpjs-kesehatan-2015-2018.txt`)
- 2020-12-19 — Evaluasi Sistem Pembayaran FKTP Era JKN (`artikel/2020-12-19_evaluasi-sistem-pembayaran-fktp-era-jkn.txt`)
- 2020-12-19 — Optimalisasi Strategic Purchasing BPJS KESEHATAN (`artikel/2020-12-19_optimalisasi-strategic-purchasing-bpjs-kesehatan.txt`)

## Katalog Dataset (75, Statistik JKN 2014–2018, walidata DJSN)

Halaman Dataset tidak tampil di menu. Katalognya ditemukan lewat crawl di `dataset-list.cbi`. Ke-75 file XLSX diunduh ke `dataset/xlsx/`, dikonversi ke `dataset/csv/`, dan kamus kolomnya ada di `dataset/*.kamus.txt`. Daftar lengkapnya ada di `daftar_dataset.csv`.

Yang relevan untuk PayRay adalah `pertumbuhan-peserta-jkn-berdasarkan-segmen-peserta.csv`: PPU 24,3 jt (2014) → 49,8 jt (2018). Sisanya statistik layanan (kunjungan, admisi, biaya klaim per provinsi).

## Yang tidak diambil

- **Data Sampel BPJS Kesehatan**: data individu riwayat layanan peserta (perlu pengajuan, dan aturan lomba
  melarang data peserta riil). Lagipula isinya layanan kesehatan, bukan kepatuhan pemberi kerja.
- **Dashboard Pembayaran Klaim FKRTL**: tabel per rumah sakit yang dirender server-side sebagai gambar
  (ekspor data dimatikan pemilik dashboard). Tidak relevan untuk PayRay.
- Halaman "Visualisasi Data JKN" kosong untuk publik.
