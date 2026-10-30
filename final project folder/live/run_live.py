"""Live flood warnings: today's river-flow forecast turned into an impact-based warning, a CAP alert and a feed.

    python live/run_live.py [--basin mahanadi ...] [--out live/out] [--horizon 10] [--no-model]
    python live/run_live.py --replay 2022-08-14     # a past flood, as the feed would have seen it that morning

For each basin (live/basins/<key>.json, written by make_basin_config.py):
1. The GloFAS ensemble forecast at the gauge (51 runs, 30 days) becomes, per run and day, the flow measure the atlas
   is fitted on (on the Mahanadi the highest daily flow at Naraj over the last 3 days).
2. The basin's flow-impact tables (mahanadi/impact_curve.py) give, per run and day, flooded land, people on it,
   villages with >= 10 % of their people on flooded land and people cut off from every hospital.
3. Each day gets the warning level of its median run and the share of runs at each level (levels.py).
4. Villages to warn, villages that lose their hospital, roads that close and health facilities that flood are listed
   with the first day they are expected (median run) or possible (90th-percentile run), within the warning horizon.
5. Official alerts for the basin's districts (NDMA SACHET), CWC stations above warning level and the latest radar
   pass are attached. On the Mahanadi a data-driven 1-3 day forecast from the upstream gauges is added
   (mahanadi/forecast_model.py, trained on 1997-2025 at the first run; needs scikit-learn).
Writes <out>/<basin>/status.json, forecast.csv, bulletin.txt, alert.cap.xml (from "Be aware" upwards), and
<out>/feed.atom (an Atom index of the alerts, the way CAP feeds are published) and <out>/index.html (status board).
CAP status is "Exercise": this is a student prototype, not an official warning.
--replay <date> issues the bulletin of that morning from the flows that actually came (a perfect forecast, from
data/<basin>/discharge.csv) and, on the Mahanadi, from the upstream-gauge model run with the flows and rain known that
day; the radar passes of the following days are listed beside the flooded land the bulletin expected for them.
"""
import argparse
import html
import json
import os
import pickle
import sys
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from levels import LEVELS, level_of  # noqa: E402
from sources import PLUGINS  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))


def load(key):
    cfg = json.load(open(os.path.join(HERE, "basins", f"{key}.json")))
    tables = {k: pd.read_csv(os.path.join(HERE, v)) for k, v in cfg["tables"].items()}
    return cfg, tables


def impact_rows(curve, q):
    """Rows of the flow-impact table at flows q (the largest tabulated flow <= q; above the table, its last row)."""
    i = np.clip(np.searchsorted(curve.q_m3s.values, np.asarray(q, float), side="right") - 1, 0, len(curve) - 1)
    return curve.iloc[np.atleast_1d(i)].reset_index(drop=True)


def measure(series, cfg):
    """The flow the atlas is fitted on, from a daily series: the highest flow over the window (or the previous day's)."""
    s = series.shift(1) if cfg["predictor_lag"] else series
    return s.rolling(cfg["predictor_days"], min_periods=1).max()


def first_day(days, q_path, thr):
    hit = np.where(q_path >= thr)[0]
    return str(days[hit[0]].date()) if len(hit) else None


