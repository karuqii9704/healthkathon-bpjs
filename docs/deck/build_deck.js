// Pitch deck PayRay (revisi) — dibangun dengan pptxgenjs sebagai deck terstruktur.
// node build_deck.js  ->  PayRay_Healthkathon2026_revisi.pptx
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa6");

const SKILL = process.env.PPTX_SKILL_DIR;
const { applyTheme } = require(path.join(SKILL, "scripts", "apply_theme.js"));
const OUT = path.join(__dirname, "PayRay_Healthkathon2026_revisi.pptx");

// --- warna merek (tema rontgen gelap + aksen hijau limau) ---
const HEX = {
  ink: "172A30", night: "0E1C20", paper: "F3F2EE", white: "FFFFFF",
  green: "1B7F57", lime: "A6CE39", panel: "17343A", panelGreen: "1A4034",
  muted: "5B6B70", card: "FBFAF7", line: "DEDCD4", mint: "E3EFE7", warm: "FBE3D6", rust: "9A3B12",
  mist: "B9C7C9",
};
const THEME = {
  name: "PayRay",
  headFontFace: "Montserrat",
  bodyFontFace: "Source Sans 3",
  colors: {
    dk1: HEX.ink, lt1: HEX.white, dk2: HEX.night, lt2: HEX.paper,
    accent1: HEX.green, accent2: HEX.lime, accent3: HEX.panel, accent4: HEX.rust,
    accent5: HEX.muted, accent6: HEX.mint, hlink: HEX.green, folHlink: HEX.muted,
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "PayRay · Healthkathon 2026";
pres.author = "Tim PayRay";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const W = 13.333, X = 0.75, CW = W - 2 * X;

// warna skema -> nama yang mudah dibaca
const S = {
  ink: C.text1, night: C.text2, white: C.background1, paper: C.background2,
  green: C.accent1, lime: C.accent2, panel: C.accent3, rust: C.accent4, muted: C.accent5, mint: C.accent6,
};

// --- layout (frame) ---
const footer = (dark) => ([
  { text: { text: "PayRay · Healthkathon 2026", options: { x: X, y: 6.92, w: 5, h: 0.3, fontSize: 11, color: dark ? HEX.mist : HEX.muted, margin: 0 } } },
]);
const slideNum = (dark) => ({ x: W - X - 0.6, y: 6.92, w: 0.6, h: 0.3, fontSize: 11, color: dark ? HEX.mist : HEX.muted, align: "right" });

pres.defineSlideMaster({
  title: "PAYRAY_LIGHT",
  background: { color: HEX.paper },
  margin: [0.5, 0.75, 0.6, 0.75],
  objects: [
    ...footer(false),
    { placeholder: { options: { name: "label", type: "body", x: X, y: 0.62, w: CW, h: 0.32, fontFace: THEME.bodyFontFace, fontSize: 13, bold: true, color: S.green, charSpacing: 2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: X, y: 0.95, w: CW, h: 0.95, fontFace: THEME.headFontFace, fontSize: 40, bold: true, color: S.ink, valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
  slideNumber: slideNum(false),
});
pres.defineSlideMaster({
  title: "PAYRAY_DARK",
  background: { color: HEX.night },
  margin: [0.5, 0.75, 0.6, 0.75],
  objects: [
    ...footer(true),
    { placeholder: { options: { name: "label", type: "body", x: X, y: 0.62, w: CW, h: 0.32, fontFace: THEME.bodyFontFace, fontSize: 13, bold: true, color: S.lime, charSpacing: 2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: X, y: 0.95, w: CW, h: 0.95, fontFace: THEME.headFontFace, fontSize: 40, bold: true, color: S.white, valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
  slideNumber: slideNum(true),
});
pres.defineSlideMaster({ title: "PAYRAY_COVER", background: { color: HEX.night }, objects: [] });

// --- ikon ---
async function icon(Comp, hex, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + hex, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

// --- helper komposisi ---
let objId = 0;
const oid = (n) => `${n}-${++objId}`;
function card(slide, x, y, w, h, opt = {}) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.12, objectName: oid("kartu"),
    fill: { color: opt.fill || S.white, transparency: opt.transparency || 0 },
    line: opt.noLine ? { type: "none" } : { color: opt.lineColor || HEX.line, width: 0.75 },
  });
}
function text(slide, str, o) {
  slide.addText(str, { isTextBox: true, margin: 0, valign: "top", fontSize: 16, color: S.ink, objectName: oid("teks"), ...o });
}
function kicker(slide, str, x, y, w, dark = false) {
  text(slide, str, { x, y, w, h: 0.3, fontSize: 12, bold: true, charSpacing: 1.5, color: dark ? S.lime : S.green });
}
function bullets(items, o = {}) {
  return items.map((t, i) => ({ text: t, options: { bullet: { indent: 16 }, breakLine: i < items.length - 1, paraSpaceAfter: o.gap ?? 6 } }));
}
async function iconBadge(slide, Comp, x, y, dark = false, d = 0.62) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: dark ? S.panel : S.mint }, line: { type: "none" }, objectName: oid("lingkar-ikon") });
  const pad = d * 0.24;
  slide.addImage({ data: await icon(Comp, dark ? HEX.lime : HEX.green), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: oid("ikon") });
}
function lightSlide(section, label, title) {
  const s = pres.addSlide({ masterName: "PAYRAY_LIGHT", sectionTitle: section });
  s.addText(label, { placeholder: "label" });
  s.addText(title, { placeholder: "title" });
  return s;
}
function darkSlide(section, label, title) {
  const s = pres.addSlide({ masterName: "PAYRAY_DARK", sectionTitle: section });
  s.addText(label, { placeholder: "label" });
  s.addText(title, { placeholder: "title" });
  return s;
}
function scanner(slide, cx, cy, r) {
  // ilustrasi rontgen: lingkaran radar, dokumen, garis pindai, bracket sudut
  [1, 0.78, 0.56].forEach((k, i) => slide.addShape(pres.shapes.OVAL, {
    x: cx - r * k, y: cy - r * k, w: 2 * r * k, h: 2 * r * k, fill: { type: "none" },
    line: { color: S.lime, width: 0.75, transparency: 70 + i * 5 }, objectName: oid("radar"),
  }));
  const dw = r * 0.82, dh = r * 1.12;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx - dw / 2, y: cy - dh / 2, w: dw, h: dh, rectRadius: 0.08, fill: { color: S.panel }, line: { color: "5FC6A6", width: 1 }, objectName: oid("dokumen") });
  [0.82, 0.55, 0.72, 0.42].forEach((k, i) => slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: cx - dw / 2 + 0.16, y: cy - dh / 2 + 0.22 + i * 0.2, w: (dw - 0.32) * k, h: 0.07, rectRadius: 0.03,
    fill: { color: "3E7F72" }, line: { type: "none" }, objectName: oid("baris-dokumen"),
  }));
  [0.5, 0.3].forEach((k, i) => slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: cx - dw / 2 + 0.16, y: cy + 0.32 + i * 0.2, w: (dw - 0.32) * k, h: 0.08, rectRadius: 0.03,
    fill: { color: S.lime }, line: { type: "none" }, objectName: oid("baris-terdeteksi"),
  }));
  slide.addShape(pres.shapes.RECTANGLE, { x: cx - r * 0.9, y: cy + 0.22, w: r * 1.8, h: 0.34, fill: { color: S.lime, transparency: 82 }, line: { type: "none" }, objectName: oid("cahaya-pindai") });
  slide.addShape(pres.shapes.LINE, { x: cx - r * 0.9, y: cy + 0.39, w: r * 1.8, h: 0, line: { color: S.lime, width: 2 }, objectName: oid("garis-pindai") });
  const b = r * 0.82, L = 0.32;
  [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sy]) => {
    const px = cx + sx * b, py = cy + sy * b;
    slide.addShape(pres.shapes.LINE, { x: sx < 0 ? px : px - L, y: py, w: L, h: 0, line: { color: S.lime, width: 2.25 }, objectName: oid("bracket") });
    slide.addShape(pres.shapes.LINE, { x: px, y: sy < 0 ? py : py - L, w: 0, h: L, line: { color: S.lime, width: 2.25 }, objectName: oid("bracket") });
  });
}

