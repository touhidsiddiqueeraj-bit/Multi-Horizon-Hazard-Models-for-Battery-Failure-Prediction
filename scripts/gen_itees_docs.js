// Generate the three ITEES submission documents:
//   1. Cover_Letter_ITEES.docx
//   2. Suggested_Reviewers_ITEES.docx
//   3. Submission_Checklist_ITEES.docx
// English formal documents (Times New Roman), no cover page, no TOC.
// Venue: International Transactions on Electrical Energy Systems (Wiley, OA).
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, WidthType, BorderStyle, ShadingType,
  Footer, PageNumber,
} = require("docx");
const fs = require("fs");

const OUT = "/home/z/my-project/download";
const FONT = { ascii: "Times New Roman", eastAsia: "Times New Roman" };
const BODY = 24;         // 12 pt
const SMALL = 21;        // 10.5 pt
const BLACK = "000000";
const GREY = "595959";

// ---------- helpers ----------
function run(text, opts = {}) {
  return new TextRun({ text, size: BODY, color: BLACK, font: FONT, ...opts });
}
function para(text, opts = {}) {
  const { children, ...rest } = opts;
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { line: 312, after: 160 },
    children: children || [run(text, rest.run || {})],
    ...(rest.paragraph || {}),
  });
}
function heading1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 140, line: 312 },
    children: [new TextRun({ text, bold: true, size: 28, color: BLACK, font: FONT })],
  });
}
function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 120, line: 312 },
    children: [new TextRun({ text, bold: true, size: 25, color: BLACK, font: FONT })],
  });
}
function bullet(lead, text) {
  return new Paragraph({
    bullet: { level: 0 },
    alignment: AlignmentType.LEFT,
    spacing: { line: 312, after: 100 },
    children: [
      run(lead ? lead + " " : "", { bold: true }),
      run(text),
    ],
  });
}
const CELL_MARGINS = { top: 60, bottom: 60, left: 120, right: 120 };
const TBL_BORDERS = {
  top: { style: BorderStyle.SINGLE, size: 4, color: "8A8A8A" },
  bottom: { style: BorderStyle.SINGLE, size: 4, color: "8A8A8A" },
  left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
  insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "C9C9C9" },
  insideVertical: { style: BorderStyle.SINGLE, size: 2, color: "C9C9C9" },
};
function cell(text, { bold = false, width, fill, size = SMALL, align = AlignmentType.LEFT } = {}) {
  const lines = Array.isArray(text) ? text : [text];
  return new TableCell({
    margins: CELL_MARGINS,
    width: width ? { size: width, type: WidthType.PERCENTAGE } : undefined,
    shading: fill ? { type: ShadingType.CLEAR, fill } : undefined,
    children: lines.map(t => new Paragraph({
      alignment: align,
      spacing: { line: 288 },
      children: [new TextRun({ text: t, bold, size, color: BLACK, font: FONT })],
    })),
  });
}
function makeTable(headerCells, rows) {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: TBL_BORDERS,
    rows: [
      new TableRow({
        tableHeader: true, cantSplit: true,
        children: headerCells,
      }),
      ...rows.map(r => new TableRow({ cantSplit: true, children: r })),
    ],
  });
}
function tableTitle(text) {
  return new Paragraph({
    keepNext: true,
    spacing: { before: 120, after: 80, line: 312 },
    children: [new TextRun({ text, bold: true, size: SMALL, color: GREY, font: FONT })],
  });
}
const pageFooter = () => new Footer({
  children: [new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: GREY, font: FONT })],
  })],
});
const PAGE = { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 } };

const TITLE = "Multi-Horizon Failure-Risk Models for Battery Failure Prediction: How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?";
const VENUE = "International Transactions on Electrical Energy Systems";

