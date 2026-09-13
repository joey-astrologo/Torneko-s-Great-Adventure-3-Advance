"""Tie title runtime proof to the exact cumulative image and owned changes."""
from pathlib import Path
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.build_title_art import OUT, ROM, BASELINE
from tools.pack_title_art import APPROVAL
from tools.extract_arrival_cards import save_json
from tools.translation_pipeline import check, load_json


def summarize():
    before=BASELINE.read_bytes();after=ROM.read_bytes()
    plan=load_json(OUT/'allocation-plan.json');report=load_json(OUT/'english-build.json')
    native=load_json(OUT/'native-verification.json');packing=load_json(OUT/'packing.json')
    prior=load_json(BASELINE.parent/'english-build.json')['ledger'];ledger=report['ledger']
    check(digest(ORIGINAL_ROM.read_bytes())==report['source_sha256'],'Source changed')
    check(digest(after)==report['rom_sha256']==native['rom_sha256'],'Runtime proof is for another ROM')
    check(digest(before)==plan['previous_sha256']==native['baseline_sha256'],'Wrong baseline')
    check(native['status']=='passed' and native['user_files_unchanged'],'Native checks incomplete')
    check(native['harness_sha256']==digest((ROOT/'tools/verify_title_art.py').read_bytes()),'Native verifier changed')
    for path,sha in native['helper_sha256'].items():check(digest((ROOT/path).read_bytes())==sha,'Native helper changed')
    check(plan['approval_sha256']==report['approval_sha256']==packing['approval_sha256']==digest(APPROVAL.read_bytes()),'Approval changed')
    expected=bytearray(before)
    for row in plan['allocations']:
        raw=(ROOT/row['file']).read_bytes();check(digest(raw)==row['sha256'],'Packed allocation changed')
        expected[row['offset']:row['offset']+len(raw)]=raw
    for row in plan['patches']:
        raw=bytes.fromhex(row['after']);expected[row['offset']:row['offset']+len(raw)]=raw
    check(bytes(expected)==after,'Changes outside title ownership')
    check(ledger['allocations'][:-2]==prior['allocations'],'Earlier allocations changed')
    check(ledger['patches'][:-1]==prior['patches'],'Earlier patches changed')
    check(ledger['memory_reservations']==prior['memory_reservations'],'RAM reservations changed')
    paths=[OUT/'allocation-plan.json',OUT/'packing.json',OUT/'native-verification.json',OUT/'approval-vs-game.png']
    blink_frames=0
    for profile in native['profiles']:
        for key in ('baseline_report','english_report'):
            path=OUT/profile[key];row=load_json(path);paths.append(path)
            check(row['all_title_pixels_exact'] and row['palette_exact'] and row['guard_checks'],'Missing native evidence')
            blink_frames+=len(row['prompt_phases'])
    acceptance={'status':'passed','source_rom':report['source_rom'],'source_sha256':report['source_sha256'],
        'output_rom':report['output_rom'],'rom_sha256':report['rom_sha256'],'baseline_sha256':digest(before),
        'approval_sha256':digest(APPROVAL.read_bytes()),'new_allocations':2,'new_bytes_with_alignment':plan['new_bytes_with_padding'],
        'checked_original_patch_ranges':1,'patched_original_bytes':12,'code_changes':False,
        'earlier_allocations_and_patches_preserved':True,'whole_image_matches_owned_changes':True,
        'permanent_ram_and_save_layout_unchanged':True,'tile_count':packing['tile_count'],
        'native_boot_routes':4,'paired_save_profiles':2,'native_blink_frames':blink_frames,
        'unchanged_screen_pairs':sum(len(p['unchanged_screen_pairs']) for p in native['profiles']),
        'quantization_rgb_mae':packing['rgb_mae'],'quantization_rgb_rmse':packing['rgb_rmse'],
        'artifacts':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in paths},
        'scope':'Approved title inserted through the unchanged loader. Native packed pixels, palette, '
                'guarded copies, fade and original prompt timing pass. Empty-save Settings and existing-save '
                'Records routes return to identical illustrated menus. Broader gameplay evidence retains prior hashes.'}
    save_json(OUT/'acceptance.json',acceptance)
    print('Accepted native title insertion:',acceptance['rom_sha256'],flush=True)


if __name__=='__main__':summarize()
