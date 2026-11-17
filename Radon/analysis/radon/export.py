"""Write the JSON files the dashboard reads."""
import json
import math
from pathlib import Path

from .clean import clean_radon, hourly
from .findings import all_findings, correlations, daily_series, hourly_profile, overview
from .load import load_raw
from .paths import DATA, WEB_DATA


def _clean_json(x):
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    if isinstance(x, dict):
        return {k: _clean_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean_json(v) for v in x]
    if hasattr(x, "item"):  # numpy scalars
        return _clean_json(x.item())
    return x


def build(csv=DATA, out: Path = WEB_DATA) -> dict:
    raw = load_raw(csv)
    _, removed = clean_radon(raw)
    h = hourly(raw)
    data = {
        "overview": overview(h, removed),
        "daily": daily_series(h),
        "hourly_profile": hourly_profile(h),
        "correlations": correlations(h),
        "findings": all_findings(h),
    }
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in data.items():
        (out / f"{name}.json").write_text(json.dumps(_clean_json(obj), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return data