async function build() {
  // ===================== 1. COVER =====================
  pres.addSection({ title: "Pembuka" });
  let s = pres.addSlide({ masterName: "PAYRAY_COVER", sectionTitle: "Pembuka" });
  kicker(s, "HEALTHKATHON 2026 · DETECT SMARTER, PROTECT JKN", X, 1.75, 8, true);
  s.addText([
    { text: "Pay", options: { color: S.white } },
    { text: "Ray", options: { color: S.lime } },
  ], { isTextBox: true, x: X, y: 2.1, w: 7.5, h: 1.45, fontFace: THEME.headFontFace, fontSize: 92, bold: true, margin: 0, valign: "top", objectName: "judul-cover" });
  text(s, "Rontgen kepatuhan pemberi kerja untuk JKN.", { x: X, y: 3.7, w: 7.2, h: 1.0, fontFace: THEME.headFontFace, fontSize: 28, bold: true, color: S.white });
  text(s, "Skor risiko berbasis AI yang menemukan upah dan pekerja yang tidak dilaporkan, supaya pemeriksaan dimulai dari badan usaha yang paling berisiko.", { x: X, y: 4.8, w: 7.0, h: 1.0, fontSize: 18, color: HEX.mist });
  s.addText([{ text: "Kategori: " }, { text: "Peserta JKN & Pemberi Kerja", options: { bold: true } }, { text: " · Tim Plan with Us" }],
    { isTextBox: true, x: X, y: 6.55, w: 8, h: 0.35, fontSize: 14, color: HEX.mist, margin: 0, objectName: "kategori-cover" });
  scanner(s, 9.95, 3.55, 1.95);
  s.addNotes("Pembuka. PayRay = Pay + X-Ray: rontgen kepatuhan pemberi kerja. Fokus kategori Peserta JKN & Pemberi Kerja.");

  // ===================== 2. POSITIONING =====================
  s = lightSlide("Pembuka", "01 · IDENTITAS & POSITIONING", "PayRay dalam satu kalimat");
  s.addText([
    { text: "PayRay memberi skor risiko kepatuhan ke " },
    { text: "seluruh", options: { color: S.green } },
    { text: " badan usaha setiap periode, sehingga petugas BPJS Kesehatan memeriksa yang paling berisiko lebih dulu." },
  ], { isTextBox: true, x: X, y: 2.05, w: 11.3, h: 1.4, fontFace: THEME.headFontFace, fontSize: 26, bold: true, color: S.ink, margin: 0, valign: "top", objectName: "kalimat-utama" });
  const cw2 = (CW - 0.6) / 3;
  const cards2 = [
    ["KATEGORI", ["Peserta JKN & Pemberi Kerja"]],
    ["SUB-KATEGORI FOKUS", ["Under-reporting Upah", "Pendaftaran Pekerja Sebagian", "Misklasifikasi Status Kerja"]],
    ["PEMBEDA", ["Alasan yang bisa dibaca petugas", "Estimasi potensi iuran dalam rupiah", "Aturan dibedakan per skala usaha: UMKM terlindungi"]],
  ];
  cards2.forEach(([k, items], i) => {
    const x = X + i * (cw2 + 0.3);
    card(s, x, 3.75, cw2, 2.75);
    kicker(s, k, x + 0.3, 4.05, cw2 - 0.6);
    if (i < 2) text(s, items.map((t, j) => ({ text: t, options: { breakLine: j < items.length - 1, paraSpaceAfter: 6 } })), { x: x + 0.3, y: 4.5, w: cw2 - 0.6, h: 1.8, fontSize: 18, bold: true });
    else text(s, bullets(items, { gap: 6 }), { x: x + 0.3, y: 4.5, w: cw2 - 0.6, h: 1.85, fontSize: 16 });
  });
  s.addNotes("Revisi: pembeda tidak lagi mengklaim 'bukan sampel', tetapi tiga hal yang bisa dibuktikan: alasan yang bisa dibaca, estimasi rupiah, dan perlindungan UMKM (aturan dibedakan per skala, PP 36/2021).");

  // ===================== 3. MASALAH =====================
  pres.addSection({ title: "Masalah" });
  s = lightSlide("Masalah", "02 · MASALAH", "Iuran PPU bocor lewat laporan");
  s.addText([
    { text: "Iuran pekerja penerima upah (PPU) dihitung 5% dari upah: " },
    { text: "4% pemberi kerja", options: { bold: true } }, { text: " dan " }, { text: "1% pekerja", options: { bold: true } },
    { text: ". Setiap rupiah upah atau setiap pekerja yang tidak dilaporkan langsung mengurangi iuran yang masuk." },
  ], { isTextBox: true, x: X, y: 2.0, w: 11.4, h: 0.85, fontSize: 18, color: S.muted, margin: 0, valign: "top", objectName: "pengantar-masalah" });
  const prob = [
    [fa.FaMoneyBillWave, "01", "Under-reporting upah", "Upah dilaporkan setara UMK, padahal upah riil lebih tinggi."],
    [fa.FaUsersSlash, "02", "Pendaftaran sebagian", "Hanya sebagian karyawan yang didaftarkan untuk menekan beban iuran."],
    [fa.FaRightLeft, "03", "Misklasifikasi status", "Pekerja dipindah ke segmen mandiri (PBPU) agar lepas dari porsi 4%."],
  ];
  for (let i = 0; i < 3; i++) {
    const [ic, n, h, d] = prob[i], x = X + i * (cw2 + 0.3);
    card(s, x, 3.15, cw2, 3.25);
    await iconBadge(s, ic, x + 0.3, 3.45);
    text(s, n, { x: x + cw2 - 1.1, y: 3.5, w: 0.8, h: 0.5, fontFace: THEME.headFontFace, fontSize: 26, bold: true, color: S.green, align: "right" });
    text(s, h, { x: x + 0.3, y: 4.25, w: cw2 - 0.6, h: 0.8, fontFace: THEME.headFontFace, fontSize: 20, bold: true });
    text(s, d, { x: x + 0.3, y: 5.1, w: cw2 - 0.6, h: 1.15, fontSize: 17, color: S.muted });
  }
  s.addNotes("Tiga modus kebocoran yang menjadi sub-kategori fokus.");

  // ===================== 4. URGENSI =====================
  s = lightSlide("Masalah", "02 · URGENSI", "Skala masalahnya");
  const stats = [
    ["282,8 jt", "peserta JKN per 30 September 2026", "Sumber: Portal Data BPJS Kesehatan"],
    ["47,0 jt", "peserta PPU Badan Usaha, 16,6% peserta JKN, segmen yang dilindungi PayRay", "Sumber: Portal Data BPJS Kesehatan"],
    ["Rp31,61 T", "pendapatan iuran PPU badan usaha & penyelenggara negara tidak didukung data memadai", "Sumber: BPK, IHPS II Tahun 2025"],
  ];
  stats.forEach(([big, lab, src], i) => {
    const x = X + i * (cw2 + 0.3);
    card(s, x, 2.05, cw2, 2.45);
    text(s, big, { x: x + 0.3, y: 2.3, w: cw2 - 0.6, h: 0.9, fontFace: THEME.headFontFace, fontSize: 46, bold: true, color: S.green });
    text(s, lab, { x: x + 0.3, y: 3.2, w: cw2 - 0.6, h: 0.85, fontSize: 16 });
    text(s, src, { x: x + 0.3, y: 4.1, w: cw2 - 0.6, h: 0.3, fontSize: 12, color: S.muted });
  });
  card(s, X, 4.8, CW, 1.75, { fill: S.mint, noLine: true });
  text(s, [
    { text: "Di Tulungagung, baru 416 dari 1.092 badan usaha terdata yang mendaftarkan pekerjanya (ANTARA, Juni 2026). ", options: { breakLine: false } },
    { text: "Kapasitas pemeriksaan terbatas; tanpa prioritas berbasis data, sebagian ketidakpatuhan tidak terpantau.", options: { breakLine: true } },
    { text: "Kami membingkainya sebagai efisiensi dan integritas, bukan tuduhan.", options: { italic: true, color: S.green, bold: true } },
  ], { x: X + 0.35, y: 5.05, w: CW - 0.7, h: 1.35, fontSize: 17, paraSpaceAfter: 8 });
  s.addNotes("Angka Rp31,61 T BUKAN iuran yang bocor: BPK menyatakan pendapatan iuran PPU BU & PN sebesar itu tidak dapat diyakini kebenarannya karena tidak didukung data memadai (IHPS II 2025). Celah verifikasi inilah yang diisi PayRay. Verifikasi angka di PDF IHPS II 2025 (bpk.go.id/ihps) sebelum submit. Peserta: Portal Data BPJS Kesehatan, rekap 30 Sep 2026. Tulungagung: ANTARA Jatim 20 Jun 2026, Kepala BPJS Kesehatan Cabang Tulungagung.");

  // ===================== 5. SOLUSI (gelap) =====================
  pres.addSection({ title: "Solusi" });
  s = darkSlide("Solusi", "03 · SOLUSI", "Prioritas pemeriksaan berbasis data");
  card(s, X, 2.3, 5.4, 3.6, { fill: S.panel, noLine: true });
  kicker(s, "HARI INI", X + 0.4, 2.6, 4.6, false);
  text(s, bullets([
    "Target pemeriksaan bergantung pada kapasitas dan informasi yang tersedia",
    "Ketidakpatuhan sering baru terlihat setelah iuran lama bocor",
    "Sulit membandingkan ribuan badan usaha sekaligus",
  ], { gap: 10 }), { x: X + 0.4, y: 3.05, w: 4.6, h: 2.6, fontSize: 17, color: HEX.mist });
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 6.42, y: 3.85, w: 0.55, h: 0.4, fill: { color: S.lime }, line: { type: "none" }, objectName: "panah-solusi" });
  card(s, 7.18, 2.3, 5.4, 3.6, { fill: S.green, transparency: 55, lineColor: HEX.lime });
  kicker(s, "DENGAN PAYRAY", 7.58, 2.6, 4.6, true);
  text(s, bullets([
    "Semua badan usaha diskor otomatis setiap periode, < 1 menit untuk 5.000",
    "Petugas mulai dari prioritas tertinggi, berdasarkan skor dan keyakinan",
    "Setiap skor disertai alasan dan estimasi potensi iuran dalam rupiah",
  ], { gap: 10 }), { x: 7.58, y: 3.05, w: 4.6, h: 2.6, fontSize: 17, color: S.white });
  s.addNotes("Revisi judul: tidak lagi 'dari sampel', supaya tidak mengklaim praktik internal BPJS yang tidak kita ketahui. Mesin prototype menilai 5.000 badan usaha dalam ±7 detik.");

  // ===================== 6. TIGA SCAN =====================
  s = lightSlide("Solusi", "03 · CARA KERJA", "Tiga sudut pandang scan");
  const scans = [
    [fa.FaChartColumn, "Scan Upah", "Under-reporting Upah", ["Bunching tepat di UMK vs sektor sejenis", "Tidak ada staf di atas UMK", "Upah beku saat UMK naik", "Upah teratas jauh di bawah sektor & wilayah"]],
    [fa.FaUsers, "Scan Headcount", "Pendaftaran Pekerja Sebagian", ["Pekerja terdaftar vs rencana tenaga kerja di NIB/OSS", "Pola jumlah pekerja per sektor (KBLI) & skala", "Fase lanjut: dicocokkan dengan BPJS Ketenagakerjaan"]],
    [fa.FaCalendarCheck, "Scan Status", "Misklasifikasi Status Kerja", ["Klaster keluar PPU lalu terdaftar PBPU ≤ 30 hari", "Dari satu pemberi kerja, dalam 3 bulan, bukan PHK", "Fase lanjut: cek pekerja masih aktif bekerja (data BPJS TK)"]],
  ];
  for (let i = 0; i < 3; i++) {
    const [ic, h, sub, items] = scans[i], x = X + i * (cw2 + 0.3);
    card(s, x, 2.05, cw2, 4.45);
    await iconBadge(s, ic, x + 0.3, 2.35);
    text(s, h, { x: x + 0.3, y: 3.15, w: cw2 - 0.6, h: 0.45, fontFace: THEME.headFontFace, fontSize: 21, bold: true });
    text(s, sub, { x: x + 0.3, y: 3.62, w: cw2 - 0.6, h: 0.35, fontSize: 15, bold: true, color: S.green });
    text(s, bullets(items, { gap: 7 }), { x: x + 0.3, y: 4.1, w: cw2 - 0.6, h: 2.25, fontSize: 15 });
  }
  s.addNotes("Revisi: 'pekerja masih aktif bekerja' ditandai fase lanjut karena butuh data BPJS TK. Setiap bullet = satu aturan transparan di mesin (engine/rules.py).");

  // ===================== 7. LEMBAR HASIL SCAN =====================
  s = lightSlide("Solusi", "03 · OUTPUT", "Lembar hasil scan untuk petugas");
  const lx = X, lw = 7.15, ly = 2.0;
  card(s, lx, ly, lw, 4.6);
  text(s, "PT Cahaya Mandiri", { x: lx + 0.35, y: ly + 0.3, w: 4.6, h: 0.45, fontFace: THEME.headFontFace, fontSize: 21, bold: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: lx + lw - 1.95, y: ly + 0.3, w: 1.6, h: 0.42, rectRadius: 0.2, fill: { color: HEX.warm }, line: { type: "none" }, objectName: "lencana-risiko" });
  text(s, "Risiko Tinggi", { x: lx + lw - 1.95, y: ly + 0.3, w: 1.6, h: 0.42, fontSize: 14, bold: true, color: HEX.rust, align: "center", valign: "middle" });
  text(s, "Keluaran asli mesin PayRay, data sintetis · Industri alas kaki · 49 pekerja dilaporkan", { x: lx + 0.35, y: ly + 0.8, w: lw - 0.7, h: 0.3, fontSize: 13, color: S.muted });
  s.addText([{ text: "99", options: { color: S.ink } }, { text: "/100", options: { color: S.muted } }],
    { isTextBox: true, x: lx + 0.35, y: ly + 1.15, w: 2.6, h: 0.8, fontFace: THEME.headFontFace, fontSize: 44, bold: true, margin: 0, valign: "middle", objectName: "skor" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: lx + 2.95, y: ly + 1.36, w: 1.95, h: 0.4, rectRadius: 0.2, fill: { color: S.mint }, line: { type: "none" }, objectName: "lencana-keyakinan" });
  text(s, "Keyakinan: tinggi", { x: lx + 2.95, y: ly + 1.36, w: 1.95, h: 0.4, fontSize: 14, bold: true, color: S.green, align: "center", valign: "middle" });
  kicker(s, "ALASAN UTAMA", lx + 0.35, ly + 2.05, 3);
  text(s, [
    "24 pekerja pindah ke PBPU ≤ 30 hari, dalam 3 bulan, bukan PHK (46%)",
    "Terdaftar 48 pekerja, rencana tenaga kerja di OSS 112 (43%)",
    "Kombinasi pola tidak biasa dibanding usaha seskala",
  ].map((t, i, a) => ({ text: t, options: { bullet: { type: "number" }, breakLine: i < a.length - 1, paraSpaceAfter: 4 } })),
  { x: lx + 0.35, y: ly + 2.4, w: lw - 0.7, h: 1.05, fontSize: 15 });
  s.addShape(pres.shapes.LINE, { x: lx + 0.35, y: ly + 3.55, w: lw - 0.7, h: 0, line: { color: HEX.line, width: 0.75 }, objectName: "pemisah" });
  text(s, "Estimasi potensi iuran tak tertagih", { x: lx + 0.35, y: ly + 3.72, w: 3.6, h: 0.45, fontSize: 14, color: S.muted, valign: "middle" });
  text(s, "± Rp212 jt/thn", { x: lx + 3.8, y: ly + 3.67, w: lw - 4.15, h: 0.55, fontFace: THEME.headFontFace, fontSize: 24, bold: true, align: "right", valign: "middle" });
  text(s, "Kerugian sebenarnya di simulasi: Rp215 jt/thn", { x: lx + 0.35, y: ly + 4.2, w: lw - 0.7, h: 0.28, fontSize: 12, color: S.green, align: "right" });
  const rx = 8.35, rw = W - X - rx;
  const side = [
    ["Skor + keyakinan", "Skor dengan keyakinan rendah tidak diprioritaskan."],
    ["Alasan yang bisa dibaca", "Bukan kotak hitam: setiap skor punya bukti."],
    ["Estimasi dalam rupiah", "Prioritas berdasarkan nilai, bukan skor saja."],
    ["Keputusan di petugas", "PayRay mengurutkan, manusia memutuskan."],
  ];
  side.forEach(([h, d], i) => {
    text(s, h, { x: rx, y: 2.05 + i * 1.12, w: rw, h: 0.4, fontFace: THEME.headFontFace, fontSize: 18, bold: true });
    text(s, d, { x: rx, y: 2.47 + i * 1.12, w: rw, h: 0.55, fontSize: 15, color: S.muted });
  });
  s.addNotes("Contoh ini keluaran asli mesin (hasil/lembar_scan/BU04224.md), bukan karangan. Estimasi Rp212 jt vs kerugian sebenarnya Rp215 jt di data simulasi. Menggantikan contoh lama yang kontradiktif ('upah tidak naik 3 tahun' vs '92% tepat di UMK').");

  // ===================== 8. PENDEKATAN TEKNIS =====================
  pres.addSection({ title: "Teknis & data" });
  s = lightSlide("Teknis & data", "04 · PENDEKATAN TEKNIS", "Dari data ke keputusan");
  const bw = 3.55, gap8 = (CW - 3 * bw) / 2;
  const steps8 = [
    ["1 · INPUT", "Data", ["Kepesertaan & upah PPU (sintetis)", "UMP / UMK", "Upah per sektor (BPS)", "Skala usaha & KBLI (OSS)"]],
    ["2 · PROSES", "Mesin scan", ["7 aturan bisnis transparan", "Isolation Forest untuk anomali", "Skor gabungan + reason code", "Kalkulator estimasi iuran"]],
    ["3 · OUTPUT", "Keputusan", ["Ranking risiko badan usaha", "Lembar hasil scan", "Antrean pemeriksaan petugas", "Hasil pemeriksaan jadi label baru"]],
  ];
  steps8.forEach(([k, h, items], i) => {
    const x = X + i * (bw + gap8);
    card(s, x, 2.0, bw, 2.55, i === 1 ? { lineColor: HEX.green } : {});
    kicker(s, k, x + 0.28, 2.2, bw - 0.5);
    text(s, h, { x: x + 0.28, y: 2.5, w: bw - 0.5, h: 0.4, fontFace: THEME.headFontFace, fontSize: 19, bold: true });
    text(s, bullets(items, { gap: 3 }), { x: x + 0.28, y: 2.95, w: bw - 0.45, h: 1.5, fontSize: 14 });
    if (i < 2) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + bw + gap8 / 2 - 0.2, y: 3.13, w: 0.4, h: 0.3, fill: { color: S.green }, line: { type: "none" }, objectName: oid("panah") });
  });
  card(s, X, 4.8, 6.55, 1.75, { fill: S.mint, noLine: true });
  kicker(s, "RUMUS KALKULATOR", X + 0.3, 4.98, 6);
  text(s, [
    { text: "(min(upah wajar, plafon) − min(upah dilaporkan, plafon)) × 5% × pekerja × 12", options: { bold: true, breakLine: true } },
    { text: "+ iuran pekerja tak terdaftar & yang dipindah ke PBPU. Plafon upah iuran Rp12 jt (Perpres 64/2020)." },
  ], { x: X + 0.3, y: 5.3, w: 6.0, h: 1.15, fontSize: 14, paraSpaceAfter: 4 });
  const kx = X + 6.85, kw = CW - 6.85;
  card(s, kx, 4.8, kw, 1.75);
  kicker(s, "KENAPA AI, BUKAN ATURAN SAJA", kx + 0.3, 4.98, kw - 0.5);
  text(s, "Aturan menangkap modus yang sudah dikenal dan mudah dijelaskan. Isolation Forest menangkap kombinasi pola tak biasa yang belum dirumuskan. Hasil pemeriksaan melatih ulang urutan prioritas.",
    { x: kx + 0.3, y: 5.3, w: kw - 0.55, h: 1.15, fontSize: 14 });
  text(s, "Stack: Python · FastAPI · PostgreSQL · scikit-learn · dashboard web   |   Keamanan: enkripsi, akses berbasis peran, audit log, NIK dipseudonimisasi",
    { x: X, y: 6.62, w: CW, h: 0.28, fontSize: 12, color: S.muted });
  s.addNotes("Revisi: rumus kalkulator kini memuat plafon upah iuran Rp12 jt (Perpres 64/2020, verifikasi sebelum submit) dan ada jawaban 'kenapa AI, bukan aturan saja'.");

  // ===================== 9. DATA & ASUMSI =====================
  s = lightSlide("Teknis & data", "04 · DATA & ASUMSI", "Data yang dipakai, dan batasnya");
  const hdr = { bold: true, color: S.ink, fill: { color: S.mint } };
  const rows9 = [
    ["Kepesertaan & upah PPU", "BPJS Kesehatan", "Sintetis, pelanggaran disisipkan blind"],
    ["Kepesertaan per segmen", "Portal Data BPJS Kesehatan", "Publik, sudah diambil (30 Sep 2026)"],
    ["UMP / UMK", "Kemnaker, Pemda", "Publik"],
    ["Upah per lapangan usaha", "BPS Sakernas Agustus 2025", "Publik; generator dikalibrasi (ρ = 0,90)"],
    ["Skala usaha & KBLI", "OSS / NIB", "Proxy sintetis"],
    ["Kepesertaan BPJS TK", "BPJS Ketenagakerjaan", "Fase lanjut, butuh kerja sama"],
  ];
  s.addTable([
    [{ text: "Data", options: hdr }, { text: "Sumber", options: hdr }, { text: "Status di prototype", options: hdr }],
    ...rows9.map((r) => r.map((t) => ({ text: t, options: { fill: { color: S.white } } }))),
  ], { x: X, y: 2.0, w: CW, colW: [3.7, 3.6, CW - 7.3], fontFace: THEME.bodyFontFace, fontSize: 15, color: S.ink, border: { type: "solid", pt: 0.75, color: HEX.line }, rowH: 0.42, margin: [0, 0.12, 0, 0.12], valign: "middle", objectName: "tabel-data" });
  card(s, X, 5.2, CW, 1.4, { fill: S.mint, noLine: true });
  kicker(s, "ASUMSI & KETERBATASAN", X + 0.3, 5.36, 6);
  text(s, bullets([
    "Pola data sintetis belum tentu sama dengan pola riil; divalidasi saat pilot",
    "Benchmark sektor lemah di wilayah dengan data sedikit; skornya diberi keyakinan rendah",
  ], { gap: 4 }), { x: X + 0.3, y: 5.7, w: CW - 0.6, h: 0.8, fontSize: 15 });
  s.addNotes("Baris baru: kepesertaan per segmen dari Portal Data BPJS (sudah di-scrape) dan upah BPS Sakernas Agustus 2025 (sekunder via CNBC; cocokkan ke bps.go.id). Kalibrasi: urutan rata-rata upah antarsektor di generator berkorelasi Spearman 0,90 dengan BPS.");

  // ===================== 10. VALIDASI DATA SINTETIS (baru) =====================
  s = lightSlide("Teknis & data", "04 · DESAIN VALIDASI", "Data sintetis yang sengaja dibuat sulit");
  const v = [
    [fa.FaBuilding, "Dunia jujur", "5.000 badan usaha, ±450 rb pekerja, 1,3 jt baris upah 2021–2025"],
    [fa.FaUserSecret, "Penyisipan blind", "15% pelanggar, seed rahasia, kasus mudah & sulit, 1–2 modus"],
    [fa.FaMask, "Hard negative", "±500 usaha patuh yang tampak mencurigakan: padat karya di UMK, UMKM sah di bawah UMK, PHK massal sah"],
    [fa.FaFlaskVial, "Uji di data baru", "Mesin dinilai pada dataset holdout yang tidak pernah dilihat saat penyetelan"],
  ];
  const vw = (CW - 0.9) / 4;
  for (let i = 0; i < 4; i++) {
    const [ic, h, d] = v[i], x = X + i * (vw + 0.3);
    card(s, x, 2.05, vw, 3.15);
    await iconBadge(s, ic, x + 0.28, 2.33);
    text(s, `${i + 1}`, { x: x + vw - 0.75, y: 2.35, w: 0.5, h: 0.5, fontFace: THEME.headFontFace, fontSize: 22, bold: true, color: S.green, align: "right" });
    text(s, h, { x: x + 0.28, y: 3.12, w: vw - 0.5, h: 0.4, fontFace: THEME.headFontFace, fontSize: 18, bold: true });
    text(s, d, { x: x + 0.28, y: 3.58, w: vw - 0.48, h: 1.5, fontSize: 14, color: S.muted });
  }
  const chips = ["Kebocoran label: metadata AUC ≈ 0,5", "Upah dikalibrasi ke BPS (ρ = 0,90)", "Label hanya dibaca evaluator", "Precision dilaporkan terpisah: mudah vs sulit"];
  const chw = (CW - 0.6) / 4;
  chips.forEach((t, i) => {
    const x = X + i * (chw + 0.2);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.5, w: chw, h: 0.75, rectRadius: 0.12, fill: { color: S.mint }, line: { type: "none" }, objectName: oid("cek") });
    text(s, t, { x: x + 0.15, y: 5.5, w: chw - 0.3, h: 0.75, fontSize: 14, bold: true, color: S.green, align: "center", valign: "middle" });
  });
  s.addNotes("Slide baru (to-do revisi). Generator: generator/ di repo. Pelanggaran disisipkan oleh anggota yang tidak membangun model, dengan seed rahasia; folder label terpisah. Audit kebocoran: AUC metadata ≈ 0,5, beda missingness antar kelas ≤ 0,7%.");

  // ===================== 11. HASIL (baru) =====================
  pres.addSection({ title: "Hasil" });
  s = lightSlide("Hasil", "05 · HASIL PROTOTYPE", "Memeriksa yang tepat, lebih dulu");
  const chartBase = {
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 13, dataLabelFontFace: "+mn-lt", dataLabelColor: HEX.ink,
    catAxisLabelColor: HEX.ink, catAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 13,
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
    showTitle: true, titleFontFace: "+mj-lt", titleFontSize: 15, titleColor: HEX.ink, barGapWidthPct: 55,
  };
  card(s, X, 2.0, 5.0, 4.55);
  s.addChart(pres.charts.BAR, [{ name: "Precision", labels: ["Pilih acak", "Aturan tunggal terbaik", "PayRay"], values: [150, 538, 684] }], {
    ...chartBase, x: X + 0.15, y: 2.1, w: 4.7, h: 4.3, barDir: "col", title: "Precision pada 10% skor tertinggi",
    chartColors: [HEX.mist, HEX.mist, HEX.green], valAxisMaxVal: 850, valAxisMinVal: 0, dataLabelFormatCode: '#0\\,0"%"', objectName: "grafik-precision",
  });
  card(s, X + 5.3, 2.0, 3.5, 4.55);
  s.addChart(pres.charts.BAR, [{ name: "Iuran", labels: ["Pilih acak", "PayRay"], values: [53, 775] }], {
    ...chartBase, x: X + 5.45, y: 2.1, w: 3.2, h: 4.3, barDir: "col", title: "Rp miliar/thn per 100 pemeriksaan",
    chartColors: [HEX.mist, HEX.green], valAxisMaxVal: 950, valAxisMinVal: 0, dataLabelFormatCode: '0\\,00', objectName: "grafik-iuran",
  });
  const sx = X + 9.1, sw = CW - 9.1;
  [["4,6×", "lebih tepat sasaran dibanding pemilihan acak"], ["14,6×", "iuran tertangkap per 100 pemeriksaan vs acak"], ["2,7%", "UMKM patuh salah ditandai (target ≤ 5%)"]].forEach(([b, l], i) => {
    text(s, b, { x: sx, y: 2.0 + i * 1.5, w: sw, h: 0.7, fontFace: THEME.headFontFace, fontSize: 36, bold: true, color: S.green });
    text(s, l, { x: sx, y: 2.7 + i * 1.5, w: sw, h: 0.65, fontSize: 14, color: S.muted });
  });
  text(s, "Data simulasi holdout (5.000 badan usaha, tidak pernah dilihat saat penyetelan). Mesin aturan + Isolation Forest menilai tanpa label.", { x: X, y: 6.62, w: CW, h: 0.28, fontSize: 12, color: S.muted });
  s.addNotes("Slide baru. Angka dari hasil_holdout/laporan_akurasi.md (seed dunia 2026, seed injeksi berbeda). Aturan tunggal terbaik = rasio pekerja vs OSS (53,8%). Data dev: 69,4% / 4,63×. Akui kelemahan bila ditanya: recall modus sulit 18–37%, salah tandai menengah/besar ±6%.");

  // ===================== 12. ALUR KERJA PETUGAS (baru) =====================
  s = lightSlide("Hasil", "05 · ALUR KERJA PETUGAS", "PayRay di meja petugas pemeriksa");
  const flow = [
    [fa.FaMagnifyingGlassChart, "Scan berkala", "Semua badan usaha diskor tiap periode"],
    [fa.FaListOl, "Antrean prioritas", "Urut skor × keyakinan, dengan estimasi Rp"],
    [fa.FaFileLines, "Lembar hasil scan", "Alasan & bukti yang bisa diverifikasi"],
    [fa.FaUserCheck, "Pemeriksaan", "Keputusan & sanksi tetap di petugas"],
    [fa.FaRotate, "Hasil jadi label", "Urutan berikutnya makin tajam"],
  ];
  // tangkapan layar asli dashboard (dashboard/index.html?buka=BU04224)
  const iw = 7.4, ih = iw * 10 / 16, iy = 1.95;
  card(s, X - 0.06, iy - 0.06, iw + 0.12, ih + 0.12, { lineColor: HEX.line });
  s.addImage({ path: path.join(__dirname, "img", "dashboard_lembar_scan.png"), x: X, y: iy, w: iw, h: ih, objectName: "tangkapan-dashboard",
    altText: "Tangkapan layar dashboard PayRay: antrean pemeriksaan dan lembar hasil scan PT Cahaya Mandiri" });
  text(s, "Tangkapan layar asli prototype dashboard (data sintetis)", { x: X, y: iy + ih + 0.1, w: iw, h: 0.28, fontSize: 12, color: S.muted });
  const fx = X + iw + 0.4, fwid = W - X - fx;
  for (let i = 0; i < 5; i++) {
    const [ic, h, d] = flow[i], y = iy + i * 0.64;
    await iconBadge(s, ic, fx, y + 0.02, false, 0.48);
    text(s, h, { x: fx + 0.62, y, w: fwid - 0.62, h: 0.3, fontFace: THEME.headFontFace, fontSize: 15, bold: true });
    text(s, d, { x: fx + 0.62, y: y + 0.3, w: fwid - 0.62, h: 0.28, fontSize: 13, color: S.muted });
  }
  card(s, fx, 5.3, fwid, 1.33, { fill: S.mint, noLine: true });
  text(s, "21,8% → 26,8%", { x: fx + 0.25, y: 5.42, w: fwid - 0.4, h: 0.5, fontFace: THEME.headFontFace, fontSize: 24, bold: true, color: S.green });
  text(s, "precision putaran berikutnya setelah belajar dari 500 hasil pemeriksaan (simulasi)", { x: fx + 0.25, y: 5.92, w: fwid - 0.45, h: 0.62, fontSize: 13 });
  s.addNotes("Tangkapan layar asli dari dashboard/index.html (HTML statis, dibangun dari output mesin; buka langsung di browser). Tombol Tandai wajar / Temuan terbukti menyimpan label umpan balik dan bisa diunduh sebagai CSV. Siklus umpan balik disimulasikan di engine/feedback.py: precision putaran 2 naik 21,8% → 26,8%, iuran tertangkap Rp1,60 M → Rp1,81 M (holdout). Waktu menyusun daftar: 5.000 badan usaha diskor dalam hitungan detik.");

  // ===================== 13. KEMATANGAN =====================
  s = lightSlide("Hasil", "05 · TINGKAT KEMATANGAN", "Posisi kami, dan target saat submit");
  const stages = [["Ide", "Konsep & desain solusi", "done"], ["Mockup", "Rancangan layar", "done"], ["Prototype", "Fitur inti berjalan, bisa didemokan", "now"], ["MVP", "Dipakai pengguna nyata", ""], ["Produk", "Teruji & siap skala", ""]];
  const stw = (CW - 0.8) / 5;
  stages.forEach(([h, d, st], i) => {
    const x = X + i * (stw + 0.2);
    card(s, x, 2.0, stw, 1.75, st === "now" ? { fill: S.mint, lineColor: HEX.green } : {});
    if (st) {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.2, y: 2.18, w: stw - 0.4, h: 0.34, rectRadius: 0.17, fill: { color: st === "now" ? S.green : S.ink }, line: { type: "none" }, objectName: oid("status-tahap") });
      text(s, st === "now" ? "Target submit" : "Selesai", { x: x + 0.2, y: 2.18, w: stw - 0.4, h: 0.34, fontSize: 13, bold: true, color: S.white, align: "center", valign: "middle" });
    }
    text(s, h, { x: x + 0.2, y: 2.62, w: stw - 0.4, h: 0.4, fontFace: THEME.headFontFace, fontSize: 19, bold: true, color: st ? (st === "now" ? S.green : S.ink) : S.muted });
    text(s, d, { x: x + 0.2, y: 3.05, w: stw - 0.4, h: 0.6, fontSize: 14, color: S.muted });
  });
  text(s, "Sudah berjalan", { x: X, y: 4.1, w: 5.5, h: 0.4, fontFace: THEME.headFontFace, fontSize: 19, bold: true });
  const doneItems = [["Generator data sintetis tervalidasi", true], ["Tiga modul scan + skor gabungan + reason code", true], ["Kalkulator estimasi, laporan akurasi & uji bias", true], ["Dashboard & lembar scan interaktif (HTML)", true]];
  for (let i = 0; i < doneItems.length; i++) {
    const [t, ok] = doneItems[i];
    s.addImage({ data: await icon(ok ? fa.FaCircleCheck : fa.FaCircleHalfStroke, ok ? HEX.green : HEX.muted), x: X, y: 4.62 + i * 0.47, w: 0.27, h: 0.27, objectName: oid("status-item") });
    text(s, ok ? t : `${t} (sedang dikerjakan)`, { x: X + 0.42, y: 4.58 + i * 0.47, w: 5.6, h: 0.36, fontSize: 15, color: ok ? S.ink : S.muted });
  }
  text(s, "Bukti yang dilampirkan", { x: X + 6.6, y: 4.1, w: 5, h: 0.4, fontFace: THEME.headFontFace, fontSize: 19, bold: true });
  text(s, bullets(["Link demo: [__]", "Video demo: [__]", "Repositori: [__]", "Status uji: internal, data sintetis"], { gap: 5 }), { x: X + 6.6, y: 4.58, w: 5, h: 1.9, fontSize: 15 });
  s.addNotes("Revisi: penanda 'Saat ini: Ide' dihapus. Isi link demo, video, dan repo sebelum submit.");

  // ===================== 14. RENCANA =====================
  pres.addSection({ title: "Rencana" });
  s = lightSlide("Rencana", "06 · RENCANA & KELAYAKAN", "Delapan minggu menuju prototype");
  const st14 = (t, c) => ({ text: t, options: { bold: true, color: c, fill: { color: S.white } } });
  const rows14 = [
    ["1–2", "Fondasi data", "Generator data sintetis + data benchmark publik terkumpul", st14("Selesai", S.green)],
    ["3–4", "Mesin scan", "Tiga modul scan + skor gabungan + reason code", st14("Selesai", S.green)],
    ["5–6", "Produk", "Dashboard, lembar hasil scan, kalkulator estimasi iuran", st14("Prototype HTML selesai", S.green)],
    ["7", "Validasi", "Laporan akurasi + uji bias per skala usaha", st14("Otomatis, tinggal finalisasi", S.green)],
    ["8", "Siap demo", "Video demo + proposal final", st14("Belum", S.muted)],
  ];
  s.addTable([
    ["Minggu", "Fokus", "Deliverable", "Status"].map((t) => ({ text: t, options: hdr })),
    ...rows14.map((r) => r.map((c) => (typeof c === "string" ? { text: c, options: { fill: { color: S.white } } } : c))),
  ], { x: X, y: 2.0, w: CW, colW: [1.2, 2.2, 5.6, CW - 9.0], fontFace: THEME.bodyFontFace, fontSize: 15, color: S.ink, border: { type: "solid", pt: 0.75, color: HEX.line }, rowH: 0.5, margin: [0, 0.12, 0, 0.12], valign: "middle", objectName: "tabel-rencana" });
  text(s, "Durasi disesuaikan dengan jadwal resmi Healthkathon 2026. Sumber daya: tim 3 orang, cloud server kecil, data publik + sintetis.", { x: X, y: 5.25, w: CW, h: 0.4, fontSize: 14, color: S.muted });
  s.addNotes("Status per 10 Okt 2026.");

  // ===================== 15. SETELAH KOMPETISI =====================
  s = lightSlide("Rencana", "06 · SETELAH KOMPETISI", "Dari prototype ke skala nasional");
  const phases = [
    ["FASE 1 · ±3 BULAN", "Pilot", ["1 Kantor Cabang, data riil berizin", "Kalibrasi model dengan hasil pemeriksaan", "Ukur hit rate vs cara saat ini"]],
    ["FASE 2 · ±6 BULAN", "Integrasi", ["Kerja sama data BPJS TK & OSS", "Scan Headcount & Status versi penuh", "Terhubung ke sistem internal"]],
    ["FASE 3 · BERTAHAP", "Skala nasional", ["Scan rutin setiap periode", "Model diperbarui dari umpan balik", "Dashboard per wilayah"]],
  ];
  phases.forEach(([k, h, items], i) => {
    const x = X + i * (bw + gap8);
    card(s, x, 2.0, bw, 3.1);
    kicker(s, k, x + 0.28, 2.25, bw - 0.5);
    text(s, h, { x: x + 0.28, y: 2.6, w: bw - 0.5, h: 0.45, fontFace: THEME.headFontFace, fontSize: 21, bold: true });
    text(s, bullets(items, { gap: 6 }), { x: x + 0.28, y: 3.15, w: bw - 0.5, h: 1.85, fontSize: 15 });
    if (i < 2) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + bw + gap8 / 2 - 0.2, y: 3.4, w: 0.4, h: 0.3, fill: { color: S.green }, line: { type: "none" }, objectName: oid("panah-fase") });
  });
  kicker(s, "KEBUTUHAN", X, 5.55, 1.6);
  ["Akses data berizin", "Mitra Kantor Cabang", "Infrastruktur aman", "Pendampingan pemeriksa"].reduce((x, t) => {
    const w = 0.22 + t.length * 0.105;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.45, w, h: 0.5, rectRadius: 0.25, fill: { color: S.mint }, line: { type: "none" }, objectName: oid("kebutuhan") });
    text(s, t, { x, y: 5.45, w, h: 0.5, fontSize: 14, align: "center", valign: "middle" });
    return x + w + 0.2;
  }, X + 1.75);
  s.addNotes("Fase lanjut termasuk cek 'pekerja masih aktif bekerja' dengan data BPJS TK.");

  // ===================== 16. METRIK =====================
  pres.addSection({ title: "Dampak" });
  s = lightSlide("Dampak", "07 · DAMPAK & METRIK", "Cara kami mengukur keberhasilan");
  const good = (t) => ({ text: t, options: { bold: true, color: S.green, fill: { color: S.white } } });
  const rows16 = [
    ["Precision pada 10% skor tertinggi", "≥ 70%", good("68,4%"), "Data sintetis berlabel (holdout)"],
    ["Hit rate vs pemilihan acak", "≈ 4,7×", good("4,6×"), "Simulasi, lalu pilot"],
    ["Iuran tertangkap per 100 pemeriksaan", "> acak", good("Rp7,7 M vs Rp0,53 M"), "Kalkulator PayRay"],
    ["Waktu menyusun daftar target", "Hari ke menit", good("Detik"), "Uji alur kerja"],
    ["Salah tandai pada UMKM patuh", "≤ 5%", good("2,7%"), "Uji bias per skala usaha"],
  ];
  s.addTable([
    ["Metrik", "Target", "Hasil prototype", "Cara ukur"].map((t) => ({ text: t, options: hdr })),
    ...rows16.map((r) => r.map((c) => (typeof c === "string" ? { text: c, options: { fill: { color: S.white } } } : c))),
  ], { x: X, y: 2.0, w: CW, colW: [4.2, 1.9, 2.6, CW - 8.7], fontFace: THEME.bodyFontFace, fontSize: 15, color: S.ink, border: { type: "solid", pt: 0.75, color: HEX.line }, rowH: 0.5, margin: [0, 0.12, 0, 0.12], valign: "middle", objectName: "tabel-metrik" });
  card(s, X, 5.3, CW, 0.85, { fill: S.mint, noLine: true });
  s.addImage({ data: await icon(fa.FaTriangleExclamation, HEX.green), x: X + 0.3, y: 5.55, w: 0.34, h: 0.34, objectName: "ikon-peringatan" });
  s.addText([{ text: "Semua angka adalah hasil pada " }, { text: "data simulasi", options: { bold: true } }, { text: ". Nilai riil baru diukur saat pilot." }],
    { isTextBox: true, x: X + 0.85, y: 5.3, w: CW - 1.1, h: 0.85, fontSize: 16, color: S.ink, margin: 0, valign: "middle", objectName: "catatan-metrik" });
  s.addNotes("Revisi: placeholder terisi. Precision 68,4% sedikit di bawah target 70%. Sampaikan jujur: target ≥70% dikejar lewat siklus umpan balik.");

  // ===================== 17. PENERIMA MANFAAT =====================
  s = lightSlide("Dampak", "07 · PENERIMA MANFAAT", "Siapa yang diuntungkan");
  const ben = [
    [fa.FaShieldHeart, "BPJS Kesehatan", "Pemeriksaan lebih tepat sasaran, penerimaan iuran naik."],
    [fa.FaUserGroup, "Pekerja", "Terdaftar sesuai upah dan status sebenarnya, tidak dipindah diam-diam ke segmen mandiri."],
    [fa.FaThumbsUp, "Pemberi kerja yang patuh", "Persaingan lebih adil, dan tidak diperiksa tanpa alasan yang jelas."],
    [fa.FaShieldHalved, "Sistem JKN", "Dana lebih berkelanjutan, gotong royong lebih adil."],
  ];
  const bw17 = (CW - 0.3) / 2;
  for (let i = 0; i < 4; i++) {
    const [ic, h, d] = ben[i], x = X + (i % 2) * (bw17 + 0.3), y = 2.0 + Math.floor(i / 2) * 2.2;
    card(s, x, y, bw17, 1.95);
    await iconBadge(s, ic, x + 0.3, y + 0.3);
    text(s, h, { x: x + 1.2, y: y + 0.32, w: bw17 - 1.5, h: 0.45, fontFace: THEME.headFontFace, fontSize: 20, bold: true });
    text(s, d, { x: x + 1.2, y: y + 0.82, w: bw17 - 1.5, h: 0.95, fontSize: 16, color: S.muted });
  }
  s.addNotes("Pemberi kerja patuh dilindungi: hard negative dan aturan per skala menekan salah tandai UMKM ke 2,7%.");

  // ===================== 18. RISIKO & ETIKA =====================
  s = lightSlide("Dampak", "08 · RISIKO, PRIVASI & ETIKA", "Dirancang aman sejak awal");
  const eth = [
    [fa.FaLock, "Perlindungan data (UU PDP)", ["Prototype 100% data sintetis", "Analisis agregat per badan usaha, NIK dipseudonimisasi", "Enkripsi, akses berbasis peran, audit log"]],
    [fa.FaScaleBalanced, "Bias & keterbatasan", ["UMKM dikecualikan dari upah minimum (PP 36/2021): aturan dibedakan per skala", "Wilayah minim data diberi keyakinan rendah"]],
    [fa.FaPeopleArrows, "Human-in-the-loop", ["PayRay hanya mengurutkan prioritas", "Keputusan pemeriksaan & sanksi tetap di petugas", "Hasil pemeriksaan kembali jadi label"]],
    [fa.FaGears, "Mitigasi risiko utama", ["Salah tandai → ambang skor + review petugas", "Model usang → retrain berkala dari umpan balik", "Kebocoran data → minimisasi data + enkripsi"]],
  ];
  for (let i = 0; i < 4; i++) {
    const [ic, h, items] = eth[i], x = X + (i % 2) * (bw17 + 0.3), y = 1.95 + Math.floor(i / 2) * 2.25;
    card(s, x, y, bw17, 2.05);
    await iconBadge(s, ic, x + 0.3, y + 0.25, false, 0.5);
    text(s, h, { x: x + 0.95, y: y + 0.28, w: bw17 - 1.2, h: 0.42, fontFace: THEME.headFontFace, fontSize: 18, bold: true });
    text(s, bullets(items, { gap: 3 }), { x: x + 0.3, y: y + 0.85, w: bw17 - 0.55, h: 1.1, fontSize: 14 });
  }
  text(s, "Tidak menggunakan data peserta JKN riil tanpa izin resmi dari pihak berwenang.", { x: X, y: 6.5, w: CW, h: 0.32, fontSize: 14, bold: true, color: S.green });
  s.addNotes("Revisi: footer kini konsisten dengan slide lain (dari layout).");

  // ===================== 19. TIM =====================
  pres.addSection({ title: "Tim & penutup" });
  s = lightSlide("Tim & penutup", "09 · PROFIL TIM · PLAN WITH US", "Teknis, data, dan produk");
  const team = [
    ["RH", HEX.green, "Rachdian Habi Yahya", "Ketua Tim · Data Scientist", ["Mahasiswa S2 Digital Business Strategy, Telkom University", "Peran: pemodelan, evaluasi, uji bias per skala usaha", "Menerjemahkan hasil model ke nilai bisnis & kebijakan"], "linkedin.com/in/rachdiaaan"],
    ["RS", "2A9D6F", "Rifqi Sigwan Nugraha", "Lead Engineer · Backend & AI", ["Lulusan IT, Telkom University", "Co-founder Plus The Site (agensi web & software)", "Python, FastAPI, PostgreSQL, multi-agent AI", "Publikasi ICORIS 2024 (pemodelan data IoT)"], null],
    ["MG", HEX.lime, "Muhammad Al Ghani", "Product Manager", ["UI/UX Designer di Torch.id", "Peran: kebutuhan petugas & alur kerja pemeriksaan", "Desain dashboard & lembar hasil scan, proposal & demo"], "linkedin.com/in/muhammad-al-ghani"],
  ];
  const liIcon = await icon(fa.FaLinkedin, HEX.green);
  team.forEach(([ini, col, name, role, items, li], i) => {
    const x = X + i * (cw2 + 0.3);
    card(s, x, 2.0, cw2, 4.05);
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: 2.3, w: 0.75, h: 0.75, fill: { color: col }, line: { type: "none" }, objectName: oid("avatar") });
    text(s, ini, { x: x + 0.3, y: 2.3, w: 0.75, h: 0.75, fontFace: THEME.headFontFace, fontSize: 24, bold: true, color: i === 2 ? S.ink : S.white, align: "center", valign: "middle" });
    if (li) {
      s.addImage({ data: liIcon, x: x + 1.25, y: 2.55, w: 0.24, h: 0.24, objectName: oid("ikon-linkedin") });
      text(s, [{ text: li.replace("linkedin.com", ""), options: { hyperlink: { url: "https://www." + li, tooltip: "LinkedIn " + name } } }],
        { x: x + 1.55, y: 2.5, w: cw2 - 1.8, h: 0.34, fontSize: 13, color: S.green, valign: "middle" });
    }
    text(s, name, { x: x + 0.3, y: 3.2, w: cw2 - 0.6, h: 0.4, fontFace: THEME.headFontFace, fontSize: 18, bold: true });
    text(s, role, { x: x + 0.3, y: 3.6, w: cw2 - 0.6, h: 0.32, fontSize: 14, bold: true, color: S.green });
    text(s, bullets(items, { gap: 3 }), { x: x + 0.3, y: 4.05, w: cw2 - 0.55, h: 1.9, fontSize: 14 });
  });
  text(s, "Kami membangun, mengukur, dan memastikan PayRay masuk akal di lapangan.", { x: X, y: 6.3, w: CW, h: 0.4, fontSize: 17, color: S.muted });
  s.addNotes("Tim Plan with Us. Tidak ada Domain Expert di tim: validasi aturan sebaiknya lewat konsultasi pakar HR-payroll/jaminan sosial dan disebut di sini bila ada.");

  // ===================== 20. PENUTUP =====================
  s = pres.addSlide({ masterName: "PAYRAY_COVER", sectionTitle: "Tim & penutup" });
  s.addText([{ text: "Pay", options: { color: S.white } }, { text: "Ray", options: { color: S.lime } }],
    { isTextBox: true, x: 0, y: 2.05, w: W, h: 1.45, fontFace: THEME.headFontFace, fontSize: 92, bold: true, align: "center", margin: 0, valign: "top", objectName: "judul-penutup" });
  text(s, "Memeriksa yang tepat, lebih dulu.", { x: 0, y: 3.6, w: W, h: 0.6, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: S.white, align: "center" });
  text(s, "Rontgen kepatuhan pemberi kerja untuk JKN yang lebih kuat.", { x: 0, y: 4.3, w: W, h: 0.45, fontSize: 20, color: HEX.mist, align: "center" });
  text(s, "Tim Plan with Us · rachdiaaan@gmail.com", { x: 0, y: 5.0, w: W, h: 0.4, fontSize: 16, color: HEX.mist, align: "center" });
  s.addNotes("Penutup. Kontak: email ketua tim.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("OK", OUT);
}

build().catch((e) => { console.error(e); process.exit(1); });
