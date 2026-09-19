"""Read-only ROM audit; writes reports, never translations or a patched ROM.

Run: .venv/bin/python -m tools.audit_combat_lines
"""
from collections import Counter
import json
import re
import struct
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.build_prose_review import pointer_words
from tools.prose_review import effective_catalog, REVIEW, REVISIONS
from tools.translation_pipeline import FontZero, check
from tools.build_enemies import measure

FAMILIES = {
    'core-gameplay': {'message'},
    'tutorial-gameplay': {'message', 'joined_damage', 'tutorial'},
    'gameplay-help': {'message'},
    'battle-completion': {'queue', 'message'},
    'encounter-ui': {'announcement'},
}
SLOTS = re.compile(r'\$(?:[midv][0-9]|t)')
# These are menus/popups, not the 208px scrolling log.
EXCLUDED = {'gameplay.001b3c06': 'Ground popup: its own narrower window',
            'help.001b4f0c': 'Ally-order notice',
            'help.00c3e334': 'Ally-order notice',
            'help.00c3e360': 'Ally-order notice',
            'help.00c3e37c': 'Ally-order notice'}
SAMPLE = {'m0': 'Torneko', 'm1': 'Slime', 'm2': 'Slime',
          'i0': 'Medicinal herb', 'i1': 'Bread', 'i2': 'Magic shield', 'i3': 'Magic shield',
          't': 'Torneko'}