// =====================================================================
// DOCUMENT 1 — COVER LETTER
// =====================================================================
const coverLetter = new Document({
  styles: {
    default: {
      document: {
        run: { font: FONT, size: BODY, color: BLACK },
        paragraph: { spacing: { line: 312 } },
      },
    },
  },
  sections: [{
    properties: { page: PAGE },
    footers: { default: pageFooter() },
    children: [
      para("", {
        children: [new TextRun({ text: "Cover Letter", bold: true, size: 32, color: BLACK, font: FONT })],
        paragraph: { spacing: { after: 60, line: 360 } },
      }),
      para(new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }), { run: { size: SMALL, color: GREY } }),
      para("The Editors-in-Chief"),
      para(VENUE),
      para("Wiley"),
      para("Subject: Submission of an original research article"),
      para("", {
        children: [
          run("Dear Editors,"),
        ],
      }),
      para("", {
        children: [
          run("We are pleased to submit our manuscript \u201C"),
          new TextRun({ text: TITLE, italics: true, size: BODY, color: BLACK, font: FONT }),
          run("\u201D for consideration as a Research Article in " + VENUE + "."),
        ],
      }),
      para("", {
        children: [
          run("Predicting whether a lithium-ion cell will fail within a short operating window \u2014 rather than estimating its remaining useful life \u2014 is the question a battery management system actually faces in electric vehicles and grid storage. This manuscript presents a validity-focused evaluation of multi-horizon failure-risk classification across four model families (three tree ensembles and a GRU), a discrete-time hazard formulation, and eight public aging datasets spanning four chemistries (LCO, LFP, NCA, NMC) from six laboratories, under cell-disjoint splits and a leakage-clean, cross-fitted calibration protocol. Its central finding is a controlled state-of-health (SOH) ablation: apparent cross-dataset transfer with SOH included (pooled AUC up to 1.00) collapses without SOH, and an unfitted distance-to-threshold rule on SOH alone reproduces much of the tuned ensembles\u2019 transfer performance \u2014 because SOH also defines the failure label, with-SOH numbers are diagnostic-proximity upper bounds rather than pure prognosis. Same-chemistry cross-laboratory controls show the collapse is driven by dataset shift at least as much as by chemistry, the findings replicate on 60 pre-registered NMC, NCA, and LFP cells from two further laboratories, and the tree ensembles deploy on a \$12 ESP32-S3 microcontroller in under a millisecond per inference."),
        ],
      }),
      para("", {
        children: [
          run("We believe this work is a natural continuation of a research line this journal has already recognized: the multi-horizon failure-intelligence framework was introduced in these pages by Shikdar and Laaksonen (\u201CLearning When Not to Use a Battery: Multihorizon Failure Intelligence,\u201D "),
          new TextRun({ text: VENUE, italics: true, size: BODY, color: BLACK, font: FONT }),
          run(", vol. 2026, Article ID 6000810), on one model and one dataset. Our manuscript answers the question that framework leaves open and that energy-system practitioners must ask before deploying such models: does anything learned on one dataset transfer to another chemistry or laboratory, and if so, what exactly transfers? The answer \u2014 a rigorous negative result about shortcut learning, with label-, feature-, and dataset-level controls \u2014 is directly relevant to battery management and grid/EV reliability practice, and is, to our knowledge, the first controlled diagnosis of what transfers under dataset and chemistry shift for this task."),
        ],
      }),
      para("All datasets used are public (NASA, CALCE, Oxford, MIT\u2013Stanford, and the Battery Archive), so every result is independently checkable; the complete tabular evidence is provided in the Supplementary Material, submitted as a separate file. The manuscript is 18 pages in the single-column submission format; we understand the journal imposes no page limit for research articles."),
      para("We confirm that this manuscript is original, has not been published previously, and is not under consideration by any other journal. All authors have read and approved the submitted version and declare no conflicts of interest. No specific funding was received for this work. All authors are affiliated with the Department of Electrical and Electronic Engineering, Leading University, Sylhet, Bangladesh; the corresponding author is Hussain Touhid Siddiquee (touhidsiddiqueeraj@gmail.com)."),
      para("Suggested reviewers are provided in the accompanying file. Thank you for considering our manuscript; we look forward to the reviewers\u2019 comments."),
      para("Yours sincerely,"),
      para("", {
        children: [
          run("Hussain Touhid Siddiquee", { bold: true }),
          run(" (corresponding author), on behalf of all authors"),
        ],
      }),
      para("Department of Electrical and Electronic Engineering", { run: { size: SMALL, color: GREY }, paragraph: { spacing: { after: 20, line: 288 } } }),
      para("Leading University, Sylhet, Bangladesh", { run: { size: SMALL, color: GREY }, paragraph: { spacing: { after: 20, line: 288 } } }),
      para("touhidsiddiqueeraj@gmail.com \u00B7 ORCID: 0009-0002-8804-6195", { run: { size: SMALL, color: GREY }, paragraph: { spacing: { after: 160, line: 288 } } }),
    ],
  }],
});

