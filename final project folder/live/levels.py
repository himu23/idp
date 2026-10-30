"""Impact-based warning levels: what a forecast flow does on the ground decides the level, not the flow itself.

The rule reads one row of a basin's impact_curve.csv (the flood at one flow):
  3  Act now        >= 25,000 people on flooded land, or >= 20,000 people cut off from every hospital
  2  Be prepared    >= 10,000 people on flooded land, or any settlement cut off from every hospital
  1  Be aware       >= 5,000 people on flooded land, or >= 3 settlements with >= 10 % of their people on flooded land
  0  No flood impact
Villages and hospital cut-offs count beyond the ordinary monsoon: what is already wet or cut at the flow exceeded on a
quarter of monsoon days (`baseline`, from make_basin_config.py) belongs to the season, not to a flood. On the Brahmani a
road without a mapped bridge cuts six villages off at almost any monsoon flow; that is a road to raise, not a warning.
Hospital access counts only where the basin has the routing graph. The thresholds are a starting point for the partner
and the district administration to set, as in impact-based forecasting (WMO-No. 1150). On the Mahanadi they start at
about 12,250, 18,500 and 21,250 m3/s at Naraj: a few river-bank hamlets get wet at ordinary monsoon flows, so a single
settlement does not raise a warning.
"""
LEVELS = [
    dict(level=0, name="No flood impact", color="#16a34a", cap=None),
    dict(level=1, name="Be aware", color="#eab308", cap="Moderate"),
    dict(level=2, name="Be prepared", color="#f08714", cap="Severe"),
    dict(level=3, name="Act now", color="#b91c1c", cap="Extreme"),
]
ABOVE_BASELINE = ("settlements_10pct", "hospital_people_cut_off", "hospital_settlements_cut_off")


def level_of(row, base=None):
    rec = row if isinstance(row, dict) else row._asdict() if hasattr(row, "_asdict") else dict(row)
    get = lambda k: max(float(rec.get(k, 0) or 0) - (float((base or {}).get(k, 0) or 0) if k in ABOVE_BASELINE else 0), 0)  # noqa: E731
    people, sett = get("people"), get("settlements_10pct")
    cut_people, cut_sett = get("hospital_people_cut_off"), get("hospital_settlements_cut_off")
    if people >= 25000 or cut_people >= 20000:
        return 3
    if people >= 10000 or cut_sett >= 1:
        return 2
    if people >= 5000 or sett >= 3:
        return 1
    return 0


def level_flows(curve, base=None):
    """The lowest flow of the curve at which each level starts (None if the curve never reaches it)."""
    out = {}
    for rec in curve.to_dict("records"):
        k = level_of(rec, base)
        for j in range(1, k + 1):
            out.setdefault(j, rec["q_m3s"])
    return {j: out.get(j) for j in (1, 2, 3)}


def baseline(curve, q):
    """The impacts of the ordinary monsoon: the curve row at flow q (the largest tabulated flow <= q)."""
    rows = curve[curve.q_m3s <= q]
    rec = (rows.iloc[-1] if len(rows) else curve.iloc[0]).to_dict()
    return {k: float(rec.get(k, 0) or 0) for k in ABOVE_BASELINE if k in rec}