def model_forecast(cfg, feeds):
    """Data-driven 1-3 day Naraj forecast from the upstream gauges and catchment rain (forecast_model.py)."""
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mahanadi"))
    import sklearn
    import forecast_model as fm
    data = os.path.join(HERE, "data", cfg["key"])
    Qh = pd.read_csv(os.path.join(data, "discharge.csv"), index_col="date", parse_dates=True)[list(fm.GAUGES)].dropna()
    Rh = pd.read_csv(os.path.join(data, "rain_catchment.csv"), index_col="date", parse_dates=True)["rain_mm"]
    cache = os.path.join(data, f"forecast_model_sklearn{sklearn.__version__}.pkl")
    if os.path.exists(cache):
        models = pickle.load(open(cache, "rb"))
    else:
        models = {L: fm.fit(Qh, Rh, L, future_rain=True, years=(1997, 2025)) for L in fm.LEADS}
        pickle.dump(models, open(cache, "wb"))
    up = PLUGINS["glofas"](cfg, past_days=10, forecast_days=1, upstream=True)
    rn = PLUGINS["rain"](cfg, points=fm.CATCHMENT_PTS, past_days=10, forecast_days=4)
    feeds.update(glofas_upstream=up.meta(), rain_catchment=rn.meta())
    if not (up.ok and rn.ok):
        raise RuntimeError("upstream flows or catchment rain unavailable")
    today = pd.Timestamp(datetime.now(IST).date())
    Q = up.data.loc[:today].dropna()
    issue = Q.index[-1]
    Qx = Q.reindex(Q.index.union(rn.data.index))  # keep the forecast rain of the days after the issue day
    out = {}
    for L, (m, cols) in models.items():
        p = fm.predict(m, cols, Qx, rn.data, L, future_rain=True)
        out[str((issue + pd.Timedelta(days=L)).date())] = round(float(p.loc[issue]))
    return dict(issued=str(issue.date()), naraj_m3s=out, note="gradient boosting on upstream GloFAS flows and "
                "ECMWF catchment rain; test-year NSE 0.99 / 0.94 / 0.89 at 1 / 2 / 3 days (forecast_summary.json)")


def model_forecast_past(cfg, issue):
    """The upstream-gauge forecast as it would have been made on a past day (rain of the next days as forecast perfectly)."""
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mahanadi"))
    import forecast_model as fm
    data = os.path.join(HERE, "data", cfg["key"])
    Qh = pd.read_csv(os.path.join(data, "discharge.csv"), index_col="date", parse_dates=True)[list(fm.GAUGES)].dropna()
    Rh = pd.read_csv(os.path.join(data, "rain_catchment.csv"), index_col="date", parse_dates=True)["rain_mm"]
    out = {}
    for L in fm.LEADS:  # trained without the year of the replay, so the forecast has not seen this flood
        m, cols = fm.fit(Qh, Rh, L, future_rain=True, years=(1997, issue.year - 1))
        Qx = Qh.loc[:issue].reindex(Qh.loc[:issue].index.union(Rh.loc[issue:issue + pd.Timedelta(days=L)].index))
        out[str((issue + pd.Timedelta(days=L)).date())] = round(float(fm.predict(m, cols, Qx, Rh, L, future_rain=True).loc[issue]))
    return dict(issued=str(issue.date()), naraj_m3s=out, note="gradient boosting on the upstream flows and ERA5 catchment "
                f"rain, trained on 1997-{issue.year - 1} (without the year replayed)")


def radar_check(cfg, curve, day0, last):
    """Radar passes between the issue day and the end of the window: observed flooded land against the land the
    flow-impact table expects at the flow of that pass (Mahanadi atlas passes)."""
    path = os.path.join(os.path.dirname(HERE), "results", "atlas", "atlas_passes.csv") if cfg["key"] == "mahanadi" else \
        os.path.join(os.path.dirname(HERE), "results", "basins", cfg["key"], "atlas", "atlas_passes.csv")
    if not os.path.exists(path):
        return []
    ps = pd.read_csv(path, parse_dates=["date"])
    ps = ps[(ps.date >= day0) & (ps.date <= last)]
    return [dict(date=str(r.date.date()), coverage=round(float(r.coverage), 2), flow_m3s=round(float(r.q)),
                 observed_km2=round(float(r.flood_km2), 1),
                 expected_km2=round(float(impact_rows(curve, r.q)["flooded_km2"].iloc[0]), 1)) for r in ps.itertuples()]


