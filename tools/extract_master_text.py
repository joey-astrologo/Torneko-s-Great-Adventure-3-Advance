"""Extract a broad, lossless Japanese source catalog without authorizing patches."""

import argparse
from collections import Counter, defaultdict, deque
import csv
import io
import json
from pathlib import Path
import struct

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.game_text import DecodeError, GameTextCodec, rebuild, token_boundaries
from tools.translation_pipeline import ANCHORS, CATALOG, atomic_write, check, load_json

MASTER = ROOT / "translations/master.json"
OUTPUT = ROOT / "build/text-extraction"

# Coarse banks established by the source inventory and the tables below. These
# contain non-text too: they limit promotion, not the whole-ROM discovery scan.
# Readable hits outside them remain in the review queue instead of being sold
# as script (graphics can coincidentally decode into long runs of kanji).
TEXT_BANKS = [(0x97000, 0xF0000), (0x18F000, 0x1C0000), (0x86E000, 0x874000),
              (0x910000, 0xC50000), (0xC78000, 0xC80000),
              (0xCAF000, 0xCB1000), (0xCE0000, 0xCF0000)]

# Structural evidence only. Counts/strides are pinned against the JP original.
# Field numbers retain the physical layout, including null and repeated slots.
TABLES = [
    ("item_names", 0x18F16C, 370, 4, [0], False),
    ("unidentified_item_names", 0x190808, 246, 8, [4], False),
    ("monster_names", 0x192568, 200, 4, [0], False),
    ("ally_dialogue", 0x1A60B0, 200, 80, list(range(0, 80, 4)), True),
    ("ally_nicknames", 0x1A9F30, 200, 4, [0], False),
    ("monster_traits", 0x1ACB74, 200, 4, [0], False),
    ("item_descriptions", 0x1B3498, 370, 4, [0], False),
    ("synthesis_descriptions", 0x1B3A60, 100, 4, [0], False),
    ("dungeon_names", 0x1B3F60, 64, 4, [0], False),
    ("trap_names", 0x1B421C, 23, 4, [0], False),
    ("object_messages", 0x86F4D8, 21, 4, [0], False),
    ("name_filter", 0xC45DE4, 165, 4, [0], False),
]


def hx(value):
    return f"0x{value:08X}"


def pointer_references(data):
    refs = defaultdict(list)
    for index, (value,) in enumerate(struct.iter_unpack("<I", data)):
        if 0x08000000 <= value < 0x08000000 + len(data):
            refs[value - 0x08000000].append(index * 4)
    return refs


def strong_text(parsed):
    visible = "".join(t["text"] for t in parsed["tokens"] if t["kind"] == "text")
    letters = sum(c.isalnum() for c in visible)
    return parsed["japanese_characters"] >= 2 and parsed["japanese_characters"] >= letters * 0.5


def region_category(offset):
    if 0x1B3BF0 <= offset < 0x1C0000:
        return "dungeon_messages_and_ui_candidate"
    if 0x910000 <= offset < 0xC40000:
        return "event_dialogue_candidate"
    if 0x97000 <= offset < 0xF0000 or 0x86E000 <= offset < 0x874000:
        return "messages_and_ui_candidate"
    if 0xC40000 <= offset < 0xC80000:
        return "menus_and_help_candidate"
    if 0xCAF000 <= offset < 0xCB1000 or 0xCE0000 <= offset < 0xCF0000:
        return "debug_and_auxiliary_candidate"
    return "unclassified"


def collapse_overlaps(parsed, references):
    """Keep whole strings; retain suffix references with byte-boundary evidence."""
    roots, aliases = [], defaultdict(list)
    for text in sorted(parsed, key=lambda t: t["offset"]):
        parent = roots[-1] if roots and text["offset"] < roots[-1]["end"] else None
        if parent:
            check(text["end"] <= parent["end"], "Overlapping parses disagree on terminator")
            delta = text["offset"] - parent["offset"]
            boundary = delta in token_boundaries(parent["tokens"])
            aliases[parent["offset"]].append({"target": hx(text["offset"]), "byte_delta": delta,
                "boundary": "token_or_character" if boundary else "inside_character_or_control",
                "pointer_candidates": [hx(p) for p in references.get(text["offset"], [])]})
        else:
            roots.append(text)
    return roots, aliases


