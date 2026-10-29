"""Assemble report/FINAL_REPORT.md from the section files and export it to Word with pandoc.

    python report/build_report.py

Order: 00 front matter, 01 introduction + data + methods, 04 benchmark results, 05 PINN (pinn/PINN_RESULTS.md),
06 Mahanadi atlas, 07 engineering impacts, 08 field visit, 09 implementation, 10 discussion, appendices A-B (training audit, 20 m retraining), C (engineering details), D (reproducing
the results) and E (glossary).
`{{TABLE:X}}` markers are replaced by the matching table of sections/02_tables.md (written by
scripts/make_tables.py), so the numbers in the text and in the tables come from the same analysis files.
"""
import os
import re

import pypandoc

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
S = os.path.join(HERE, "sections")


def read(p):
    return open(p, encoding="utf-8").read().strip() + "\n\n"


tables = {}
for block in re.split(r"\n(?=\*\*Table [A-Z]\.)", read(os.path.join(S, "02_tables.md"))):
    m = re.match(r"\*\*Table ([A-Z])\.", block.strip())
    if m:
        tables[m.group(1)] = block.strip()

pinn = read(os.path.join(ROOT, "pinn", "PINN_RESULTS.md"))
pinn = re.sub(r"^## (\d)\. ", r"### 5.\1 ", pinn, flags=re.M)  # sub-sections first, so the chapter title is not renumbered
pinn = re.sub(r"^# .*\n", "## 5. Physics track: Saint-Venant equations and the PINN\n", pinn, count=1)
pinn = pinn.replace("`results/logs/`", "`pinn/results/logs/`").replace("`results/figures/`", "`pinn/results/figures/`")

order = ["00_front.md", "01_intro_data_methods.md", "04_results.md", None, "06_mahanadi.md", "07_impacts.md",
         "08_field.md", "09_implementation.md", "10_discussion.md", "11_appendix.md", "12_appendix_c.md", "13_appendix_de.md"]
parts = [pinn if name is None else read(os.path.join(S, name)) for name in order if name is None or os.path.exists(os.path.join(S, name))]
md = "".join(parts)
md = re.sub(r"\{\{TABLE:([A-Z])\}\}", lambda m: tables.get(m.group(1), f"*(Table {m.group(1)} missing)*"), md)
out_md = os.path.join(HERE, "FINAL_REPORT.md")
open(out_md, "w", encoding="utf-8").write(md)
pypandoc.convert_file(out_md, "docx", outputfile=os.path.join(HERE, "FINAL_REPORT.docx"),
                      extra_args=[f"--resource-path={HERE}{os.pathsep}{ROOT}", "--toc", "--toc-depth=2"])
print("written FINAL_REPORT.md and FINAL_REPORT.docx", len(md.split()), "words")
