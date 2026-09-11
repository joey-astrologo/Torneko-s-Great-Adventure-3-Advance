"""Import the complete independent item reviews, preserving existing drafts.

Review TSVs retain full prose/names; insertion catalogs contain measured display
text. Source metadata is validated against the original before and after import.
Existing text is accepted only if identical, never silently overwritten.
"""

import csv
import json

from tools.build_first_label import ORIGINAL_ROM, ROOT
from tools import build_items, build_item_contexts
from tools.build_enemies import measure, wrap
from tools.translation_pipeline import FontZero, atomic_write, check, load_json


def reviews(name):
    path = ROOT / f"translations/{name}-review.tsv"
    rows = list(csv.DictReader(path.open(), delimiter="\t"))
    result = {int(r["row"]): r["english"] for r in rows}
    check(len(result) == len(rows), f"Duplicate review row: {name}")
    return result


def prepare():
    original = ORIGINAL_ROM.read_bytes()
    font = FontZero(original)
    items, contexts = load_json(build_items.CATALOG), load_json(build_item_contexts.CATALOG)
    build_items.validate_catalog(original, items)
    build_item_contexts.validate_catalog(original, contexts)
    names, descriptions = reviews("item-name"), reviews("item-description")
    unknown, effects = reviews("unidentified-name"), reviews("synthesis-effect")
    overrides = load_json(ROOT / "translations/item-display-overrides.json")["entries"]
    # Resolve synthesis headings by exact Japanese identity, not an effect match.
    japanese_names = {e["japanese"]: names[e["item_indices"][0]] for e in items["entries"] if e["family"] == "name"}
    check(len(names) == 369 and len(unknown) == 246, "Name review coverage changed")
    for catalog, builder in ((items, build_items), (contexts, build_item_contexts)):
        for entry in catalog["entries"]:
            row = entry.get("item_indices", entry.get("rows"))[0]
            family = entry["family"]
            if family == "name":
                text = names[row]
            elif family == "unidentified":
                text = unknown[row]
            elif entry["english"] is not None:
                # Earlier prose drafts have intentional line breaks and review notes.
                builder.encode_english(entry, font)
                continue
            elif family == "description":
                if row in descriptions:
                    text = descriptions[row]
                else:
                    source = entry["japanese"].split("<CR>", 1)[-1].removesuffix("<CR>")
                    simple = {"装備すると攻撃力が上がるぞ。": "Raises attack power while equipped.",
                              "装備すると防御力が上がるぞ。": "Raises defence while equipped."}
                    check(source in simple, f"Untranslated description: {row}")
                    text = simple[source]
                text = wrap(text, font, 192)
            else:
                check(family == "synthesis", "Unknown item family")
                if entry["layout"] == "synthesis_plain":
                    check(entry["japanese"] == "なし<CR>", "Unrecognized synthesis placeholder")
                    text = "None"
                else:
                    source_heading = entry["japanese"].split("<CR>", 1)[0]
                    jp = source_heading.split(" ", 1)[0]
                    check(jp in japanese_names, f"Unmatched synthesis heading {row}: {jp}")
                    heading = japanese_names[jp] + " synthesis"
                    check(measure(heading, font) <= 192, f"Synthesis heading too wide: {row}")
                    text = heading + "\n" + wrap(effects[row], font, 192)
            if entry["id"] in overrides:
                override = overrides[entry["id"]]
                check(text == override["canonical"] and measure(text, font) == override["canonical_width"], "Stale display override")
                text = override["display"]
            check(entry["english"] in (None, text), f"Existing English differs: {entry['id']}")
            if entry["english"] is None:
                entry["english"] = text
                entry["notes"] = "Combined milestone: independently translated from this Japanese source; review TSV retains full prose/name. See glossary for official versus project terminology."
                if entry["id"] in overrides:
                    entry["notes"] += " Short display form measured and recorded in item-display-overrides.json."
            builder.encode_english(entry, font)
        builder.validate_catalog(original, catalog)
    # Publish only after both complete catalogs pass every source and layout check.
    for path, catalog in ((build_items.CATALOG, items), (build_item_contexts.CATALOG, contexts)):
        atomic_write(path, (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({"items": len(items["entries"]), "contexts": len(contexts["entries"]), "complete": True}))


if __name__ == "__main__":
    prepare()