def merge_drafts(fresh, previous):
    """Only English and notes are editable. Never silently drop an older entry."""
    if previous is None:
        return fresh
    check(previous["schema"] == fresh["schema"] and previous["base_sha256"] == fresh["base_sha256"],
          "Existing master uses another schema or ROM")
    old = {e["id"]: e for e in previous["entries"]}
    check(len(old) == len(previous["entries"]), "Duplicate master ID")
    new = {e["id"]: e for e in fresh["entries"]}
    check(old.keys() <= new.keys(), "Existing master entries would disappear; review extraction changes first")
    for ident, entry in old.items():
        check(entry["source_hex"] == new[ident]["source_hex"], f"Source bytes changed: {ident}")
        english, notes = entry.get("english"), entry.get("notes", "")
        check(english is None or isinstance(english, str), f"English must be text or null: {ident}")
        check(isinstance(notes, str), f"Notes must be text: {ident}")
        new[ident]["english"], new[ident]["notes"] = english, notes
    return fresh


def verify_roundtrip(original, entries):
    reconstructed, previous_end = bytearray(original), 0
    for entry in sorted(entries, key=lambda e: int(e["offset"], 0)):
        start = int(entry["offset"], 0)
        raw = rebuild(entry["source_tokens"])
        check(raw.hex() == entry["source_hex"], f"Token reconstruction mismatch: {entry['id']}")
        check(start >= previous_end, "Master has overlapping source spans")
        check(raw == original[start:start + len(raw)], f"Source mismatch: {entry['id']}")
        reconstructed[start:start + len(raw)] = raw
        previous_end = start + len(raw)
    check(reconstructed == original, "Japanese round trip changed the ROM")
    return digest(reconstructed)


