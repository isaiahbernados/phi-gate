"""Synthetic smoke evaluation; never prints source text or provider error bodies."""

import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args, flags = parser.parse_known_args()
    cases = json.loads((ROOT / 'tests/synthetic.json').read_text())
    results = []
    for case in cases:
        started = time.monotonic()
        process = subprocess.run([sys.executable, str(ROOT / 'phi_gate.py'), *flags], input=case['text'], text=True, capture_output=True)
        try:
            actual = json.loads(process.stdout) if process.returncode == 0 else None
        except ValueError:
            actual = None
        if type(actual) is not bool:
            actual = None
        results.append({'id': case['id'], 'expected': case['phi'], 'actual': actual, 'seconds': round(time.monotonic() - started, 3)})
    valid = [r for r in results if r['actual'] is not None]
    report = {
        'scope': '24 synthetic English cases; smoke check, not PHI accuracy certification',
        'total': len(results),
        'errors': len(results) - len(valid),
        'correct': sum(r['actual'] == r['expected'] for r in valid),
        'false_negatives': sum(r['expected'] and not r['actual'] for r in valid),
        'false_positives': sum(not r['expected'] and r['actual'] for r in valid),
        'median_seconds': round(statistics.median(r['seconds'] for r in results), 3),
        'results': results,
    }
    encoded = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end='')
    return 2 if report['errors'] else int(report['correct'] != report['total'])


if __name__ == '__main__':
    sys.exit(main())
