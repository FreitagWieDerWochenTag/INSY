"""Data-backed findings. Every finding computes its own statistic and says whether it holds.

The hourly grid (clean.hourly) is the base. Hourly values are strongly autocorrelated, so tests use one value
per day (paired by day where possible) instead of thousands of hours, which would make every p-value tiny.
A finding "holds" when its test is significant (p < ALPHA) and the effect is large enough to matter.
The statements are built from the numbers, so they change if the data changes.
"""
import numpy as np
import pandas as pd
from scipy import stats
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from .clean import daily
from .load import ROOMS

ALPHA = 0.01          # significance level for every test
MIN_RHO = 0.2         # |Spearman rho| below this is "no clear link", even if significant
MIN_RATIO = 1.10      # a difference of less than 10 % is not reported as an effect
REFERENCE = 300       # Bq/m³, reference level of the Austrian radon protection ordinance (and EU 2013/59/Euratom)
WHO_LEVEL = 100       # Bq/m³, WHO recommendation
EMPTY_CO2_RANGE = 100  # ppm: a day on which neither CO₂ sensor moves more than this had nobody at home
NIGHT, AFTERNOON = (0, 6), (12, 18)

DRIVERS = {  # daily driver -> label
    "out_temp": "Outdoor temperature",
    "temp_gap": "Indoor − outdoor temperature",
    "soil_temp_54": "Soil temperature (54 cm)",
    "wind": "Wind speed",
    "out_pressure": "Air pressure",
    "pressure_change": "Air pressure change (24 h)",
    "kitchen_co2": "CO₂ kitchen",
    "bedroom_co2": "CO₂ bedroom",
    "kitchen_humidity": "Humidity kitchen",
    "bedroom_humidity": "Humidity bedroom",
}


def rooms_in(h):
    return [r for r in ROOMS if r in h]


def label(room):
    return ROOMS[room][0]


def r1(x, nd=1):
    return None if x is None or pd.isna(x) else round(float(x), nd)


def pct(ratio):
    return f"{(ratio - 1) * 100:.0f} %"


# ---------------------------------------------------------------- building blocks

def empty_days(h: pd.DataFrame) -> pd.DatetimeIndex:
    """Days on which nobody was at home: the CO₂ of both rooms stays flat (people breathe, cook, sleep: CO₂ moves)."""
    cols = [c for c in ("kitchen_co2", "bedroom_co2") if c in h]
    span = pd.concat([h[c].resample("1D").max() - h[c].resample("1D").min() for c in cols], axis=1)
    flat = (span < EMPTY_CO2_RANGE).all(axis=1) & span.notna().all(axis=1)
    return flat[flat].index


def zones(h: pd.DataFrame) -> list[list[str]]:
    """Group the rooms whose radon moves together (average-linkage clustering on 1 − Spearman rho, cut at rho 0.5)."""
    rooms = rooms_in(h)
    corr = h[rooms].corr("spearman").to_numpy()
    dist = squareform(1 - corr, checks=False)
    ids = fcluster(linkage(dist, "average"), t=0.5, criterion="distance")
    groups = {}
    for room, i in zip(rooms, ids):
        groups.setdefault(i, []).append(room)
    return sorted(groups.values(), key=len, reverse=True)


def multi_zones(h):
    """Zones with more than one room; if the rooms don't group at all, all rooms count as one zone."""
    return [g for g in zones(h) if len(g) > 1] or [rooms_in(h)]


def zone_name(group):
    return "Living area" if len(group) > 2 else " & ".join(label(r) for r in group)


def daily_frame(h: pd.DataFrame, drop_empty=True) -> pd.DataFrame:
    """Daily means + derived drivers; empty-house days are dropped so they don't dominate the weather links."""
    d = daily(h)
    d["temp_gap"] = d[["kitchen_temp", "bedroom_temp"]].mean(axis=1) - d["out_temp"]
    d["pressure_change"] = d["out_pressure"].diff()
    if drop_empty:
        d = d.drop(index=empty_days(h), errors="ignore")
    return d


def spearman(x, y):
    m = x.notna() & y.notna()
    if m.sum() < 10:
        return None, None, int(m.sum())
    rho, p = stats.spearmanr(x[m], y[m])
    return float(rho), float(p), int(m.sum())


