"""
Converte il catalogo CWE (formato XML di MITRE, cwec_vX.Y.xml o il suo .zip)
in tanti file Markdown leggibili, uno per debolezza, pronti per il RAG.

Uso:
    python cwe_to_md.py <file .xml o .zip> <cartella di output>

Esempio:
    python cwe_to_md.py C:\\AI\\SecurityKB\\CWE\\cwec_latest.xml.zip C:\\AI\\SecurityKB\\CWE\\md
"""

import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Lo "spazio dei nomi" XML del catalogo CWE: ogni tag è prefissato da questo
NS = {"c": "http://cwe.mitre.org/cwe-7"}

# Quanti esempi reali (CVE) elencare al massimo per debolezza
MAX_CVE = 10


def open_catalog(path):
    """Apre il catalogo, che sia l'.xml o lo .zip che lo contiene."""
    if path.lower().endswith(".zip"):
        archive = zipfile.ZipFile(path)
        xml_name = next(n for n in archive.namelist() if n.lower().endswith(".xml"))
        return ET.parse(archive.open(xml_name)).getroot()
    return ET.parse(path).getroot()


def flatten(element):
    """Trasforma un pezzo di XML (che può contenere paragrafi, elenchi, codice)
    in testo semplice, andando a capo dove serve."""
    if element is None:
        return ""
    parts = []

    def walk(e):
        tag = e.tag.split("}")[-1]
        if tag in ("br", "p", "div", "tr", "ul", "ol", "table"):
            parts.append("\n")
        elif tag == "li":
            parts.append("\n- ")
        if e.text:
            parts.append(e.text)
        for child in e:
            walk(child)
            if child.tail:
                parts.append(child.tail)
        if tag in ("p", "div", "li", "tr"):
            parts.append("\n")

    walk(element)
    lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(parts).split("\n")]
    out = []
    for line in lines:
        if line or (out and out[-1]):  # niente righe vuote doppie
            out.append(line)
    return "\n".join(out).strip()


def items(weakness, path):
    """Restituisce tutti gli elementi che corrispondono al percorso indicato."""
    return weakness.findall(path, NS)


def write_weakness(w, out_dir):
    cwe_id = f"CWE-{w.get('ID')}"
    lines = [f"# {cwe_id} — {w.get('Name')}", ""]
    lines.append(f"- **ID:** {cwe_id}")
    lines.append(f"- **Abstraction:** {w.get('Abstraction')}")
    lines.append(f"- **Status:** {w.get('Status')}")

    likelihood = w.find("c:Likelihood_Of_Exploit", NS)
    if likelihood is not None:
        lines.append(f"- **Likelihood of exploit:** {likelihood.text}")

    related = [
        f"{r.get('Nature')} CWE-{r.get('CWE_ID')}"
        for r in items(w, "c:Related_Weaknesses/c:Related_Weakness")
    ]
    if related:
        lines.append(f"- **Related weaknesses:** {', '.join(dict.fromkeys(related))}")

    capec = [f"CAPEC-{a.get('CAPEC_ID')}" for a in items(w, "c:Related_Attack_Patterns/c:Related_Attack_Pattern")]
    if capec:
        lines.append(f"- **Related attack patterns (CAPEC):** {', '.join(capec)}")

    lines.append(f"- **Source:** https://cwe.mitre.org/data/definitions/{w.get('ID')}.html")

    # Descrizione
    lines += ["", "## Description", "", flatten(w.find("c:Description", NS))]
    extended = flatten(w.find("c:Extended_Description", NS))
    if extended:
        lines += ["", extended]

    # Classificazioni esterne (OWASP Top Ten, ecc.)
    mappings = []
    for m in items(w, "c:Taxonomy_Mappings/c:Taxonomy_Mapping"):
        entry_id = m.findtext("c:Entry_ID", "", NS)
        entry_name = m.findtext("c:Entry_Name", "", NS)
        label = " ".join(x for x in (entry_id, entry_name) if x)
        if label:
            mappings.append(f"- {m.get('Taxonomy_Name')}: {label}")
    if mappings:
        lines += ["", "## Taxonomy mappings", ""] + mappings

    # Conseguenze
    consequences = []
    for c in items(w, "c:Common_Consequences/c:Consequence"):
        scope = ", ".join(s.text for s in c.findall("c:Scope", NS))
        impact = ", ".join(i.text for i in c.findall("c:Impact", NS))
        note = flatten(c.find("c:Note", NS))
        consequences.append(f"- **{scope}** — {impact}" + (f": {note}" if note else ""))
    if consequences:
        lines += ["", "## Common consequences", ""] + consequences

    # Rilevamento
    detections = []
    for d in items(w, "c:Detection_Methods/c:Detection_Method"):
        method = d.findtext("c:Method", "", NS)
        effectiveness = d.findtext("c:Effectiveness", "", NS)
        header = f"**{method}**" + (f" (effectiveness: {effectiveness})" if effectiveness else "")
        detections.append(f"- {header}: {flatten(d.find('c:Description', NS))}")
    if detections:
        lines += ["", "## Detection methods", ""] + detections

    # Mitigazioni
    mitigations = []
    for m in items(w, "c:Potential_Mitigations/c:Mitigation"):
        phase = ", ".join(p.text for p in m.findall("c:Phase", NS))
        strategy = m.findtext("c:Strategy", "", NS)
        header = " / ".join(x for x in (phase, strategy) if x) or "General"
        mitigations.append(f"- **{header}**: {flatten(m.find('c:Description', NS))}")
    if mitigations:
        lines += ["", "## Potential mitigations", ""] + mitigations

    # Esempi di codice: testo e blocchi di codice, nell'ordine originale
    examples = items(w, "c:Demonstrative_Examples/c:Demonstrative_Example")
    if examples:
        lines += ["", "## Demonstrative examples"]
        for n, ex in enumerate(examples, 1):
            lines += ["", f"### Example {n}", ""]
            for part in ex:
                tag = part.tag.split("}")[-1]
                if tag == "Example_Code":
                    nature = part.get("Nature", "")
                    language = part.get("Language", "")
                    lines.append(f"Code ({nature}{', ' + language if language else ''}):")
                    lines += ["```" + language.lower().replace(" ", ""), flatten(part), "```"]
                elif tag in ("Intro_Text", "Body_Text"):
                    lines += [flatten(part), ""]

    # Casi reali (CVE)
    observed = []
    for o in items(w, "c:Observed_Examples/c:Observed_Example")[:MAX_CVE]:
        observed.append(f"- {o.findtext('c:Reference', '', NS)}: {o.findtext('c:Description', '', NS)}")
    if observed:
        lines += ["", "## Observed examples (real CVEs)", ""] + observed

    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)) + "\n"
    (out_dir / f"{cwe_id}.md").write_text(text, encoding="utf-8")


def main(input_path, output_dir):
    root = open_catalog(input_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    count = 0
    for w in root.findall("c:Weaknesses/c:Weakness", NS):
        if w.get("Status") == "Deprecated":  # scarta le voci ritirate
            continue
        write_weakness(w, out)
        count += 1

    print(f"Fatto: {count} debolezze dal catalogo CWE {root.get('Version')} in {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
