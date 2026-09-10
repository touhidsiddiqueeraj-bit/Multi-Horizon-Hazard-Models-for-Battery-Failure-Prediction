"""Produce main_docx.tex: the conference paper flattened for pandoc
(IEEE headings numbered, \\cite/\\ref resolved, floats simplified)."""
import re

src = open("main.tex").read()

# label -> rendered number maps (order = document order)
SEC = []  # (label not used; sections numbered by order)
sec_num = 0
sub_num = 0
def num_sections(m):
    global sec_num, sub_num
    if m.group(1) is None:
        sec_num += 1
        sub_num = 0
        rom = ["I", "II", "III", "IV", "V", "VI"][sec_num - 1]
        return "\\section{%s. %s}" % (rom, m.group(2))
    sub_num += 1
    letter = "ABCDEFGH"[sub_num - 1]
    return "\\subsection{%s-%s %s}" % (["I", "II", "III", "IV", "V", "VI"][sec_num - 1],
                                       letter, m.group(2))

src = re.sub(r"\\(sub)?section\{([^}]*)\}", num_sections, src)

REF = {
    "tab:datasets": "Table I", "tab:within": "Table II", "tab:calibration": "Table III",
    "tab:transfer": "Table IV", "tab:faildef": "Table V", "tab:samechem": "Table VI",
    "tab:hazard": "Table VII", "tab:operational": "Table VIII", "tab:soh": "Table IX",
    "fig:framework": "Fig. 1", "fig:horizons": "Fig. 2",
    "fig:reliability": "Fig. 3", "fig:collapse": "Fig. 4",
    "eq:features": "(1)", "eq:window": "(2)", "eq:label": "(3)", "eq:prob": "(4)",
    "eq:platt": "(5)", "eq:iso": "(6)", "eq:hazarddef": "(7)", "eq:survival": "(8)",
}
src = src.replace("Figure~\\ref{", "\\ref{").replace("Fig.~\\ref{", "\\ref{").replace("Table~\\ref{", "\\ref{")
for k, v in REF.items():
    src = src.replace("\\ref{%s}" % k, v)

CITES = ["berecibar2016", "xu2024", "bairwa2025", "tetik2026", "jin2021",
         "li2026", "thelen2024", "li2026lightgbm", "wang2021", "rastegarpanah2024",
         "sun2025", "ibraheem2025", "li2024", "yao2024", "pang2026",
         "platt1999", "zadrozny2002", "goldstein2020", "lundberg2017",
         "dosreis2021", "li2025", "delong1988", "severson2019", "saha2007",
         "calce2023", "birkl2017"]
NUM = {k: i + 1 for i, k in enumerate(CITES)}

def cite_sub(m):
    keys = [k.strip() for k in m.group(1).split(",")]
    nums = sorted(NUM[k] for k in keys)
    # consecutive runs -> dashes
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            parts.append("[%d]--[%d]" % (nums[i], nums[j]))
        elif j == i:
            parts.append("[%d]" % nums[i])
        else:
            parts.append("[%d], [%d]" % (nums[i], nums[j]))
        i = j + 1
    return "".join(parts)

src = re.sub(r"\\cite\{([^}]*)\}", cite_sub, src)

# pandoc mangles multicolumn/cline headers -> flatten for the docx
src = re.sub(r"\\cline\{[0-9-]+\}(?:\\cline\{[0-9-]+\})*\n", "", src)
src = src.replace(
    " & \\multicolumn{2}{c|}{\\textbf{Oxford}} & \\multicolumn{2}{c|}{\\textbf{Severson}}\\\\\n"
    "\\textbf{Label endpoint} & \\textbf{w/ SOH} & \\textbf{no SOH} & \\textbf{w/ SOH} & \\textbf{no SOH}\\\\",
    "\\textbf{Label endpoint} & \\textbf{Oxford w/ SOH} & \\textbf{Oxford no SOH} & \\textbf{Severson w/ SOH} & \\textbf{Severson no SOH}\\\\")
