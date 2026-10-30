"""Flood risk in rupees and person-days: what the floods cost, and what road raising and warnings are worth.

    ATLAS_DIR=runs/_atlas/build_r20 IMPACT_DIR=runs/_atlas/impact_r20 python mahanadi/risk_economics.py

Houses (structural): people on flooded land by depth (depth_T*.tif from impact_depth.py) times the JRC depth-damage
curve for residential buildings in Asia (Huizinga et al. 2017, JRC105688) gives damage in house-equivalents (one
household per HH_SIZE people), priced at the PMAY-G rural housing assistance of Rs 1.20 lakh per house: the public cost
of rebuilding, a lower bound of the private loss.
Crops: kharif paddy on flooded cropland (ESA WorldCover) at Odisha's rice yield of 2,081 kg/ha (RBI Handbook of
Statistics on Indian States, 2023-24) and the 2025-26 MSP of Rs 2,369 per quintal; the crop is lost where water is
>= 0.5 m deep and 30 % is lost where it is shallower (an assumption that the farmers' interviews of the field visit test).
Expected annual damage (EAD): trapezoid rule over annual exceedance probability from the 2- to the 100-year flood, plus
the 100-year damage for the rarer tail; above the largest flood seen the maps are lower bounds, so the EAD is too.
The daily record: every day of 1997-2025 at Naraj (the GloFAS series starts in 1997), as the 3-day peak flow, through impact_curve.csv gives person-days a
year on flooded land and without road access to any hospital, with and without the ten critical links raised, and the
days a year at each warning level of live/levels.py (how often a warning service would have spoken).
Road raising (construction management + transportation): the earthwork of cm_plan.json, annualised over 20 years at
10 %, against the hospital-access person-days it saves, each valued at the Odisha MGNREGA wage of Rs 254 (2024-25):
a conservative value that leaves out health outcomes.
Early warning: 24 hours of warning cuts flood damage by about 30 % (Global Commission on Adaptation, 2019).
Hirakud (water resources): people and hospital access saved per 1,000 m3/s taken off a 2-, 5- and 10-year peak.
Outputs in IMPACT_DIR: risk_economics.json, damage_by_scenario.csv, alert_days_per_year.csv
"""
import json
import os
import sys

import numpy as np
import pandas as pd

from impact_common import ATLAS, CTX, IMPACT, PIX_KM2, dump, read

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "live"))
from levels import baseline, level_of  # noqa: E402

DEPTH = [0, 0.5, 1, 1.5, 2, 3, 4, 5, 6]
JRC_ASIA_RESIDENTIAL = [0, 0.327, 0.493, 0.617, 0.72, 0.87, 0.93, 0.983, 1.0]
HH_SIZE = 4.4               # people per rural household (assumption, order of Census 2011 for Odisha)
HOUSE_RS = 1.20e5           # PMAY-G unit assistance, plain areas
PADDY_RS_PER_HA = 2.081 * 23690  # t/ha x Rs/t
SHALLOW_CROP_LOSS = 0.30
WAGE_RS_DAY = 254
LIFE_Y, RATE = 20, 0.10
WARNING_CUT = 0.30

AS = json.load(open(f"{ATLAS}/atlas_summary.json"))
RP = {int(k): v for k, v in AS["gumbel"]["return_period_m3s"].items()}
pop = np.nan_to_num(read(f"{CTX}/grid20_pop.tif").astype(np.float64))
crop = read(f"{CTX}/grid20_worldcover.tif") == 40

# ------------------------------------------------------------------ damage per design flood
rows = []
for T in sorted(RP):
    name = f"T{T}" if os.path.exists(f"{IMPACT}/depth_T{T}.tif") else "T25"  # T50 has the T25/T100 map (lower bound)
    dd = read(f"{IMPACT}/depth_{name}.tif")
    wet = dd != 255
    depth = np.where(wet, dd / 10.0, 0)
    frac = np.interp(depth, DEPTH, JRC_ASIA_RESIDENTIAL) * wet
    houses = float((pop * frac).sum() / HH_SIZE)
    crop_ha = float((crop & wet).sum() * PIX_KM2 * 100)
    crop_loss_ha = float(((crop & wet) * np.where(depth >= 0.5, 1.0, SHALLOW_CROP_LOSS)).sum() * PIX_KM2 * 100)
    rows.append(dict(T=T, flow_m3s=round(RP[T]), depth_map=name, people_on_flooded_land=round(float(pop[wet].sum())),
                     house_equivalents_damaged=round(houses), houses_rs_crore=round(houses * HOUSE_RS / 1e7, 2),
                     paddy_flooded_ha=round(crop_ha), paddy_lost_ha=round(crop_loss_ha),
                     paddy_rs_crore=round(crop_loss_ha * PADDY_RS_PER_HA / 1e7, 2)))
dmg = pd.DataFrame(rows)
dmg["total_rs_crore"] = dmg.houses_rs_crore + dmg.paddy_rs_crore
dmg.to_csv(f"{IMPACT}/damage_by_scenario.csv", index=False)


def ead(col):
    p = 1 / dmg["T"].values
    d = dmg[col].values
    return float(np.sum((d[:-1] + d[1:]) / 2 * (p[:-1] - p[1:])) + d[-1] * p[-1])