def collect(data, anchors, curated):
    codec, refs = GameTextCodec(data), pointer_references(data)
    cache, failures = {}, {}

    def parse(at):
        if at not in cache and at not in failures:
            try:
                cache[at] = codec.parse(data, at)
            except DecodeError as exc:
                failures[at] = {"failure_offset": hx(exc.offset), "reason": exc.reason}
        return cache.get(at)

    memberships, table_reports, included, evidence = defaultdict(list), [], set(), defaultdict(set)
    for name, start, count, stride, fields, nullable in TABLES:
        records, targets, nonnull = [], set(), 0
        for row in range(count):
            for field in fields:
                word = start + row * stride + field
                pointer = struct.unpack_from("<I", data, word)[0]
                record = {"row": row, "field_offset": field, "pointer_offset": hx(word), "target": None}
                if pointer or not nullable:
                    target = pointer - 0x08000000
                    parsed = parse(target)
                    check(parsed is not None, f"Table {name} row {row}, field {field}: cannot decode {hx(target)}")
                    record["target"] = hx(target)
                    membership = {"table": name, "row": row, "field_offset": field, "pointer_offset": hx(word)}
                    memberships[target].append(membership)
                    targets.add(target)
                    included.add(target)
                    evidence[target].add("structured_table")
                    nonnull += 1
                records.append(record)
        table_reports.append({"id": name, "offset": hx(start), "rows": count, "stride": stride,
                              "pointer_fields": fields, "nonnull_slots": nonnull, "unique_targets": len(targets),
                              "evidence": "static structure; runtime callers and relocation not yet validated",
                              "records": records})

    # Computed 12-byte records have only three references to their shared base;
    # the absolute-pointer scan cannot discover the remaining action labels.
    # Their full table is documented by the native readers in MEMORY_MAP.md.
    for row in range(41):
        at = 0x1B4281 + row * 12
        text = parse(at)
        check(text is not None and text["end"] <= at + 12 and
              data[at:at + 3] == b"\x03\x05\x07", "Fixed action record changed")
        included.add(at)
        evidence[at].add("fixed_action_record_12_bytes")
    for at in (0x1B4278, 0x1B453E, 0x1B4548):
        check(parse(at) is not None, "Interface placeholder/protagonist source changed")
        included.add(at)
        evidence[at].add("interface_computed_reader")

    # Main command variants and stair choices use fixed records too; their
    # only base pointers cannot seed every source. Preserve exact padding.
    for base, count, stride in ((0x1B3CAB, 4, 30), (0x1B40D6, 3, 32)):
        for row in range(count):
            at = base + row * stride
            text = parse(at)
            check(text is not None and text['end'] <= at + stride and
                  data[text['end']:at + stride] == bytes(at + stride - text['end']),
                  'Computed command/choice record changed')
            included.add(at)
            evidence[at].add(f'gameplay_fixed_record_{stride}_bytes')

    curated_by_id = {e["id"]: e for e in curated["entries"]}
    anchor_map = {}
    for anchor in anchors["entries"]:
        at = int(anchor["offset"], 0)
        text = parse(at)
        check(text is not None and text["raw_hex"] == curated_by_id[anchor["id"]]["source_hex"],
              f"Curated source differs: {anchor['id']}")
        for word in anchor["pointers"]:
            check(int(word, 0) in refs[at], f"Curated pointer differs: {anchor['id']}")
        included.add(at)
        evidence[at].add("curated_runtime_verified")
        anchor_map[at] = anchor

    # Pointer seeds are filtered for plausible text and source starts. Small
    # labels can enter through tables and neighboring string pools below.
    for at in refs:
        text = parse(at)
        if (text and strong_text(text) and (at % 4 == 0 or data[at - 1] == 0)
                and 0x97000 <= at < 0xCB1000):
            included.add(at)
            evidence[at].add("static_pointer_candidate")

    # Search the whole ROM for independently readable aligned pool starts.
    # Unreferenced long text is kept as a candidate, never an owned pointer.
    for at in range(4, len(data), 4):
        if data[at - 1] or data[at] == 0:
            continue
        text = parse(at)
        if text and strong_text(text) and text["japanese_characters"] >= 8:
            included.add(at)
            evidence[at].add("readable_unreferenced_scan" if not refs.get(at) else "aligned_string_scan")

    # Adjacent strings have either no padding or up to three zero bytes for
    # four-byte alignment. This recovers ASCII placeholders and short labels.
    pending = deque(sorted(included))
    visited = set()
    while pending:
        at = pending.popleft()
        if at in visited:
            continue
        visited.add(at)
        text = parse(at)
        end = text["end"]
        following = [end, (end + 3) & ~3]
        for next_at in dict.fromkeys(following):
            if next_at >= len(data) or any(data[end:next_at]):
                continue
            other = parse(next_at)
            if (other and other["display"] and any(c.isalnum() for c in other["display"])
                    and next_at not in included):
                included.add(next_at)
                evidence[next_at].add("adjacent_string_candidate")
                pending.append(next_at)
        # Recover an immediately preceding aligned string when it ends at this
        # start (plus padding). Do not hunt arbitrary byte starts in instructions.
        for previous in range(max(4, (at - 1024) & ~3), at, 4):
            if data[previous - 1] != 0 or data[previous] == 0:
                continue
            other = parse(previous)
            if (other and other["display"] and 0 <= at - other["end"] <= 3
                    and not any(data[other["end"]:at]) and previous not in included):
                included.add(previous)
                evidence[previous].add("adjacent_string_candidate")
                pending.append(previous)

    # Consider all parsed pointer targets inside selected spans so that an
    # accidental mid-character match cannot become an independent source.
    outside_banks = {at for at in included if not any(start <= at < end for start, end in TEXT_BANKS)}
    unresolved = {at for at in included if any(t.get("grammar") == "unresolved" for t in cache[at]["tokens"])
                  and at not in memberships and at not in anchor_map}
    deferred = outside_banks | unresolved
    selected = [cache[at] for at in included - deferred]
    roots, aliases = collapse_overlaps(selected, refs)
    for root in roots:
        for at in range(root["offset"] + 1, root["end"]):
            if at in refs and not any(int(a["target"], 0) == at for a in aliases[root["offset"]]):
                delta = at - root["offset"]
                aliases[root["offset"]].append({"target": hx(at), "byte_delta": delta,
                    "boundary": "token_or_character" if delta in token_boundaries(root["tokens"]) else "inside_character_or_control",
                    "pointer_candidates": [hx(p) for p in refs[at]]})

    entries = []
    for text in roots:
        at = text["offset"]
        anchor = anchor_map.get(at)
        ident = f"jp_{at:08x}"
        flags = []
        if text["indexed_characters"]:
            flags.append("indexed_glyphs_viewed_with_font_0")
        if any(t.get("grammar") == "unresolved" for t in text["tokens"]):
            flags.append("unresolved_dollar_command")
        if "`" in text["display"]:
            flags.append("reader_specific_backtick")
        if any("argument_template_candidate" in t for t in text["tokens"]):
            flags.append("printf_may_supply_control_argument")
        if any(t["kind"] == "opaque_control" for t in text["tokens"]):
            flags.append("reader_specific_03_prefix")
        if not refs.get(at):
            flags.append("no_absolute_pointer_found")
        if not strong_text(text) and not memberships.get(at) and not anchor:
            flags.append("short_or_non_japanese_pool_candidate")
        categories = (["action_labels"] if "fixed_action_record_12_bytes" in evidence[at]
                      else sorted({m["table"] for m in memberships.get(at, [])})) or [region_category(at)]
        approved = anchor["pointers"] if anchor else []
        entry = {"id": ident, "offset": hx(at), "address": hx(at + 0x08000000),
                 "bytes_including_nul": text["end"] - at, "japanese": text["display"],
                 "english": None, "notes": "", "categories": categories,
                 "evidence": sorted(evidence[at]), "flags": flags,
                 "source_hex": text["raw_hex"], "source_tokens": text["tokens"],
                 "pointer_candidates": [hx(p) for p in refs.get(at, [])],
                 "interior_references": sorted(aliases[at], key=lambda a: a["byte_delta"]),
                 "table_memberships": memberships.get(at, []),
                 "curated_id": anchor["id"] if anchor else None,
                 "verified_pointer_owners": approved}
        if anchor:
            # The curated file remains the single editable/buildable English
            # authority. Do not create a second copy that can silently diverge.
            entry["context"] = anchor["context"]
        entries.append(entry)
    check(set(anchor_map) <= {int(e["offset"], 0) for e in entries}, "An overlap swallowed a curated entry")
    check(sum(len(e["table_memberships"]) for e in entries) == sum(t["nonnull_slots"] for t in table_reports),
          "An overlap swallowed a table target; preserve its membership before continuing")

    covered = set()
    for text in roots:
        covered.update(range(text["offset"], text["end"]))
    review = []
    for at in sorted(deferred - refs.keys()):
        review.append({"offset": hx(at), "pointer_candidates": [],
                       "reason": "outside mapped text banks or unresolved source grammar",
                       "preview": cache[at]["display"][:160], "raw_hex": cache[at]["raw_hex"]})
    for at, pointers in sorted(refs.items()):
        if at in covered:
            continue
        text = cache.get(at)
        # Keep text-like rejected hits, not the millions of arbitrary data words.
        if text and text["display"] and (text["japanese_characters"] or len(text["display"]) >= 3):
            review.append({"offset": hx(at), "pointer_candidates": [hx(p) for p in pointers],
                           "reason": "outside selected text pools / weak text or source-boundary evidence",
                           "preview": text["display"][:160], "raw_hex": text["raw_hex"]})
        elif at in failures and (0x18F734 <= at < 0x1B4300 or 0x910000 <= at < 0xC80000):
            item = {"offset": hx(at), "pointer_candidates": [hx(p) for p in pointers], **failures[at],
                    "raw_prefix_hex": data[at:at + 48].hex()}
            failure_at = int(failures[at]["failure_offset"], 0)
            if failure_at - at >= 8:
                try:
                    prefix = codec.parse(data[at:failure_at] + b"\0", 0)
                    if prefix["japanese_characters"] >= 4:
                        item["decoded_prefix_before_failure"] = prefix["display"]
                except DecodeError:
                    pass
            review.append(item)
    return entries, table_reports, review, len(refs)


