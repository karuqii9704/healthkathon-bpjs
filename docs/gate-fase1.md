# Gate Fase 1 (t16) · 2026-10-14

| Exit criteria | Status | Bukti |
|---|---|---|
| EC-1.1 Migrasi 001–004 bersih di DB kosong lokal, CI, Neon; versi di README | Sebagian | Lokal + DB uji: lulus (`tests/conftest.py` migrasi tiap sesi). CI fork run 38495237191 lulus untuk 001–002. Neon: belum (t13 terblokir) |
| EC-1.2 CI 7 stage hijau di `main`; AGENTS.md/CLAUDE.md berisi GR-6..13 | Sebagian | 7 stage hijau di PR fork karuqii9704/healthkathon-bpjs#1. Merge ke `main` ditunda user. GR ada di kedua file |
| EC-1.3 SEC-1..7, 10, 11, 13, 14 | Lulus | `tests/test_queue.py`, `test_scan_sheet.py`, `test_db_permissions.py`, `test_auth.py`, `test_middleware.py`, `test_seed.py`; SEC-4 UI di `docs/ui-checklist.md`; SEC-13 `pip-audit` 0 temuan; SEC-14 run 38495683953 gagal di gitleaks seperti diharapkan |
| EC-1.4 BUG-2, 4, 5, 8, 9 | Lulus | `tests/test_scoring.py`, `tests/test_queue.py` |
| EC-1.5 API live di Render + smoke production | Belum | t13 terblokir (akun Render/Neon). Smoke lulus 5/5 terhadap image Docker lokal |
| EC-1.6 Checklist §12 Login, Antrean, Scan Sheet | Lulus | `docs/ui-checklist.md` |
| EC-1.7 MASTER.md berisi token §12 | Lulus | `design-system/payray/MASTER.md` |
| EC-1.8 KILL-1 (3 penguji) dan KILL-2 (Neon) | Belum | Skrip siap di `docs/usability.md`; KILL-2 lulus lokal (`scripts/check_permissions.py` 4/4), Neon belum |
| Audit dependensi + secret scan | Lulus | `pip-audit`: tidak ada vulnerability; gitleaks hijau di PR #1 |

## Go/No-Go

KILL-1 dan KILL-2 belum bisa dicek (butuh 3 penguji dan akun Neon). Atas instruksi user ("lanjut build feature dulu"), pembangunan Fase 2 dilanjutkan dengan syarat: KILL-1 dan KILL-2 wajib dicek sebelum deploy production, dan hasilnya ditulis di sini.