EAD = {c: round(ead(c), 2) for c in ("houses_rs_crore", "paddy_rs_crore", "total_rs_crore")}

# ------------------------------------------------------------------ the daily record through the impact curve
curve = pd.read_csv(f"{IMPACT}/impact_curve.csv")
Q = pd.read_csv(f"{CTX}/discharge.csv", index_col="date", parse_dates=True)["naraj"]
Q3 = Q.rolling(3).max()
Q3 = Q3[(Q3.index.year >= 1984) & (Q3.index.year <= 2025)].dropna()
i = np.clip(np.searchsorted(curve.q_m3s.values, Q3.values, side="right") - 1, 0, len(curve) - 1)
daily = curve.iloc[i].reset_index(drop=True)
daily.index = Q3.index
years = Q3.index.year.nunique()
per_year = {"person_days_on_flooded_land": float(daily.people.sum() / years)}
raised_saving = None
if "hospital_people_cut_off" in daily:
    per_year["person_days_without_hospital_access"] = float(daily.hospital_people_cut_off.sum() / years)
    per_year["person_days_without_hospital_access_links_raised"] = float(daily.hospital_people_cut_off_links_raised.sum() / years)
    raised_saving = per_year["person_days_without_hospital_access"] - per_year["person_days_without_hospital_access_links_raised"]
q_base = float(Q3[Q3.index.month.isin([6, 7, 8, 9, 10, 11])].quantile(0.75))  # the ordinary monsoon, as in live/levels.py
lv = pd.Series([level_of(r, baseline(curve, q_base)) for r in daily.to_dict("records")], index=daily.index)
alert = pd.DataFrame({f"days_level_{k}_or_more": (lv >= k).groupby(lv.index.year).sum() for k in (1, 2, 3)})
alert.rename_axis("year").to_csv(f"{IMPACT}/alert_days_per_year.csv")

# ------------------------------------------------------------------ road raising: benefit / cost
cm = json.load(open(f"{IMPACT}/cm_plan.json"))["link_raising"]
crf = RATE / (1 - (1 + RATE) ** -LIFE_Y)
cost_y = cm["cost_crore_rs_at_350_per_m3"] * 1e7 * crf
benefit_y = (raised_saving or 0) * WAGE_RS_DAY
road = dict(earthwork_m3=cm["earthwork_m3"], cost_rs_crore=cm["cost_crore_rs_at_350_per_m3"], life_years=LIFE_Y,
            discount_rate=RATE, annual_cost_rs_lakh=round(cost_y / 1e5, 1),
            person_days_saved_per_year=round(raised_saving or 0),
            annual_benefit_rs_lakh=round(benefit_y / 1e5, 1), benefit_cost_ratio=round(benefit_y / cost_y, 2) if cost_y else None)

# ------------------------------------------------------------------ Hirakud: 1,000 m3/s off the peak
def at(q, c):
    j = int(np.clip(np.searchsorted(curve.q_m3s.values, q, side="right") - 1, 0, len(curve) - 1))
    return float(curve[c].iloc[j]) if c in curve else None


hirakud = {f"T{T}": dict(flow_m3s=round(RP[T]),
                         people_saved=round(at(RP[T], "people") - at(RP[T] - 1000, "people")),
                         hospital_access_saved=(round(at(RP[T], "hospital_people_cut_off") - at(RP[T] - 1000, "hospital_people_cut_off"))
                                                if "hospital_people_cut_off" in curve else None),
                         flooded_km2_saved=round(at(RP[T], "flooded_km2") - at(RP[T] - 1000, "flooded_km2"), 1))
           for T in (2, 5, 10)}

out = dict(parameters=dict(depth_damage="JRC residential, Asia (Huizinga et al. 2017)", depth_m=DEPTH,
                           damage_fraction=JRC_ASIA_RESIDENTIAL, people_per_household=HH_SIZE, house_rs=HOUSE_RS,
                           paddy_rs_per_ha=round(PADDY_RS_PER_HA), shallow_crop_loss=SHALLOW_CROP_LOSS,
                           wage_rs_per_day=WAGE_RS_DAY, warning_damage_cut=WARNING_CUT),
           damage_by_flood=dmg.to_dict("records"), expected_annual_damage_rs_crore=EAD,
           warning_saving_rs_crore_per_year=round(EAD["total_rs_crore"] * WARNING_CUT, 2),
           daily_record=dict(years=f"{Q3.index.year.min()}-{Q3.index.year.max()} ({years} years)", per_year={k: round(v) for k, v in per_year.items()},
                             mean_days_per_year_at_level={k: round(float(v.mean()), 1) for k, v in alert.items()},
                             years_with_any_level_3=int((alert["days_level_3_or_more"] > 0).sum())),
           road_raising=road, hirakud_1000_m3s_off_the_peak=hirakud)
dump(out, f"{IMPACT}/risk_economics.json")
print(json.dumps({k: out[k] for k in ("expected_annual_damage_rs_crore", "daily_record", "road_raising", "hirakud_1000_m3s_off_the_peak")}, indent=1))
print(dmg.to_string())
print("RISK_DONE")
