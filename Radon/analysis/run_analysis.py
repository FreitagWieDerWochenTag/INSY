"""Run the whole analysis: CSV -> cleaned hourly grid -> findings -> web/build/data/*.json, and print the findings.

    .venv/bin/python Radon/analysis/run_analysis.py
"""
import time

from radon.export import build
from radon.paths import WEB_DATA

t0 = time.perf_counter()
data = build()
ov = data["overview"]
print(f"Radon data {ov['start']} – {ov['end']}, {len(ov['rooms'])} rooms, empty-house days: {', '.join(ov['empty_days'])}")
for r in ov["rooms"]:
    print(f"  {r['label']:<22} mean {r['mean']:6.1f}  p95 {r['p95']:6.1f}  max {r['max']:6.1f}  h>300: {r['hours_above_ref']:4d} "
          f"({r['hours_above_ref_empty']} on empty days)")
print("Findings:")
for f in data["findings"]:
    s = f["stat"]
    p = f" p={s['p']:.1e}" if s.get("p") is not None else ""
    print(f"  [{'holds' if f['held'] else 'no   '}] {f['title']}: {s['name']} = {s['value']}{p}, n={s['n']} {s['unit']}")
    print(f"           {f['statement']}")
print(f"JSON written to {WEB_DATA} in {time.perf_counter() - t0:.1f} s")
