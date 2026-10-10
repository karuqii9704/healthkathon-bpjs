# PayRay

Rontgen kepatuhan pemberi kerja untuk JKN — Healthkathon 2026. Konteks lengkap: [CLAUDE.md](CLAUDE.md).

## Mesin scan

```bash
python -m engine --data data --out hasil              # ranking, antrean, lembar hasil scan (tanpa label)
python -m engine --data data --out hasil --evaluate   # + laporan_akurasi.md (butuh data/label/)
```

Cara kerjanya, berurutan:
1. **[features.py](engine/features.py)** menghitung fitur yang bisa dibaca manusia per badan usaha: porsi upah tepat/di bawah/di atas UMK, upah beku saat UMK naik, kenaikan = kenaikan UMK, upah teratas vs sektor, rasio pekerja terdaftar vs OSS, dan klaster pindah PBPU ≤30 hari.
2. **[rules.py](engine/rules.py)** menjalankan 7 aturan transparan dalam 3 modul (upah, headcount, status). Aturannya dibedakan per skala usaha, karena UMKM dikecualikan dari UMK. Pembanding selalu badan usaha sejenis (sektor × skala).
3. **[score.py](engine/score.py)** menggabungkan aturan (noisy-OR) dengan Isolation Forest yang distandarkan per skala. Hasilnya skor 0–100, keyakinan (tinggi/sedang/rendah), 3 alasan utama, dan estimasi Rp per modul.
4. **[evaluate.py](engine/evaluate.py)** dan **[feedback.py](engine/feedback.py)** adalah satu-satunya bagian yang membaca label. Isinya metrik, uji bias per skala, recall per modus, dan simulasi siklus "hasil pemeriksaan jadi label".

Output di `hasil/`: `ranking.csv`, `antrean_pemeriksaan.csv` (risiko ≥ sedang dan keyakinan ≥ sedang), `lembar_scan/*.md`, `ranking_top.json` (untuk dashboard), `laporan_akurasi.md`.

### Hasil (top-10%, tanpa label saat menilai)

| | Data dev (seed 42) | Data holdout (seed 2026) | Target |
|---|---|---|---|
| Precision@10% | 69,4% | **68,4%** | ≥ 70% |
| Lift vs acak | 4,63× | **4,56×** | ≈ 4,7× |
| Salah tandai UMKM patuh | 2,5% | **2,7%** | ≤ 5% |
| Iuran tertangkap per 100 pemeriksaan | Rp7,9 M vs Rp0,63 M acak | Rp7,7 M vs Rp0,53 M acak | > acak |

Generator dikalibrasi ke upah BPS Sakernas Agustus 2025 (urutan sektor ρ = 0,90), lalu kedua dataset dibuat ulang dengan seed injeksi baru. Mesin tidak disetel ulang setelahnya, jadi kedua kolom adalah data yang belum pernah dilihat. Kelemahan yang sudah diketahui:
- Recall modus sulit masih rendah (`potong_sebagian` ±18%, `daftar_sebagian` ±37%)
- Kalkulator estimasi Rp baru berkorelasi 0,34 (log) dengan kerugian sebenarnya
- Salah tandai di usaha menengah/besar ±6%, sebagian besar dari usaha padat karya sah yang membayar UMK

Siklus umpan balik (belajar dari 500 hasil pemeriksaan + 250 audit acak) menaikkan precision putaran berikutnya dari ±22% menjadi 25–27%, dan iuran yang tertangkap ikut naik.

## Generator data sintetis

```bash
pip install -r requirements.txt
python -m generator --out data                      # 5.000 badan usaha, ±35 detik
python -m generator --out data --n-employers 500    # versi kecil untuk iterasi
python -m generator.validate data                   # validasi ulang tanpa generate
python -m pytest
```

Prototype ini 100% sintetis. Tidak ada data peserta riil, dan `worker_id` adalah pseudonim (hash berkunci), bukan NIK.

### Cara kerja

1. **`world.py` membangun dunia nyata.** Semua pemberi kerja jujur: upah riil, rekrutmen, turnover, kenaikan merit, dan penyesuaian ke UMK tiap tahun. Sekitar 12% sengaja dibuat **hard negative**, yaitu patuh tapi tampak mencurigakan:
   - `padat_karya_umk`: industri padat karya yang sah membayar 85–97% pekerja tepat di UMK
   - `umkm_bawah_umk`: usaha mikro/kecil yang sah membayar di bawah UMK (PP 36/2021)
   - `phk_massal_sah`: PHK massal sungguhan, dengan sebagian korban pindah ke PBPU
   - `upah_seragam_sah`: usaha kecil dengan upah seragam