def run_basin(key, out, horizon, use_model, replay=None):
    cfg, T = load(key)
    curve = T["impact_curve"]
    feeds, status = {}, dict(basin=key, name=cfg["name"], river=cfg["river"], gauge=cfg["gauge_name"],
                             issued=datetime.now(IST).replace(microsecond=0).isoformat())
    if replay:  # the flows that came, as a perfect single-run forecast issued at 06:00 IST that day
        today = pd.Timestamp(replay)
        hist = pd.read_csv(os.path.join(HERE, "data", key, "discharge.csv"), index_col="date", parse_dates=True)[cfg["gauge"]]
        runs = hist.loc[today - pd.Timedelta(days=10):today + pd.Timedelta(days=29)].to_frame("control")
        status.update(issued=f"{today.date()}T06:00:00+05:30", replay=True)
    else:
        g = PLUGINS["glofas"](cfg)
        feeds["glofas"] = g.meta()
        if not g.ok:
            raise SystemExit(f"{key}: no river-flow forecast ({g.error})")
        runs = g.data.dropna(how="all")
        today = pd.Timestamp(datetime.now(IST).date())
    Qm = runs.apply(lambda s: measure(s, cfg))
    fc = Qm.loc[today:]
    days = fc.index
    stats = pd.DataFrame(dict(median=fc.median(axis=1), p10=fc.quantile(0.1, axis=1), p90=fc.quantile(0.9, axis=1),
                              control=fc.get("control")), index=days)
    base, q_base = cfg.get("baseline"), cfg.get("baseline_m3s", 0)  # what the ordinary monsoon already floods or cuts
    lv = np.stack([[level_of(r, base) for r in impact_rows(curve, fc[c].values).to_dict("records")] for c in fc.columns], axis=1)
    med_rows = impact_rows(curve, stats["median"].values)
    p90_rows = impact_rows(curve, stats["p90"].values)
    stats["level"] = [level_of(r, base) for r in med_rows.to_dict("records")]
    for k in (1, 2, 3):
        stats[f"p_level{k}"] = (lv >= k).mean(axis=1).round(2)
    for c in ("flooded_km2", "people", "settlements_10pct", "hospital_people_cut_off"):
        if c in med_rows:
            stats[f"{c}_median"], stats[f"{c}_p90"] = med_rows[c].values, p90_rows[c].values
    os.makedirs(os.path.join(out, key), exist_ok=True)
    stats.round(1).rename_axis("date").to_csv(os.path.join(out, key, "forecast.csv"))

    win = stats.iloc[:horizon]
    peak = win["median"].idxmax()
    peak90 = win["p90"].idxmax()
    lvl = int(win.level.max())
    status.update(
        horizon_days=horizon, level=lvl, level_name=LEVELS[lvl]["name"],
        level_possible=int(max([k for k in (1, 2, 3) if win[f"p_level{k}"].max() >= 0.2] or [0])),
        peak=dict(date=str(peak.date()), median_m3s=round(win["median"].max()), p90_m3s=round(win["p90"].max()),
                  p90_date=str(peak90.date()), lakh_cusec=round(win["median"].max() / 2831.7, 2)),
        today_m3s=round(float(stats["median"].iloc[0])), design_flows_m3s=cfg["design_flows_m3s"],
        level_flows_m3s=cfg["level_flows_m3s"], largest_seen_m3s=cfg["largest_seen_m3s"],
        beyond_record=bool(win["p90"].max() > cfg["largest_seen_m3s"]),
        impact_at_peak={c: float(impact_rows(curve, win["median"].max())[c].iloc[0]) for c in curve.columns if c != "q_m3s"},
        impact_at_peak_p90={c: float(impact_rows(curve, win["p90"].max())[c].iloc[0]) for c in curve.columns if c != "q_m3s"},
        days=[dict(date=str(d.date()), median_m3s=round(r["median"]), p10_m3s=round(r.p10), p90_m3s=round(r.p90),
                   level=int(r.level), p_level=[r.p_level1, r.p_level2, r.p_level3]) for d, r in stats.iterrows()])
    qm, q9 = win["median"].values, win["p90"].values
    dd = win.index
    st = T["settlement_thresholds"]
    warn = []
    for _, r in st[st.q_flood10.notna() & (st.q_flood10 > q_base) & (st.q_flood10 <= q9.max())].iterrows():
        warn.append(dict(name=r["name"], lat=r.lat, lon=r.lon, pop=int(r["pop"]), flow_10pct=round(r.q_flood10),
                         expected=first_day(dd, qm, r.q_flood10), possible=first_day(dd, q9, r.q_flood10)))
    status["villages_to_warn"] = sorted(warn, key=lambda w: (w["expected"] is None, w["flow_10pct"]))
    cut = []
    if "q_cut_hospital" in st:
        for _, r in st[st.q_cut_hospital.notna() & (st.q_cut_hospital > q_base) & (st.q_cut_hospital <= q9.max())].iterrows():
            cut.append(dict(name=r["name"], lat=r.lat, lon=r.lon, pop=int(r["pop"]), flow=round(r.q_cut_hospital),
                            expected=first_day(dd, qm, r.q_cut_hospital), possible=first_day(dd, q9, r.q_cut_hospital)))
    status["hospital_access_lost"] = sorted(cut, key=lambda w: (w["expected"] is None, w["flow"]))
    if "road_cut_flows" in T:
        rd = T["road_cut_flows"]
        rd = rd[rd.cut_flow > q_base]  # stretches under water at ordinary monsoon flows (ferry ghats, river-bed tracks) are not news
        named = rd[(rd.cut_flow <= q9.max()) & (rd["name"].notna() | rd["ref"].notna())]
        status["roads_closing"] = [dict(road=r["name"] if isinstance(r["name"], str) else r["ref"], highway=r.highway,
                                        flow=int(r.cut_flow), expected=first_day(dd, qm, r.cut_flow),
                                        possible=first_day(dd, q9, r.cut_flow), lat=r.lat, lon=r.lon)
                                   for _, r in named.head(15).iterrows()]
        status["road_segments_closing"] = int((rd.cut_flow <= q9.max()).sum())
    if "facility_thresholds" in T:
        fac = T["facility_thresholds"]
        f = fac[(fac.kind == "health") & (fac.q_flood60m > q_base) & (fac.q_flood60m <= q9.max())]
        status["health_facilities_at_risk"] = [dict(name=r["name"] if isinstance(r["name"], str) else "health facility",
                                                    flow=round(r.q_flood60m), expected=first_day(dd, qm, r.q_flood60m),
                                                    lat=r.lat, lon=r.lon) for _, r in f.iterrows()]

    for name in () if replay else ("rain", "sachet", "cwc", "sentinel1"):
        f = PLUGINS[name](cfg)
        feeds[name] = f.meta()
        if not f.ok:
            continue
        if name == "rain":
            r_ = f.data.loc[today:]
            status["rain"] = dict(model=f.data.attrs.get("model"), next_3d_mm=round(float(r_.iloc[:3].sum()), 1),
                                  next_7d_mm=round(float(r_.iloc[:7].sum()), 1),
                                  daily=[dict(date=str(d.date()), mm=round(float(v), 1)) for d, v in r_.iloc[:10].items()])
        elif name == "sachet":
            rel = []
            for a_ in f.data:  # the SDMA re-issues IMD's text with small edits: keep one of each
                t_ = " ".join((a_.get("headline") or a_["title"]).lower().split())
                if (a_["districts"] or a_["river"]) and not any(
                        SequenceMatcher(None, t_, " ".join((k_.get("headline") or k_["title"]).lower().split())).ratio() > 0.85 for k_ in rel):
                    rel.append(a_)
            # the basin's own districts first (river and flood alerts, then weather), then river alerts elsewhere in the state
            rel.sort(key=lambda a_: (not a_["districts"], not a_["river"]))
            status["official_alerts"] = rel[:8]
            status["official_alerts_total"] = len(f.data)
        elif name == "cwc":
            status["cwc_above_warning"] = dict(stations=len(f.data), by_status=pd.Series([x["status"] for x in f.data]).value_counts().to_dict())
        elif name == "sentinel1":
            status["latest_radar_passes"] = f.data[:3]
    if replay:
        status["radar_check"] = radar_check(cfg, curve, today, today + pd.Timedelta(days=horizon))
    if use_model and cfg.get("forecast_model"):
        try:
            status["model_forecast"] = model_forecast_past(cfg, today) if replay else model_forecast(cfg, feeds)
        except Exception as ex:
            status["model_forecast"] = dict(error=f"{type(ex).__name__}: {str(ex)[:160]}")
    status["sources"] = feeds
    status["note"] = ("Student prototype (IIT Bombay CE IDP with ClimMaTech), not an official warning. Flood extents from the "
                      "Sentinel-1 atlas 2017-2026; flows above the largest seen give lower bounds.")
    json.dump(status, open(os.path.join(out, key, "status.json"), "w"), indent=1, default=str)
    write_bulletin(status, cfg, os.path.join(out, key))
    write_outlook_png(status, os.path.join(out, key, "outlook.png"))
    if lvl >= 1:
        write_cap(status, cfg, os.path.join(out, key, "alert.cap.xml"))
    elif os.path.exists(os.path.join(out, key, "alert.cap.xml")):
        os.remove(os.path.join(out, key, "alert.cap.xml"))
    print(f"{key}: level {lvl} ({LEVELS[lvl]['name']}), peak {status['peak']['median_m3s']:,} m3/s on {status['peak']['date']} "
          f"(90th pct {status['peak']['p90_m3s']:,}); villages to warn {len(warn)}; official alerts "
          f"{len(status.get('official_alerts', []))}", flush=True)
    return status


