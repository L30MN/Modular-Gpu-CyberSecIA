# Knowledge-base conversion scripts

Each script converts a public security dataset into small, per-entry Markdown
files suitable for RAG (one file per technique / weakness / attack pattern),
which you then upload as a Knowledge collection in Open WebUI.

**No external dependencies** — all three use only the Python standard library
(Python 3.8+). There is nothing to `pip install`.

| Script | Input | Output |
|---|---|---|
| `mitre_to_md.py` | MITRE ATT&CK STIX JSON (`enterprise-attack.json`) | one `.md` per technique + a tactics overview |
| `cwe_to_md.py` | CWE XML (`cwec_latest.xml.zip`, zip or extracted) | one `.md` per weakness |
| `capec_to_md.py` | CAPEC STIX JSON (`stix-capec.json`) | one `.md` per attack pattern |

## Usage

```bash
python scripts/mitre_to_md.py  <path-to>/enterprise-attack.json  <output-dir>
python scripts/cwe_to_md.py    <path-to>/cwec_latest.xml.zip     <output-dir>
python scripts/capec_to_md.py  <path-to>/stix-capec.json         <output-dir>
```

See `INSTALLATION.md` (step 5) for where to download each source and the
relevant licenses / attribution.
