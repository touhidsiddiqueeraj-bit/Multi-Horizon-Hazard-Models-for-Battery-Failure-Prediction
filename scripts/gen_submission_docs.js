// Generate the three IEEE TR submission documents:
//   1. Cover_Letter_IEEE_TR.docx
//   2. Suggested_Reviewers_IEEE_TR.docx
//   3. Submission_Checklist_IEEE_TR.docx
// English formal documents (Profile A: Times New Roman), no cover page, no TOC.
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
// Block-style English body paragraph: left-aligned, no first-line indent.
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
// Bulleted paragraph with bold lead-in.
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
const ITAL_TITLE = { children: [new TextRun({ text: TITLE, italics: true, size: BODY, color: BLACK, font: FONT })] };

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
      // Sender block
      para("", { children: [run("Hussain Touhid Siddiquee", { bold: true })], paragraph: { spacing: { line: 312, after: 0 } } }),
      para("", { children: [run("Researcher and Embedded Systems Engineer", { size: SMALL })], paragraph: { spacing: { line: 288, after: 0 } } }),
      para("", { children: [run("Department of Electrical and Electronic Engineering", { size: SMALL })], paragraph: { spacing: { line: 288, after: 0 } } }),
      para("", { children: [run("Leading University, Sylhet, Bangladesh", { size: SMALL })], paragraph: { spacing: { line: 288, after: 0 } } }),
      para("", { children: [run("touhidsiddiqueeraj@gmail.com", { size: SMALL })], paragraph: { spacing: { line: 288, after: 200 } } }),

      para("October 30, 2026", { paragraph: { spacing: { line: 312, after: 200 } } }),

      para("", { children: [run("The Editor-in-Chief", { bold: true })], paragraph: { spacing: { line: 288, after: 0 } } }),
      para("", { children: [run("IEEE Transactions on Reliability", { bold: true })], paragraph: { spacing: { line: 288, after: 200 } } }),

      para("", { children: [run("Subject: ", { bold: true }), run("Submission of a Regular Paper \u2014 \u201CMulti-Horizon Failure-Risk Models for Battery Failure Prediction: How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?\u201D")], paragraph: { spacing: { line: 312, after: 200 } } }),

      para("Dear Editor-in-Chief,"),

      para("On behalf of all co-authors, I am pleased to submit our manuscript titled " ),
      para("", ITAL_TITLE),
      para("for consideration as a Regular Paper in the IEEE Transactions on Reliability. The manuscript is 12 double-column pages, accompanied by a 3-page Supplementary Material."),

      para("", {
        children: [
          run("Predicting whether a lithium-ion cell will fail inside a short operating window is an operational reliability question, distinct from remaining-useful-life regression, and it is the question a battery management system must answer in real time. Our manuscript widens a recently proposed multi-horizon failure-risk classification framework into a validity-focused evaluation: four model families and a discrete-time hazard model are compared on eight public aging datasets spanning four chemistries (LCO, LFP, nickel-rich NCA, and NMC) from six laboratories, under cell-disjoint splits and a leakage-clean, cross-fitted calibration protocol."),
        ],
      }),
      para("The central result is a controlled state-of-health (SOH) ablation. Apparent cross-dataset transfer with SOH included (pooled AUC up to 1.00) collapses without SOH (at best 0.58 at a 20-cycle horizon); a distance-to-threshold rule on SOH alone reproduces much of the with-SOH signal; relabeling failures by voltage sag alone, a criterion SOH does not define, removes about a fifth of the with-SOH advantage; and same-chemistry cross-laboratory controls show the collapse is driven by dataset shift at least as much as by chemistry. These findings replicate on 60 pre-registered NMC, NCA, and LFP cells from two further laboratories. The paper further quantifies probability-calibration failure under shift and its partial repair, includes a cost-sensitive operational evaluation, and demonstrates complete deployment of the three tree ensembles on a \$12 ESP32-S3 microcontroller in under a millisecond per SRAM-resident model."),

      para("We believe the manuscript fits the scope of the IEEE Transactions on Reliability closely. It treats battery prognostics as operational reliability estimation; it develops a discrete-time hazard formulation whose survival product is monotone in the horizon by construction; it evaluates the trustworthiness of risk estimates through calibration, uncertainty, and cost analyses; and it asks when reliability metrics survive distribution shift \u2014 a question of direct consequence for certifying prognostic models for electric-vehicle and grid deployment."),

      heading2("Originality and Integrity Statements"),
      para("We confirm that the manuscript is original, has not been published previously in any form, and is not under consideration by any other journal or conference. All authors have read and approved the submitted version and meet the authorship criteria of the IEEE. All datasets used are publicly available and are properly cited. We have no conflicts of interest, financial or otherwise, to declare. No human or animal subjects were involved."),
      para("Suggested reviewers are provided in the accompanying file. The Supplementary Material is submitted as a separate file and is referred to from the main text."),

      para("Thank you for considering our manuscript. We look forward to the reviewers\u2019 comments."),

      para("Sincerely,", { paragraph: { alignment: AlignmentType.RIGHT, spacing: { before: 300, line: 312, after: 0 } } }),
      para("", {
        children: [run("Hussain Touhid Siddiquee", { bold: true })],
        paragraph: { alignment: AlignmentType.RIGHT, spacing: { line: 312, after: 0 } },
      }),
      para("", {
        children: [run("on behalf of all authors", { size: SMALL, color: GREY })],
        paragraph: { alignment: AlignmentType.RIGHT, spacing: { line: 288 } },
      }),
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
  cell("Country", { bold: true, width: 12, fill: "EEF2F6" }),
  cell("Expertise relevant to this submission", { bold: true, width: 42, fill: "EEF2F6" }),
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
    "Author of the multihorizon failure-risk framework that this manuscript extends; deepest familiarity with the base protocol, its hazard formulation, and its calibration layer."],
  ["7", "Hannu Laaksonen", "University of Vaasa", "Finland",
    "Co-author of the multihorizon failure-risk framework; energy storage in power systems and battery analytics; can assess the reliability-aware dispatch framing."],
].map(r => [
  cell(r[0], { width: 4 }),
  cell(r[1], { bold: true, width: 18 }),
  cell(r[2], { width: 24 }),
  cell(r[3], { width: 12 }),
  cell(r[4], { width: 42 }),
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
        children: [run("Submitted to: IEEE Transactions on Reliability \u2014 Regular Paper", { size: SMALL, color: GREY })],
        paragraph: { spacing: { after: 220, line: 312 } },
      }),

      para("The following researchers have expertise directly relevant to this submission. None of them has collaborated with, co-published with, or supervised any of the submitting authors, and to the best of our knowledge none has a conflict of interest with this work. They are listed in priority order."),

      tableTitle("Table 1. Suggested reviewers (in priority order)."),
      makeTable(revHeader, reviewerRows),

      heading2("Notes for the submission form"),
      bullet("E-mail addresses:", "are deliberately not pre-filled here, to avoid transcription errors. Before entry, copy each address from the researcher\u2019s official faculty page, the journal\u2019s own reviewer records, or a recent corresponding-author e-mail on one of their papers (e.g., for the CALCE director, the CALCE center page at the University of Maryland)."),
      bullet("ORCID lookup:", "reviewer ORCIDs can be resolved by searching the name at orcid.org if the form requests them."),
      bullet("Opposed reviewers:", "none declared."),
      bullet("Domain balance:", "the list spans battery PHM (1, 2, 5), machine learning for battery state estimation (3), calibration methodology (4), and the base failure-risk framework (6, 7), matching the manuscript\u2019s three pillars: prognostics, validity controls, and calibration."),
    ],
  }],
});