def make_report(data, entries, tables, review, reference_targets):
    total = sum(e["bytes_including_nul"] for e in entries)
    categories = Counter(c for e in entries for c in e["categories"])
    controls = Counter(t["raw_hex"] for e in entries for t in e["source_tokens"] if t["kind"] == "binary_control")
    dollars = Counter(t["text"] for e in entries for t in e["source_tokens"] if t["kind"] == "dollar_command")
    encoded = Counter(t.get("encoding") for e in entries for t in e["source_tokens"] if t["kind"] == "text")
    return {"source_sha256": digest(data), "entries": len(entries), "source_byte_union_including_nuls": total,
            "unique_source_payloads": len({e["source_hex"] for e in entries}),
            "curated_entries": sum(e["curated_id"] is not None for e in entries),
            "font_index_entries": sum("indexed_glyphs_viewed_with_font_0" in e["flags"] for e in entries),
            "unreferenced_entries": sum(not e["pointer_candidates"] for e in entries),
            "interior_reference_targets": sum(len(e["interior_references"]) for e in entries),
            "invalid_interior_targets": sum(a["boundary"] == "inside_character_or_control" for e in entries for a in e["interior_references"]),
            "review_queue_entries": len(review), "aligned_absolute_reference_targets_scanned": reference_targets,
            "review_failure_reasons": dict(Counter(e["reason"] for e in review)),
            "review_entries_with_readable_prefix": sum("decoded_prefix_before_failure" in e for e in review),
            "categories": dict(categories), "text_token_encodings": dict(encoded),
            "binary_controls": dict(controls), "dollar_commands": dict(dollars),
            "tables": [{k: v for k, v in t.items() if k != "records"} for t in tables],
            "text_banks": [{"start": hx(start), "end_exclusive": hx(end)} for start, end in TEXT_BANKS],
            "roundtrip_sha256": verify_roundtrip(data, entries),
            "storage_scenarios": [{"source_byte_multiplier": factor,
                "payload_plus_worst_case_alignment": total * factor + len(entries) * 3,
                "appended_16_mib_remaining": 0x1000000 - total * factor - len(entries) * 3}
                for factor in (1, 2, 4)],
            "limitations": [
                "This is a broad source catalog, not proof that every player-visible string has been found.",
                "Static candidates, table roles, and active fonts need runtime context; unused/debug text can be included.",
                "Glyph indexes and single-byte characters are viewed through original font 0; other fonts may differ.",
                "Only aligned primary-view absolute pointer words are indexed; relative/computed/unaligned/mirrored references can be missed.",
                "Unknown controls, other encodings, compressed text and text baked into graphics remain outside this decoder.",
                "Unknown dollar commands are opaque lexical tokens; printf matches do not establish argument semantics.",
                "Only curated verified_pointer_owners are authorized by the existing builder; this tool does not patch a ROM.",
                "Storage scenarios are assumptions for these extracted sources, exclude other assets/code, and do not establish RAM or line-width limits."]}


