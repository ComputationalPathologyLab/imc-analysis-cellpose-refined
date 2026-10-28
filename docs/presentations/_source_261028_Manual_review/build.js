const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/Users/rashid/.claude/skills/synced/8443690f-80f7-42d6-a1e4-04ae8172d321_0da9667d-55a5-486a-b125-a34bd9fc1041/pptx/scripts/apply_theme.js");
const OUT = process.argv[2];
const THEME = { name: "CHS IMC", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "222222", lt1: "FFFFFF", dk2: "3A3F47", lt2: "F2F3F5", accent1: "B5446E", accent2: "5B6C7D",
            accent3: "9AA5B1", accent4: "D9DDE3", accent5: "2F6F73", accent6: "C9A227", hlink: "2F6F73", folHlink: "5B6C7D" } };
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Rashid Hussain";
pres.title = "Manual review applied to the cells";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
pres.defineSlideMaster({ title: "CONTENT", background: { color: "FFFFFF" }, margin: [0.5, 0.6, 0.6, 0.6],
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.9, fontSize: 28, bold: true,
    color: C.text1, fontFace: "Calibri", valign: "top", align: "left", margin: 0 }, text: "" } }] });
const P = (t, o) => ({ text: t, options: { breakLine: true, ...o } });
const L = (t, o) => ({ text: t, options: { ...o } });
const cell = (t, o) => ({ text: t, options: o || {} });
const H = (t) => cell(t, { bold: true, color: C.text2 });
const mono = { fontFace: "Courier New" };
function table(s, rows, o) {
  s.addTable([rows[0].map(H), ...rows.slice(1).map((r, i) => r.map((t, j) => cell(t, {
    color: C.text1, ...(j === 0 ? mono : {}), fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" } })))],
    { x: 0.6, w: 12.1, fontFace: "Calibri", valign: "middle", border: { type: "none" }, margin: [0.03, 0.1, 0.03, 0.1], ...o });
}
let s;

// 1 what script 10 does
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("Applying the manual review to the cells (script 10)", { placeholder: "title" });
s.addText([
  P("For every core, the pathologist's shapes are laid over the Cellpose mask:", { bold: true }),
  P("1.  Check the review files are unchanged (fingerprints in MANIFEST.sha256)"),
  P("2.  Paint the shapes onto the pixel grid: one image for the evaluable area, one for all excluded patches together"),
  P("3.  For each cell: its centre point, and the share of its pixels on excluded patches"),
  P("4.  Give each cell a label"),
  P("5.  Area for densities = evaluable area minus excluded area"),
  P(" ", { fontSize: 6 }),
  P("Labels", { bold: true }),
  P("centre outside the evaluable area → outside_evaluable_area", { bullet: true }),
  P("more than 75% on patches → aggregate_removed", { bullet: true }),
  P("more than 0%, up to 75% → phenotype_not_assessable", { bullet: true }),
  P("0% → clean", { bullet: true }),
  P(" ", { fontSize: 6 }),
  P("The rules are the reviewer's own code (apply_manual_review.py), used unchanged. Only shapes and positions are used, no marker values.", { color: "555555" }),
], { isTextBox: true, x: 0.6, y: 1.4, w: 6.9, h: 4.7, fontSize: 15, color: C.text1, valign: "top", margin: 0, paraSpaceAfter: 5 });
s.addImage({ path: path.join(__dirname, "fig", "step3_zoom_ROI001_E10_crop.png"), x: 7.75, y: 1.45, w: 5.2, h: 3.86, objectName: "zoom ROI001_E10" });
s.addText([
  L("Checks: ", { bold: true }),
  L("145 review files unchanged · area for densities identical to the release in all 136 cores · all 79,739 cells of cells.csv labelled once, same area · no errors.")],
  { isTextBox: true, x: 0.6, y: 6.3, w: 12.1, h: 0.6, fontSize: 13, color: "555555", margin: 0, valign: "top" });
s.addText("ROI001_E10, 110 × 110 µm crop. Outline colour = label; pink = excluded patch; cyan = evaluable area edge.",
  { isTextBox: true, x: 7.75, y: 5.45, w: 5.2, h: 0.4, fontSize: 10, color: "666666", margin: 0 });

// 2 cell_flags.csv
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("cell_flags.csv: one row per cell (79,739 rows)", { placeholder: "title" });
table(s, [
  ["Column", "Meaning", "Example"],
  ["Image", "Core (ROI) name, without .tiff", "ROI001_E10"],
  ["mask_file", "Mask file the cell comes from", "ROI001_E10.tiff"],
  ["Object", "Cell number in the mask; same as Object in cells.csv", "18"],
  ["area_px", "Number of pixels of the cell (1 px = 1 µm²)", "31"],
  ["centroid_x", "Centre of the cell, column (x) + 0.5", "605.21"],
  ["centroid_y", "Centre of the cell, row (y) + 0.5", "34.79"],
  ["in_evaluable_area", "Is the centre inside the evaluable area polygon?", "True"],
  ["frac_in_evaluable", "Share of the cell's pixels inside the evaluable area (0–1)", "1.0"],
  ["frac_in_excluded", "Share of the cell's pixels on excluded patches (0–1)", "0.3226"],
  ["cell_status", "Label: clean / phenotype_not_assessable / aggregate_removed / outside_evaluable_area", "phenotype_not_assessable"],
], { y: 1.4, colW: [2.3, 6.9, 2.9], fontSize: 14, rowH: 0.42 });
s.addText("Example: ROI001_E10, cell 18. Its centre is inside the evaluable area and 10 of its 31 pixels (32%) lie on an excluded patch, so it is counted but not phenotyped.",
  { isTextBox: true, x: 0.6, y: 6.25, w: 12.1, h: 0.6, fontSize: 13, color: "555555", margin: 0, valign: "top" });

// 3 core_areas.csv
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("core_areas.csv: one row per core (136 rows)", { placeholder: "title" });
table(s, [
  ["Column", "Meaning", "ROI001_E10"],
  ["roi", "Core (ROI) name", "ROI001_E10"],
  ["height_px, width_px", "Image size in pixels", "1000, 1000"],
  ["evaluable_area_px", "Pixels inside the evaluable area", "771,984"],
  ["excluded_in_evaluable_px", "Excluded pixels inside the evaluable area", "7,315"],
  ["denominator_px / _mm2", "Area for densities = evaluable − excluded", "764,669 / 0.765"],
  ["denominator_matches_release", "Same as the pathologist's own area table?", "True"],
  ["clean … outside_evaluable_area", "Number of cells with each label (4 columns)", "989 · 104 · 20 · 20"],
  ["facility_position", "Position on the TMA slide", "E10"],
  ["patient_id", "Patient number (16 − facility column)", "6"],
  ["region", "Sampling region expected from the TMA row", "High inflammatory"],
  ["dna_status", "Nuclear staining of the core: valid / intermediate / dna_negative", "intermediate"],
  ["he_core", "Core on H&E: present / partial", "present"],
  ["evaluable_for_IMC", "Core included in the analysis? (yes 121, no 15)", "yes"],
  ["exclusion_reason", "Why a core is excluded", "(blank)"],
  ["matrix_pct", "% of the core that is chondroid matrix on H&E", "10"],
  ["special_area_flag", "H&E finding not drawn on IMC: hemorrhage / necrosis / fold", "hemorrhage_not_drawn"],
], { y: 1.25, colW: [3.3, 6.3, 2.5], fontSize: 12, rowH: 0.29 });
s.addText("The last nine columns are copied from the pathologist's core review sheet; the rest are computed by script 10.",
  { isTextBox: true, x: 0.6, y: 6.95, w: 12.1, h: 0.35, fontSize: 13, color: "555555", margin: 0, valign: "top" });

(async () => { await pres.writeFile({ fileName: OUT }); await applyTheme(OUT, THEME); })();
