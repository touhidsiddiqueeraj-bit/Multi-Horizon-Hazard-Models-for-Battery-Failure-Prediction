#!/usr/bin/env python3
"""Assemble paper_tr/main_tr.tex:
- lines 1-250 recovered verbatim from the previous session's cache,
- author block corrected and completed (add-authors task),
- Fig05 figure + reference inserted into Results III-A,
- reconstructed second half appended (results, analysis, conclusion,
  references, author biographies).
"""
import re

CACHE = "/home/z/my-project/recovered/main_tr_lines_1_250.tex"
PART2 = "/home/z/my-project/scripts/main_tr_part2.tex"
OUT = "/home/z/my-project/download/paper_tr/main_tr.tex"

cached = open(CACHE).read().split("\n")
# keep lines 1-250 (index 0-249); the recovered file may carry trailer lines
part1 = "\n".join(cached[:250]).rstrip() + "\n"

# ---- 1. author block: correct names, affiliation, corresponding author ----
old_author = """\\author{Hussain~Touhid~Siddiquee,
        Syeda~Salsabil~Islam,
        Ariya~Jasimul~Islam,
        and~Chowdhury~Farzana~Hoque~Eshica%
\\thanks{Manuscript received XXX; revised XXX. (Corresponding author: Hussain Touhid Siddiquee.)}%
\\thanks{The authors are with [TODO: DEPARTMENT], [TODO: UNIVERSITY], Dhaka [TODO: POSTCODE], Bangladesh (e-mail: [TODO: corresponding email]). [TODO: confirm author order and emails.]}}"""

new_author = """\\author{Hussain~Touhid~Siddiquee,
        Syeda~Salsabil~Islam,
        Jasimul~Islam~Chowdhury,
        and~Farzana~Hoque~Eshica%
\\thanks{Manuscript received XXX; revised XXX. (Corresponding author: Hussain Touhid Siddiquee.)}%
\\thanks{Hussain Touhid Siddiquee, Syeda Salsabil Islam, Jasimul Islam Chowdhury, and Farzana Hoque Eshica are with the Department of Electrical and Electronic Engineering, Leading University, Sylhet, Bangladesh (e-mail: [TODO: corresponding author e-mail]).}}"""

assert old_author in part1, "author block not found verbatim in cached part!"
part1 = part1.replace(old_author, new_author)

# ---- 2. add Fig05 reference in III-A and the figure block after fig:within ----
old_iiia = "Every tree configuration clears 0.89 at every horizon on both datasets (Fig.~\\ref{fig:within}); the GRU matches the means with higher fold variance, and the single-fit hazard model lands in the same range."
new_iiia = "Every tree configuration clears 0.89 at every horizon on both datasets (Fig.~\\ref{fig:within}); the GRU matches the means with higher fold variance (Fig.~\\ref{fig:multihorizon}), and the single-fit hazard model lands in the same range."
assert old_iiia in part1, "III-A sentence not found verbatim!"
part1 = part1.replace(old_iiia, new_iiia)

fig_within_block = """\\includegraphics[width=\\columnwidth]{Fig01_Within_Dataset_AUC.png}
\\caption{Within-dataset AUC heatmap for the tree ensembles, mean across horizons, Platt-calibrated. Right block: the four new Battery Archive groups. GRU and hazard within-dataset numbers are in Table~\\ref{tab:within}.}
\\label{fig:within}
\\end{figure}"""

fig05_block = fig_within_block + """

\\begin{figure}[!t]
\\centering
\\includegraphics[width=\\columnwidth]{Fig05_MultiHorizon_AUC.png}
\\caption{Multi-horizon AUC on NASA at $H\\in\\{10,20,30,50\\}$ (Platt-calibrated fold means). Values match Table~\\ref{tab:within}.}
\\label{fig:multihorizon}
\\end{figure}"""

assert fig_within_block in part1, "fig:within block not found!"
part1 = part1.replace(fig_within_block, fig05_block)

# ---- 3. append reconstructed second half ----
part2 = open(PART2).read()
if not part2.endswith("\n"):
    part2 += "\n"

tex = part1 + "\n" + part2
open(OUT, "w").write(tex)

# sanity checks
n_lines = tex.count("\n") + 1
labels = re.findall(r"\\label\{([^}]+)\}", tex)
refs = set(re.findall(r"\\ref\{([^}]+)\}", tex))
missing = refs - set(labels)
print(f"main_tr.tex written: {n_lines} lines")
print(f"labels: {len(labels)}; refs used: {len(refs)}; refs w/o label: {sorted(missing) or 'none'}")
cites = []
for m in re.findall(r"\\cite\{([^}]+)\}", tex):
    cites += [k.strip() for k in m.split(",")]
bibs = re.findall(r"\\bibitem\{([^}]+)\}", tex)
print(f"cite keys: {len(set(cites))}; bibitems: {len(bibs)}")
print(f"cited but no bibitem: {sorted(set(cites)-set(bibs)) or 'none'}")
print(f"bibitem never cited: {sorted(set(bibs)-set(cites)) or 'none'}")
inc = re.findall(r"\\includegraphics\[[^]]*\]\{([^}]+)\}", tex)
print(f"figures included: {inc}")
