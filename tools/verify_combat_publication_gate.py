"""The actual pre-join ROM must fail publication without replacing latest files."""
from unittest.mock import patch
from tools import build_english as publisher, build_combat_lines as b
from tools.translation_pipeline import check,load_json


def main():
    paths=[publisher.OUTPUT/(publisher.STEM+ext) for ext in ('.gba','.bps','.json')]+[publisher.DETAILS]
    before={str(p):b.digest(p.read_bytes()) for p in paths}
    data=b.BASELINE.read_bytes();report=load_json(b.BASELINE.parent/'english-build.json')
    with patch.object(publisher.current,'build_rom',return_value=(data,report)):
        try:publisher.build()
        except ValueError as error:
            check('Boundary mismatch 208px' in str(error),'Unexpected gate failure: '+str(error))
            failure=str(error)
        else:raise ValueError('Unjoined baseline was published')
    check(before=={str(p):b.digest(p.read_bytes()) for p in paths},'Rejected build modified latest artifacts')
    b.save(b.OUTPUT/'publication-rejection-check.json',dict(rejected_rom_sha256=b.digest(data),
        expected_failure=failure,latest_artifacts_unchanged=before))
    print('Pre-join candidate rejected; latest artifacts unchanged.',flush=True)

if __name__=='__main__':main()