// =====================================================================
// DOCUMENT 3 — SUBMISSION CHECKLIST
// =====================================================================
const chk = (name, detail, status, statusFill) => [
  cell(name, { bold: true, width: 24 }),
  cell(detail, { width: 56 }),
  cell(status, { bold: true, width: 20, fill: statusFill, align: AlignmentType.CENTER }),
];

const submissionChecklist = new Document({
  styles: {
    default: {
      document: {
        run: { font: FONT, size: BODY, color: BLACK },
        paragraph: { spacing: { line: 312 } },
      },
      heading1: { run: { font: FONT, size: 28, bold: true, color: BLACK }, paragraph: { spacing: { before: 320, after: 140, line: 312 } } },
      heading2: { run: { font: FONT, size: 25, bold: true, color: BLACK }, paragraph: { spacing: { before: 240, after: 120, line: 312 } } },
    },
  },
  sections: [{
    properties: { page: PAGE },
    footers: { default: pageFooter() },
    children: [
      para("", {
        children: [new TextRun({ text: "IEEE Transactions on Reliability \u2014 Submission Checklist", bold: true, size: 32, color: BLACK, font: FONT })],
        paragraph: { spacing: { after: 60, line: 360 } },
      }),
      para("", {
        children: [run("Manuscript: ", { bold: true }), new TextRun({ text: TITLE, italics: true, size: SMALL, color: BLACK, font: FONT })],
        paragraph: { spacing: { after: 60, line: 312 } },
      }),
      para("", {
        children: [run("Corresponding author: Hussain Touhid Siddiquee \u00B7 touhidsiddiqueeraj@gmail.com \u00B7 prepared October 30, 2026", { size: SMALL, color: GREY })],
        paragraph: { spacing: { after: 220, line: 312 } },
      }),

      heading1("A. Files in this package"),
      tableTitle("Table A-1. Package contents and readiness."),
      makeTable([
        cell("File", { bold: true, width: 34, fill: "EEF2F6" }),
        cell("Purpose", { bold: true, width: 46, fill: "EEF2F6" }),
        cell("Status", { bold: true, width: 20, fill: "EEF2F6" }),
      ], [
        chk("paper_tr/main_tr.pdf", "Main manuscript, 12 double-column pages (IEEEtran journal class), compiled from main_tr.tex.", "Ready", "E3F2E3"),
        chk("paper_tr/main_tr.tex", "LaTeX source of the main manuscript, including the corrected author block and verified bibliography.", "Ready", "E3F2E3"),
        chk("paper_tr/supplement_tr.pdf", "Supplementary Material, 3 pages, all tables generated programmatically from the validated results file.", "Ready", "E3F2E3"),
        chk("paper_tr/supplement_tr.tex", "LaTeX source of the supplement.", "Ready", "E3F2E3"),
        chk("paper_tr/figs/ (4 figures)", "Fig01 within-dataset AUC, Fig02 SOH-ablation transfer collapse, Fig05 multi-horizon AUC, deployment architecture figure.", "Ready", "E3F2E3"),
        chk("paper_tr/IEEEtran.cls", "Class file used for compilation.", "Ready", "E3F2E3"),
        chk("Cover_Letter_IEEE_TR.docx", "Cover letter for the submission.", "Ready", "E3F2E3"),
        chk("Suggested_Reviewers_IEEE_TR.docx", "Seven suggested reviewers with expertise rationale; e-mails to be completed from official pages.", "1 field", "FFF4E0"),
        chk("AUTHORS.md", "Author order, roles, ORCIDs, and profile links for the submission forms.", "Ready", "E3F2E3"),
        chk("README.md", "Guide to the package, its recovery history, and the four-round review record.", "Ready", "E3F2E3"),
      ]),

      heading1("B. Manuscript compliance"),
      tableTitle("Table B-1. IEEE TR format requirements."),
      makeTable([
        cell("Requirement", { bold: true, width: 24, fill: "EEF2F6" }),
        cell("How it is met", { bold: true, width: 56, fill: "EEF2F6" }),
        cell("Status", { bold: true, width: 20, fill: "EEF2F6" }),
      ], [
        chk("Double-column IEEE format", "IEEEtran journal class (class file included); Times-equivalent text face via TeX Gyre Termes.", "Met", "E3F2E3"),
        chk("Length", "12 pages main text plus a 3-page supplement (15 total), within the ~15-page regular-paper limit. Verify the current limit and over-length policy on the IEEE TR Author Center before uploading.", "Verify limit", "FFF4E0"),
        chk("Title, abstract, index terms", "Abstract is single-paragraph and self-contained; nine index terms follow the abstract.", "Met", "E3F2E3"),
        chk("Author block", "All four authors with affiliation; corresponding author marked; all four author e-mail addresses in the first-page footnote.", "Met", "E3F2E3"),
        chk("Co-author e-mails", "All four authors\u2019 e-mail addresses (corresponding author and the three co-authors) are listed in the first-page \\thanks footnote.", "Met", "E3F2E3"),
        chk("References", "39 entries in IEEE style, ordered by first citation: the original 25 verified against publisher records, plus 14 added citations (battery PHM/BMS reviews, dataset shift, shortcut learning, and the methodological sources for the GRU, hazard model, bootstrap, AUC, Brier score, ECE, PR-AUC, and TinyML), all verified on October 30, 2026.", "Met", "E3F2E3"),
        chk("Author biographies", "IEEE-style biography paragraphs for all four authors after the references; photos can be added at revision or acceptance.", "Met", "E3F2E3"),
        chk("Figures", "All four figures referenced in the text, no missing or unused files; every page visually inspected after the final compile.", "Met", "E3F2E3"),
        chk("\u201CManuscript received\u201D dates", "Left as XXX on the first-page footnote; the editorial office fills these in.", "Standard", "E3F2E3"),
        chk("Funding / acknowledgments", "No funding or acknowledgment section is currently present. Add one before submission if funding applies.", "If applicable", "FFF4E0"),
      ]),

      heading1("C. Items to complete before uploading"),
      para("", {
        children: [run("These are the genuinely open items; each is also marked in the source files.", { color: GREY, size: SMALL })],
        paragraph: { spacing: { after: 120, line: 312 } },
      }),
      bullet("1. Companion-study reference [18]: ", "the entry for Shikdar and Laaksonen\u2019s calibration-robustness companion study is currently cited as \u201Cmanuscript under review.\u201D Replace with the final venue if it is accepted before submission."),
      bullet("2. Lost figures (optional): ", "the SHAP beeswarm panels, the Python-vs-C agreement scatter, the Battery Archive capacity-trace audit, the decision-curve figure, and the calibration figure were lost with the earlier working environment. If the local repository still holds them, copy them into paper_tr/figs/ and re-add their figure environments; otherwise the paper stands complete with the four regenerated figures and the text-only SHAP paragraph."),
      bullet("3. ORCIDs: ", "enter all four authors\u2019 ORCIDs in ScholarOne (listed in AUTHORS.md); ORCIDs are entered in the system, not printed in the manuscript."),
      bullet("4. Data and code availability: ", "all eight datasets are public and cited; prepare a short availability statement for the form if requested, noting that the Battery Archive summaries were accessed in September 2026."),
      bullet("5. Page-charge policy: ", "check the current IEEE TR over-length page charges and open-access options on the Author Center when submitting."),

      heading1("D. Quality assurance record (four-round review)"),
      para("The manuscript has been through four review rounds; all fixes below are already applied in the compiled PDF."),
      bullet("Round 1 \u2014 Figures: ", "four figures, all present, referenced, and visually inspected; no overflow, overlap, or cut-off content on any page. Figures were regenerated programmatically from the validated results file; five legacy figure sets are documented as lost with the earlier environment (see item C-2)."),
      bullet("Round 2 \u2014 Numbers: ", "379 automated checks of every table row and in-text claim in the main paper and supplement against the validated results file \u2014 all pass. Three transcription errors were caught and fixed during re-verification (Oxford SOH-delta range, a factorial-ablation value, a column ordering in the supplement)."),
      bullet("Round 3 \u2014 References: ", "39 cite keys matched to 39 bibliography entries, in order of first citation; no undefined citations, orphans, or duplicates. On October 30, 2026, every entry was verified against publisher records: five reconstructed entries were corrected to their published details, one unverifiable entry (a JMLR attribution) was replaced with the verifiable ICML 2023 paper by the same authors, one citation-context mismatch was fixed (the Huang et al. finding on imbalanced-data calibration is now stated accurately), and 14 standard citations were added to widen coverage of the battery-PHM, dataset-shift, and methodology literature, each verified against Crossref, the publisher page, PMLR, the ACL Anthology, or arXiv."),
      bullet("Round 4 \u2014 Consistency and readability: ", "section cross-references verified against the compiled headings; author biographies deduplicated; placeholder audit clean; layout inspected on all 15 pages. The package was recompiled and re-inspected after the author-block, bibliography-expansion, and reference-verification updates of October 30, 2026."),

      heading1("E. At submission and after"),
      bullet("Upload order: ", "main PDF, supplement PDF, cover letter, then the source files if the system requests LaTeX sources (include IEEEtran.cls, both .tex files, and the figs/ directory)."),
      bullet("Suggested reviewers: ", "enter the seven names from Suggested_Reviewers_IEEE_TR.docx, completing each e-mail from the researcher\u2019s official page."),
      bullet("After the decision: ", "respond to reviewers point by point; re-run the number-verification script after any change to a quantitative claim; author photos are typically required with the final files."),
    ],
  }],
});

// ---------- write all three ----------
Promise.all([
  Packer.toBuffer(coverLetter).then(b => fs.writeFileSync(OUT + "/Cover_Letter_IEEE_TR.docx", b)),
  Packer.toBuffer(suggestedReviewers).then(b => fs.writeFileSync(OUT + "/Suggested_Reviewers_IEEE_TR.docx", b)),
  Packer.toBuffer(submissionChecklist).then(b => fs.writeFileSync(OUT + "/Submission_Checklist_IEEE_TR.docx", b)),
]).then(() => console.log("All three documents written to " + OUT));
