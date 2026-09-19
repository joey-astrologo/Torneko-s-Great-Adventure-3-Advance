"""Prove the publisher rejects the known-bad prior ROM without changing latest."""
from unittest.mock import patch
from tools import build_english as publisher, build_menu_fixes as menus
from tools.translation_pipeline import check,load_json


def main():
    paths=[publisher.OUTPUT/(publisher.STEM+ext) for ext in ('.gba','.bps','.json')]+[publisher.DETAILS]
    before={str(p):menus.digest(p.read_bytes()) for p in paths}
    data=menus.BASELINE.read_bytes();report=load_json(menus.BASELINE.parent/'english-build.json')
    # Substitute only the build result, using the actual pre-fix ROM/ledger.
    # All publisher validation and native emulation still run normally.
    with patch.object(publisher.current,'build_rom',return_value=(data,report)):
        try:publisher.build()
        except ValueError as error:
            check('Missing command shading' in str(error),'Unexpected gate failure: '+str(error))
            failure=str(error)
        else:raise ValueError('Known-bad baseline was published')
    check(before=={str(p):menus.digest(p.read_bytes()) for p in paths},'Rejected build modified latest artifacts')
    menus.save(menus.OUTPUT/'publication-rejection-check.json',dict(rejected_rom_sha256=menus.digest(data),
        expected_failure=failure,latest_artifacts_unchanged=before))
    print('Known-bad candidate rejected; latest artifacts unchanged.',flush=True)

if __name__=='__main__':main()
