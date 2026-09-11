"""Import the reviewed enemy drafts without replacing existing authored work.

This is an authoring operation. Insertion belongs to build_enemies.py; the
separate TSV reviews retain game/source evidence and editorial provenance.
"""

import csv
import json
from pathlib import Path
import re

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.translation_pipeline import atomic_write, check


def write_json(path, data):
    atomic_write(path, (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode())


def prepare():
    path = ROOT / "translations/master.json"
    master = json.loads(path.read_text())
    glossary_path = ROOT / "translations/glossary.json"
    glossary = json.loads(glossary_path.read_text())
    families = {name: {} for name in ("monster_names", "monster_traits")}
    for entry in master["entries"]:
        for member in entry["table_memberships"]:
            if member["table"] in families:
                families[member["table"]][member["row"]] = entry
    check(all(len(v) == 200 for v in families.values()), "Enemy tables incomplete")
    by_jp = {jp: term for term in glossary["terms"] for jp in term["japanese"]}
    for review in csv.DictReader((ROOT / "translations/enemy-name-review.tsv").open(), delimiter="\t"):
        row = int(review["row"])
        entry = families["monster_names"][row]
        english = review["english"]
        check(entry["english"] in (None, english), f"Existing name differs: {row}")
        if entry["english"] is None:
            entry.update(english=english, notes=f"Combined enemy/item review: {review['note']}")
        jp = entry["japanese"]
        ident = "enemy_" + re.sub(r"[^a-z0-9]+", "_", english.lower()).strip("_")
        sources = []
        if review["source"]:
            key = "combined_" + ident
            sources = [key]
            glossary["sources"][key] = {"url": review["source"], "reference_game": review["reference_game"],
                "evidence": "Secondary fan-maintained reference; Japanese identity and localized name. " + review["note"]}
        term = by_jp.get(jp)
        if term is None:
            term = {"id": ident, "japanese": [jp], "english": english,
                    "status": "modern_official_name_secondary_evidence" if sources else "project_choice",
                    "sources": sources, "notes": review["note"], "occurrences": [],
                    "batch": "combined-enemies-items", "insertion_status": "pending"}
            glossary["terms"].append(term)
            by_jp[jp] = term
        check(term["english"] == english, f"Conflicting glossary name for {jp}")
        occurrence = {"catalog": "translations/master.json", "id": entry["id"]}
        if occurrence not in term["occurrences"]:
            term["occurrences"].append(occurrence)
    reviews = list(csv.DictReader((ROOT / "translations/enemy-trait-review.tsv").open(), delimiter="\t"))
    known = {e["japanese"]: (e["english"], e["notes"]) for e in families["monster_traits"].values() if e["english"]}
    for review in reviews:
        entry = families["monster_traits"][int(review["row"])]
        known[entry["japanese"]] = (review["english"], review["note"])
    for row, entry in families["monster_traits"].items():
        if entry["english"] is None:
            english, note = known[entry["japanese"]]
            check(english.count("<CR>") == entry["japanese"].count("<CR>"), f"Source draft line-control count differs: {row}")
            entry.update(english=english, notes="Combined enemy/item independent Japanese translation: " + note)
    check(all(e["english"] for f in families.values() for e in f.values()), "Incomplete enemy drafts")
    write_json(path, master)
    write_json(glossary_path, glossary)
    return master


if __name__ == "__main__":
    prepare()