2. **`inject.py` menyisipkan pelanggaran secara blind** pada 15% badan usaha dengan seed rahasia. Setiap modus punya varian mudah dan sulit:

   | Modus | Mudah | Sulit |
   |---|---|---|
   | Upah | `lapor_umk` (semua dilaporkan = UMK), `upah_beku` (upah tak pernah diperbarui sampai jatuh di bawah UMK) | `potong_sebagian` (hanya pekerja bergaji tinggi dipotong 15–40%, tetap ≥ UMK) |
   | Headcount | 35–60% pekerja didaftarkan | 75–90% didaftarkan |
   | Status | 25–50% pekerja dipindah ke PBPU dalam 1 bulan | 8–18% tersebar 2–4 bulan |

   Sekitar 25% pelanggar punya dua modus sekaligus.
3. **`export.py` menulis output** dengan pemisahan akses (lihat di bawah).
4. **`validate.py` menulis `data/laporan_validasi.md`** berisi invarian, cek kebocoran label dari metadata, dan baseline aturan naif yang harus dikalahkan model.

### Protokol blind

| Folder | Siapa yang boleh baca |
|---|---|
| `data/publik/` | Semua (data "yang dilihat BPJS") |
| `data/referensi/` | Semua (UMK, sektor, benchmark upah ala Sakernas) |
| `data/label/` | **Hanya evaluator / penyisip pelanggaran** |

Penyisip menjalankan `python -m generator --inject-seed <angka rahasia>` dan menyimpan folder `label/` terpisah. Seed injeksi tidak ditulis ke `manifest.json`. Di PostgreSQL, pemisahan ini berupa skema `publik`, `referensi`, dan `label` dengan peran berbeda (lihat [db/schema.sql](db/schema.sql)):

```bash
pip install "psycopg[binary]"
python scripts/load_postgres.py --dsn postgresql://user:pass@localhost/payray            # tim model
python scripts/load_postgres.py --dsn postgresql://user:pass@localhost/payray_eval --with-labels
```

### Kamus data

**publik/employers.csv**: `employer_id`, `nama`, `kbli`, `nama_sektor`, `padat_karya`, `kode_wilayah`, `skala_usaha` (mikro/kecil/menengah/besar), `tahun_berdiri`, `tk_oss` (rencana tenaga kerja di NIB/OSS)

**publik/workers.csv**: pekerja yang terdaftar PPU: `worker_id`, `employer_id`, `tgl_masuk`, `tgl_keluar`, `tahun_lahir`, `jenis_kelamin`

**publik/wage_history.csv**: `worker_id`, `employer_id`, `tahun`, `upah_dilaporkan`, `bulan_aktif`

**publik/mutations.csv**: `mutation_id`, `worker_id`, `employer_id`, `tanggal`, `jenis` (DAFTAR_PPU / KELUAR_PPU), `segmen_tujuan` (PBPU / NONAKTIF / PPU_LAIN), `tgl_segmen_baru`, `alasan`

**referensi/benchmark_upah.csv**: median upah per sektor × wilayah × tahun, simulasi survei dengan galat ±3%. `median_upah` kosong jika `n_sampel` < 30. Wilayah ini harus mendapat keyakinan rendah.

**label/labels.csv**: `is_violator`, `modus`, `kesulitan` (mudah/sulit/hard_negative/normal), `hard_negative_type`, jumlah pekerja tersembunyi/dipindah/dipotong, `iuran_tak_tertagih_tahun_terakhir`, `iuran_tak_tertagih_total`. Kerugian kebenaran = iuran riil − iuran dilaporkan, sehingga pemberi kerja patuh selalu tepat 0.

**label/**: `hidden_workers.csv`, `moved_workers.csv`, dan `upah_riil.csv` untuk menguji akurasi kalkulator estimasi.

### Hasil run default (seed 42)

- 5.000 badan usaha, 450 ribu pekerja terdaftar, 1,28 juta baris upah
- 750 pelanggar (469 mudah, 281 sulit), 512 hard negative
- Aturan naif terbaik mencapai precision@10% 52,8%. Model GBM cepat dengan ±15 fitur mencapai **83,8%** (lift 5,6×, salah tandai UMKM 2,0%), dengan recall kasus sulit hanya 11%. Artinya target di CLAUDE.md bisa dicapai, tetapi data tidak trivial.

### Angka yang wajib diverifikasi sebelum submit

Semua ada di [generator/config.py](generator/config.py) dan [generator/reference.py](generator/reference.py):
- Tarif iuran PPU 5% (4% + 1%) dan plafon upah Rp12.000.000 (Perpres 64/2020)
- UMK 2024 per wilayah (perkiraan dari SK Gubernur) dan faktor kenaikan tahunan
- Pengecualian upah minimum UMKM (PP 36/2021)
