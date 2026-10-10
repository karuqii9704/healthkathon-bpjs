# Bukti & Angka untuk Revisi Pitch Deck PayRay

Disusun 10 Okt 2026. Semua angka prototype berasal dari data **simulasi**. Angka publik dilengkapi sumber dan status verifikasinya.

## Slide 4 · Skala masalah (ganti placeholder)

| Kartu | Angka | Sumber | Status |
|---|---|---|---|
| Peserta JKN | **282,8 jt** (30 Sep 2026) | Portal Data BPJS Kesehatan, dashboard Kepesertaan (`data_publik/bpjs_portal/kepesertaan_segmen.csv`) | Primer. Gantikan "285 jt+ per 1 Juni 2026" yang tidak konsisten |
| Segmen sasaran PayRay | **47,0 jt peserta PPU Badan Usaha** (16,6%) | idem | Primer |
| Iuran PPU yang belum terverifikasi | **Rp31,61 T** pendapatan iuran PPU BU & PN "tidak dapat diyakini kebenarannya" karena tidak didukung data memadai | BPK, IHPS II 2025, via [Monitor Indonesia, 15 Jun 2026](https://monitorindonesia.com/hukum/read/2026/06/627776/bpk-iuran-bpjs-rp31-triliun-bermasalah) | Sekunder. **Cek di PDF IHPS II 2025** ([bpk.go.id/ihps](https://www.bpk.go.id/ihps)) sebelum submit |

**Framing Rp31,61 T (penting):** angka ini BUKAN iuran yang bocor. Artinya, kebenaran pendapatan iuran PPU tidak bisa dipastikan dari data yang ada, dan celah verifikasi itulah yang diisi PayRay. Kalimat aman untuk slide: *"BPK: pendapatan iuran PPU Rp31,61 T tidak didukung data memadai (IHPS II 2025)"*.

Kartu "[__ ribu] badan usaha terdaftar" diganti dengan kartu BPK di atas, karena angka nasional tidak dipublikasikan. Bukti lokal bisa dipakai sebagai kalimat pendukung:
- *Tulungagung: baru 416 dari 1.092 badan usaha terdata (38%) yang mendaftarkan pekerjanya, dan 336 rutin membayar* ([ANTARA Jatim, 20 Jun 2026](https://jatim.antaranews.com/berita/1075348/bpjs-kesehatan-416-badan-usaha-daftarkan-pekerja-sebagai-peserta-jkn), Kepala BPJS Kesehatan Cabang Tulungagung).
- *BPK: "pembayaran iuran PPNPN dan PPU berpotensi tidak sesuai dengan penghasilan yang sebenarnya"*; penyisihan piutang iuran tak tertagih PPU badan usaha cenderung meningkat (LHP DJS 2017–2019, [BPK Perwakilan Sumbar, 30 Des 2020](https://sumbar.bpk.go.id/bikin-jengkel-bpk-data-kepesertaan-bpjs-kesehatan-selalu-bermasalah/)).
- Tren: peserta PPU 24,3 jt (2014) → 49,8 jt (2018) → 68,4 jt PPU PN+BU (Sep 2026). Sumber: Statistik JKN DJSN 2014–2018 dan Portal Data BPJS.

## Slide 7 · Lembar hasil scan (ganti contoh fiktif)

Pakai output asli mesin: [hasil/lembar_scan/BU04224.md](../hasil/lembar_scan/BU04224.md)

> **PT Cahaya Mandiri** · Industri kulit & alas kaki · 49 pekerja dilaporkan · *data sintetis*
> **98/100** · Keyakinan: tinggi
> 1. 24 pekerja keluar PPU lalu terdaftar PBPU ≤30 hari dalam 3 bulan (46% tenaga kerja), alasan bukan PHK
> 2. Rata-rata pekerja terdaftar 48 orang, rencana tenaga kerja di OSS 112 orang (43%)
> 3. Kombinasi pola tidak biasa dibanding usaha seskala
> Estimasi potensi iuran tak tertagih **± Rp212 jt/thn**

Kerugian sebenarnya di data simulasi adalah Rp215 jt/thn. Estimasinya meleset 1%, dan ini bisa disebut sebagai bukti kalkulator. Kombinasi ini juga menyelesaikan kontradiksi lama ("upah tidak naik" vs "92% di UMK"). Kalau ingin contoh modul upah, lihat `BU00633` (industri makanan, 105 pekerja).

## Slide 9 · Data yang dipakai (tambah baris)

| Data | Sumber | Status di prototype |
|---|---|---|
| Kepesertaan JKN per segmen | Portal Data BPJS Kesehatan | **Publik, sudah diambil** (rekap 30 Sep 2026) |
| Statistik JKN 2014–2018 (75 dataset) | DJSN via Portal Data BPJS | **Publik, sudah diambil** |
| Upah buruh per lapangan usaha | BPS Sakernas Agustus 2025 | **Publik.** Generator dikalibrasi ke sini: urutan sektor ρ = 0,90 |

## Slide 13 · Metrik (isi placeholder)

Angka dari data simulasi yang **tidak pernah dilihat saat penyetelan** (holdout seed 2026). Mesin aturan + Isolation Forest tidak memakai label saat menilai.

| Metrik | Target | Hasil prototype |
|---|---|---|
| Precision pada 10% skor tertinggi | ≥ 70% | **68,4%** (data dev 69,4%) |
| Hit rate vs pemilihan acak | ≈ 4,7× | **4,6×** |
| Iuran tertangkap per 100 pemeriksaan | > acak | **Rp7,7 M/thn vs Rp0,53 M acak (14,6×)** |
| Salah tandai UMKM patuh | ≤ 5% | **2,7%** |

Siklus umpan balik (500 hasil pemeriksaan + 250 audit acak jadi label) menaikkan precision putaran berikutnya dari 21,8% ke 26,8%. Iuran yang tertangkap juga naik, dari Rp1,60 M ke Rp1,81 M.

Kelemahan yang sebaiknya diakui (juri teknis menghargai ini):
- Modus sulit (pemotongan upah selektif, pendaftaran 75–90% pekerja) recall-nya baru 18–37%
- Salah tandai di usaha menengah/besar 6%, umumnya usaha padat karya sah yang membayar UMK

## Slide 10 · Kematangan

Hapus "Saat ini: Ide". Yang sudah berjalan: generator data sintetis tervalidasi, tiga modul scan + skor gabungan + reason code, kalkulator estimasi, laporan akurasi + uji bias per skala. Yang belum: dashboard.
