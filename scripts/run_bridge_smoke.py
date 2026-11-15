"""Prepare or execute a reviewed independent BL-16 case; never invents human approval."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.api.platform import Services
from backend.app.api.cases import submit_case
from backend.app.simulation import bridge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-id')
    parser.add_argument('--version', type=int, default=1)
    args = parser.parse_args()
    if not args.case_id:
        case = bridge.create(bridge.CaseInput(), Services.catalog())
        print(json.dumps(case, ensure_ascii=True, indent=2))
        print('Human review required through POST /api/cases/{id}/review before execution.')
        return 0
    run = submit_case(args.case_id, args.version)
    print(run.run_id, flush=True)
    try:
        while True:
            result = Services.sim().get_run(run.run_id)
            if result['state'] in ('COMPLETED','FAILED','BLOCKED'): break
            time.sleep(1)
        out = ROOT / 'docs/evidence' / f'BL-16_real_{run.run_id}.json'
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(result['state'], out, flush=True)
        return 0 if result['state']=='COMPLETED' else 1
    finally:
        Services.sim().stop()


if __name__ == '__main__': raise SystemExit(main())