// =====================================================================
// DOCUMENT 2 — SUGGESTED REVIEWERS
// =====================================================================
const revHeader = [
  cell("#", { bold: true, width: 4, fill: "EEF2F6" }),
  cell("Name", { bold: true, width: 18, fill: "EEF2F6" }),
  cell("Affiliation", { bold: true, width: 24, fill: "EEF2F6" }),
  cell("Country", { bold: true, width: 10, fill: "EEF2F6" }),
  cell("Expertise relevant to this submission", { bold: true, width: 44, fill: "EEF2F6" }),
];
const reviewerRows = [
  ["1", "Michael G. Pecht", "CALCE, University of Maryland, College Park", "USA",
    "Battery prognostics and health management; founder of the CALCE Battery Data Center, one of the datasets evaluated in the manuscript; product reliability and failure analysis."],
  ["2", "David A. Howey", "Department of Engineering Science, University of Oxford", "UK",
    "Battery degradation diagnostics and machine learning for battery management; lead author group of the Oxford degradation-diagnostic dataset used as a transfer target in this study."],
  ["3", "Rui Xiong", "Beijing Institute of Technology", "China",
    "State-of-health estimation and transfer learning for lithium-ion batteries; co-author of the deep-learning SOH estimation study cited in the manuscript; EV battery management systems."],
  ["4", "Aaditya K. Ramdas", "Carnegie Mellon University", "USA",
    "Distribution-free calibration of predicted probabilities, including online recalibration; cited in the manuscript; ideal evaluator of the calibration-under-shift analysis."],
  ["5", "Yohann Preger", "Sandia National Laboratories", "USA",
    "Cross-chemistry lithium-ion degradation testing; lead author of the SNL degradation study whose cells form the NCA, NMC, and LFP transfer targets used here."],
  ["6", "Tareq Anwar Shikdar", "University of Vaasa", "Finland",
    "Author of the multihorizon failure-intelligence framework (published in this journal, vol. 2026, Article ID 6000810) that this manuscript extends; deepest familiarity with the base protocol and its calibration layer."],
  ["7", "Hannu Laaksonen", "University of Vaasa", "Finland",
    "Co-author of the multihorizon failure-intelligence framework published in this journal; energy storage in power systems and battery analytics; can assess the energy-systems framing."],
].map(r => [
  cell(r[0], { width: 4 }),
  cell(r[1], { bold: true, width: 18 }),
  cell(r[2], { width: 24 }),
  cell(r[3], { width: 10 }),
  cell(r[4], { width: 44 }),
]);

const suggestedReviewers = new Document({
  styles: {
    default: {
      document: {
        run: { font: FONT, size: BODY, color: BLACK },
        paragraph: { spacing: { line: 312 } },
      },
    },
  },
  sections: [{
    properties: { page: PAGE },
    footers: { default: pageFooter() },
    children: [
      para("", {
        children: [new TextRun({ text: "Suggested Reviewers", bold: true, size: 32, color: BLACK, font: FONT })],
        paragraph: { spacing: { after: 60, line: 360 } },
      }),
      para("", {
        children: [run("Manuscript: ", { bold: true }), new TextRun({ text: TITLE, italics: true, size: SMALL, color: BLACK, font: FONT })],
        paragraph: { spacing: { after: 60, line: 312 } },
      }),
      para("", {
        children: [run("Submitted to: " + VENUE + " \u2014 Research Article", { size: SMALL, color: GREY })],
        paragraph: { spacing: { after: 220, line: 312 } },
      }),

      para("The following researchers have expertise directly relevant to this submission. None of them has collaborated with, co-published with, or supervised any of the submitting authors, and to the best of our knowledge none has a conflict of interest with this work. They are listed in priority order."),

      tableTitle("Table 1. Suggested reviewers (in priority order)."),
      makeTable(revHeader, reviewerRows),

      heading2("Notes for the submission form"),
      bullet("E-mail addresses:", "are deliberately not pre-filled here, to avoid transcription errors. Before entry, copy each address from the researcher\u2019s official faculty page or a recent corresponding-author e-mail on one of their papers (e.g., for the CALCE director, the CALCE center page at the University of Maryland)."),
      bullet("ORCID lookup:", "reviewer ORCIDs can be resolved by searching the name at orcid.org if the form requests them."),
      bullet("Opposed reviewers:", "none declared."),
      bullet("Domain balance:", "the list spans battery PHM (1, 2, 5), machine learning for battery state estimation (3), calibration methodology (4), and the base failure-intelligence framework published in this journal (6, 7), matching the manuscript\u2019s three pillars: prognostics, validity controls, and calibration."),
      bullet("Venue continuity:", "reviewers 6 and 7 authored the framework paper in this journal (vol. 2026, Article ID 6000810) that this manuscript builds on; they are the most natural evaluators of the extension\u2019s faithfulness to the original protocol."),
    ],
  }],
});