# ---------------------------------------------------------------- overview

def overview(h: pd.DataFrame, removed: dict) -> dict:
    empty = empty_days(h)
    in_empty = h.index.normalize().isin(empty)
    rooms = []
    for r in rooms_in(h):
        s = h[r].dropna()
        above = s > REFERENCE
        rooms.append({
            "room": r, "label": label(r), "hours": len(s),
            "first": s.index.min().strftime("%Y-%m-%d"), "last": s.index.max().strftime("%Y-%m-%d"),
            "mean": r1(s.mean()), "median": r1(s.median()), "p95": r1(s.quantile(0.95)), "max": r1(s.max()),
            "hours_above_who": int((s > WHO_LEVEL).sum()), "hours_above_ref": int(above.sum()),
            "hours_above_ref_empty": int((above & in_empty[h.index.get_indexer(s.index)]).sum()),
            "mean_occupied": r1(s[~in_empty[h.index.get_indexer(s.index)]].mean()),
            "cleaning": removed.get(r, {}),
        })
    return {
        "start": h.index.min().strftime("%Y-%m-%d"), "end": h.index.max().strftime("%Y-%m-%d"),
        "reference": REFERENCE, "who": WHO_LEVEL, "rooms": rooms,
        "empty_days": [d.strftime("%Y-%m-%d") for d in empty],
        "zones": [{"name": zone_name(g), "rooms": g} for g in zones(h)],
    }


def daily_series(h: pd.DataFrame) -> dict:
    d = h[rooms_in(h)].resample("1D")
    mean, lo, hi = d.mean(), d.min(), d.max()
    out = {"dates": [t.strftime("%Y-%m-%d") for t in mean.index], "rooms": {}}
    for r in mean.columns:
        out["rooms"][r] = {"mean": [r1(v) for v in mean[r]], "min": [r1(v) for v in lo[r]], "max": [r1(v) for v in hi[r]]}
    w = daily(h)
    out["out_temp"] = [r1(v) for v in w["out_temp"]]
    return out


def hourly_profile(h: pd.DataFrame) -> dict:
    """Mean radon per hour of the day (occupied days only), per room."""
    occ = h[~h.index.normalize().isin(empty_days(h))]
    g = occ.groupby(occ.index.hour)
    return {r: [r1(v) for v in g[r].mean()] for r in rooms_in(h)}


def correlations(h: pd.DataFrame) -> dict:
    d = daily_frame(h)
    rooms = rooms_in(h)
    cells = []
    for r in rooms:
        for k in DRIVERS:
            rho, p, n = spearman(d[k], d[r]) if k in d else (None, None, 0)
            cells.append({"room": r, "driver": k, "rho": r1(rho, 2), "p": p, "n": n,
                          "held": rho is not None and p < ALPHA and abs(rho) >= MIN_RHO})
    rr = h[rooms].corr("spearman")
    return {
        "drivers": [{"key": k, "label": v} for k, v in DRIVERS.items()],
        "rooms": [{"key": r, "label": label(r)} for r in rooms],
        "cells": cells,
        "room_matrix": [[r1(rr.loc[a, b], 2) for b in rooms] for a in rooms],
    }


# ---------------------------------------------------------------- findings

def f_zones(h):
    rooms = rooms_in(h)
    groups = zones(h)
    rr = h[rooms].corr("spearman")
    zone_of = {r: i for i, g in enumerate(groups) for r in g}
    within, between = [], []
    for i, a in enumerate(rooms):
        for b in rooms[i + 1:]:
            (within if zone_of[a] == zone_of[b] else between).append(rr.loc[a, b])
    held = len(groups) > 1 and np.mean(within) - np.mean(between) >= MIN_RHO
    big = [g for g in groups if len(g) > 1]
    names = "; ".join(f"{zone_name(g)} ({', '.join(label(r) for r in g)})" for g in big)
    return {
        "id": "zones", "title": "The house has two radon zones",
        "statement": (f"Rooms inside a zone move together (mean ρ = {np.mean(within):.2f}), rooms of different zones barely "
                      f"(ρ = {np.mean(between):.2f}). Zones found in the data: {names}. They need separate measures."),
        "held": bool(held), "stat": {"name": "mean ρ within − between", "value": r1(np.mean(within) - np.mean(between), 2),
                                    "n": int(h[rooms].dropna().shape[0]), "unit": "hours"},
        "method": "Spearman correlation of the hourly radon values of every room pair; rooms grouped by average-linkage clustering (cut at ρ = 0.5).",
        "chart": {"type": "matrix", "labels": [label(r) for r in rooms], "values": [[r1(rr.loc[a, b], 2) for b in rooms] for a in rooms]},
    }


