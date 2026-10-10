# Laporan Validasi Model ML PayRay

Training: 750 hasil pemeriksaan di world dev (500 prioritas teratas + 250 audit acak, bobot IPW audit 18.0). Test: world holdout 5,000 badan usaha (prevalensi 15.0%), seed generator dan seed injeksi berbeda, tidak pernah dilihat saat training/tuning.

## Perbandingan metode (holdout, top-10%)

| Metode | Precision@10% (CI 95%) | PR-AUC | ROC-AUC | Recall kasus sulit | Salah tandai UMKM | Iuran/100 pemeriksaan |
|---|---|---|---|---|---|---|
| Acak | 13.0% (10.2%–16.2%) | 0.142 | 0.468 | 7% | 10.2% | Rp0.08 M |
| Aturan + Isolation Forest | 68.4% (63.0%–72.8%) | 0.598 | 0.783 | 14% | 2.7% | Rp7.75 M |
| Model ML (dari hasil pemeriksaan) | 80.2% (74.8%–85.6%) | 0.640 | 0.824 | 15% | 3.1% | Rp5.24 M |
| PayRay gabungan (stacking) | 82.2% (77.2%–87.2%) | 0.716 | 0.837 | 15% | 2.7% | Rp5.30 M |
| Gabungan × estimasi Rp (nilai harapan) | 51.6% (46.8%–56.4%) | 0.472 | 0.750 | 15% | 0.8% | Rp17.91 M |

## Kalibrasi probabilitas

Gabungan: Brier 0.0735 · ECE 0.035. Model ML saja: Brier 0.0742 · ECE 0.008. Baseline (prevalensi saja): Brier 0.1275.

## Kesepakatan dua metode independen

| Kelompok | n | Precision |
|---|---|---|
| Keduanya menandai | 327 | 95.1% |
| Hanya aturan | 173 | 17.9% |
| Hanya ML | 173 | 52.0% |

## Stabilitas & learning curve

10× bootstrap training: precision 77.9% ± 3.3%, overlap top-10% (Jaccard) 0.71

| Label pemeriksaan | PR-AUC | Precision@10% |
|---|---|---|
| 150 | 0.589 ± 0.027 | 69.1% |
| 300 | 0.640 ± 0.063 | 77.2% |
| 450 | 0.683 ± 0.012 | 78.9% |
| 600 | 0.695 ± 0.003 | 80.7% |
| 750 | 0.701 ± 0.000 | 81.4% |

## Permutation importance (holdout, penurunan PR-AUC)

| Fitur | Δ PR-AUC |
|---|---|
| Porsi upah tidak naik | 0.229 ± 0.008 |
| Pekerja terdaftar / rencana OSS | 0.165 ± 0.005 |
| Pekerja pindah PPU→PBPU (klaster) | 0.085 ± 0.004 |
| Rencana tenaga kerja OSS | 0.071 ± 0.007 |
| Porsi kenaikan = kenaikan UMK | 0.051 ± 0.004 |
| Porsi upah seragam | 0.032 ± 0.005 |
| Pekerja dilaporkan | 0.030 ± 0.003 |
| Porsi pekerja pindah ke PBPU | 0.023 ± 0.002 |
| Porsi pekerja di atas UMK | 0.014 ± 0.001 |
| Upah vs benchmark sektor | 0.010 ± 0.001 |

## Rentang estimasi Rp (conformalized quantile regression)

Target coverage 80% → coverage holdout **84.2%** (n = 411 pelanggar yang tertangkap). Korelasi log: kalkulator 0.46 → model 0.84. Median galat relatif: kalkulator 78% → model 40%.

## Fairness per skala (gabungan)

| Skala | n | Precision | Recall | Salah tandai patuh |
|---|---|---|---|---|
| mikro | 1741 | 69% | 48% | 3.8% |
| kecil | 1661 | 86% | 56% | 1.6% |
| menengah | 1143 | 93% | 62% | 0.8% |
| besar | 455 | 95% | 62% | 0.5% |

## Drift fitur dev → holdout (PSI)

| Fitur | PSI |
|---|---|
| Upah vs benchmark sektor | 0.015 |
| Porsi pekerja di atas UMK | 0.010 |
| Porsi pekerja di bawah UMK | 0.008 |
| Upah P90 / UMK | 0.007 |
| Pekerja dilaporkan | 0.006 |
| Median upah / UMK | 0.006 |

## Kualitas data input

| Pemeriksaan | Status | Temuan |
|---|---|---|
| Skema kolom wajib | lulus | 23 kolom di 4 tabel lengkap |
| ID badan usaha unik | lulus | 0 dari 5.000 baris |
| ID pekerja unik per badan usaha | lulus | 0 dari 450.341 baris |
| Nilai kosong di kolom kunci | lulus | 0 dari 2.413.044 baris |
| Pekerja → badan usaha terdaftar (referential integrity) | lulus | 0 dari 450.341 baris |
| Riwayat upah → pekerja terdaftar | lulus | 0 dari 1.279.728 baris |
| Mutasi → pekerja terdaftar | lulus | 0 dari 677.975 baris |
| Upah dilaporkan > 0 | lulus | 0 dari 1.279.728 baris |
| Bulan aktif dalam 1–12 | lulus | 0 dari 1.279.728 baris |
| Duplikat upah (pekerja, badan usaha, tahun) | lulus | 0 dari 1.279.728 baris |
| Tanggal keluar ≥ tanggal masuk | lulus | 0 dari 450.341 baris |
| Usia saat masuk kerja 15–70 tahun | lulus | 0 dari 450.341 baris |
| Wilayah ada di tabel UMK | lulus | 0 dari 5.000 baris |
| KBLI ada di tabel sektor | lulus | 0 dari 5.000 baris |
| UMK tersedia untuk setiap tahun upah | lulus | 0 dari 1.279.728 baris |
| Upah ekstrem (> 40× UMK) | lulus | 0 dari 1.279.728 baris · bisa direksi/eksekutif sah; tidak memengaruhi iuran karena plafon Rp12 jt |
| Tahun berdiri ≤ tahun data | lulus | 0 dari 5.000 baris |