// =====================================================================
// DOCUMENT 3 — SUBMISSION CHECKLIST
// =====================================================================
const chkHeader = [
  cell("Item", { bold: true, width: 26, fill: "EEF2F6" }),
  cell("What to check / do", { bold: true, width: 52, fill: "EEF2F6" }),
  cell("Status", { bold: true, width: 10, fill: "EEF2F6" }),
  cell("Where", { bold: true, width: 12, fill: "EEF2F6" }),
];
function chk(item, what, status, where, fill) {
  return [cell(item, { bold: true }), cell(what), cell(status, { align: AlignmentType.CENTER, fill }), cell(where)];
}
const chkRows = [
  chk("Venue & article type", VENUE + " (Wiley, fully open access, Scopus/WoS indexed, SJR Q2 in all three categories). Article type: Research Article. Continuous publication; no page limit \u2014 the manuscript is 18 pages (single column) + 5-page supplement.", "\u2713 set", "Portal step 1", "E8F5E9"),
  chk("Submission portal", "New submissions via the Wiley Research Exchange portal (linked from the journal\u2019s \u201CSubmit an Article\u201D page on Wiley Online Library). Register with the corresponding author\u2019s e-mail (touhidsiddiqueeraj@gmail.com); ORCID is required and auto-linked.", "to do", "Portal", "FFF4E0"),
  chk("ORCID iDs", "Have all four authors\u2019 ORCIDs ready (all recorded in AUTHORS.md): H.T.S. 0009-0002-8804-6195; S.S.I. 0009-0000-2658-273X; J.I.C. 0009-0002-1678-9993; F.H.E. 0009-0003-5908-6822. Corresponding author\u2019s is mandatory in the form.", "ready", "AUTHORS.md", "E8F5E9"),
  chk("APC waiver (Bangladesh)", "ITEES lists an APC of USD 2,175. Bangladesh is on Wiley\u2019s Research4Life Group A full-waiver list for fully open-access journals, and all four authors are affiliated in Bangladesh (waiver rule: corresponding author in an eligible country AND \u226550% of authors affiliated there \u2014 both satisfied). A waiver estimate e-mail arrives shortly after submission; confirm it reflects a 100% waiver before acceptance. Do not pay any invoice without checking the waiver.", "auto after submit", "E-mail", "FFF4E0"),
  chk("Main manuscript file", "paper_itees/main_itees.pdf \u2014 title page with all four authors + affiliation + correspondence, 250-word abstract, 9 keywords, sections 1\u20135, Table 1 capability matrix, Tables 2\u201312, Figures 1\u20134, Funding / Conflict of Interest / Data Availability / Author Contributions declarations, 39 references. Upload the PDF for initial submission.", "\u2713 ready", "paper_itees/", "E8F5E9"),
  chk("Author Contributions", "The declaration uses a standard CRediT default (conceptualization/software/writing to the first author; data curation/validation to co-authors). Adjust the wording to the actual contributions before submitting \u2014 it is a formal declaration.", "to verify", "main_itees.tex + form", "FFF4E0"),
  chk("Supplementary material", "paper_itees/supplement_itees.pdf (5 pages, 9 numbered sections of supporting tables). Upload as a separate supplementary file; the main text cites it as \u201CSupplementary Material\u201D throughout.", "\u2713 ready", "paper_itees/", "E8F5E9"),
  chk("References", "39 entries, all verified against publisher records (2026-10-30); ordered by first citation; months stripped per journal style. Entry [10] (the framework paper in this journal) is final. Entry [18] cites the companion study as \u201Cmanuscript under review\u201D \u2014 update its venue if it is accepted before submission.", "\u2713 verified", "main_itees.tex", "E8F5E9"),
  chk("Data availability", "All eight datasets are public (NASA, CALCE, Oxford, MIT\u2013Stanford, Battery Archive). The declaration in the manuscript matches; the portal\u2019s Data Availability field can repeat it.", "\u2713 ready", "Declarations", "E8F5E9"),
  chk("Funding & conflicts", "No specific funding; no competing interests. Enter \u201Cnone\u201D / \u201Cno\u201D in the corresponding portal fields.", "\u2713 ready", "Portal form", "E8F5E9"),
  chk("Cover letter", "Cover_Letter_ITEES.docx \u2014 leads with the study\u2019s validity focus and its continuity with the framework paper published in this journal. Attach at the cover-letter step.", "\u2713 ready", "this folder", "E8F5E9"),
  chk("Suggested reviewers", "Suggested_Reviewers_ITEES.docx \u2014 seven names with rationale; complete each e-mail from official pages before entry.", "to do (e-mails)", "this folder", "FFF4E0"),
  chk("Numbers QA", "379 automated checks of every table row and in-text claim against the validated results JSON were run for this manuscript\u2019s content (2026-10-30 record); the ITEES conversion changed layout and the abstract only, no numbers. If any quantitative claim is edited before submission, re-run the verification script.", "\u2713 verified", "scripts/", "E8F5E9"),
  chk("Similarity screening", "Wiley screens submissions with automated similarity checking. The manuscript is an original work; ensure no earlier draft of this study is posted in a public repository or under review elsewhere before submitting.", "\u2713 ok", "\u2014", "E8F5E9"),
  chk("License", "Fully OA articles publish under CC BY (or CC BY-NC-ND where mandated). The corresponding author signs the license agreement at acceptance, after the APC waiver is confirmed.", "at acceptance", "Portal", "E2F0FB"),
  chk("After submission", "Expect (1) the waiver-estimate e-mail within ~2 weeks \u2014 verify the 100% Bangladesh waiver; (2) editor screening, then anonymous peer review; median first decision for the journal is roughly 6\u201317 weeks; (3) at revision, respond point by point and re-run the number checks for any changed value.", "\u2014", "E-mail/portal", "E2F0FB"),
];

