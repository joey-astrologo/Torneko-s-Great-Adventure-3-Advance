"""One allocation, patch and reservation ledger for a complete ROM image."""

from copy import deepcopy

from tools.build_first_label import digest, load_manifest

ROM_LIMIT = 0x02000000


def check(condition, message):
    if not condition:
        raise ValueError(message)


def overlaps(start, end, other_start, other_end):
    return start < other_end and other_start < end


class AppendAllocator:
    def __init__(self, start=0x01000000, limit=ROM_LIMIT):
        check(0 <= start <= limit <= ROM_LIMIT, "Invalid allocation region")
        self.start, self.cursor, self.limit = start, start, limit
        self.allocations, self.ids = [], set()

    def allocate(self, ident, payload, alignment=4):
        check(ident not in self.ids, f"Duplicate allocation ID: {ident}")
        check(payload, "Empty allocation")
        check(alignment > 0 and alignment & (alignment - 1) == 0, "Alignment must be a power of two")
        at = (self.cursor + alignment - 1) & -alignment
        check(at + len(payload) <= self.limit, "Appended ROM allocation exceeds capacity")
        self.allocations.append({"id": ident, "offset": at, "address": f"0x{0x08000000 + at:08X}",
                                 "bytes": len(payload), "padding_before": at - self.cursor,
                                 "sha256": digest(payload)})
        self.ids.add(ident)
        self.cursor = at + len(payload)
        return at