def f_night(h):
    occ = h[~h.index.normalize().isin(empty_days(h))]
    hr = occ.index.hour
    rows, held_rooms = [], []
    for r in rooms_in(h):
        night = occ[r][(hr >= NIGHT[0]) & (hr < NIGHT[1])].resample("1D").mean()
        day = occ[r][(hr >= AFTERNOON[0]) & (hr < AFTERNOON[1])].resample("1D").mean()
        x = pd.concat([night, day], axis=1, keys=["n", "d"]).dropna()
        p = stats.wilcoxon(x["n"], x["d"]).pvalue
        ratio = x["n"].mean() / x["d"].mean()
        ok = p < ALPHA and ratio >= MIN_RATIO
        rows.append({"room": r, "night": x["n"].mean(), "day": x["d"].mean(), "ratio": ratio, "p": p,
                     "share": (x["n"] > x["d"]).mean(), "n": len(x), "held": ok})
        if ok:
            held_rooms.append(rows[-1])
    if held_rooms:
        lo = min(x["ratio"] for x in held_rooms); hi = max(x["ratio"] for x in held_rooms)
        share = np.mean([x["share"] for x in held_rooms])
        rest = [label(x["room"]) for x in rows if not x["held"]]
        statement = (f"In {len(held_rooms)} of {len(rows)} rooms radon is {pct(lo)}–{pct(hi)} higher at night (0–6 h) than in "
                     f"the afternoon (12–18 h), on {share * 100:.0f} % of the days: at night nobody opens a window, so the gas that "
                     f"seeps in from the ground accumulates; daytime airing removes it again." +
                     (f" Not in: {', '.join(rest)} (difference < 10 %)." if rest else ""))
    else:
        statement = "No room shows a night/afternoon difference of 10 % or more."
    best = max(rows, key=lambda x: x["ratio"])
    return {
        "id": "night", "title": "Radon peaks at night, lowest in the afternoon",
        "statement": statement, "held": bool(held_rooms),
        "stat": {"name": f"night / afternoon ({label(best['room'])})", "value": r1(best["ratio"], 2), "p": best["p"],
                 "n": best["n"], "unit": "days"},
        "method": "Per day the mean of 0–6 h and of 12–18 h; Wilcoxon signed-rank test over the days (paired by day). Empty-house days excluded.",
        "chart": {"type": "bars", "labels": [label(x["room"]) for x in rows], "unit": "Bq/m³",
                  "series": [{"name": "Night 0–6 h", "values": [r1(x["night"]) for x in rows]},
                             {"name": "Afternoon 12–18 h", "values": [r1(x["day"]) for x in rows]}]},
        "rooms": {x["room"]: x["held"] for x in rows},
    }


