const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/Users/rashid/.claude/skills/synced/8443690f-80f7-42d6-a1e4-04ae8172d321_0da9667d-55a5-486a-b125-a34bd9fc1041/pptx/scripts/apply_theme.js");
const OUT = process.argv[2];
const F = (n) => path.join(__dirname, "fig", n);
const THEME = { name: "CHS IMC", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "222222", lt1: "FFFFFF", dk2: "3A3F47", lt2: "F2F3F5", accent1: "B5446E", accent2: "5B6C7D",
            accent3: "9AA5B1", accent4: "D9DDE3", accent5: "2F6F73", accent6: "C9A227", hlink: "2F6F73", folHlink: "5B6C7D" } };
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Rashid Hussain";
pres.title = "IMC analysis of the chondrosarcoma TMA";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
pres.defineSlideMaster({ title: "TITLE", background: { color: "FFFFFF" }, objects: [
  { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.3, w: 11.5, h: 1.6, fontSize: 36, bold: true, color: "222222", fontFace: "Calibri", valign: "bottom", align: "left", margin: 0 }, text: "" } },
  { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.1, w: 11.5, h: 1.2, fontSize: 18, color: "555555", fontFace: "Calibri", valign: "top", align: "left", margin: 0 }, text: "" } } ] });
pres.defineSlideMaster({ title: "CONTENT", background: { color: "FFFFFF" }, margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
  { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.9, fontSize: 28, bold: true, color: C.text1, fontFace: "Calibri", valign: "top", align: "left", margin: 0 }, text: "" } } ] });

const body = (s, runs, o) => s.addText(runs, { isTextBox: true, fontSize: 15, color: C.text1, valign: "top", margin: 0, paraSpaceAfter: 8, ...o });
const note = (s, t, o) => s.addText(t, { isTextBox: true, fontSize: 12, italic: false, color: "666666", margin: 0, ...o });
const img = (s, f, x, y, w, h) => s.addImage({ path: F(f), x, y, w, h, objectName: f });
const P = (t, o) => ({ text: t, options: { breakLine: true, ...o } });
const L = (t, o) => ({ text: t, options: { ...o } });
function bigNum(s, n, label, x, y, w, color) {
  s.addText([{ text: n, options: { fontSize: 26, bold: true, color: C.text1, fontFace: "Calibri", breakLine: true } },
             { text: label, options: { fontSize: 13, color: C.text2 } }], { isTextBox: true, x, y, w, h: 1.3, margin: 0, valign: "top" });
}
const cell = (t, o) => ({ text: t, options: o || {} });
const H = (t, o) => cell(t, { bold: true, color: C.text2, ...o });
let s;

// 1 title
pres.addSection({ title: "Intro" });
s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Intro" });
s.addText("IMC analysis of the chondrosarcoma TMA", { placeholder: "title" });
s.addText("From the raw images to a single-cell table\nRashid Hussain · October 2026", { placeholder: "body" });
s.addNotes("This covers notebook 01: everything from the raw files to the table with one row per cell. What happens to the cells after that is a separate talk.");

// 2 steps
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Intro" });
s.addText("The steps in notebook 01", { placeholder: "title" });
body(s, [
  P("1.  Check the raw files: 136 ROI folders, 43 TIFFs each", { indentLevel: 0 }),
  P("2.  Write panel.csv: which channel is which and what it is used for", { indentLevel: 0 }),
  P("3.  Stack the 43 channels into one image per ROI, removing hot pixels on the way", { indentLevel: 0 }),
  P("4.  Segment the cells with Cellpose: 79,739 objects", { indentLevel: 0 }),
  P("5.  Measure the intensity of every channel in every cell", { indentLevel: 0 }),
  P("6.  Measure the shape and position of every cell", { indentLevel: 0 }),
  P("7.  Find each cell's neighbours", { indentLevel: 0 }),
  P("8.  Export everything as one table, an AnnData file and one graph per ROI", { indentLevel: 0 }),
], { x: 0.6, y: 1.5, w: 7.6, h: 4.6, fontSize: 17, paraSpaceAfter: 10 });
body(s, [P("Each step is a script called from the notebook. It writes its own files and a log, and a check cell after it prints what was produced."),
         P("Steps 3 and 5 to 8 use steinbock 0.16.1 (Docker). Cellpose 4.2.1 runs in Python."),
         L("The raw files are only read, never changed.")],
     { x: 8.7, y: 1.6, w: 4.1, h: 4.6, fontSize: 15, color: "555555" });
s.addNotes("The notebook works for any subset of ROIs: one ROI, a test pair, or the whole array. Panel, ROI counts and summaries are worked out from the files present, not hard-coded.");

// 2b setup
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Intro" });
s.addText("Set-up: the computer and the software", { placeholder: "title" });
const su = [["Computer", "MacBook Air, Apple M4 (10 cores), 16 GB memory, macOS 26.6"],
            ["Python", "3.14.6 in a virtual environment (/Users/rashid/Installations/venve)"],
            ["Segmentation", "Cellpose 4.2.1 with PyTorch 2.13.0, run on the CPU (no GPU)"],
            ["Image tables", "NumPy 2.4.3, pandas 3.0.1, tifffile 2026.3.3"],
            ["Measurement", "steinbock 0.16.1, run in Docker (Docker Desktop 29.2.1)"],
            ["Disk", "about 12 GB for the stacked images and masks of 136 ROIs"]];
