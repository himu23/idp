"""Live data sources for the flood warning feed, one plugin per source.

Each plugin takes a basin's settings (live/basins/<key>.json) and returns a Feed: ok, data, error, url, fetched.
A source that is down never stops the bulletin; it is reported as unavailable. Add a source by writing a function and
decorating it with @plugin("name"); run_live.py calls every registered plugin a basin lists under "sources".

glofas     GloFAS v4 river-flow forecast at the basin's gauge cell (Open-Meteo flood API): the control run and 50
           ensemble members, 7 past days and 30 days ahead; also the upstream gauges for the data-driven model
rain       ECMWF IFS 0.25 deg daily rain (Open-Meteo forecast API), mean of the basin's rain points, 7 past and 16 days
           ahead; also over the Mahanadi catchment for the data-driven model
sachet     official alerts (CAP) from NDMA's SACHET feed for the basin's state: IMD rain, CWC river and SDMA alerts,
           matched to the basin's districts
cwc        CWC flood-forecasting network: stations now above warning level (ffs.india-water.gov.in; answers from Indian
           networks only)
sentinel1  the latest Sentinel-1 pass over the box on Microsoft Planetary Computer (needs pystac-client)
No source needs a login or a key.
"""
import json
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import pandas as pd
import requests

UA = {"User-Agent": "Prithvi-Flood-IN live feed (IIT Bombay IDP prototype)"}
PLUGINS = {}
_NATIONAL = {}  # answers that are the same for every basin, fetched once per run


@dataclass
class Feed:
    name: str
    ok: bool = False
    data: object = None
    error: str = ""
    url: str = ""
    fetched: str = field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat())

    def meta(self):
        d = asdict(self)
        d.pop("data")
        return d


def plugin(name):
    def register(fn):
        def run(basin, **kw):
            f = Feed(name)
            try:
                f.data, f.url = fn(basin, **kw)
                f.ok = True
            except Exception as ex:  # a dead source is reported, never fatal
                f.error = f"{type(ex).__name__}: {str(ex)[:200]}"
            return f
        PLUGINS[name] = run
        return run
    return register


def get_json(url, params, tries=3, timeout=60):
    for k in range(tries):
        r = requests.get(url, params=params, headers=UA, timeout=timeout)
        if r.status_code == 429 or (r.ok and isinstance(r.json(), dict) and r.json().get("error")):
            time.sleep(20 * (k + 1))  # Open-Meteo's per-minute limit
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate-limited: {url}")


@plugin("glofas")
def glofas(basin, past_days=7, forecast_days=30, upstream=False):
    """DataFrame (date x run): 'control' and member01..member50 at the gauge cell; with upstream=True a dict of
    deterministic series for every gauge in the basin settings instead."""
    url = "https://flood-api.open-meteo.com/v1/flood"
    if upstream:
        out = {}
        for name, (lat, lon) in basin["gauges"].items():
            d = get_json(url, dict(latitude=lat, longitude=lon, daily="river_discharge", past_days=past_days,
                                   forecast_days=forecast_days))
            out[name] = pd.Series(d["daily"]["river_discharge"], index=pd.to_datetime(d["daily"]["time"]), dtype=float)
        return pd.DataFrame(out), url
    lat, lon = basin["gauges"][basin["gauge"]]
    d = get_json(url, dict(latitude=lat, longitude=lon, daily="river_discharge", past_days=past_days,
                           forecast_days=forecast_days, ensemble="true"))
    df = pd.DataFrame({k.replace("river_discharge_", "").replace("river_discharge", "control"): v
                       for k, v in d["daily"].items() if k != "time"}, index=pd.to_datetime(d["daily"]["time"]))
    df.attrs["cell"] = (d["latitude"], d["longitude"])
    return df.astype(float), url


