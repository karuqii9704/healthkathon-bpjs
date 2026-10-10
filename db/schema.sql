-- Skema PostgreSQL PayRay.
-- Pemisahan akses blind: tim model hanya diberi akses ke skema `publik`
-- dan `referensi`; skema `label` hanya untuk evaluator.

CREATE SCHEMA IF NOT EXISTS publik;
CREATE SCHEMA IF NOT EXISTS referensi;
CREATE SCHEMA IF NOT EXISTS label;

-- referensi -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS referensi.umk (
    kode_wilayah  TEXT    NOT NULL,
    nama_wilayah  TEXT    NOT NULL,
    provinsi      TEXT    NOT NULL,
    tahun         INT     NOT NULL,
    umk           BIGINT  NOT NULL,
    PRIMARY KEY (kode_wilayah, tahun)
);

CREATE TABLE IF NOT EXISTS referensi.sektor (
    kbli          TEXT PRIMARY KEY,
    nama_sektor   TEXT    NOT NULL,
    padat_karya   BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS referensi.benchmark_upah (
    kbli          TEXT    NOT NULL,
    kode_wilayah  TEXT    NOT NULL,
    tahun         INT     NOT NULL,
    median_upah   BIGINT,            -- NULL = disensor, sampel kurang
    n_sampel      INT     NOT NULL,
    PRIMARY KEY (kbli, kode_wilayah, tahun)
);

-- publik (data yang "dilihat" BPJS) ----------------------------------------
CREATE TABLE IF NOT EXISTS publik.employers (
    employer_id    TEXT PRIMARY KEY,
    nama           TEXT    NOT NULL,
    kbli           TEXT    NOT NULL,
    nama_sektor    TEXT    NOT NULL,
    padat_karya    BOOLEAN NOT NULL,
    kode_wilayah   TEXT    NOT NULL,
    skala_usaha    TEXT    NOT NULL CHECK (skala_usaha IN ('mikro', 'kecil', 'menengah', 'besar')),
    tahun_berdiri  INT     NOT NULL,
    tk_oss         INT     NOT NULL
);

CREATE TABLE IF NOT EXISTS publik.workers (
    worker_id      TEXT PRIMARY KEY,  -- pseudonim (hash berkunci), bukan NIK
    employer_id    TEXT NOT NULL REFERENCES publik.employers,
    tgl_masuk      DATE NOT NULL,
    tgl_keluar     DATE,
    tahun_lahir    INT,
    jenis_kelamin  CHAR(1)
);

CREATE TABLE IF NOT EXISTS publik.wage_history (
    worker_id        TEXT   NOT NULL REFERENCES publik.workers,
    employer_id      TEXT   NOT NULL REFERENCES publik.employers,
    tahun            INT    NOT NULL,
    upah_dilaporkan  BIGINT NOT NULL,
    bulan_aktif      INT    NOT NULL CHECK (bulan_aktif BETWEEN 1 AND 12),
    PRIMARY KEY (worker_id, tahun)
);
CREATE INDEX IF NOT EXISTS wage_history_employer_idx ON publik.wage_history (employer_id, tahun);

CREATE TABLE IF NOT EXISTS publik.mutations (
    mutation_id      TEXT PRIMARY KEY,
    worker_id        TEXT NOT NULL REFERENCES publik.workers,
    employer_id      TEXT NOT NULL REFERENCES publik.employers,
    tanggal          DATE NOT NULL,
    jenis            TEXT NOT NULL CHECK (jenis IN ('DAFTAR_PPU', 'KELUAR_PPU')),
    segmen_tujuan    TEXT,            -- PBPU / NONAKTIF / PPU_LAIN
    tgl_segmen_baru  DATE,
    alasan           TEXT
);
CREATE INDEX IF NOT EXISTS mutations_employer_idx ON publik.mutations (employer_id, tanggal);

-- label (khusus evaluator) --------------------------------------------------
CREATE TABLE IF NOT EXISTS label.labels (
    employer_id                        TEXT PRIMARY KEY,
    hard_negative_type                 TEXT,
    is_violator                        INT    NOT NULL,
    modus                              TEXT,
    kesulitan                          TEXT   NOT NULL,
    pekerja_tersembunyi                INT    NOT NULL,
    pekerja_dipindah_pbpu              INT    NOT NULL,
    pekerja_upah_dikurangi             INT    NOT NULL,
    iuran_tak_tertagih_tahun_terakhir  BIGINT NOT NULL,
    iuran_tak_tertagih_total           BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS label.hidden_workers (
    worker_id    TEXT PRIMARY KEY,
    employer_id  TEXT NOT NULL,
    tgl_masuk    DATE NOT NULL,
    tgl_keluar   DATE
);

CREATE TABLE IF NOT EXISTS label.moved_workers (
    worker_id        TEXT PRIMARY KEY,
    employer_id      TEXT NOT NULL,
    tgl_pindah       DATE NOT NULL,
    tgl_keluar_riil  DATE
);

CREATE TABLE IF NOT EXISTS label.upah_riil (
    worker_id    TEXT   NOT NULL,
    employer_id  TEXT   NOT NULL,
    tahun        INT    NOT NULL,
    upah_riil    BIGINT NOT NULL,
    bulan_aktif  INT    NOT NULL,
    PRIMARY KEY (worker_id, tahun)
);

-- Contoh peran (jalankan sekali oleh admin):
-- CREATE ROLE payray_model LOGIN PASSWORD '...';
-- GRANT USAGE ON SCHEMA publik, referensi TO payray_model;
-- GRANT SELECT ON ALL TABLES IN SCHEMA publik, referensi TO payray_model;
-- CREATE ROLE payray_evaluator LOGIN PASSWORD '...';
-- GRANT USAGE ON SCHEMA publik, referensi, label TO payray_evaluator;
-- GRANT SELECT ON ALL TABLES IN SCHEMA publik, referensi, label TO payray_evaluator;
