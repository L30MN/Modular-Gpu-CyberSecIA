"""
Converte il database MITRE ATT&CK (formato STIX, enterprise-attack.json)
in tanti file Markdown leggibili, uno per tecnica, pronti per il RAG.

Uso:
    python mitre_to_md.py <file enterprise-attack.json> <cartella di output>

Esempio:
    python mitre_to_md.py C:\\AI\\SecurityKB\\MITRE\\enterprise-attack.json C:\\AI\\SecurityKB\\MITRE\\md
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Quanti gruppi/software elencare al massimo per tecnica (per non gonfiare i file)
MAX_USERS = 15


def attack_id(obj):
    """Restituisce l'ID ATT&CK (es. T1003.001) e l'URL ufficiale di un oggetto."""
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return ref.get("external_id", ""), ref.get("url", "")
    return "", ""


def clean(text):
    """Toglie i rimandi bibliografici '(Citation: ...)' che al RAG non servono."""
    text = re.sub(r"\(Citation:[^)]*\)", "", text or "")
    return re.sub(r"[ \t]+\n", "\n", text).strip()


def is_active(obj):
    """Scarta gli oggetti revocati o deprecati da MITRE."""
    return not obj.get("revoked") and not obj.get("x_mitre_deprecated")


def main(input_path, output_dir):
    # 1. Leggi il file JSON
    with open(input_path, encoding="utf-8") as f:
        objects = json.load(f)["objects"]

    # 2. Indicizza tutti gli oggetti per id, per ritrovarli velocemente
    by_id = {o["id"]: o for o in objects}

    # 3. Tattiche: dal nome breve (es. 'credential-access') al nome leggibile
    tactics = {
        o["x_mitre_shortname"]: o
        for o in objects
        if o["type"] == "x-mitre-tactic" and is_active(o)
    }

    # 4. Leggi le relazioni tra oggetti (chi mitiga, chi rileva, chi usa cosa)
    mitigations = defaultdict(list)   # tecnica -> [(nome mitigazione, come)]
    detections = defaultdict(list)    # tecnica -> [nome strategia di rilevamento]
    users = defaultdict(set)          # tecnica -> {gruppi e software che la usano}
    parent_of = {}                    # sotto-tecnica -> tecnica madre

    for r in objects:
        if r["type"] != "relationship" or not is_active(r):
            continue
        src = by_id.get(r["source_ref"])
        tgt = r["target_ref"]
        if src is None or not is_active(src):
            continue
        kind = r["relationship_type"]
        if kind == "mitigates" and src["type"] == "course-of-action":
            mitigations[tgt].append((src["name"], clean(r.get("description", ""))))
        elif kind == "detects":
            detections[tgt].append(src["name"])
        elif kind == "uses" and src["type"] in ("intrusion-set", "malware", "tool"):
            users[tgt].add(src["name"])
        elif kind == "subtechnique-of":
            parent_of[r["source_ref"]] = tgt

    # 5. Scrivi un file Markdown per ogni tecnica attiva
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    count = 0

    for t in objects:
        if t["type"] != "attack-pattern" or not is_active(t):
            continue
        tid, url = attack_id(t)
        if not tid:
            continue

        tactic_names = [
            tactics[p["phase_name"]]["name"]
            for p in t.get("kill_chain_phases", [])
            if p["phase_name"] in tactics
        ]

        lines = [f"# {tid} — {t['name']}", ""]
        lines.append(f"- **ID:** {tid}")
        lines.append(f"- **Tactic:** {', '.join(tactic_names) or 'n/a'}")
        lines.append(f"- **Platforms:** {', '.join(t.get('x_mitre_platforms', [])) or 'n/a'}")
        if t["id"] in parent_of:
            parent = by_id[parent_of[t["id"]]]
            pid, _ = attack_id(parent)
            lines.append(f"- **Sub-technique of:** {pid} — {parent['name']}")
        lines.append(f"- **Source:** {url}")
        lines += ["", "## Description", "", clean(t.get("description", ""))]

        if mitigations[t["id"]]:
            lines += ["", "## Mitigations", ""]
            for name, how in sorted(mitigations[t["id"]]):
                lines.append(f"- **{name}**: {how}" if how else f"- **{name}**")

        if detections[t["id"]]:
            lines += ["", "## Detection", ""]
            lines += [f"- {name}" for name in sorted(set(detections[t["id"]]))]

        if users[t["id"]]:
            known = sorted(users[t["id"]])
            lines += ["", "## Known use (groups and software)", ""]
            lines.append(", ".join(known[:MAX_USERS]) + (" ..." if len(known) > MAX_USERS else ""))

        (out / f"{tid}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        count += 1

    # 6. Un file riassuntivo con tutte le tattiche e le loro tecniche
    by_tactic = defaultdict(list)
    for t in objects:
        if t["type"] == "attack-pattern" and is_active(t):
            tid, _ = attack_id(t)
            for p in t.get("kill_chain_phases", []):
                if p["phase_name"] in tactics:
                    by_tactic[p["phase_name"]].append(f"{tid} {t['name']}")

    summary = ["# MITRE ATT&CK Enterprise — Tactics overview", ""]
    summary.append(f"This matrix contains {len(tactics)} tactics:")
    summary.append("")
    for short, tac in sorted(tactics.items(), key=lambda kv: attack_id(kv[1])[0]):
        taid, _ = attack_id(tac)
        summary += [f"## {taid} — {tac['name']}", "", clean(tac.get("description", "")), ""]
        summary.append("Techniques: " + "; ".join(sorted(by_tactic[short])))
        summary.append("")
    (out / "00-tactics-overview.md").write_text("\n".join(summary), encoding="utf-8")

    print(f"Fatto: {count} tecniche + 1 file riassuntivo in {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