@plugin("rain")
def rain(basin, points=None, past_days=7, forecast_days=16):
    """Series of daily rain (mm), mean over the points, ECMWF IFS 0.25 deg; the best available model if IFS is missing."""
    pts = points or basin["rain_pts"]
    url = "https://api.open-meteo.com/v1/forecast"
    base = dict(latitude=",".join(str(p[0]) for p in pts), longitude=",".join(str(p[1]) for p in pts),
                daily="precipitation_sum", past_days=past_days, forecast_days=forecast_days, timezone="Asia/Kolkata")
    for model in ("ecmwf_ifs025", "best_match"):
        d = get_json(url, dict(base, models=model))
        d = d if isinstance(d, list) else [d]
        s = pd.concat([pd.Series(x["daily"]["precipitation_sum"], index=pd.to_datetime(x["daily"]["time"]), dtype=float)
                       for x in d], axis=1).mean(axis=1)
        if s.notna().sum() > past_days:
            s.attrs["model"] = model
            return s.rename("rain_mm"), url
    raise RuntimeError("no rain forecast")


@plugin("sachet")
def sachet(basin, limit=40):
    """Official CAP alerts of the state feed; each with its headline, sender, category, time, link and the basin's
    districts it names (empty when it names none of them)."""
    url = f"https://sachet.ndma.gov.in/cap_public_website/rss/rss_{basin['sachet']}.xml"
    r = requests.get(url, headers=UA, timeout=40)
    r.raise_for_status()
    items = []
    for it in ET.fromstring(r.content).findall("./channel/item")[:limit]:
        title = (it.findtext("title") or "").strip()
        link = it.findtext("link") or ""
        detail = {}
        try:  # the CAP document carries the English headline and the area
            cap = ET.fromstring(requests.get(link, headers=UA, timeout=30).content)
            ns = {"c": "urn:oasis:names:tc:emergency:cap:1.2"}
            for k in ("event", "headline", "severity", "urgency", "certainty", "expires"):
                detail[k] = cap.findtext(f".//c:info/c:{k}", default="", namespaces=ns)
            detail["area"] = "; ".join(a.text or "" for a in cap.findall(".//c:info/c:area/c:areaDesc", ns))
            detail["sender"] = cap.findtext("c:sender", default="", namespaces=ns)
        except Exception:
            pass
        text = " ".join([title, detail.get("headline", ""), detail.get("area", "")]).lower()
        items.append(dict(title=title, category=it.findtext("category") or "", author=it.findtext("author") or "",
                          published=it.findtext("pubDate") or "", link=link, **detail,
                          districts=[d for d in basin["districts"] if d.lower() in text],
                          river=any(w in text for w in ("river", "flood", "water level", "बाढ़", "ବନ୍ୟା"))))
    return items, url


@plugin("cwc")
def cwc(basin):
    """CWC stations now above their warning level: code, status (WARNING / SEVERE / EXTREME), trend, level (m)."""
    url = "https://ffs.india-water.gov.in/eswis-gis/api/station-water-level-above-warning/"
    if url not in _NATIONAL:  # one national list per run, so every basin reports the same stations
        r = requests.get(url, headers=dict(UA, **{"class-name": "StationWaterLevelAboveWarningDto", "Accept": "application/json"}),
                         timeout=90)
        r.raise_for_status()
        _NATIONAL[url] = [dict(station=x.get("stationCode"), status=x.get("status"), trend=x.get("trend"), level_m=x.get("value"))
                          for x in r.json()]
    return list(_NATIONAL[url]), url


@plugin("sentinel1")
def sentinel1(basin, days=21):
    """Latest Sentinel-1 RTC passes over the box in the last `days` days (date, orbit direction, relative orbit)."""
    import pystac_client
    url = "https://planetarycomputer.microsoft.com/api/stac/v1"
    end = pd.Timestamp.utcnow().normalize() + pd.Timedelta(days=1)
    items = pystac_client.Client.open(url).search(collections=["sentinel-1-rtc"], bbox=basin["bbox"],
                                                  datetime=f"{(end - pd.Timedelta(days=days)).date()}/{end.date()}").items()
    passes = {}
    for it in items:
        p = it.properties
        passes[(it.datetime.strftime("%Y-%m-%d %H:%M"), p.get("sat:orbit_state"), p.get("sat:relative_orbit"))] = it.id
    rows = [dict(time_utc=k[0], orbit=k[1], relative_orbit=k[2], item=v) for k, v in sorted(passes.items(), reverse=True)]
    return rows, url


if __name__ == "__main__":
    import sys
    b = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "live/basins/mahanadi.json"))
    for name, run in PLUGINS.items():
        f = run(b)
        print(name, f.ok, f.error or (len(f.data) if hasattr(f.data, "__len__") else f.data))