class RomBuild:
    def __init__(self, original):
        check(len(original) == 0x01000000 and digest(original) == load_manifest()["base_sha256"],
              "Build requires the pinned 16 MiB Japanese original")
        self.original = bytes(original)
        self.data = bytearray(original)
        self.allocator = AppendAllocator(len(original))
        self.patches, self.protected_sources, self.memory_reservations = [], [], []

    def protect_source(self, ident, start, end, owner):
        check(0 <= start < end <= len(self.original), "Invalid protected source range")
        for patch in self.patches:
            check(not overlaps(start, end, patch["offset"], patch["offset"] + len(bytes.fromhex(patch["before"]))),
                  f"Protected source overlaps patch {patch['id']}: {ident}")
        # Multiple readers may intentionally protect the same immutable bytes.
        record = {"id": ident, "start": start, "end_exclusive": end, "owner": owner}
        if record not in self.protected_sources:
            self.protected_sources.append(record)

    def reserve_memory(self, ident, start, end, owner, space="ram", purpose=""):
        check(space == "ram" and 0x02000000 <= start < end <= 0x02040000,
              "This build currently supports EWRAM reservations only")
        for reservation in self.memory_reservations:
            check(ident != reservation["id"], f"Duplicate reservation ID: {ident}")
            check(not overlaps(start, end, reservation["start"], reservation["end_exclusive"]),
                  f"RAM reservation overlaps {reservation['id']}: {ident}")
        self.memory_reservations.append({"id": ident, "start": start, "end_exclusive": end,
                                         "owner": owner, "space": space, "purpose": purpose})

    def allocate(self, ident, payload, owner, alignment=4):
        at = self.allocator.allocate(ident, payload, alignment)
        self.allocator.allocations[-1]["owner"] = owner
        if len(self.data) == len(self.original):
            self.data.extend(b"\xff" * (ROM_LIMIT - len(self.data)))
        self.data[at:at + len(payload)] = payload
        return at

    def patch(self, ident, offset, expected, replacement, owner, reason=""):
        expected, replacement = bytes(expected), bytes(replacement)
        end = offset + len(expected)
        check(expected and len(expected) == len(replacement), "Patch must preserve original region size")
        check(0 <= offset < end <= len(self.original), "Patch is outside the original ROM")
        for old in self.patches:
            check(not overlaps(offset, end, old["offset"], old["offset"] + len(bytes.fromhex(old["before"]))),
                  f"Patch collision: {owner}/{ident} overlaps {old['owner']}/{old['id']}")
        for source in self.protected_sources:
            check(not overlaps(offset, end, source["start"], source["end_exclusive"]),
                  f"Patch overlaps protected source: {source['id']}")
        check(self.original[offset:end] == expected and self.data[offset:end] == expected,
              f"Patch precondition failed at {offset:08X}: {reason}")
        record = {"id": ident, "offset": offset, "before": expected.hex(), "after": replacement.hex(),
                  "owner": owner, "reason": reason}
        self.data[offset:end] = replacement
        self.patches.append(record)
        return record

    def supersede_patch(self, ident, previous_id, previous_owner, expected,
                        replacement, owner, reason):
        """Replace one exact owned patch, retaining its complete audit history.

        This is deliberately separate from patch(): partial overlaps, changed
        source bytes, stale targets and implicit ownership remain errors.
        """
        matches = [(i, p) for i, p in enumerate(self.patches)
                   if p["id"] == previous_id and p["owner"] == previous_owner]
        check(len(matches) == 1, "Supersession requires one exact previous owner/ID")
        check(ident not in {p["id"] for p in self.patches}, "Duplicate patch ID")
        check(owner and reason, "Supersession requires owner and reason")
        index, old = matches[0]
        expected, replacement = bytes(expected), bytes(replacement)
        start = old["offset"]
        before = bytes.fromhex(old["before"])
        check(expected and len(expected) == len(replacement) == len(before),
              "Supersession must replace the whole patch at its original size")
        end = start + len(before)
        check(bytes.fromhex(old["after"]) == expected and self.data[start:end] == expected
              and self.original[start:end] == before, "Supersession precondition failed")
        record = {"id": ident, "offset": start, "before": old["before"],
                  "after": replacement.hex(), "owner": owner, "reason": reason,
                  "supersedes": deepcopy(old)}
        self.data[start:end] = replacement
        self.patches[index] = record
        return record

    def finish(self):
        """Verify the entire image, including unused appended bytes and padding."""
        expected = bytearray(self.original)
        if self.allocator.allocations:
            expected.extend(b"\xff" * (ROM_LIMIT - len(expected)))
        cursor = self.allocator.start
        ids = set()
        for allocation in self.allocator.allocations:
            start, size = allocation["offset"], allocation["bytes"]
            end = start + size
            check(allocation["id"] not in ids, "Duplicate allocation ownership")
            ids.add(allocation["id"])
            check(cursor <= start < end <= self.allocator.limit and start - cursor == allocation["padding_before"],
                  "Allocation collision or incorrect alignment ledger")
            payload = bytes(self.data[start:end])
            check(digest(payload) == allocation["sha256"], f"Allocation changed outside ledger: {allocation['id']}")
            expected[start:end] = payload
            cursor = end
        check(cursor == self.allocator.cursor, "Allocation cursor differs from ledger")
        previous_end = 0
        for patch in sorted(self.patches, key=lambda p: p["offset"]):
            start = patch["offset"]
            before, after = bytes.fromhex(patch["before"]), bytes.fromhex(patch["after"])
            end = start + len(before)
            check(previous_end <= start < end <= len(self.original) and len(before) == len(after),
                  "Patch collision or invalid patch range")
            check(self.original[start:end] == before, "Patch source differs from original")
            expected[start:end] = after
            previous_end = end
        check(expected == self.data, "Unaccounted ROM changes outside the allocation/patch ledger")
        result = bytes(self.data)
        ledger = {"schema": 1, "source_sha256": digest(self.original), "rom_sha256": digest(result),
                  "rom_bytes": len(result), "range_convention": "start inclusive, end exclusive; ROM file offsets",
                  "allocations": deepcopy(self.allocator.allocations), "patches": deepcopy(self.patches),
                  "protected_sources": deepcopy(self.protected_sources),
                  "memory_reservations": deepcopy(self.memory_reservations),
                  "appended_used_with_padding": cursor - self.allocator.start,
                  "appended_remaining": self.allocator.limit - cursor,
                  "complete_image_matches_ledger": True}
        return result, ledger