def write_outlook_png(s, path):
    """The 30-day outlook as a figure for reports and slides (skipped without matplotlib)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    d = pd.DataFrame(s["days"])
    t = pd.to_datetime(d.date)
    fig, ax = plt.subplots(figsize=(9, 3.4))
    if not s.get("replay"):
        ax.fill_between(t, d.p10_m3s, d.p90_m3s, color="#0c9ce4", alpha=0.18, lw=0, label="10-90 % of the 51 runs")
    ax.plot(t, d.median_m3s, color="#0c3c6c", lw=2, label="flow that came (replay)" if s.get("replay") else "median run")
    top = max(d.p90_m3s.max() * 1.15, (s["level_flows_m3s"].get("1") or 0) * 1.1)
    for k, q in s["level_flows_m3s"].items():
        if q and q <= top:
            ax.axhline(q, color=LEVELS[int(k)]["color"], ls="--", lw=1.3)
            ax.text(t.iloc[-1], q, f" {LEVELS[int(k)]['name']} ({q:,.0f})", va="bottom", ha="right", fontsize=8)
    ax.set_ylim(0, top)
    ax.set_ylabel(f"{s['gauge']} flow (m³/s)")
    ax.set_title(f"{s['name']}: " + (f"replay of {s['issued'][:10]}" if s.get("replay") else f"GloFAS outlook issued {s['issued'][:10]}")
                 + f", level '{s['level_name']}'", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def write_bulletin(s, cfg, d):
    pk, imp = s["peak"], s["impact_at_peak"]
    lines = [f"{cfg['name'].upper()} - FLOOD OUTLOOK issued {s['issued']} (next {s['horizon_days']} days)",
             f"Level: {s['level_name']} (" + ("replay: the flows that came, as a perfect forecast" if s.get("replay") else "median of 51 GloFAS runs") + ")" + (f"; up to '{LEVELS[s['level_possible']]['name']}' in at least 20 % of runs"
                                                                      if s["level_possible"] > s["level"] else ""),
             f"{cfg['gauge_name']} flow (the measure the atlas uses): today {s['today_m3s']:,} m3/s; peak {pk['median_m3s']:,} m3/s "
             f"on {pk['date']} (90th percentile {pk['p90_m3s']:,} m3/s)",
             f"At the median peak: {imp['flooded_km2']:.0f} km2 of land outside the river under water, about "
             f"{int(imp['people']):,} people on it" + (f", {int(imp.get('hospital_people_cut_off', 0)):,} cut off from every hospital"
                                                       if imp.get("hospital_people_cut_off") else "")]
    exp = [w for w in s["villages_to_warn"] if w["expected"]]
    pos = [w for w in s["villages_to_warn"] if not w["expected"] and w["possible"]]
    if exp:
        lines.append("Villages with >= 10 % of people on flooded land, expected: " +
                     "; ".join(f"{w['name']} from {w['expected']}" for w in exp[:12]))
    if pos:
        lines.append(f"Possible in the wettest runs: {len(pos)} more villages")
    if s.get("hospital_access_lost"):
        lines.append("Losing road access to every hospital (expected / possible): " +
                     "; ".join(f"{w['name']} ({w['expected'] or 'possible ' + str(w['possible'])})" for w in s["hospital_access_lost"][:8]))
    if s.get("roads_closing"):
        lines.append("Named roads going under water (beyond the ordinary monsoon): " + "; ".join(f"{r['road']} from {r['flow']:,} m3/s" for r in s["roads_closing"][:6]))
    if s.get("rain"):
        lines.append(f"Rain over the mapped area (ECMWF): {s['rain']['next_3d_mm']} mm in 3 days, {s['rain']['next_7d_mm']} mm in 7 days")
    if s.get("model_forecast", {}).get("naraj_m3s"):
        lines.append("Upstream-gauge model, daily Naraj flow: " + ", ".join(f"{d} {q:,} m3/s" for d, q in s["model_forecast"]["naraj_m3s"].items()))
    for a in s.get("official_alerts", [])[:4]:
        lines.append(f"Official ({a.get('sender') or a['author']}): {a.get('headline') or a['title']}")
    lines.append(s["note"])
    open(os.path.join(d, "bulletin.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_cap(s, cfg, path, radius_km=1.5):
    lv = LEVELS[s["level"]]
    pk = s["peak"]
    sure = max(d["p_level"][s["level"] - 1] for d in s["days"][:s["horizon_days"]])
    lead = (pd.Timestamp(pk["date"]) - pd.Timestamp(s["issued"][:10])).days
    areas = "".join(f"<area><areaDesc>{escape(str(w['name']))}: {w['pop']:,} people, flooding from {w['expected']}</areaDesc>"
                    f"<circle>{w['lat']:.4f},{w['lon']:.4f} {radius_km}</circle></area>"
                    for w in s["villages_to_warn"] if w["expected"])[:200000]
    if not areas:
        W, S, E, N = cfg["bbox"]
        areas = (f"<area><areaDesc>{escape(cfg['name'])}</areaDesc>"
                 f"<polygon>{S},{W} {N},{W} {N},{E} {S},{E} {S},{W}</polygon></area>")
    cap = ('<?xml version="1.0" encoding="UTF-8"?>\n<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">'
           f"<identifier>prithvi-flood-in-{s['basin']}-{s['issued'][:19].replace(':', '')}</identifier>"
           f"<sender>prithvi-flood-in.iitb.prototype</sender><sent>{s['issued']}</sent><status>Exercise</status>"
           "<msgType>Alert</msgType><scope>Public</scope><info><language>en-IN</language><category>Met</category>"
           f"<event>River flood</event><urgency>{'Immediate' if lead <= 1 else 'Expected' if lead <= 3 else 'Future'}</urgency>"
           f"<severity>{lv['cap']}</severity><certainty>{'Likely' if sure >= 0.5 else 'Possible'}</certainty>"
           f"<onset>{pk['date']}T00:00:00+05:30</onset>"
           f"<headline>{escape(cfg['name'])}: {lv['name']} - {cfg['gauge_name']} flow peaking near {pk['median_m3s']:,} m3/s on {pk['date']}</headline>"
           f"<description>{escape(open(os.path.join(os.path.dirname(path), 'bulletin.txt'), encoding='utf-8').read())}</description>"
           "<instruction>Follow the district administration; keep off flooded roads; move livestock and grain to high ground.</instruction>"
           f"<parameter><valueName>peak_flow_m3s</valueName><value>{pk['median_m3s']}</value></parameter>"
           f"<parameter><valueName>people_on_flooded_land</valueName><value>{int(s['impact_at_peak']['people'])}</value></parameter>"
           f"{areas}</info></alert>\n")
    open(path, "w", encoding="utf-8").write(cap)


def write_feed(statuses, out):
    now = datetime.now(IST).replace(microsecond=0).isoformat()
    entries = []
    for s in statuses:
        pk = s["peak"]
        link = f"{s['basin']}/alert.cap.xml" if s["level"] >= 1 else f"{s['basin']}/status.json"
        entries.append(f"<entry><id>urn:prithvi-flood-in:{s['basin']}:{s['issued']}</id>"
                       f"<title>{escape(s['name'])}: {LEVELS[s['level']]['name']}</title><updated>{s['issued']}</updated>"
                       f"<link rel=\"alternate\" type=\"{'application/cap+xml' if s['level'] >= 1 else 'application/json'}\" href=\"{link}\"/>"
                       f"<summary>{escape(s['gauge'])} flow peaking near {pk['median_m3s']:,} m3/s on {pk['date']}; "
                       f"about {int(s['impact_at_peak']['people']):,} people on flooded land at the median peak.</summary></entry>")
    feed = ('<?xml version="1.0" encoding="UTF-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">'
            "<id>urn:prithvi-flood-in:feed</id><title>Prithvi Flood-IN: impact-based flood outlooks (prototype)</title>"
            f"<updated>{now}</updated><author><name>Prithvi Flood-IN, IIT Bombay CE IDP</name></author>"
            + "".join(entries) + "</feed>\n")
    open(os.path.join(out, "feed.atom"), "w", encoding="utf-8").write(feed)


def write_board(statuses, out):
    """A standalone status board (no scripts): one card per basin with the 30-day hydrograph."""
    cards = []
    for s in statuses:
        lv = LEVELS[s["level"]]
        d = s["days"]
        n = len(d)
        top = max(max(x["p90_m3s"] for x in d), (s["level_flows_m3s"].get("3") or 0) * 1.05, 1)
        X = lambda i: 40 + i * 600 / max(n - 1, 1)  # noqa: E731
        Y = lambda q: 190 - q / top * 170  # noqa: E731
        band = " ".join(f"{X(i):.1f},{Y(x['p90_m3s']):.1f}" for i, x in enumerate(d)) + " " + \
               " ".join(f"{X(i):.1f},{Y(x['p10_m3s']):.1f}" for i, x in reversed(list(enumerate(d))))
        line = " ".join(f"{X(i):.1f},{Y(x['median_m3s']):.1f}" for i, x in enumerate(d))
        thr = "".join(f'<line x1="40" x2="640" y1="{Y(q):.1f}" y2="{Y(q):.1f}" stroke="{LEVELS[int(k)]["color"]}" stroke-dasharray="4 4"/>'
                      f'<text x="644" y="{Y(q) + 4:.1f}" font-size="11" fill="#555">{LEVELS[int(k)]["name"]}</text>'
                      for k, q in s["level_flows_m3s"].items() if q and q < top)
        ticks = "".join(f'<text x="{X(i):.1f}" y="208" font-size="10" fill="#555" text-anchor="middle">{x["date"][5:]}</text>'
                        for i, x in enumerate(d) if i % 5 == 0)
        svg = (f'<svg viewBox="0 0 760 215" role="img" aria-label="{html.escape(s["gauge"])} flow forecast">'
               f'<polygon points="{band}" fill="#0c9ce4" opacity="0.18"/><polyline points="{line}" fill="none" stroke="#0c3c6c" stroke-width="2"/>'
               f'{thr}{ticks}<text x="40" y="12" font-size="11" fill="#555">{html.escape(s["gauge"])} flow, m³/s (line: median of 51 runs; band: 10–90 %)</text></svg>')
        vill = "".join(f"<li>{html.escape(str(w['name']))} · {w['pop']:,} people · from {w['expected'] or 'possible ' + str(w['possible'])}</li>"
                       for w in s["villages_to_warn"][:8]) or "<li>None expected in the next days.</li>"
        offi = "".join(f"<li>{html.escape(a.get('headline') or a['title'])} <span>({html.escape(a.get('sender') or a['author'])})</span></li>"
                       for a in s.get("official_alerts", [])[:4]) or "<li>No river or district alert in the state feed.</li>"
        cards.append(f'<section class="card"><header><h2>{html.escape(s["name"])}</h2><span class="lv" style="background:{lv["color"]}">'
                     f'{lv["name"]}</span></header><p class="k">Peak <b>{s["peak"]["median_m3s"]:,} m³/s</b> on {s["peak"]["date"]} '
                     f'(90 %: {s["peak"]["p90_m3s"]:,}) · about <b>{int(s["impact_at_peak"]["people"]):,}</b> people on flooded land at the peak</p>'
                     f'{svg}<div class="cols"><div><h3>Villages to warn</h3><ul>{vill}</ul></div><div><h3>Official alerts (NDMA SACHET)</h3>'
                     f'<ul>{offi}</ul></div></div></section>')
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Flood outlook board</title><style>body{margin:0;background:#f9fafb;color:#000;font:15px/1.5 Inter,system-ui,sans-serif}'
            'main{max-width:900px;margin:0 auto;padding:24px 16px}h1{font-size:26px;margin:0 0 4px}.sub{color:#555;margin:0 0 20px}'
            '.card{background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:18px;margin:0 0 18px}header{display:flex;'
            'justify-content:space-between;align-items:center;gap:12px}h2{margin:0;font-size:19px}.lv{color:#fff;border-radius:999px;'
            'padding:4px 12px;font-weight:600;font-size:13px}.k{color:#333}svg{width:100%;height:auto}.cols{display:grid;'
            'grid-template-columns:1fr 1fr;gap:16px}h3{font-size:14px;margin:8px 0 4px}ul{margin:0;padding-left:18px;color:#333}'
            'li span{color:#777}@media(max-width:640px){.cols{grid-template-columns:1fr}}</style></head><body><main>'
            f'<h1>Flood outlook</h1><p class="sub">Issued {datetime.now(IST):%d %b %Y %H:%M} IST from the GloFAS ensemble, the Sentinel-1 '
            'flood atlas and official alerts. Student prototype, not an official warning.</p>' + "".join(cards) + "</main></body></html>")
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basin", nargs="*", help="basin keys (default: every live/basins/*.json)")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--horizon", type=int, default=10, help="days ahead that count for the warning level")
    ap.add_argument("--no-model", action="store_true", help="skip the data-driven Naraj forecast")
    ap.add_argument("--replay", help="a past date (YYYY-MM-DD): the feed as it would have run that morning")
    a = ap.parse_args()
    keys = a.basin or sorted(f[:-5] for f in os.listdir(os.path.join(HERE, "basins")) if f.endswith(".json"))
    if a.replay:
        a.out = os.path.join(a.out, f"replay_{a.replay}")
        keys = [k for k in keys if os.path.exists(os.path.join(HERE, "data", k, "discharge.csv"))]
    os.makedirs(a.out, exist_ok=True)
    statuses = [run_basin(k, a.out, a.horizon, not a.no_model, a.replay) for k in keys]
    write_feed(statuses, a.out)
    write_board(statuses, a.out)
    print("LIVE_DONE", os.path.join(a.out, "index.html"))


if __name__ == "__main__":
    main()