src = src.replace(
    " & \\multicolumn{2}{c|}{\\textbf{$H{=}20$}} & \\multicolumn{2}{c|}{\\textbf{$H{=}50$}}\\\\\n"
    "\\textbf{Setting} & \\textbf{Fixed} & \\textbf{Hazard} & \\textbf{Fixed} & \\textbf{Hazard}\\\\",
    "\\textbf{Setting} & \\textbf{Fixed $H{=}20$} & \\textbf{Hazard $H{=}20$} & \\textbf{Fixed $H{=}50$} & \\textbf{Hazard $H{=}50$}\\\\")
src = src.replace(
    " & \\multicolumn{2}{c|}{\\textbf{Oxford}} & \\multicolumn{2}{c|}{\\textbf{Severson}}\\\\\n"
    "\\textbf{Training} & \\textbf{Model} & \\textbf{w/ SOH} & \\textbf{no SOH} & \\textbf{w/ SOH} & \\textbf{no SOH}\\\\",
    "\\textbf{Training} & \\textbf{Model} & \\textbf{Oxford w/ SOH} & \\textbf{Oxford no SOH} & \\textbf{Severson w/ SOH} & \\textbf{Severson no SOH}\\\\")
src = re.sub(r"\\fontsize\{\d+\}\{\d+\}\\selectfont\n?", "", src)
src = re.sub(r"\\setlength\{\\tabcolsep\}\{[^}]*\}\n?", "", src)

# collapse doubled words created by ref resolution
src = src.replace(
    " & \\multicolumn{2}{c}{Oxford} & \\multicolumn{2}{c}{Severson}\\\\\n"
    "Label endpoint & w/ SOH & no SOH & w/ SOH & no SOH\\\\",
    "Label endpoint & \\textbf{Oxford w/ SOH} & \\textbf{Oxford no SOH} & \\textbf{Severson w/ SOH} & \\textbf{Severson no SOH}\\\\")
src = src.replace("Fig. Fig.", "Fig.").replace("Table Table", "Table ")
src = src.replace("Figure Fig.", "Figure")

# pandoc cannot parse \input inside tabular -> inline the fragments
def inline_frag(m):
    return open(m.group(1) + ".tex").read()
src = re.sub(r"\\input\{(generated/[a-z_]+)\}", inline_frag, src)

# flatten environments pandoc does not know
src = src.replace("\\begin{abstract}", "\\noindent\\textbf{Abstract---}")
src = src.replace("\\end{abstract}", "\n")
src = src.replace("\\begin{IEEEkeywords}", "\\noindent\\textbf{Index Terms---}")
src = src.replace("\\end{IEEEkeywords}", "\n")
src = src.replace("\\IEEEkeywords", "")

# tables: strip resizebox + booktabs rules stay (pandoc reads tabular)
src = src.replace("\\resizebox{\\columnwidth}{!}{%\n", "")
src = src.replace("\\end{tabular}}", "\\end{tabular}")

# equation numbers: pandoc drops numbering -> add explicit tag text
eq_labels = re.findall(r"\\label\{(eq:[a-z]+)\}", src)
for i, lab in enumerate(eq_labels, 1):
    src = src.replace("\\label{%s}" % lab,
                      "\\qquad \\text{(%d)}" % i)

# drop layout-only commands
for cmd in ["\\balance", "\\clearpage", "\\raggedbottom",
            "\\setlength{\\abovecaptionskip}{3pt}",
            "\\setlength{\\belowcaptionskip}{1pt}",
            "\\setlength{\\textfloatsep}{7pt plus 2pt minus 2pt}",
            "\\setlength{\\floatsep}{7pt plus 2pt minus 2pt}",
            "\\setlength{\\intextsep}{7pt plus 2pt minus 2pt}",
            "\\titlepgskip=-21pt", "\\EOD"]:
    src = src.replace(cmd + "\n", "")
src = src.replace("\\emergencystretch=6em\n", "")
src = src.replace("\\makeatletter\\def\\UrlBreaks{\\do\\/\\do\\-}\\makeatother\n", "")

open("main_docx.tex", "w").write(src)
print("wrote main_docx.tex (%d chars)" % len(src))