def f_empty(h):
    empty = empty_days(h)
    d = daily(h)
    is_empty = d.index.isin(empty)
    rows = []
    for r in rooms_in(h):
        e, o = d.loc[is_empty, r].dropna(), d.loc[~is_empty, r].dropna()
        if len(e) < 3:
            continue
        p = stats.mannwhitneyu(e, o, alternative="two-sided").pvalue
        rows.append({"room": r, "empty": e.mean(), "occ": o.mean(), "ratio": e.mean() / o.mean(), "p": p, "n": len(e)})
    if not rows:
        return None
    held = [x for x in rows if x["p"] < ALPHA and x["ratio"] >= MIN_RATIO]
    lo = min(x["ratio"] for x in rows); hi = max(x["ratio"] for x in rows)
    peak = max(x["empty"] for x in rows)
    days = ", ".join(t.strftime("%d %b") for t in empty)
    return {
        "id": "empty", "title": "Nobody home, windows shut: radon builds up",
        "statement": (f"On {len(empty)} days nobody was at home (CO₂ flat at the outdoor level: {days}). Radon then rose to "
                      f"{lo:.1f}–{hi:.1f}× the usual level in every room, with daily means up to {peak:.0f} Bq/m³ – above the "
                      f"{REFERENCE} Bq/m³ reference level. Daily airing is what keeps radon low in this house."),
        "held": len(held) == len(rows),
        "stat": {"name": "empty / occupied (lowest room)", "value": r1(lo, 1), "p": max(x["p"] for x in rows),
                 "n": len(empty), "unit": "empty days"},
        "method": f"A day is 'empty' if neither CO₂ sensor varies by more than {EMPTY_CO2_RANGE} ppm. Mann-Whitney U test of the daily means, empty vs. occupied days.",
        "chart": {"type": "bars", "labels": [label(x["room"]) for x in rows], "unit": "Bq/m³",
                  "series": [{"name": "Occupied days", "values": [r1(x["occ"]) for x in rows]},
                             {"name": "Empty days", "values": [r1(x["empty"]) for x in rows]}]},
        "days": [t.strftime("%Y-%m-%d") for t in empty], "ratio_range": [r1(lo, 1), r1(hi, 1)],
    }


def airing_events(h, room, drop=150, gap="6h"):
    """Hours in which the room's CO₂ falls by at least `drop` ppm: a window or door was opened."""
    d = h[f"{room}_co2"].diff()
    events, last = [], None
    for t in d[d <= -drop].index:
        if last is None or t - last > pd.Timedelta(gap):
            events.append(t)
            last = t
    return events


def f_airing(h):
    rows = []
    for room in ("bedroom", "kitchen"):
        if f"{room}_co2" not in h:
            continue
        pairs = []
        for t in airing_events(h, room):
            before = h[room].loc[t - pd.Timedelta("3h"):t - pd.Timedelta("1h")].mean()
            after = h[room].loc[t + pd.Timedelta("1h"):t + pd.Timedelta("3h")].mean()
            pairs.append((before, after))
        x = pd.DataFrame(pairs, columns=["before", "after"]).dropna()
        if len(x) < 10:
            continue
        p = stats.wilcoxon(x["before"], x["after"]).pvalue
        rows.append({"room": room, "before": x["before"].median(), "after": x["after"].median(), "p": p, "n": len(x),
                     "share": (x["after"] < x["before"]).mean()})
    held = [x for x in rows if x["p"] < ALPHA and x["before"] / x["after"] >= MIN_RATIO]
    parts = [f"{label(x['room']).lower()} {x['before']:.0f} → {x['after']:.0f} Bq/m³ (lower after {x['share'] * 100:.0f} % of "
             f"{x['n']} airings)" for x in rows]
    return {
        "id": "airing", "title": "Airing lowers radon within hours",
        "statement": ("When a window is opened (CO₂ drops by ≥ 150 ppm within an hour), radon falls in the hours after: " +
                      "; ".join(parts) + "."),
        "held": len(held) == len(rows) and bool(rows),
        "stat": {"name": f"before / after ({label(rows[0]['room']).lower()})" if rows else "before / after",
                 "value": r1(rows[0]["before"] / rows[0]["after"], 2) if rows else None, "p": max((x["p"] for x in rows), default=None),
                 "n": sum(x["n"] for x in rows), "unit": "airings"},
        "method": "Airing = CO₂ falls by ≥ 150 ppm from one hour to the next (at most one per 6 h). Median radon 1–3 h before vs. 1–3 h after; Wilcoxon signed-rank test.",
        "chart": {"type": "bars", "labels": [label(x["room"]) for x in rows], "unit": "Bq/m³",
                  "series": [{"name": "1–3 h before", "values": [r1(x["before"]) for x in rows]},
                             {"name": "1–3 h after", "values": [r1(x["after"]) for x in rows]}]},
    }