def extract(rom=ORIGINAL_ROM, master=MASTER, output=OUTPUT):
    rom, master, output = Path(rom).resolve(), Path(master).resolve(), Path(output).resolve()
    check(master.suffix == ".json", "Master output must be JSON")
    family_paths = [ROOT / "translations" / name for name in ("items.json", "item-contexts.json", "enemies.json", "dungeon-interface.json", "core-gameplay.json", "gameplay-help.json", "ally-services.json", "tutorial-gameplay.json", "ally-dialogue.json", "companion-dialogue.json", "ally-nicknames.json", "opening-story.json", "first-village.json", "early-journey.json", "story-completion.json", "story-special.json", "shared-story.json", "arena-services.json", "adventure-history.json", "adventure-results.json", "church-services.json", "frontend-completion.json", "code-owned-text.json", "item-display.json", "dungeon-events.json", "battle-completion.json", "merchants.json", "keyboard-completion.json", "inscriptions.json", "world-completion.json", "system-labels.json", "encounter-ui.json", "arena-final.json", "arena-graphics.json", "remaining-display.json", "text-polish.json")]
    protected = {rom, ANCHORS.resolve(), CATALOG.resolve(), ORIGINAL_ROM.resolve(), *(p.resolve() for p in family_paths)}
    check(master not in protected, "Master output would overwrite a source input")
    data = rom.read_bytes()
    check(digest(data) == load_manifest()["base_sha256"], "Broad extraction requires the pinned Japanese original")
    anchors, curated = load_json(ANCHORS), load_json(CATALOG)
    check(anchors["base_sha256"] == curated["base_sha256"] == digest(data), "Catalog/anchor source hash mismatch")
    destinations = [master, *(output / name for name in ("coverage.json", "tables.json", "review-queue.json", "master.tsv", "index.html"))]
    check(len({p.resolve() for p in destinations}) == len(destinations), "Output files overlap each other")
    check(not any(p.resolve() in protected for p in destinations), "Output overlaps a source input")
    entries, tables, review, count = collect(data, anchors, curated)
    document = {"schema": 1, "base_sha256": digest(data), "decoding_font": 0,
                "purpose": "Japanese source inventory and translation drafts; not direct input to the ROM builder",
                "english_authority": "Insertion uses translations/catalog.json, items.json, item-contexts.json, enemies.json, dungeon-interface.json, core-gameplay.json, gameplay-help.json, ally-services.json, tutorial-gameplay.json, ally-dialogue.json, companion-dialogue.json, ally-nicknames.json, opening-story.json, first-village.json, early-journey.json, story-completion.json, story-special.json, shared-story.json, arena-services.json, adventure-history.json, adventure-results.json, church-services.json, frontend-completion.json, item-display.json, dungeon-events.json, battle-completion.json, merchants.json, keyboard-completion.json, inscriptions.json, world-completion.json, system-labels.json, encounter-ui.json, arena-final.json, arena-graphics.json, remaining-display.json and text-polish.json. Later text-polish entries explicitly supersede earlier wording without shifting prior allocations. A catalog English draft does not by itself establish native or full-game acceptance; see docs/COMPLETION.md for current evidence. code-owned-text.json links already-authored code assets to inventory entries and does not grant insertion ownership. Master english/notes retain independent full drafts; the browser overlays insertion catalogs without overwriting them.",
                "entries": entries}
    document = merge_drafts(document, load_json(master) if master.exists() else None)
    report = make_report(data, document["entries"], tables, review, count)
    tsv = io.StringIO(newline="")
    writer = csv.writer(tsv, delimiter="\t", lineterminator="\n")
    writer.writerow(["id", "offset", "categories", "bytes", "curated_id", "japanese", "english", "flags"])
    for e in document["entries"]:
        writer.writerow([e["id"], e["offset"], ",".join(e["categories"]), e["bytes_including_nul"], e["curated_id"],
                         e["japanese"].replace("\n", "<LF>"), e["english"], ",".join(e["flags"])])
    artifacts = {master: document, output / "coverage.json": report,
                 output / "tables.json": tables, output / "review-queue.json": review}
    check(not any(p.resolve() in protected for p in artifacts), "Output overlaps a source input")
    for path, contents in artifacts.items():
        atomic_write(path, (json.dumps(contents, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    atomic_write(output / "master.tsv", tsv.getvalue().encode("utf-8"))
    english = {e["id"]: e["english"] for e in curated["entries"]}
    browser_entries = [{k: v for k, v in e.items() if k != "source_tokens"} for e in document["entries"]]
    for entry in browser_entries:
        entry["curated_english"] = english.get(entry["curated_id"])
        entry["insertion_sources"] = []
    browser_by_id = {e["id"]: e for e in browser_entries}
    browser_offsets = {int(e["offset"], 0) for e in browser_entries}
    for path in family_paths:
        if not path.exists():
            continue
        family = load_json(path)
        check(family["base_sha256"] == digest(data), "Insertion overlay has a different source ROM")
        for entry in family["entries"]:
            if not entry.get("master_id"):
                at = int(entry["offset"], 0)
                raw = bytes.fromhex(entry["source_hex"])
                check(at not in browser_offsets and data[at:at + len(raw)] == raw,
                      "Outside-inventory overlay is not a distinct checked source")
                continue
            target = browser_by_id[entry["master_id"]]
            check(target["source_hex"] == entry["source_hex"], "Insertion overlay source bytes differ")
            target["insertion_sources"].append({"catalog": path.name, "id": entry["id"],
                                               "english": entry.get("display") or entry["english"]})
    payload = json.dumps({"entries": browser_entries, "report": report}, ensure_ascii=False,
                         separators=(",", ":")).replace("<", "\\u003c")
    html = (ROOT / "tools/text_catalog.html").read_text(encoding="utf-8").replace("__CATALOG_DATA__", payload)
    atomic_write(output / "index.html", html.encode("utf-8"))
    print(json.dumps({k: report[k] for k in ("entries", "source_byte_union_including_nuls", "font_index_entries",
        "curated_entries", "unreferenced_entries", "invalid_interior_targets", "review_queue_entries", "roundtrip_sha256", "storage_scenarios")}, indent=2))
    return document, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--master", type=Path, default=MASTER)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    extract(args.rom, args.master, args.output)
