"""Link already-authored code-owned display text to the master inventory."""
import json
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, rebuild
from tools.translation_pipeline import load_json, atomic_write, check

ROM = ROOT/'build/completion/frontend/torneko3-frontend-completion-english.gba'
CATALOG = ROOT/'translations/code-owned-text.json'
SPECS = (
    (0xC3D910, 0x6CD18, 'interface.puzzle-format', '031225732023256400', 'docs/DUNGEON_INTERFACE.md'),
    (0xC3E3E4, 0x732C8, 'enemy.layout.ally_species', '4d6178204850202464300308405b246d305d00', 'docs/ENEMIES_AND_ITEMS.md'),
    (0xC46730, 0x7BED4, 'name.hint-7bed4', '423a20457261736500', 'docs/NAME_ENTRY.md'),
    (0xC46738, 0x7BED0, 'name.hint-7bed0', '423a2043616e63656c00', 'docs/NAME_ENTRY.md'),
    (0xC46740, 0x7BEEC, 'name.hint-7beec', '413a20456e74657220204c3a20436173652020523a20446f6e6500', 'docs/NAME_ENTRY.md'),
    (0xC784EC, 0x85950, 'name.confirmation', '5573652022246930220a61732074686520416476656e74757265204c6f67206e616d653f00', 'docs/NAME_ENTRY.md'),
)


def reconcile():
    original = ORIGINAL_ROM.read_bytes(); data = ROM.read_bytes(); codec = GameTextCodec(original)
    master = {int(e['offset'], 0): e for e in load_json(ROOT/'translations/master.json')['entries']}
    report = load_json(ROM.parent/'english-build.json'); ledger = report['ledger']
    check(report['rom_sha256'] == digest(data) and report['source_sha256'] == digest(original), 'Code-text ROM/ledger mismatch')
    patches = {p['offset']: p for p in ledger['patches']}; allocations = {a['id']: a for a in ledger['allocations']}; entries = []
    for at, word, allocation, expected_hex, evidence in SPECS:
        m = master[at]; p = patches[word]; a = allocations[allocation]; raw = bytes.fromhex(expected_hex)
        check(bytes.fromhex(p['before']) == (at+0x08000000).to_bytes(4, 'little'), 'Code-text original owner differs')
        check(bytes.fromhex(p['after']) == (a['offset']+0x08000000).to_bytes(4, 'little') == data[word:word+4], 'Code-text relocated pointer differs')
        check(a['bytes'] == len(raw) and data[a['offset']:a['offset']+len(raw)] == raw and a['sha256'] == digest(raw), 'Code-text authored payload differs')
        s = codec.parse(data, a['offset']); check(rebuild(s['tokens']) == raw, 'Code-text payload reconstruction differs')
        src = bytes.fromhex(m['source_hex']); check(original[at:at+len(src)] == src == data[at:at+len(src)], 'Code-text source changed')
        check((ROOT/evidence).is_file(), 'Code-text evidence missing')
        entries.append({'id': f'code-text.{at:08x}', 'master_id': m['id'], 'offset': m['offset'], 'source_hex': m['source_hex'],
            'japanese': m['japanese'], 'english': s['display'], 'display': None,
            'notes': 'Existing independently authored code-owned display, now linked to the inventory. This report makes no ROM changes and does not claim additional runtime coverage.',
            'code_owner': p['owner'], 'patch_id': p['id'], 'pointer_word': hex(word), 'allocation_id': allocation,
            'replacement_hex': raw.hex(), 'prior_native_evidence': evidence,
            'other_source_reference_words': [w for w in m['pointer_candidates'] if int(w, 0) != word]})
    document = {'schema': 1, 'base_sha256': digest(original), 'authority': 'Existing code-owned strings; informational overlay only, never a second insertion owner',
        'verified_combined_rom': str(ROM.relative_to(ROOT)), 'verified_combined_rom_sha256': digest(data), 'entries': entries}
    if CATALOG.exists():
        previous = load_json(CATALOG)
        check(previous == document, 'Refusing to overwrite an earlier code-text reconciliation with different evidence')
    atomic_write(CATALOG, (json.dumps(document, ensure_ascii=False, indent=2)+'\n').encode())
    atomic_write(ROOT/'build/completion/code-text-reconciliation.json', (json.dumps({'status': 'existing_code_text_reconciled',
        'sources': len(entries), 'new_rom_writes': 0, 'catalog_sha256': digest(CATALOG.read_bytes()), 'rom_sha256': digest(data),
        'scope': 'Six existing direct pointer/allocated-string replacements now count as authored inventory sources. Compact character maps/default-name decoding and indirect keyboard replacements remain separately classified.'}, indent=2)+'\n').encode())
    print(len(entries), 'existing code-owned sources reconciled; no ROM writes', flush=True)


if __name__ == '__main__':
    reconcile()
