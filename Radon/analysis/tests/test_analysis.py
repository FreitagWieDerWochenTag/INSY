"""Tests of the radon analysis: cleaning rules on tiny inputs, each statistic on synthetic data with a known answer,
and one run over the real CSV."""
import json

import numpy as np
import pandas as pd
import pytest

from radon import findings as F
from radon.clean import WARMUP_MIN, clean_radon, daily, hourly
from radon.export import build
from radon.load import ROOMS, column_names, load_raw
from radon.paths import DATA

RNG = np.random.default_rng(0)


def synthetic(days=60, night_boost=0.0, empty=(), noise=5.0):
    """Hourly frame shaped like clean.hourly(): every room ~50 Bq/m³ (+ night_boost × at 0–6 h), CO₂ moving
    every day except on `empty` days (flat), weather columns with mild noise."""
    idx = pd.date_range("2026-04-01", periods=24 * days, freq="1h", tz="Europe/Vienna")
    hour = idx.hour.to_numpy()
    base = 50 * (1 + night_boost * ((hour >= 0) & (hour < 6)))
    h = pd.DataFrame(index=idx)
    for r in ROOMS:
        h[r] = base + RNG.normal(0, noise, len(idx))
    co2 = 500 + 300 * np.sin(np.pi * hour / 24)
    for room in ("kitchen", "bedroom"):
        h[f"{room}_co2"] = co2 + RNG.normal(0, 10, len(idx))
        h[f"{room}_temp"] = 22 + RNG.normal(0, 0.5, len(idx))
        h[f"{room}_humidity"] = 50 + RNG.normal(0, 3, len(idx))
    for day in empty:
        m = idx.normalize() == pd.Timestamp(day, tz="Europe/Vienna")
        h.loc[m, ["kitchen_co2", "bedroom_co2"]] = 420
        h.loc[m, list(ROOMS)] *= 6
    h["out_temp"] = 15 + RNG.normal(0, 5, len(idx))
    h["out_pressure"] = 980 + RNG.normal(0, 3, len(idx))
    h["wind"] = np.abs(RNG.normal(8, 4, len(idx)))
    h["soil_temp_54"] = 14 + RNG.normal(0, 1, len(idx))
    return h


# ---------------------------------------------------------------- loading and cleaning

def test_every_csv_column_is_mapped():
    header = pd.read_csv(DATA, nrows=0).columns
    names = column_names()
    assert set(header) - set(names) == {"Zeit (UTC)", "Zeit (Europe/Vienna)"}
    assert len(set(names.values())) == len(names)


def test_load_converts_to_vienna_time(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text("Zeit (UTC),Zeit (Europe/Vienna),Buero – Radon (Bq/m³),Buero – Betriebszeit (min)\n"
                   "2026-07-01T10:00:00.5Z,2026-07-01 12:00:00,40.0,500\n", encoding="utf-8")
    df = load_raw(csv)
    assert df.index[0].hour == 12 and str(df.index.tz) == "Europe/Vienna"
    assert df["office_radon"].iloc[0] == 40.0


def test_warmup_and_dropouts_are_removed_but_real_zeros_kept():
    idx = pd.date_range("2026-04-01", periods=12, freq="10min", tz="Europe/Vienna")
    raw = pd.DataFrame(index=idx)
    raw["office_radon"] = [200, 210, 0, 205, 200, 210, 200, 205, 210, 200, 205, 200.0]   # 0 between ~200: dropout
    raw["office_uptime"] = [10, 20] + [WARMUP_MIN + i for i in range(10)]                  # first two: warm-up
    raw["utility_radon"] = [0, 0, 5, 0, 3, 0, 0, 4, 0, 0, 2, 0.0]                          # low room: zeros are real
    raw["utility_uptime"] = 1000.0
    radon, removed = clean_radon(raw)
    assert removed["office"]["warmup"] == 2 and removed["office"]["dropouts"] == 1
    assert (radon["office"].dropna() > 0).all()
    assert removed["utility"]["dropouts"] == 0 and (radon["utility"] == 0).sum() == 8


def test_daily_needs_enough_hours():
    idx = pd.date_range("2026-04-01", periods=30, freq="1h", tz="Europe/Vienna")
    d = daily(pd.DataFrame({"x": 1.0}, index=idx))
    assert d["x"].iloc[0] == 1.0 and np.isnan(d["x"].iloc[1])   # day 2 has only 6 hours


# ---------------------------------------------------------------- findings on data with a known answer

def test_empty_days_are_found_from_flat_co2():
    h = synthetic(empty=["2026-04-10", "2026-04-11", "2026-04-12"])
    assert [d.strftime("%m-%d") for d in F.empty_days(h)] == ["04-10", "04-11", "04-12"]
    f = F.f_empty(h)
    assert f["held"] and f["stat"]["value"] > 4


def test_night_peak_is_detected_and_absent_when_flat():
    assert F.f_night(synthetic(night_boost=0.5))["held"]
    assert not F.f_night(synthetic(night_boost=0.0))["held"]


def test_zones_split_independent_groups():
    h = synthetic()
    common, other = RNG.normal(0, 30, len(h)), RNG.normal(0, 30, len(h))
    for r in ROOMS:
        h[r] += other if r in ("utility", "workshop") else common
    assert sorted(map(sorted, F.zones(h))) == [sorted(set(ROOMS) - {"utility", "workshop"}), ["utility", "workshop"]]


def test_airing_events_need_a_co2_drop_and_are_spaced():
    h = synthetic(days=2)
    h["bedroom_co2"] = 800.0
    t = h.index[10]
    h.loc[t, "bedroom_co2"] = 500.0          # drop of 300 ppm at t
    h.loc[h.index[12], "bedroom_co2"] = 500.0  # second drop 2 h later: same airing
    assert F.airing_events(h, "bedroom") == [t]


def test_no_link_is_reported_as_not_holding():
    h = synthetic()
    f = F.f_no_link(h, "out_pressure", "Pressure: no visible effect", "")
    assert not f["held"] and f["title"] == "Pressure: no visible effect"


# ---------------------------------------------------------------- the real data

@pytest.fixture(scope="module")
def real(tmp_path_factory):
    out = tmp_path_factory.mktemp("data")
    build(out=out)
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in out.glob("*.json")}


def test_build_writes_all_files(real):
    assert set(real) == {"overview", "daily", "hourly_profile", "correlations", "findings"}
    assert len(real["overview"]["rooms"]) == len(ROOMS)
    assert len(real["daily"]["dates"]) == len(real["daily"]["rooms"]["office"]["mean"])


def test_real_findings_have_numbers(real):
    for f in real["findings"]:
        assert f["title"] and f["statement"] and isinstance(f["held"], bool)
        assert f["stat"]["n"] > 0
        for s in f.get("chart", {}).get("series", []):
            assert len(s["values"]) == len(f["chart"]["labels"])


def test_real_hourly_grid_matches_raw():
    h = hourly(load_raw())
    assert h.index.freq == "h" or (h.index[1] - h.index[0]) == pd.Timedelta("1h")
    assert 30 < h["office"].mean() < 50