def f_co2(h):
    """Closed rooms: the more CO₂ has accumulated, the more radon has too (same room, same hour)."""
    d = daily_frame(h)
    x = d[["bedroom_co2", "bedroom"]].dropna()
    q = pd.qcut(x["bedroom_co2"], 4, labels=False)
    means = x.groupby(q)["bedroom"].mean()
    edges = x.groupby(q)["bedroom_co2"].agg(["min", "max"])
    rho, p, n = spearman(d["bedroom_co2"], d["bedroom"])
    ratio = means.iloc[-1] / means.iloc[0]
    return {
        "id": "co2", "title": "Stale air means more radon",
        "statement": (f"In the bedroom, the days with the highest CO₂ (windows mostly closed) have {pct(ratio)} more radon "
                      f"than the best-ventilated days ({means.iloc[-1]:.0f} vs. {means.iloc[0]:.0f} Bq/m³). CO₂ is a cheap "
                      f"indicator: if it is high, radon usually is too."),
        "held": bool(p is not None and p < ALPHA and rho >= MIN_RHO and ratio >= MIN_RATIO),
        "stat": {"name": "ρ daily CO₂ vs. radon", "value": r1(rho, 2), "p": p, "n": n, "unit": "days"},
        "method": "Daily mean bedroom CO₂ split into quartiles, mean bedroom radon per quartile; Spearman correlation of the daily means (empty days excluded).",
        "chart": {"type": "bars", "unit": "Bq/m³",
                  "labels": [f"{edges.loc[i, 'min']:.0f}–{edges.loc[i, 'max']:.0f} ppm" for i in means.index],
                  "series": [{"name": "Bedroom radon", "values": [r1(v) for v in means]}]},
    }


def f_season(h):
    groups = multi_zones(h)
    d = daily_frame(h)
    monthly = daily_frame(h).resample("MS").mean()
    series, stats_ = [], []
    for g in groups[:2]:
        z = d[g].mean(axis=1)
        rho, p, n = spearman(d["out_temp"], z)
        stats_.append({"zone": zone_name(g), "rho": rho, "p": p, "n": n})
        series.append({"name": zone_name(g), "values": [r1(v) for v in monthly[g].mean(axis=1)]})
    held = len(stats_) == 2 and all(s["p"] < ALPHA and abs(s["rho"]) >= MIN_RHO for s in stats_) and \
        np.sign(stats_[0]["rho"]) != np.sign(stats_[1]["rho"])
    a, b = stats_[0], stats_[-1]
    return {
        "id": "season", "title": "Warm days: the zones go opposite ways",
        "statement": (f"On warm days the {a['zone'].lower()} has {'less' if a['rho'] < 0 else 'more'} radon (ρ = {a['rho']:.2f}), "
                      f"the {b['zone'].lower()} {'less' if b['rho'] < 0 else 'more'} (ρ = {b['rho']:.2f}). The living rooms are likely aired "
                      f"more in warm weather; the {b['zone'].lower()} follows the warm soil (soil temperature at 54 cm: "
                      f"ρ = {spearman(d['soil_temp_54'], d[groups[-1]].mean(axis=1))[0]:.2f})."),
        "held": bool(held),
        "stat": {"name": f"ρ outdoor temp vs. {b['zone'].lower()}", "value": r1(b["rho"], 2), "p": b["p"], "n": b["n"], "unit": "days"},
        "method": "Spearman correlation of daily outdoor temperature with the daily mean radon of each zone (empty days excluded). Chart: monthly means.",
        "chart": {"type": "lines", "labels": [t.strftime("%b") for t in monthly.index], "unit": "Bq/m³", "series": series},
    }