def main():
    rompath = ROOT/'build/torneko-3-english.gba'
    rom = rompath.read_bytes()
    ledgerpath = ROOT/'build/latest/english-build.json'
    ledger = json.loads(ledgerpath.read_text())
    check(digest(rom) == ledger['rom_sha256'], 'Published ROM/ledger mismatch')
    original = ORIGINAL_ROM.read_bytes()
    check(digest(original) == ledger['source_sha256'], 'Original ROM mismatch')
    font, livefont = FontZero(original), FontZero(rom)
    widths = {chr(c): max(font.glyph(chr(c))[1:]) for c in range(32,127)}
    check(all(font.glyph(c) == livefont.glyph(c) for c in widths), 'Font metrics changed')
    widest = max(widths, key=widths.get)
    patch_by_offset = {p['offset']: p for p in ledger['ledger']['patches']}
    planpath = ROOT/'build/damage-lines/allocation-plan.json'
    plan = json.loads(planpath.read_text())
    handled = {m['address']-0x08000000 for m in plan['messages']}
    # A stale plan must not be mistaken for current runtime coverage.
    formatter = next(a for a in plan['allocations'] if a['id']=='damage-lines.formatter')
    check(rom[formatter['offset']:formatter['offset']+len(bytes.fromhex(plan['code_hex']))].hex()
          == plan['code_hex'], 'Existing joining code differs')
    check(rom[0x7D8CC:0x7D8D8].hex()==plan['replacement_hex'], 'Joining hook differs')
    for m in plan['messages']:
        at=m['address']-0x08000000
        check(rom[at:at+len(bytes.fromhex(m['raw_hex']))].hex()==m['raw_hex'], 'Joining source differs')

    def dimensions(s):
        return {'pixels': measure(s, font), 'guard_pixels': sum(widths[c] for c in s),
                'bytes': len(s.encode('ascii'))}

    def fits(d):
        return d['guard_pixels'] <= 208 and d['bytes'] <= 59

    def metrics(s):
        sample = SLOTS.sub(lambda m:SAMPLE.get(m[0][1:], '6'), s)
        # Maximum ASCII width and byte length permitted by each buffer, deliberately
        # more conservative than the builders' 120px/144px nominal name budgets.
        def upper(m):
            k=m[0][1:]
            return widest*(29 if k[0]=='m' else 99 if k[0]=='i' else 7) if k[0] in 'mit' else '-2147483648'
        worst=SLOTS.sub(upper,s)
        return {'example': sample, 'example_metrics': dimensions(sample),
                'slot_capacity_upper_metrics': dimensions(worst),
                'literal_only_metrics': dimensions(SLOTS.sub('',s)),
                'minimum_nonempty_metrics': dimensions(SLOTS.sub(lambda m: '0' if m[0][1] in 'dv' else min(widths,key=widths.get),s)),
                'all_ascii_slot_values_fit':fits(dimensions(worst))}

    rows=[]; coverage=[]
    for cat,families in FAMILIES.items():
        entries=effective_catalog(cat)['entries']
        selected=[e for e in entries if e.get('family') in families]
        coverage.append({'catalog':cat,'total_entries':len(entries),'selected_entries':len(selected),
                         'families':sorted(families)})
        for e in selected:
            pointers=pointer_words(e); targets={}
            for p in pointers:
                check(p in patch_by_offset, f'Unowned pointer {e["id"]}: {p:x}')
                patch=patch_by_offset[p]
                check(rom[p:p+4].hex()==patch['after'], 'Current pointer differs from ledger')
                at=struct.unpack_from('<I',rom,p)[0]-0x08000000
                check(0<=at<len(rom),'Bad target')
                targets.setdefault(at,[]).append(f'0x{p:08X}')
            for at,owners in targets.items():
                end=rom.index(b'\0',at)
                raw=rom[at:end]
                text=raw.decode('ascii',errors='backslashreplace')
                row={'id':e['id'],'catalog':cat,'family':e['family'],
                     'japanese':e['japanese'],'target':f'0x{at:08X}',
                     'pointer_owners':owners,'raw_hex':raw.hex(), 'template':text,
                     'breaks':text.count('\n'),'segments':[]}
                outside=EXCLUDED.get(e['id'])
                if cat=='battle-completion' and e['family']=='message':outside='Paged shop/companion/recruitment dialogue'
                if cat=='tutorial-gameplay' and e['family']=='tutorial':outside='Tutorial: preserve pause and instruction structure'
                if cat=='core-gameplay' and int(e['offset'],0)>=0xC00000:outside='System/settings message'
                if outside:
                    row.update(category='outside-log',reason=outside)
                elif not row['breaks']:
                    row.update(category='no-break',reason='Already one physical template line; no LF to remove')
                elif at in handled:
                    row.update(category='already-handled',reason='Current hook conditionally joins final pair; earlier event/sentence breaks stay')
                elif any(c not in range(32,127) and c!=10 for c in raw) or '$' in SLOTS.sub('',text):
                    row.update(category='keep-controls',reason='Indexed glyph or control needs its existing rendering contract')
                elif text.startswith('!'):
                    row.update(category='continuation-review',reason='Fits may depend on earlier attacker fragment; dedicated continuation tests required')
                    row['segments']=[{'joined':text[1:].replace('\n',' '),**metrics(text[1:].replace('\n',' '))}]
                elif '"' in text:
                    row.update(category='keep-dialogue',reason='Spoken/event dialogue; preserve pacing')
                else:
                    # Preserve actual sentence boundaries. Join only layout breaks
                    # within a sentence, never merge independent event sentences.
                    groups=[];group=[];preserved=[]
                    for i,line in enumerate(text.split('\n')):
                        group.append(line)
                        if re.search(r'[.!?]$',line) or not line:
                            groups.append(group);group=[]
                            if i<row['breaks']:preserved.append(i+1)
                    if group:groups.append(group)
                    for group in groups:
                        if len(group)<2:continue
                        joined=' '.join(group)
                        m=metrics(joined)
                        decision=('always-fits-ascii' if m['all_ascii_slot_values_fit'] else
                                  'keep-too-long' if not fits(m['minimum_nonempty_metrics']) else
                                  'conditional-join')
                        row['segments'].append({'before':'\n'.join(group),'joined':joined,'decision':decision,**m})
                    row['preserved_sentence_breaks']=preserved
                    check(sum(s['before'].count('\n') for s in row['segments'])+len(preserved)==row['breaks'],
                          'Unaccounted line-break boundary: '+e['id'])
                    decisions={s['decision'] for s in row['segments']}
                    row['category']=('candidate' if decisions & {'always-fits-ascii','conditional-join'} else 'keep')
                    row['reason']=('Join candidate sentence spans only when final text fits; retain other breaks' if row['category']=='candidate' else
                                   'Even minimum nonempty substitutions exceed capacity, or breaks separate sentences')
                rows.append(row)
    counts=dict(Counter(r['category'] for r in rows))
    segments=[s for r in rows if r['category']=='candidate' for s in r['segments'] if s['decision']!='keep-too-long']
    result={'schema':1,'mode':'audit-only; no ROM or translation edits','rom':str(rompath.relative_to(ROOT)),
            'rom_sha256':digest(rom),'source_sha256':digest(original),
            'ledger_sha256':digest(ledgerpath.read_bytes()),'revisions_sha256':digest(REVISIONS.read_bytes()),
            'audit_tool_sha256':digest((ROOT/'tools/audit_combat_lines.py').read_bytes()),
            'limits':{'pixels':208,'history_payload_bytes':59},'coverage':coverage,'counts':counts,
            'candidate_sentence_spans':len(segments),
            'sample_fitting_spans':sum(fits(s['example_metrics']) for s in segments),'rows':rows}
    output=ROOT/'build/combat-line-audit';output.mkdir(parents=True,exist_ok=True)
    (output/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    def cell(s):return s.replace('|','&#124;').replace('\n',' ↵ ')
    md=['# Combat line-break audit', '', '**Audit only — awaiting approval. No game text, ROM, or build behavior changed.**','',
        f'Published ROM SHA-256: `{digest(rom)}`.', '',
        '## Recommendation', '',
        'Use measured, conditional joining for the candidate sentence spans below. Join only after the real names, item labels and numbers have been substituted, and only if the resulting ASCII text fits **208 pixels and 59 payload bytes**. Otherwise preserve the current breaks. Keep sentence/event boundaries, pauses, indexed glyphs and dialogue pacing. Do not shorten official names or rewrite prose in this pass.', '',
        f'There are **{len(segments)} candidate sentence spans in {counts.get("candidate",0)} templates**. '
        f'Of these spans, **{sum(s["all_ascii_slot_values_fit"] for s in segments)}** fit even the conservative ASCII slot-capacity bounds. '
        'The others require a runtime fit check; a short example is not a guarantee for every name.', '',
        f'**Recommended first pass: {sum(fits(s["example_metrics"]) for s in segments)} spans that fit the stated short-name fixtures**, with fallback for longer substitutions. '
        f'**Defer {sum(not fits(s["example_metrics"]) for s in segments)} marginal spans** whose example already exceeds the limit. They may fit unusually short substitutions, but are lower priority. Two critical/brutal continuation fragments are separately listed for dedicated validation.', '',
        'Examples that fit: “Slime recovered 6 HP.” (105px), “Torneko avoided the poison.” (133px), and “Torneko is no longer confused.” (147px). These are measured examples, with the same conditional fallback required for longer actors.', '',
        f'Of the **{sum(r["breaks"]>0 and r["category"]!="outside-log" for r in rows)} multiline log/feedback templates**, '
        f'{counts["candidate"]} have candidate spans, {counts["continuation-review"]} are continuation cases, '
        f'{counts["already-handled"]} already have joining, and '
        f'{sum(counts.get(k,0) for k in ("keep","keep-controls","keep-dialogue"))} should keep their current layout in this pass.', '',
        '## Scope and evidence', '',
        'This inventories every currently inserted entry in the message/queue families of the four combat/gameplay catalogs, plus tutorials and the encounter announcement to make exclusions explicit. Includes item-use, traps, status changes and dungeon feedback, not only direct attacks. Current bytes are read through every recorded pointer owner and checked against the combined build ledger; superseded translations are not used for measurements. Paged conversations, system notices, ally-order notices and the narrower Ground popup are excluded from log joining. Entity labels, item descriptions, story dialogue and menu tables are not combat log sentences. This is an audit of the known inserted inventory, not proof that no undiscovered text exists.', '',
        '| Catalog | All entries | Audited family entries |', '|---|---:|---:|']
    for c in coverage:md.append(f'| {c["catalog"]} | {c["total_entries"]} | {c["selected_entries"]} |')
    md+=['','| Classification | Templates |','|---|---:|']
    for k,v in counts.items():md.append(f'| {k} | {v} |')
    md+=['',f'Total: **{len(rows)} templates**, **{sum(r["breaks"]>0 for r in rows)} containing LF**, **{sum(r["breaks"] for r in rows)} LF boundaries (including excluded families)**.', '',
        '### How to read the measurements', '',
        '`↵` marks a current ROM line break. `$mN` is an actor/name slot, `$iN` an item/effect slot, `$dN` a number and `$t` the protagonist substitution. Example fixtures use Torneko, Slime, Medicinal herb, Bread and 6; these demonstrate space usage, not that each fixture can occur at every call site. Width uses font 0 from the ROM. The conservative joining guard sums max(advance, ink width) for each glyph, matching the existing hook; a few edge glyphs can therefore cost more than the exact rendered extent.', '',
        'The upper bounds allow 29 ASCII bytes per actor slot, 99 per item slot, seven for the protagonist and signed 32-bit numbers. These are conservative storage bounds, not claims that normal item names reach those lengths. The builders’ nominal 120px actor/144px item budgets are not sufficient evidence to delete breaks unconditionally. Non-ASCII substitutions must fall back. No battle replay or new native runtime test was performed for this audit.', '',
        '## Candidates for conditional joining', '',
        'Only the spans shown are considered for joining. Other sentence boundaries in the same template remain. “Example exceeds” means this specific fixture stays wrapped; shorter real substitutions may fit. Such entries are deferred in the recommended first pass, not a promise of a one-line result.', '',
        '| ID | Current span → proposed joined span | Example guard px / bytes | Result for example |', '|---|---|---:|---|']
    for r in rows:
        if r['category']!='candidate':continue
        for s in r['segments']:
            if s['decision']=='keep-too-long':continue
            d=s['example_metrics']
            md.append(f'| `{r["id"]}` | {cell(s["before"])} → **{cell(s["joined"])}** | {d["guard_pixels"]} / {d["bytes"]} | {"Fits" if fits(d) else "Example exceeds"} |')
    for title,categories in [('Already handled in the published build',{'already-handled'}),
                             ('Continuation cases requiring separate validation',{'continuation-review'}),
                             ('Keep current layout',{'keep','keep-controls','keep-dialogue'}),
                             ('Excluded multiline messages',{'outside-log'})]:
        md+=['','## '+title,'','| ID | Current template | Reason |','|---|---|---|']
        for r in rows:
            if r['category'] in categories and r['breaks']:
                md.append(f'| `{r["id"]}` | {cell(r["template"])} | {r["reason"]} |')
    md+=['','## Approval scope and later validation','',
         'Proposed implementation: the candidate spans marked Fits, plus the two critical/brutal continuation variants after explicit attacker-prefix validation. This requires extending the guarded joining mechanism to the approved spans, including three-line spans; merely adding every source to the current final-pair allowlist would not implement this audit correctly. Do not merge independent messages or remove every LF globally.', '',
         'Before publishing any implementation, run native formatter/live-queue/history tests for every approved span, short and longest practical names, item suffixes, numeric extremes, non-ASCII fallback, buffer guards, ring wrap and sentence-boundary preservation. Include exact 208/209px and 59/60-byte boundary cases, and combined attacker/critical/damage sequences. Preserve existing XP/damage tests and menu publication checks. A passing static measurement is not runtime acceptance.', '',
         'The machine-readable inventory includes every entry, including those without breaks, original Japanese, current ROM target, pointer owners, exact bytes, per-span measurements and decisions: [audit.json](../build/combat-line-audit/audit.json). Regenerate with `.venv/bin/python -m tools.audit_combat_lines`. Existing renderer/history evidence: [tutorial gameplay](TUTORIAL_GAMEPLAY.md), [battle feedback](BATTLE_COMPLETION.md), [current damage joining](DAMAGE_LINES.md).','']
    (ROOT/'docs/COMBAT_LINE_BREAK_AUDIT.md').write_text('\n'.join(md))
    print(json.dumps({**counts,'candidate_spans':len(segments),'examples_fit':sum(fits(s['example_metrics']) for s in segments),'all_ascii_fit':sum(s['all_ascii_slot_values_fit'] for s in segments)},indent=2))

if __name__=='__main__':main()