const submissionChecklist = new Document({
  styles: {
    default: {
      document: {
        run: { font: FONT, size: BODY, color: BLACK },
        paragraph: { spacing: { line: 312 } },
      },
    },
  },
  sections: [{
    properties: { page: PAGE },
    footers: { default: pageFooter() },
    children: [
      para("", {
        children: [new TextRun({ text: "Submission Checklist \u2014 International Transactions on Electrical Energy Systems", bold: true, size: 30, color: BLACK, font: FONT })],
        paragraph: { spacing: { after: 60, line: 360 } },
      }),
      para("", {
        children: [run("Manuscript: ", { bold: true }), new TextRun({ text: TITLE, italics: true, size: SMALL, color: BLACK, font: FONT })],
        paragraph: { spacing: { after: 60, line: 312 } },
      }),
      para("", {
        children: [run("Corresponding author: Hussain Touhid Siddiquee, Leading University, Sylhet, Bangladesh \u00B7 Generated 2026-10-30", { size: SMALL, color: GREY })],
        paragraph: { spacing: { after: 220, line: 312 } },
      }),

      para("Venue facts verified 2026-10-30: Wiley fully open-access journal (ex-Hindawi, now on the Research Exchange portal); Scopus/Web of Science/DOAJ indexed; SJR 2025 Q2 in all three categories (Energy Engineering & Power Technology, Modeling & Simulation, Electrical & Electronic Engineering); CiteScore 7.1; continuous publication; APC USD 2,175 with a full Research4Life Group A waiver for Bangladesh; no page limit; anonymous peer review."),

      heading2("Pre-upload checks and portal steps"),
      tableTitle("Table 1. Checklist (green = done/ready, orange = action needed, blue = later stage)."),
      makeTable(chkHeader, chkRows),

      heading2("Package contents"),
      bullet("paper_itees/main_itees.tex, main_itees.pdf \u2014 ", "the manuscript (18 pp., single-column Wiley/Hindawi submission format, compiles with tectonic/xelatex)."),
      bullet("paper_itees/supplement_itees.tex, supplement_itees.pdf \u2014 ", "Supplementary Material (5 pp., matching format)."),
      bullet("paper_itees/figs/ \u2014 ", "the four figures as PNG (source files for production)."),
      bullet("Cover_Letter_ITEES.docx, Suggested_Reviewers_ITEES.docx, Submission_Checklist_ITEES.docx \u2014 ", "this set of submission documents."),
      bullet("AUTHORS.md \u2014 ", "author list, ORCIDs, and profiles for the submission forms."),
    ],
  }],
});

// ---------- write ----------
Promise.all([
  Packer.toBuffer(coverLetter).then(b => fs.writeFileSync(OUT + "/Cover_Letter_ITEES.docx", b)),
  Packer.toBuffer(suggestedReviewers).then(b => fs.writeFileSync(OUT + "/Suggested_Reviewers_ITEES.docx", b)),
  Packer.toBuffer(submissionChecklist).then(b => fs.writeFileSync(OUT + "/Submission_Checklist_ITEES.docx", b)),
]).then(() => console.log("ITEES submission documents written."));
