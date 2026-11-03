"""
Converte il catalogo CAPEC (formato STIX, stix-capec.json del repository mitre/cti)
in tanti file Markdown leggibili, uno per schema d'attacco, pronti per il RAG.

Uso:
    python capec_to_md.py <file stix-capec.json> <cartella di output>

Esempio:
    python capec_to_md.py C:\\AI\\SecurityKB\\CAPEC\\stix-capec.json C:\\AI\\SecurityKB\\CAPEC\\md
"""

import json
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

# Stati da scartare: voci ritirate o superate da altre
SKIP_STATUS = {"Deprecated", "Obsolete"}


class TextFromHTML(HTMLParser):
    """Trasforma i pezzi di HTML presenti in CAPEC in testo semplice."""

    def __init__(self):
        super().__init__()
        self.parts = []

    def after_bullet(self):
        """Vero se l'ultimo pezzo scritto (spazi esclusi) è l'inizio di un punto elenco."""
        for part in reversed(self.parts):
            if part.strip():
                return part.endswith("- ")
        return False

    def handle_starttag(self, tag, attrs):
        tag = tag.split(":")[-1]  # 'xhtml:p' -> 'p'
        if tag in ("h2", "h3", "h4"):
            self.parts.append("\n\n**")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "th":
            self.parts.append("\n  ")
        elif tag == "td":
            self.parts.append("\n  - ")
        elif tag in ("p", "div", "br", "ul", "ol", "table") and not self.after_bullet():
            self.parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.split(":")[-1]
        if tag in ("h2", "h3", "h4"):
            self.parts.append("**\n")
        elif tag == "th":
            self.parts.append(":")
        elif tag in ("p", "div"):
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(html):
    if not html:
        return ""
    parser = TextFromHTML()
    parser.feed(html)
    out = []
    for raw in "".join(parser.parts).split("\n"):
        # le voci delle tabelle ("Techniques") restano rientrate sotto il loro punto
        indent = "  " if raw.startswith("  - ") else ""
        line = indent + re.sub(r"\s+", " ", raw).strip()
        # sistema i titoli in grassetto ("** Explore **" -> "**Explore**")
        line = re.sub(r"\*\*\s*(.*?)\s*\*\*", r"**\1**", line)
        if line == "**Execution Flow**":  # già presente come titolo di sezione
            continue
        if line or (out and out[-1]):  # niente righe vuote doppie
            out.append(line)
    return "\n".join(out).strip()


def capec_id(obj):
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "capec":
            return ref.get("external_id", "")
    return ""


def main(input_path, output_dir):
    with open(input_path, encoding="utf-8") as f:
        objects = json.load(f)["objects"]

    by_id = {o["id"]: o for o in objects}

    # Mitigazioni: nel formato STIX sono oggetti separati, collegati da relazioni
    mitigations = defaultdict(list)
    for r in objects:
        if r["type"] == "relationship" and r["relationship_type"] == "mitigates":
            coa = by_id.get(r["source_ref"])
            if coa is not None:
                mitigations[r["target_ref"]].append(html_to_text(coa.get("description", "")))

    def ids(refs):
        """Da una lista di riferimenti interni agli ID CAPEC leggibili."""
        return [capec_id(by_id[r]) for r in refs or [] if r in by_id and capec_id(by_id[r])]

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    count = 0

    for a in objects:
        if a["type"] != "attack-pattern" or a.get("revoked") or a.get("x_capec_status") in SKIP_STATUS:
            continue
        cid = capec_id(a)
        if not cid:
            continue

        refs = a.get("external_references", [])
        cwes = [r["external_id"] for r in refs if r.get("source_name") == "cwe"]
        others = [
            f"{r['source_name']}: {r.get('description') or r.get('external_id', '')}"
            for r in refs
            if r.get("source_name") in ("WASC", "OWASP Attacks", "ATTACK")
        ]

        lines = [f"# {cid} — {a['name']}", ""]
        lines.append(f"- **ID:** {cid}")
        lines.append(f"- **Abstraction:** {a.get('x_capec_abstraction', 'n/a')}")
        lines.append(f"- **Status:** {a.get('x_capec_status', 'n/a')}")
        lines.append(f"- **Likelihood of attack:** {a.get('x_capec_likelihood_of_attack', 'n/a')}")
        lines.append(f"- **Typical severity:** {a.get('x_capec_typical_severity', 'n/a')}")
        if a.get("x_capec_child_of_refs"):
            lines.append(f"- **Child of:** {', '.join(ids(a['x_capec_child_of_refs']))}")
        if a.get("x_capec_parent_of_refs"):
            lines.append(f"- **Parent of:** {', '.join(ids(a['x_capec_parent_of_refs']))}")
        if cwes:
            lines.append(f"- **Related weaknesses (CWE):** {', '.join(cwes)}")
        if others:
            lines.append(f"- **Other references:** {'; '.join(others)}")
        lines.append(f"- **Source:** https://capec.mitre.org/data/definitions/{cid.split('-')[1]}.html")

        lines += ["", "## Description", "", html_to_text(a.get("description", ""))]
        if a.get("x_capec_extended_description"):
            lines += ["", html_to_text(a["x_capec_extended_description"])]

        if a.get("x_capec_prerequisites"):
            lines += ["", "## Prerequisites", ""]
            lines += [f"- {html_to_text(p)}" for p in a["x_capec_prerequisites"]]

        if a.get("x_capec_skills_required"):
            lines += ["", "## Skills required", ""]
            lines += [f"- **{level}**: {html_to_text(text)}" for level, text in a["x_capec_skills_required"].items()]

        if a.get("x_capec_resources_required"):
            lines += ["", "## Resources required", ""]
            lines += [f"- {html_to_text(r)}" for r in a["x_capec_resources_required"]]

        if a.get("x_capec_execution_flow"):
            lines += ["", "## Execution flow", "", html_to_text(a["x_capec_execution_flow"])]

        if a.get("x_capec_consequences"):
            lines += ["", "## Consequences", ""]
            for scope, impacts in a["x_capec_consequences"].items():
                lines.append(f"- **{scope.replace('_', ' ')}**: {', '.join(dict.fromkeys(impacts))}")

        if mitigations[a["id"]]:
            lines += ["", "## Mitigations", ""]
            lines += [f"- {m}" for m in mitigations[a["id"]] if m]

        if a.get("x_capec_example_instances"):
            lines += ["", "## Example instances", ""]
            lines += [f"- {html_to_text(e)}" for e in a["x_capec_example_instances"]]

        text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)) + "\n"
        (out / f"{cid}.md").write_text(text, encoding="utf-8")
        count += 1

    print(f"Fatto: {count} schemi d'attacco CAPEC in {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
