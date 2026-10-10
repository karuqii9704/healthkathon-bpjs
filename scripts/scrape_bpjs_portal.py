"""Scrape data publik Portal Data BPJS Kesehatan ke teks/CSV lokal.

Sumber: https://data.bpjs-kesehatan.go.id/bpjs-portal/action/dash-publik.cbi?page=1
  - Dashboard publik (Tableau di dataviz.bpjs-kesehatan.go.id) -> angka yang ditampilkan, sebagai CSV
  - Publikasi & artikel statistik -> teks polos

Tidak disentuh: "Data Sampel" (data individu peserta; aturan lomba melarang data peserta riil)
dan dashboard Pembayaran Klaim per RS (dirender server-side sebagai gambar, tidak relevan untuk PayRay).

    pip install tableauscraper beautifulsoup4
    python scripts/scrape_bpjs_portal.py --out data_publik/bpjs_portal
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tableauscraper import TableauScraper, api, utils

PORTAL = "https://data.bpjs-kesehatan.go.id/bpjs-portal/action"
TABLEAU = "https://dataviz.bpjs-kesehatan.go.id/t/Stakeholder/views/PesertadanProviderJKN"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PayRay-research (Healthkathon 2026)"
DELAY = 1.0  # detik antar request, sopan ke server


class TableauScraper2025(TableauScraper):
    """Tableau Server 2025.x tidak lagi menaruh tsConfig di HTML; ambil lewat startSession."""

    def loads(self, url, params=None):
        api.setSession(self)
        self.session.headers["User-Agent"] = UA
        u = urlparse(url)
        self.host = f"{u.scheme}://{u.netloc}"
        q = {":embed": "y", ":showVizHome": "n"}
        self.session.get(url, params=q, timeout=60)
        m = re.match(r"/t/([^/]+)/views/([^/]+)/([^/?]+)", u.path)
        start = f"{self.host}/vizql/t/{m[1]}/w/{m[2]}/v/{m[3]}/startSession/viewing"
        self.tableauData = self.session.post(start, params=q, timeout=60).json()
        raw = api.getTableauData(self)
        self.raw = raw
        g = re.search(r"\d+;({.*})\d+;({.*})", raw, re.S)
        self.info, self.data = json.loads(g[1]), json.loads(g[2])
        pm = self.data["secondaryInfo"]["presModelMap"]
        self.dataSegments = (pm["dataDictionary"]["presModelHolder"]["genDataDictionaryPresModel"]["dataSegments"]
                             if "dataDictionary" in pm else {})
        self.parameters = utils.getParameterControlInput(self.info)
        self.dashboard = self.info["sheetName"]
        self.filters = utils.getFiltersForAllWorksheet(self.logger, self.data, self.info, rootDashboard=self.dashboard)


def _col(df: pd.DataFrame, pattern: str) -> pd.Series:
    return df[next(c for c in df.columns if re.search(pattern, c))]


def scrape_dashboards(out: Path) -> dict[str, pd.DataFrame]:
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    result = {}

    t = TableauScraper2025(logLevel=logging.WARNING)
    t.loads(f"{TABLEAU}/Peserta")
    (raw_dir / "tableau_peserta.txt").write_text(t.raw, encoding="utf-8")
    d = t.getWorksheet("Pst").data
    peserta = pd.DataFrame({
        "segmen": _col(d, r"^Jenis Peserta Rekap-alias$"),
        "jumlah_peserta": pd.to_numeric(_col(d, r"^SUM\(JUMLAH_PESERTA\)-alias$")).astype("int64"),
        "porsi": pd.to_numeric(_col(d, r"pcto:sum:jumlah_peserta")).round(6),
        "tgl_rekap": _col(d, r"TGL_REKAP"),
    })
    peserta["kelompok"] = peserta.segmen.str.extract(r"^(PBI|PPU|PBPU|Bukan Pekerja)")[0]
    result["kepesertaan_segmen"] = peserta
    time.sleep(DELAY)

    t = TableauScraper2025(logLevel=logging.WARNING)
    t.loads(f"{TABLEAU}/Faskes")
    (raw_dir / "tableau_faskes.txt").write_text(t.raw, encoding="utf-8")
    d = t.getWorksheet("Prov (2)").data
    result["faskes_jenis"] = pd.DataFrame({
        "kelompok": _col(d, r"^Group-alias$"),
        "jenis_faskes": _col(d, r"^Jenis Fasilitas Kesehatan-alias$"),
        "jumlah": pd.to_numeric(_col(d, r"Jumlah Faskes\)-alias$")).astype("int64"),
        "tgl_data": _col(d, r"Inserdate"),
    })

    for name, df in result.items():
        df.to_csv(out / f"{name}.csv", index=False)
    return result


def _get(s: requests.Session, url: str, tries: int = 4) -> BeautifulSoup:
    for i in range(tries):
        time.sleep(DELAY * (3 ** i))  # server portal kadang 500/lambat: mundur 1s, 3s, 9s, 27s
        try:
            r = s.get(url, timeout=60)
            r.raise_for_status()
            break
        except requests.RequestException:
            if i == tries - 1:
                raise
    # server mengaku ISO-8859-1, isinya cp1252
    return BeautifulSoup(r.content.decode("cp1252", errors="replace"), "html.parser")


def scrape_articles(out: Path) -> list[dict]:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    art_dir = out / "artikel"
    art_dir.mkdir(parents=True, exist_ok=True)

    links: dict[str, str] = {}
    for list_page, detail in (("blog.cbi", "blog-detail.cbi"), ("blog-statistik.cbi", "blog-detail-statistik.cbi")):
        page = 1
        while True:
            soup = _get(s, f"{PORTAL}/{list_page}?page={page}")
            found = {a["href"].split("?id=")[1]: f"{PORTAL}/{a['href']}"
                     for a in soup.find_all("a", href=True) if a["href"].startswith(f"{detail}?id=")}
            new = {k: v for k, v in found.items() if k not in links}
            if not new:
                break
            links.update(new)
            page += 1

    meta = []
    for aid, url in links.items():
        soup = _get(s, url)
        art = soup.find("article") or soup.find("main")
        lines = art.get_text("\n", strip=True).split("\n")
        title, tanggal = lines[0], next((x for x in lines if re.fullmatch(r"\d{4}-\d{2}-\d{2}", x)), "")
        body = "\n".join(lines)
        ext = sorted({a["href"] for a in art.find_all("a", href=True) if a["href"].startswith("http")})
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:70]
        fname = f"{tanggal}_{slug}.txt"
        (art_dir / fname).write_text(
            f"Judul   : {title}\nTanggal : {tanggal}\nSumber  : {url}\nTautan  : {', '.join(ext) or '-'}\n\n{body}\n",
            encoding="utf-8")
        meta.append({"tanggal": tanggal, "judul": title, "file": f"artikel/{fname}", "url": url,
                     "tautan_luar": " ".join(ext), "statistik": "statistik" in url})
    pd.DataFrame(meta).sort_values("tanggal", ascending=False).to_csv(out / "daftar_artikel.csv", index=False)
    return meta


def scrape_datasets(out: Path) -> pd.DataFrame:
    """Katalog Dataset (dataset-list.cbi): metadata, kamus kolom, dan file XLSX -> CSV per sheet."""
    s = requests.Session()
    s.headers["User-Agent"] = UA
    ds_dir = out / "dataset"
    (ds_dir / "xlsx").mkdir(parents=True, exist_ok=True)
    (ds_dir / "csv").mkdir(parents=True, exist_ok=True)

    ids_file = ds_dir / "ids.txt"
    ids: list[str] = ids_file.read_text().split() if ids_file.exists() else []
    page, misses = 1, (3 if ids else 0)  # daftar id di-cache: listing portal lambat
    while misses < 3:
        try:
            soup = _get(s, f"{PORTAL}/dataset-list.cbi?page={page}&filter=&kategori=")
            found = [a["href"].split("?id=")[1] for a in soup.find_all("a", href=True)
                     if a["href"].startswith("dataset-single.cbi?id=")]
        except requests.RequestException as e:
            print(f"  halaman {page} gagal: {e}")
            found = []
        new = [i for i in dict.fromkeys(found) if i not in ids]
        misses = 0 if new else misses + 1
        ids += new
        page += 1
    ids_file.write_text("\n".join(ids))
    print(f"  {len(ids)} dataset di katalog")

    rows = []
    for n, did in enumerate(ids, 1):
        main = None
        for _ in range(3):  # server kadang membalas 200 kosong
            try:
                main = _get(s, f"{PORTAL}/dataset-single.cbi?id={did}").find("main")
            except requests.RequestException:
                main = None
            if main is not None:
                break
        if main is None:
            rows.append({"id": did, "error": "halaman detail kosong/gagal"})
            print(f"  {did}: gagal")
            continue
        text = main.get_text("\n", strip=True).split("\n")
        title = text[2] if len(text) > 2 else did

        def after(label):
            return text[text.index(label) + 1] if label in text else ""

        kategori = after("Kategori")
        kamus = []
        if "Nama Kolom" in text:
            i = text.index("Nama Kolom") + 2
            kamus = [(text[j], text[j + 1]) for j in range(i, len(text) - 1, 2)]
        dl = next((a["href"] for a in main.find_all("a", href=True)
                   if "drive.google" in a["href"] or a["href"].lower().endswith((".xlsx", ".csv", ".xls"))), "")
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80]
        row = {"id": did, "judul": title, "walidata": after("Walidata"), "kategori": kategori,
               "diperbarui": after("Pembaharuan Terakhir"), "unduh": dl, "file_csv": "", "error": ""}
        if dl:
            try:
                time.sleep(DELAY)
                r = s.get(dl, timeout=120)
                r.raise_for_status()
                if r.content[:2] == b"PK":  # xlsx
                    xp = ds_dir / "xlsx" / f"{slug}.xlsx"
                    xp.write_bytes(r.content)
                    sheets = pd.read_excel(xp, sheet_name=None, header=None)
                    files = []
                    for sh, df in sheets.items():
                        df = df.dropna(how="all").dropna(axis=1, how="all")
                        name = slug if len(sheets) == 1 else f"{slug}__{re.sub(r'[^a-z0-9]+', '-', str(sh).lower())}"
                        df.to_csv(ds_dir / "csv" / f"{name}.csv", index=False, header=False)
                        files.append(f"dataset/csv/{name}.csv")
                    row["file_csv"] = " ".join(files)
                else:
                    row["error"] = f"bukan xlsx ({r.headers.get('content-type')})"
            except Exception as e:  # file rusak / drive minta konfirmasi
                row["error"] = f"{type(e).__name__}: {e}"[:200]
        (ds_dir / f"{slug}.kamus.txt").write_text(
            f"{title}\nWalidata: {row['walidata']} · Kategori: {kategori} · Diperbarui: {row['diperbarui']}\n"
            f"Sumber: {PORTAL}/dataset-single.cbi?id={did}\nUnduh: {dl}\n\nKolom:\n"
            + "\n".join(f"- {k}: {v}" for k, v in kamus) + "\n", encoding="utf-8")
        rows.append(row)
        if n % 10 == 0:
            print(f"  {n}/{len(ids)}")
    cat = pd.DataFrame(rows)
    cat.to_csv(out / "daftar_dataset.csv", index=False)
    return cat


def write_summary(out: Path, dash: dict[str, pd.DataFrame], arts: list[dict]) -> None:
    p, f = dash["kepesertaan_segmen"], dash["faskes_jenis"]
    total = p.jumlah_peserta.sum()
    ppu = p[p.kelompok == "PPU"]
    bu = p[p.segmen == "PPU - BU"].iloc[0]
    pbpu = p[p.segmen.str.startswith("PBPU")].iloc[0]
    L = [
        "# Data Publik Portal BPJS Kesehatan",
        "",
        f"Diambil {date.today().isoformat()} dari {PORTAL}/dash-publik.cbi?page=1 (dashboard Tableau publik dan publikasi).",
        "",
        f"## Kepesertaan JKN per segmen (rekap {p.tgl_rekap.iloc[0]})",
        "",
        "| Segmen | Jumlah peserta | Porsi |",
        "|---|---:|---:|",
        *[f"| {r.segmen} | {r.jumlah_peserta:,} | {r.porsi:.1%} |" for r in p.itertuples()],
        f"| **Total** | **{total:,}** | 100% |",
        "",
        "### Relevansi untuk PayRay",
        "",
        f"- Segmen sasaran PayRay, **PPU – Badan Usaha: {bu.jumlah_peserta:,} peserta ({bu.porsi:.1%})**. "
        f"Total PPU (PN + BU) {ppu.jumlah_peserta.sum():,} ({ppu.porsi.sum():.1%}).",
        f"- PBPU – Pekerja Mandiri: {pbpu.jumlah_peserta:,} ({pbpu.porsi:.1%}), segmen tujuan modus misklasifikasi PPU → PBPU.",
        f"- Rasio PBPU : PPU-BU = 1 : {bu.jumlah_peserta / pbpu.jumlah_peserta:.2f}.",
        "- Portal TIDAK menyediakan jumlah badan usaha, nilai iuran, atau tunggakan. Angka-angka itu tetap perlu",
        "  dicari dari Laporan Keuangan/Pengelolaan Program BPJS Kesehatan atau LHP BPK (placeholder slide 4).",
        "",
        f"## Fasilitas kesehatan kerja sama (data {f.tgl_data.iloc[0]})",
        "",
        "| Kelompok | Jenis | Jumlah |",
        "|---|---|---:|",
        *[f"| {r.kelompok} | {r.jenis_faskes} | {r.jumlah:,} |" for r in f.itertuples()],
        "",
        f"## Publikasi & artikel ({len(arts)})",
        "",
        "Teks lengkap ada di `artikel/`.",
        "",
        *[f"- {a['tanggal']} — {a['judul']} (`{a['file']}`)" for a in sorted(arts, key=lambda a: a["tanggal"], reverse=True)],
        "",
        "## Yang tidak diambil",
        "",
        "- **Data Sampel BPJS Kesehatan**: data individu riwayat layanan peserta (perlu pengajuan, dan aturan lomba",
        "  melarang data peserta riil). Lagipula isinya layanan kesehatan, bukan kepatuhan pemberi kerja.",
        "- **Dashboard Pembayaran Klaim FKRTL**: tabel per rumah sakit yang dirender server-side sebagai gambar",
        "  (ekspor data dimatikan pemilik dashboard). Tidak relevan untuk PayRay.",
        "- Halaman \"Dataset\" dan \"Visualisasi Data JKN\" kosong untuk publik.",
    ]
    (out / "RINGKASAN.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("data_publik/bpjs_portal"))
    ap.add_argument("--only-datasets", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.only_datasets:
        cat = scrape_datasets(a.out)
        print(f"Selesai: {len(cat)} dataset, {(cat.file_csv != '').sum()} berhasil diunduh")
        return
    print("Dashboard Tableau...")
    dash = scrape_dashboards(a.out)
    print("Publikasi & artikel...")
    arts = scrape_articles(a.out)
    write_summary(a.out, dash, arts)
    print(f"Selesai: {len(arts)} artikel, ringkasan di {a.out / 'RINGKASAN.md'}")


if __name__ == "__main__":
    main()