def f_wind(h):
    d = daily_frame(h)
    groups = multi_zones(h)
    bands = pd.qcut(d["wind"], 4, labels=False)
    edges = d.groupby(bands)["wind"].agg(["min", "max"])
    series, rhos = [], []
    for g in groups[:2]:
        z = d[g].mean(axis=1)
        rhos.append((zone_name(g),) + spearman(d["wind"], z))
        series.append({"name": zone_name(g), "values": [r1(v) for v in z.groupby(bands).mean()]})
    held = [r for r in rhos if r[2] < ALPHA and r[1] <= -MIN_RHO]
    txt = "; ".join(f"{n.lower()} ρ = {rho:.2f}" for n, rho, _, _ in rhos)
    return {
        "id": "wind", "title": "Windy days are low-radon days",
        "statement": (f"The windier the day, the less radon in the {' and the '.join(r[0].lower() for r in held)} ({txt}). "
                      f"Wind pushes outdoor air through gaps and open doors and dilutes the indoor air"
                      + ("; in the other zone the link is weak." if len(held) < len(rhos) else ".")
                      if held else f"Wind has no clear effect ({txt})."),
        "held": bool(held),
        "stat": {"name": f"ρ wind vs. {held[0][0].lower() if held else rhos[0][0].lower()}",
                 "value": r1((held or rhos)[0][1], 2), "p": (held or rhos)[0][2], "n": rhos[0][3], "unit": "days"},
        "method": "Spearman correlation of daily mean wind speed with daily mean radon per zone (empty days excluded). Chart: wind quartiles.",
        "chart": {"type": "bars", "unit": "Bq/m³", "labels": [f"{edges.loc[i, 'min']:.0f}–{edges.loc[i, 'max']:.0f} km/h" for i in edges.index],
                  "series": series},
    }


def f_weekday(h):
    d = daily_frame(h)
    rooms = rooms_in(h)
    z = d[rooms].mean(axis=1).dropna()
    we = z[z.index.day_of_week >= 5]; wd = z[z.index.day_of_week < 5]
    p = stats.mannwhitneyu(we, wd, alternative="two-sided").pvalue
    ratio = we.mean() / wd.mean()
    by_day = z.groupby(z.index.day_of_week).mean()
    held = p < ALPHA and abs(ratio - 1) >= MIN_RATIO - 1
    return {
        "id": "weekday", "title": "Weekends differ" if held else "Weekends are not different",
        "statement": (f"Weekend days have {abs(ratio - 1) * 100:.0f} % {'more' if ratio > 1 else 'less'} radon than weekdays "
                      f"(p = {p:.2f}) – " + ("a real difference." if held else "too small to tell apart from chance.")),
        "held": bool(held), "negative": True,
        "stat": {"name": "weekend / weekday", "value": r1(ratio, 2), "p": p, "n": len(z), "unit": "days"},
        "method": "Daily mean over all rooms, weekend vs. weekday days; Mann-Whitney U test (empty days excluded).",
        "chart": {"type": "bars", "unit": "Bq/m³", "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                  "series": [{"name": "All rooms", "values": [r1(v) for v in by_day]}]},
    }


def f_no_link(h, key, title, why):
    """Drivers people often suspect; reported honestly when the data shows no clear link."""
    d = daily_frame(h)
    groups = multi_zones(h)
    rhos = [(zone_name(g),) + spearman(d[key], d[g].mean(axis=1)) for g in groups[:2]]
    strongest = max(rhos, key=lambda r: abs(r[1]))
    held = strongest[2] < ALPHA and abs(strongest[1]) >= MIN_RHO
    txt = "; ".join(f"{n.lower()} ρ = {rho:.2f}" for n, rho, _, _ in rhos)
    return {
        "id": key, "title": title if not held else f"{DRIVERS[key]} matters", "negative": True,
        "statement": (f"{DRIVERS[key]} shows {'a link' if held else 'no clear link'} with radon ({txt}). {why}"),
        "held": bool(held),
        "stat": {"name": f"ρ ({strongest[0].lower()})", "value": r1(strongest[1], 2), "p": strongest[2], "n": strongest[3], "unit": "days"},
        "method": f"Spearman correlation of the daily {DRIVERS[key].lower()} with daily mean radon per zone (empty days excluded).",
    }


def all_findings(h: pd.DataFrame) -> list[dict]:
    found = [f_empty(h), f_night(h), f_airing(h), f_co2(h), f_zones(h), f_season(h), f_wind(h), f_weekday(h),
             f_no_link(h, "pressure_change", "Falling air pressure: no visible effect",
                       "Falling pressure is said to pull soil gas out of the ground; in this house the effect is lost behind airing and weather."),
             f_no_link(h, "bedroom_humidity", "Humidity: no visible effect",
                       "Humid air does not come with more radon here.")]
    return [f for f in found if f]