s.addTable(su.map((r, i) => r.map((t, j) => cell(t, { bold: j === 0, color: C.text1, fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" } }))),
  { x: 0.6, y: 1.45, w: 12.1, colW: [2.3, 9.8], fontSize: 15, fontFace: "Calibri", rowH: 0.45, valign: "middle", border: { type: "none" }, margin: [0.04, 0.12, 0.04, 0.12] });
body(s, [P("Every steinbock step is one Docker command. The data folder is mounted inside the container as /data, so steinbock reads and writes the project's own files:"),
         P("docker run --rm -v <project>/data:/data ghcr.io/bodenmillergroup/steinbock:0.16.1 measure intensities", { fontFace: "Courier New", fontSize: 12.5 }),
         L("Each script writes the exact command, the versions and the settings to its log in logs/, so the run can be repeated as it was.", { color: "555555" })],
     { x: 0.6, y: 4.35, w: 12.1, h: 2.2, fontSize: 15 });
s.addNotes("Docker Desktop has to be running before the measuring steps. Cellpose ran overnight on the CPU; the steinbock steps take seconds to a few minutes each.");

// 2c re-run
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Intro" });
s.addText("What this re-run fixed, from the pipeline review", { placeholder: "title" });
const rr = [["1.1", "No hot-pixel filter in the first run", "steinbock filter on every channel before stacking; 31,416 pixels replaced, same count as in the review"],
            ["1.3", "10 ROIs named ROI032_ROI_032 … with no core position", "Named after their cores at stacking; raw folders untouched"],
            ["1.4", "Size limit of 1000 × 1000 would drop 27 ROIs", "Limit set to 0; all 136 ROIs kept"],
            ["2.2", "Segmentation markers included CD20, CD138, CD163", "New sets: nuclei DNA1, DNA2, SOX9; cell bodies S100, CD68, αSMA, CD31, CD3, CD66b. Fixed scaling tested, not adopted"],
            ["2.3", "Technical channels mixed in with markers", "analysis column in panel.csv; 6 channels flagged"],
            ["2.6", "Notebook text and code disagreed on the channels", "Text now matches the code"],
            ["4.4", "No record of versions or settings; a crash meant starting over", "Versions, model and settings logged; a stopped run resumes ROI by ROI"],
            ["5.1", "Measurements made on the old images and masks", "Steps 5–8 re-run on the new ones"]];
s.addTable([[H("Item"), H("Problem"), H("What was done")], ...rr.map((r, i) => r.map((t, j) => cell(t, { bold: j === 0, color: C.text1, fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" } })))],
  { x: 0.6, y: 1.4, w: 12.1, colW: [0.8, 4.6, 6.7], fontSize: 13, fontFace: "Calibri", rowH: 0.5, valign: "middle", border: { type: "none" }, margin: [0.03, 0.1, 0.03, 0.1] });
body(s, [L("Result: all 136 ROIs segmented with no errors, 79,739 objects (79,452 before, +0.4%).", { bold: true })], { x: 0.6, y: 6.35, w: 12.1, h: 0.45, fontSize: 15 });
s.addNotes("Item numbers are those of the review document of 4 October. Each item was tested on two ROIs first (ROI032_I13 and ROI107_A5), then run on all 136.");

// 3 array
pres.addSection({ title: "Raw data" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Raw data" });
s.addText("The array: 15 patients, 11 areas each", { placeholder: "title" });
img(s, "tma_acquired.png", 0.5, 1.5, 8.7, 3.96);
body(s, [P("One column per patient, one row per area of the tumour, so the row already tells you what a core should contain."),
         P("136 of the 165 positions were imaged, one ROI per core. 21 cores were lost when the block was cut, and 8 normal-tissue cores in row K were skipped to save instrument time."),
         L("All 136 ROIs go through the notebook.", {})],
     { x: 9.6, y: 1.6, w: 3.2, h: 4.9 });
note(s, "Dashed boxes: no image. Chordoma (153 ROIs) was imaged too and will follow.", { x: 0.6, y: 5.6, w: 8.5, h: 0.35 });
s.addNotes("Hyperion, Humanitas imaging unit, 1 µm per pixel.");

// 4 one ROI
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Raw data" });
s.addText("What one ROI holds", { placeholder: "title" });
img(s, "roi_channels.png", 0.5, 1.4, 8.4, 4.45);
body(s, [P("One folder per ROI with 43 single-channel OME-TIFFs, named channel_marker, e.g. 164Dy_S100.ome.tiff."),
         P("35 antibodies, 2 DNA channels (191Ir, 193Ir) and 6 technical channels (127I, 131Xe, 134Xe, 138Ba, 208Pb, 80ArAr)."),
         L("Each pixel is one laser shot, 1 µm across, holding a count of ions. Most pixels hold 0, 1 or 2.", {})],
     { x: 9.3, y: 1.5, w: 3.5, h: 4.6 });
note(s, "ROI072_H14, one 500 × 500 µm corner, raw counts. Step 1 only checks that every folder and file is there.", { x: 0.6, y: 6.0, w: 8.4, h: 0.5 });
s.addNotes("The facility exported these TIFFs from the 24 GB .mcd file. Barium and lead are not markers; argon is the plasma background.");

// 5 panel
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Raw data" });
s.addText("panel.csv: the list that says which channel is which", { placeholder: "title" });
const pr = [["191Ir", "DNA1", "1", "1", "1"], ["193Ir", "DNA2", "1", "1", "1"], ["146Nd", "SOX9", "1", "1", "1"], ["164Dy", "S100", "1", "2", "1"],
            ["141Pr", "CD68", "1", "2", "1"], ["115In", "CD20", "1", "", "1"], ["138Ba", "138Ba", "1", "", "0"], ["80ArAr", "80ArAr", "1", "", "0"]];
s.addTable([[H("channel"), H("name"), H("keep", { align: "center" }), H("cellpose", { align: "center" }), H("analysis", { align: "center" })],
  ...pr.map((r, i) => r.map((t, j) => cell(t, { align: j > 1 ? "center" : "left", fontFace: j === 0 ? "Courier New" : "Calibri",
     color: (j === 4 && t === "0") ? C.accent1 : C.text1, fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" } })))],
  { x: 0.6, y: 1.5, w: 6.4, colW: [1.4, 1.4, 1.2, 1.2, 1.2], fontSize: 15, fontFace: "Calibri", rowH: 0.47, valign: "middle", border: { type: "none" }, margin: [0.04, 0.12, 0.04, 0.12] });
note(s, "8 of the 43 rows.", { x: 0.6, y: 5.85, w: 6, h: 0.3 });
body(s, [P("Written by a script from the file names, so nothing is typed by hand."),
         P("keep: stack this channel (all 43 are kept).", { bullet: true }),
         P("cellpose: 1 goes into the nuclear image, 2 into the cell-body image.", { bullet: true }),
         P("analysis: 0 marks the 6 technical channels, so they stay in the files but never enter the analysis.", { bullet: true }),
         L("A second table records which ROI has which channel. Here all 136 ROIs have all 43, but with chordoma in the mix that will not be true.", { color: C.text2 })],
     { x: 7.5, y: 1.5, w: 5.3, h: 4.9 });
s.addNotes("The panel is the union of channel-marker pairs across all ROI folders. If a ROI lacks a channel, it gets a zero-filled channel at stacking and the log says so.");

// 6 stacking
pres.addSection({ title: "Preprocessing" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Preprocessing" });
s.addText("Stacking: one 43-channel image per ROI", { placeholder: "title" });
const hk = [
  ["Names", "10 ROIs came as ROI032_ROI_032 … ROI041, with no core position", "Matched to their cores from the facility's list, in the code"],
  ["Sizes", "27 ROIs are not 1 × 1 mm (0.23 to 1.18 mm²), mostly row A at the slide edge", "All kept; the 1000 × 1000 minimum is now 0, so a re-export from the .mcd would keep them too"],
  ["Hot pixels", "Isolated spikes in single pixels", "Filtered in every channel before stacking (next section)"],
  ["Counts", "The TIFF export kept whole numbers only, so intensities are a little low (8–14% in ROI032)", "Noted as a limitation; the .mcd keeps the decimals"]];
s.addTable([[H("What"), H("In the raw files"), H("What the stacking step does")],
  ...hk.map((r, i) => r.map((t, j) => cell(t, { bold: j === 0, color: C.text1, fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" } })))],
  { x: 0.6, y: 1.5, w: 12.1, colW: [1.9, 5.5, 4.7], fontSize: 15, fontFace: "Calibri", rowH: [0.5, 0.9, 0.9, 0.75, 0.9], valign: "middle", border: { type: "none" }, margin: [0.08, 0.15, 0.08, 0.15] });
body(s, [L("Output: data/img/ROI072_H14.tiff and so on, channels in panel order, plus images.csv with the size of each image. Every image now carries its core name, which is what all later tables join on.", {})],
     { x: 0.6, y: 5.7, w: 12.1, h: 0.8, fontSize: 14, color: C.text2 });
s.addNotes("Stacks keep the integer counts of the TIFFs; the filter only swaps in a neighbouring integer.");

// H1 what a pixel holds
pres.addSection({ title: "Hot pixels" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hot pixels" });
s.addText("Hot pixels 1: what a normal pixel holds", { placeholder: "title" });
img(s, "hp_hist.png", 0.6, 1.5, 7.4, 4.16);
body(s, [P("The laser fires at one 1 µm spot, the tissue there is vaporised, and the detector counts the ions of each metal that arrive. That count is the pixel value: a whole number. A CD31 value of 3 means 3 ions of 144Nd, the CD31 tag."),
         P("In this ROI (1000 × 1000 = 1 million pixels), 91% of CD31 pixels hold 0 ions and 8% hold 1. Only 51 pixels reach 50 or more. Even inside a vessel a pixel usually holds a few to a few tens of ions."),
         L("The single highest value is 816, and its neighbours hold 0 to 3. A cell spreads over several pixels, so real staining cannot look like that.", {})],
     { x: 8.5, y: 1.6, w: 4.3, h: 4.6, fontSize: 14 });
note(s, "ROI018_B10, CD31, raw counts from the TIFF, all 1,000,000 pixels.", { x: 0.6, y: 5.8, w: 7.4, h: 0.35 });
s.addNotes("The Hyperion does not take a photograph. The laser fires at one 1 µm spot and vaporises it; the metal tags on the antibodies in that spot are carried into the mass spectrometer, which counts the ions of each metal. Then the laser moves 1 µm and fires again. So every pixel is one shot, and its value is a count of ions: 0, 1, 2, 15 and so on. A CD31 value of 3 means 3 ions of neodymium-144 came off that spot. The chart shows all one million CD31 pixels of ROI018_B10: 912,273 hold 0, 76,057 hold 1, and the bigger the count the rarer it is; only 51 pixels reach 50. That is normal for IMC: most tissue has no CD31, and even a CD31-positive vessel cell gives a few to a few tens of ions per pixel. The brightest pixel in the whole ROI is 816, and the next slide shows its neighbours are 0, 1 and 3. A cell is several micrometres across, so real signal covers several pixels and the neighbours of a bright pixel are bright too. A lone 816 is a burst of ions recorded in one shot by the detector: a hot pixel, and that is what the filter removes.");

// H2 the spike
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hot pixels" });
s.addText("Hot pixels 2: one spot, far brighter than everything around it", { placeholder: "title" });
img(s, "hp_grid.png", 0.6, 1.5, 7.6, 3.8);
body(s, [P("The 816 sits in the middle of a patch of 0s, 1s and 3s. Its brightest neighbour is 3."),
         P("Real staining never looks like that. A cell is several micrometres across, so its signal is spread over many pixels, and the pixels next to a bright one are bright too."),
         L("A single pixel this far above its neighbours is the detector, not the tissue: a burst of ions recorded in one shot.")],
     { x: 8.6, y: 1.6, w: 4.2, h: 4.6 });
note(s, "The 5 × 5 pixels around the spike in ROI018_B10, CD31. Right: the same pixels after the filter.", { x: 0.6, y: 5.45, w: 7.6, h: 0.5 });
s.addNotes("These spikes turn up in any channel, at random places. They are rare, but one is enough to matter, as the next slides show.");

// H3 the rule
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hot pixels" });
s.addText("Hot pixels 3: the rule, step by step", { placeholder: "title" });
body(s, [P("For every pixel of every channel:"),
         P("1.  Look at its 8 neighbours (the ring of pixels around it)."),
         P("2.  Find the brightest of the 8."),
         P("3.  If the pixel is more than 50 counts above that neighbour, replace it with the neighbour's value."),
         P("4.  Otherwise leave it as it is."),
         P(" "),
         P("Our spike:   816 − 3 = 813,  more than 50,  so 816 becomes 3.", { bold: true }),
         L("Nothing else in that patch changes.", {})],
     { x: 0.6, y: 1.5, w: 6.6, h: 4.8, fontSize: 17 });
body(s, [P("How it is done in the code", { bold: true }),
         P("Same rule as steinbock's own filter, written into our stacking script because our data came as TIFFs.", { bullet: true }),
         P("The brightest neighbour is found with a 3 × 3 maximum filter that leaves out the centre. At the image edge the missing neighbours are mirrored.", { bullet: true }),
         P("The subtraction is done in decimals, so it cannot wrap around on the unsigned 16-bit counts.", { bullet: true }),
         P("The replaced value is a real neighbouring count, so the images stay whole numbers.", { bullet: true }),
         L("The threshold, 50 counts, is the value used in steinbock (hpf = 50).", { bullet: true })],
     { x: 7.6, y: 1.5, w: 5.2, h: 5.0, fontSize: 14 });
s.addNotes("scripts/02_preprocess_imc_images.py, function filter_hot_pixels. It runs on each single-channel image before the 43 channels are stacked.");

// H4 nucleus passes
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hot pixels" });
s.addText("Hot pixels 4: a real nucleus is left alone", { placeholder: "title" });
img(s, "hp_nucleus.png", 0.8, 1.5, 4.5, 4.77);
body(s, [P("The brightest DNA1 pixel of a nucleus in the same ROI is 49. Its brightest neighbour is 32."),
         P("49 − 32 = 17, well under 50, so it stays.", { bold: true }),
         P("This is the point of comparing with the brightest neighbour rather than with the average: a bright cell is bright all over, so even its brightest pixel always has a bright pixel next to it."),
         L("So the filter only removes isolated spikes. Across all the antibody and DNA channels it touched about 1 pixel in 150,000.", {})],
     { x: 6.0, y: 1.6, w: 6.8, h: 4.8 });
s.addNotes("The counter-case: a very bright, very small object could in principle lose its centre pixel, but at 1 µm per pixel nothing biological is one pixel wide.");

// H5 effect on a cell
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hot pixels" });
s.addText("Hot pixels 5: what one spike does to a cell", { placeholder: "title" });
img(s, "cell.png", 0.6, 1.5, 7.4, 3.7);
const hc = [["", "before", "after"], ["sum of CD31 counts in the cell", "828", "15"], ["pixels in the cell", "40", "40"], ["mean CD31", "20.7", "0.38"]];
s.addTable(hc.map((r, i) => r.map((t, j) => cell(t, { bold: i === 0 || i === 3, align: j ? "right" : "left", color: i === 0 ? C.text2 : C.text1, fill: { color: i % 2 ? "F2F3F5" : "FFFFFF" } }))),
  { x: 8.4, y: 1.6, w: 4.4, colW: [2.4, 1.0, 1.0], fontSize: 15, fontFace: "Calibri", rowH: 0.5, valign: "middle", border: { type: "solid", pt: 0.5, color: "D9DDE3" }, margin: [0.04, 0.12, 0.04, 0.12] });
body(s, [P("The spike sits inside cell 606. The cell's value is the mean of its 40 pixels, so the one pixel of 816 alone gives it a mean of 20."),
         L("With it, the cell reads as strongly CD31-positive. Without it, the cell is clearly negative, which is what the image shows.", {})],
     { x: 8.4, y: 3.9, w: 4.4, h: 2.4, fontSize: 15 });
note(s, "ROI018_B10, cell 606 (outlined). Left raw, right after the filter.", { x: 0.6, y: 5.35, w: 7.4, h: 0.35 });
s.addNotes("828 − 816 + 3 = 15. The value 0.38 is exactly what steinbock wrote for this cell after the filter.");

// H6 where
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hot pixels" });
s.addText("Hot pixels 6: how many, and where", { placeholder: "title" });
img(s, "hp_channels.png", 0.6, 1.45, 6.6, 4.42);
body(s, [P("31,416 pixels replaced in the antibody and DNA channels of the 136 ROIs.", { bold: true }),
         P("They are spread over all markers, but some channels have many more: PD-L1, CD31, S100, SOX9, αSMA and CD68. A channel with many spikes and little real signal is exactly where a false positive would come from."),
         P("The DNA channels had very few (129), so segmentation was hardly affected; the marker means were."),
         L("The technical channels are a different story: the argon channel had 10.6 million replacements, because its background is noisy everywhere. It does not matter, since those channels are never analysed.", { color: "555555" })],
     { x: 7.6, y: 1.5, w: 5.2, h: 5.0, fontSize: 14 });
s.addNotes("Per ROI and per channel counts are in logs/02_preprocess_imc_images.log. The totals per channel match the numbers in the pipeline review exactly.");

// H7 why none before
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hot pixels" });
s.addText("Hot pixels 7: why the first run had none", { placeholder: "title" });
const why = [["Usual steinbock route", "raw .mcd or .txt files", "steinbock preprocess imc", "filter applied"],
             ["Our first run", "one TIFF per channel from the facility", "our own stacking script", "no filter"],
             ["Now", "the same TIFFs", "stacking script with the steinbock rule (hpf = 50)", "filter applied, counts logged"]];
s.addTable([[H("Route"), H("Input"), H("Stacked by"), H("Hot pixels")], ...why.map((r, i) => r.map((t, j) => cell(t, { bold: j === 0, color: C.text1, fill: { color: i === 1 ? "F6E9EF" : (i === 2 ? "EAF2F2" : "F2F3F5") } })))],
  { x: 0.6, y: 1.5, w: 12.1, colW: [2.6, 3.4, 3.9, 2.2], fontSize: 15, fontFace: "Calibri", rowH: 0.6, valign: "middle", border: { type: "solid", pt: 0.5, color: "FFFFFF" }, margin: [0.05, 0.12, 0.05, 0.12] });
body(s, [P("steinbock filters hot pixels while it reads the raw acquisition files. Our data arrived as single-channel TIFFs, so that step was skipped and the images were stacked by our own script, without the filter."),
         L("The filter is now part of that script, so it runs on every channel of every ROI before anything else happens to the images.")],
     { x: 0.6, y: 4.3, w: 12.1, h: 2.0, fontSize: 15 });
s.addNotes("Flagged as item 1.1 in the pipeline review. Everything downstream (segmentation, intensities) was re-run after the fix.");

// 9 Cellpose inputs
pres.addSection({ title: "Segmentation" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Segmentation" });
s.addText("What Cellpose sees", { placeholder: "title" });
img(s, "H14_comp.png", 0.6, 1.35, 5.55, 5.33);
body(s, [P("Cellpose wants two images, not 43, so the panel's cellpose column builds them:"),
         P("Nuclei: DNA1, DNA2 and SOX9. SOX9 is there because in many cores the DNA stain is weak.", { bullet: true }),
         P("Cell bodies: S100, CD68, αSMA, CD31, CD3 and CD66b, to cover tumour cells, macrophages, stroma, vessels, T cells and neutrophils.", { bullet: true }),
         P("Each image takes, at every pixel, the highest value among its channels, and is then rescaled to 0–1 for that ROI (next slide)."),
         L("CD20 was left out (almost no signal), CD138 (doubtful staining) and CD163 (CD68 is the cleaner macrophage marker).", { color: C.text2 })],
     { x: 6.6, y: 1.45, w: 6.2, h: 5.3, fontSize: 14 });
s.addNotes("H14 is a tumour-periphery core with a good DNA signal. The whole core gives 1,369 objects.");

// 9b composite maths
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Segmentation" });
s.addText("How the two input images are computed", { placeholder: "title" });
body(s, [P("1.  At every pixel, take the highest count among the channels of the image.", {}),
         P("nuclear = max(DNA1, DNA2, SOX9)        cell body = max(S100, CD68, αSMA, CD31, CD3, CD66b)", { fontFace: "Courier New", fontSize: 13 }),
         P("2.  Find the 1st and 99.5th percentile of that image over the whole ROI, and rescale:", {}),
         P("scaled = (value − p1) / (p99.5 − p1), then cut to the range 0 to 1", { fontFace: "Courier New", fontSize: 13 }),
         P("3.  Give Cellpose the two images as one two-channel picture: cell body first, nuclei second.", {})],
     { x: 0.6, y: 1.5, w: 12.1, h: 2.8, fontSize: 16 });
const ex2 = [["", "channel counts", "max", "p1 / p99.5 in H14", "scaled"],
             ["nuclear", "DNA1 8, DNA2 7, SOX9 1", "8", "0 / 23", "8 / 23 = 0.35"],
             ["cell body", "S100 10, αSMA 3, CD68, CD31, CD3, CD66b 0", "10", "0 / 18", "10 / 18 = 0.56"]];
s.addTable(ex2.map((r, i) => r.map((t, j) => cell(t, { bold: i === 0 || j === 0, color: i === 0 ? C.text2 : C.text1, fill: { color: i === 0 ? "FFFFFF" : (i % 2 ? "F2F3F5" : "FFFFFF") } }))),
  { x: 0.6, y: 4.45, w: 12.1, colW: [1.6, 4.6, 1.0, 2.4, 2.5], fontSize: 15, fontFace: "Calibri", rowH: 0.48, valign: "middle", border: { type: "solid", pt: 0.5, color: "D9DDE3" }, margin: [0.04, 0.12, 0.04, 0.12] });
note(s, "One pixel inside cell 735 of ROI072_H14, worked through by hand.", { x: 0.6, y: 6.05, w: 12, h: 0.35 });
s.addNotes("Because the percentiles are taken per ROI, a ROI with weak staining is stretched more than a bright one. That is what lets Cellpose work in the DNA-poor cores, and also why a channel with no real signal can look noisy after stretching.");

// 10 settings + fixed
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Segmentation" });
s.addText("Settings, and one idea we tested and dropped", { placeholder: "title" });
const st = [["Cellpose", "4.2.1, default model, no retraining"], ["Flow threshold", "0.4"], ["Cell probability threshold", "0"], ["Cell diameter", "not set, Cellpose estimates it"], ["Smallest object kept", "20 pixels"]];
s.addTable(st.map((r, i) => r.map((t, j) => cell(t, { bold: j === 0, color: C.text1, fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" } }))),
  { x: 0.6, y: 1.5, w: 5.6, colW: [2.6, 3.0], fontSize: 15, fontFace: "Calibri", rowH: 0.5, valign: "middle", border: { type: "none" }, margin: [0.05, 0.12, 0.05, 0.12] });
body(s, [L("The output is a mask: an image the size of the ROI where every pixel holds the number of the cell it belongs to, or 0.", {})], { x: 0.6, y: 4.3, w: 5.6, h: 1.0, fontSize: 14, color: C.text2 });
img(s, "fixed.png", 6.8, 1.5, 6.0, 3.01);
s.addTable([[H(""), H("ROI032_I13", { align: "right" }), H("ROI107_A5", { align: "right" })],
  [cell("Percentile scaling"), cell("615", { align: "right" }), cell("127", { align: "right" })],
  [cell("Fixed scale for all ROIs", {}), cell("23–26", { align: "right" }), cell("14–16", { align: "right" })]],
  { x: 6.8, y: 4.65, w: 6.0, colW: [2.8, 1.6, 1.6], fontSize: 14, fontFace: "Calibri", rowH: 0.42, border: { type: "solid", pt: 0.5, color: "D9DDE3" }, margin: [0.04, 0.12, 0.04, 0.12] });
note(s, "Objects found. With one scale for every ROI, single counts in weak channels took over the image.", { x: 6.8, y: 6.0, w: 6.0, h: 0.5 });
s.addNotes("The fixed scale divided each channel by a dataset-wide maximum. CD3 got divided by 3, so one stray count became a third of full brightness, while real DNA reached about 10%. Kept as an option, not the default.");

// 11 result
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Segmentation" });
s.addText("79,739 objects in 136 ROIs", { placeholder: "title" });
img(s, "seg_counts.png", 0.6, 1.5, 12.1, 4.07);
body(s, [P("Median 342 objects per ROI, from 9 to 7,991: the array mixes dense inflamed cores with cores that are mostly cartilage matrix.", { breakLine: false })],
     { x: 0.6, y: 5.75, w: 7.6, h: 0.9, fontSize: 14 });
body(s, [L("Median object area 58 µm². Cellpose ran overnight on the CPU (9 Oct 19:03 to 10 Oct 13:15), 0 errors; within 0.4% of the previous run.", {})], { x: 8.6, y: 5.75, w: 4.1, h: 0.9, fontSize: 14, color: C.text2 });
s.addNotes("All 136 ROIs segmented, none failed. Checked by eye on overlays; not yet scored against hand-drawn cells.");

// 12 intensity
pres.addSection({ title: "Measurement" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Measurement" });
s.addText("How a cell's intensity is calculated", { placeholder: "title" });
img(s, "intensity_cell.png", 0.5, 1.4, 8.6, 4.23);
body(s, [P("steinbock lays the mask over the filtered image and, for each cell, takes the pixels with that cell's number."),
         P("The intensity is the mean count over those pixels:", {}),
         P("547 counts ÷ 47 pixels = 11.6", { bold: true, fontSize: 20 }),
         L("That is exactly the S100 value steinbock wrote for cell 735. Recomputed by hand for all 43 channels of this cell, every one matches. All 136 ROIs took under a minute in Docker.", { color: C.text2 })],
     { x: 9.5, y: 1.5, w: 3.3, h: 4.9 });
note(s, "ROI072_H14, cell 735. Pixels outside the outline are ignored, however bright.", { x: 0.6, y: 5.75, w: 8.5, h: 0.35 });
s.addNotes("Command: steinbock measure intensities. The default aggregation is the mean. A mean, not a sum, so a big cell and a small cell with the same staining get the same value.");

// 13 what the numbers are
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Measurement" });
s.addText("One mask, 43 numbers per cell", { placeholder: "title" });
const cv = [["S100", "11.64"], ["DNA1", "6.57"], ["SOX9", "0.87"], ["CD68", "0.26"], ["CD3", "0.11"], ["CD31", "0.02"]];
s.addTable([[H("cell 735"), H("mean count", { align: "right" })], ...cv.map((r, i) => [cell(r[0], { fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" } }), cell(r[1], { align: "right", fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" }, bold: i < 2 })])],
  { x: 0.6, y: 1.5, w: 3.8, colW: [2.2, 1.6], fontSize: 16, fontFace: "Calibri", rowH: 0.5, valign: "middle", border: { type: "none" }, margin: [0.05, 0.15, 0.05, 0.15] });
note(s, "6 of its 43 values, from data/intensities/ROI072_H14.csv.", { x: 0.6, y: 5.15, w: 3.8, h: 0.5 });
body(s, [P("The same outline is used for every channel, so each cell gets one row of 43 means. This one is clearly an S100+ cell with a nucleus; the immune markers are close to zero.", {}),
         P("The values are raw ion counts. Nothing is transformed or scaled at this stage; that comes later, once the cells are cleaned.", { bullet: true }),
         P("Most cells are near 0 for most markers, because most pixels are 0.", { bullet: true }),
         P("Technical channels are measured too, and stay flagged.", { bullet: true }),
         L("At 1 µm a cell edge is only a few pixels wide, so some signal from a touching neighbour can end up in a cell's mean. That is why double-positive cells will be checked against their neighbours.", {})],
     { x: 5.0, y: 1.5, w: 7.8, h: 5.0 });
s.addNotes("Output: one CSV per ROI in data/intensities, one row per object, one column per channel.");

// 14 regionprops
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Measurement" });
s.addText("Shape and position of each cell", { placeholder: "title" });
img(s, "regionprops_cell.png", 0.8, 1.45, 4.6, 4.6);
const rv = [["area", "47 pixels = 47 µm²"], ["centroid", "row 583.3, column 504.6"], ["major axis", "11.3 µm"], ["minor axis", "5.3 µm"], ["eccentricity", "0.88 (0 is a circle, 1 a line)"]];
s.addTable(rv.map((r, i) => r.map((t, j) => cell(t, { bold: j === 0, color: j === 0 ? C.text1 : C.text2, fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" } }))),
  { x: 6.0, y: 1.6, w: 6.7, colW: [2.0, 4.7], fontSize: 15, fontFace: "Calibri", rowH: 0.5, valign: "middle", border: { type: "none" }, margin: [0.05, 0.15, 0.05, 0.15] });
body(s, [P("Computed on the mask alone (steinbock uses scikit-image): area = number of pixels; centroid = mean row and mean column of those pixels; axes = 4 × √ of the spread along the two main directions; eccentricity = √(1 − (minor/major)²) = √(1 − (5.3/11.3)²) = 0.88."),
         L("The axes are those of the ellipse with the same spread as the cell (drawn in pink). Area is used to catch fragments and very large objects, the centroid places the cell in the tissue.", { color: C.text2 })],
     { x: 6.0, y: 4.4, w: 6.7, h: 1.9, fontSize: 14 });
note(s, "Cell 735 again; yellow dot = centroid.", { x: 0.8, y: 6.15, w: 4.6, h: 0.35 });
s.addNotes("One pixel is 1 µm, so pixel counts and µm² are the same number here.");

// 15 neighbours
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Measurement" });
s.addText("Who is next to whom", { placeholder: "title" });
img(s, "neighbours.png", 0.5, 1.4, 8.6, 4.44);
body(s, [P("steinbock grows every cell outward by up to 4 pixels into empty space, never into another cell. Two cells whose grown areas touch are neighbours."),
         P("Cell 735 has three: 734, 740 and 747."),
         P("The result is an edge list per ROI: object, neighbour."),
         L("In matrix-rich cores many cells touch nothing within 4 pixels, so a distance-based graph will be added for the spatial analysis.", {})],
     { x: 9.5, y: 1.5, w: 3.3, h: 4.9 });
s.addNotes("Command: steinbock measure neighbors --type expansion --dmax 4. The graph is built on all objects; it will be rebuilt once the cells are cleaned.");

// 16 export
pres.addSection({ title: "Export" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Export" });
s.addText("What comes out", { placeholder: "title" });
const ex = [["cells.csv", "79,739 rows, one per object. 51 columns: image, object number, the 43 intensities and 6 shape measures."],
            ["cells.h5ad", "The same cells as an AnnData object. X is the 79,739 × 43 intensity matrix; obs holds shape, position and image details; var holds the panel."],
            ["graphs/*.graphml", "136 files, one per ROI. Cells are nodes carrying their intensities and shape; neighbours are edges."]];
s.addTable(ex.map((r, i) => [cell(r[0], { bold: true, fontFace: "Courier New" }), cell(r[1])]),
  { x: 0.6, y: 1.5, w: 12.1, colW: [2.8, 9.3], fontSize: 16, fontFace: "Calibri", rowH: 0.9, valign: "middle", border: { type: "solid", pt: 0.5, color: "D9DDE3" }, margin: [0.08, 0.15, 0.08, 0.15] });
body(s, [L("Every row ties back to its ROI and its object number in the mask, so any value can be traced to the pixels it came from. This is the end of notebook 01; cleaning the cells and phenotyping start from these files.")],
     { x: 0.6, y: 4.6, w: 12.1, h: 1.2, fontSize: 15, color: "555555" });
s.addNotes("Commands: steinbock export csv, export anndata, export graphs. Numbered copies also go into results/.");

// F1 files
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Export" });
s.addText("What each step writes", { placeholder: "title" });
const fl = [["2", "01_create_panel_from_raw.py", "data/panel.csv, roi_marker_availability.csv", "01_panel.csv, 01_roi_marker_availability.csv"],
            ["3", "02_preprocess_imc_images.py", "data/img/*.tiff, data/images.csv", "02_images.csv, 03_preprocessed_tiff_inventory.csv"],
            ["4", "03_segment_cellpose.py", "data/masks/*.tiff", "04_cellpose_mask_inventory.csv"],
            ["5", "04_measure_intensities.py", "data/intensities/*.csv", "05_intensity_table_inventory.csv"],
            ["6", "05_measure_regionprops.py", "data/regionprops/*.csv", "06_regionprops_table_inventory.csv"],
            ["7", "06_measure_neighbors.py", "data/neighbors/*.csv", "07_neighbors_table_inventory.csv"],
            ["8", "07_export_data.py", "data/cells.csv, cells.h5ad, graphs/", "08_cells.csv, 09_cells.h5ad, 10_graphml/"]];
s.addTable([[H("Step"), H("Script"), H("Working files (names steinbock expects)"), H("Copy for the record, in results/")],
  ...fl.map((r, i) => r.map((t, j) => cell(t, { fontFace: j ? "Courier New" : "Calibri", bold: j === 0, color: C.text1, fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" } })))],
  { x: 0.6, y: 1.45, w: 12.1, colW: [0.7, 3.4, 4.1, 3.9], fontSize: 11.5, fontFace: "Calibri", rowH: 0.5, valign: "middle", border: { type: "none" }, margin: [0.03, 0.1, 0.03, 0.1] });
body(s, [L("steinbock only finds files under fixed names (panel.csv, img/, masks/ …), so those are kept. The numbered copies in results/ follow the order of the steps, and each script also writes its own log in logs/.", {})],
     { x: 0.6, y: 5.7, w: 12.1, h: 0.8, fontSize: 14, color: "555555" });
s.addNotes("Step 1 only reads. The notebook finds the project folder itself, so it can be started from the notebooks folder or the project folder.");

// F2 checks
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Export" });
s.addText("How each step is checked before the next one runs", { placeholder: "title" });
const ck = [["1  Raw files", "136 ROI folders, 43 channel TIFFs in each, file names in the channel_marker form"],
            ["2  Panel", "43 channel-marker pairs; nuclear and cell-body markers set in the cellpose column; 6 technical channels marked; every ROI has every channel"],
            ["3  Stacking", "136 images of 43 channels; every image name found in the TMA core map; non-square ROIs kept; hot pixels reported per channel"],
            ["4  Cellpose", "one mask per image (136); model, versions and settings printed from the log; 0 errors"],
            ["5–7  Measuring", "one intensity, one shape and one neighbour table per image (136 each)"],
            ["8  Export", "cells.csv has 79,739 rows, the sum of the objects in all masks; cells.h5ad is 79,739 × 43; 136 graph files"]];
s.addTable(ck.map((r, i) => r.map((t, j) => cell(t, { bold: j === 0, color: C.text1, fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" } }))),
  { x: 0.6, y: 1.45, w: 12.1, colW: [2.2, 9.9], fontSize: 14, fontFace: "Calibri", rowH: 0.62, valign: "middle", border: { type: "none" }, margin: [0.04, 0.12, 0.04, 0.12] });
body(s, [L("If a script fails, its cell stops with an error. The check cells then print these counts so they can be read before the next step is started.", {})], { x: 0.6, y: 5.75, w: 12.1, h: 0.5, fontSize: 15 });
s.addNotes("These are the validation cells that follow each step in the notebook.");

// 17 still to do
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Export" });
s.addText("Still to do", { placeholder: "title" });
const td = [["4.1", "Score the segmentation against cells drawn by hand (4–6 crops, 200–300 cells), and compare settings, including fixed scaling, on that score"],
            ["4.3", "One size threshold for small objects everywhere"],
            ["2.4", "Check on cores with good DNA whether SOX9 in the nuclear image changes the cells found"],
            ["4.7", "Call the masks by the same name (Cellpose model) in every file and text"],
            ["1.2", "Decimal counts: the original .mcd file (24 GB) has been found; decide whether to re-export from it"],
            ["2.1", "Staining protocol from the facility, and a DAPI test on a section of the DNA-poor cores"],
            ["7.1, 7.2", "A distance-based neighbour graph, built after the cells are cleaned"],
            ["S.4", "First commit and push of the project to the lab's GitHub"]];
s.addTable(td.map((r, i) => r.map((t, j) => cell(t, { bold: j === 0, color: C.text1, fill: { color: i % 2 ? "FFFFFF" : "F2F3F5" } }))),
  { x: 0.6, y: 1.45, w: 12.1, colW: [1.2, 10.9], fontSize: 14, fontFace: "Calibri", rowH: 0.5, valign: "middle", border: { type: "none" }, margin: [0.04, 0.12, 0.04, 0.12] });
body(s, [L("After that come the steps on the measured cells: cleaning, transformation (arcsinh), phenotyping and the spatial analysis.", {})], { x: 0.6, y: 5.75, w: 12.1, h: 0.6, fontSize: 15, color: "555555" });
s.addNotes("4.1 is the most important open item for this part: so far the segmentation has only been checked by eye.");

(async () => { await pres.writeFile({ fileName: OUT }); await applyTheme(OUT, THEME); console.log("written"); })();
