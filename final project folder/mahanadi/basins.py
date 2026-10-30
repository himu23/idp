"""Areas the atlas pipeline knows: one entry per river delta or floodplain.

Every script that used to hard-code the Mahanadi box reads its settings from here with --basin <key>
(default "mahanadi", so the original commands are unchanged).

bbox        lon/lat box (W, S, E, N) of the radar archive and of every context layer
gauge       column of discharge.csv that the trigger map is fitted on (the flow a forecast is issued for)
gauges      GloFAS v4 cells (lat, lon) read from the Open-Meteo flood API; each cell was checked to lie on the
            main river (largest mean flow in a 0.05 deg search window, 2015-2024)
rain_pts    ERA5 points averaged into the local-rain series
dry/wet     months of the dry-season passes (normal water) and of the flood season
pbf         Geofabrik India extract that covers the box (OSM layers when Overpass is down)
districts   districts whose official alerts (NDMA SACHET CAP feed) concern the box
"""

BASINS = {
    "mahanadi": dict(
        name="Mahanadi delta", state="Odisha", river="Mahanadi", gauge_name="Naraj",
        bbox=[85.80, 20.25, 86.45, 20.65], gauge="naraj",
        gauges={"naraj": (20.475, 85.775), "tikarpara": (20.58, 84.78), "hirakud_below": (21.50, 83.88)},
        rain_pts=[(20.35, 85.90), (20.35, 86.10), (20.35, 86.30), (20.55, 85.90), (20.55, 86.10), (20.55, 86.30)],
        dry=[2, 3], wet=[6, 7, 8, 9, 10, 11], pbf="eastern-zone",
        districts=["Cuttack", "Kendrapara", "Jagatsinghapur", "Jagatsinghpur", "Khordha", "Puri", "Jajapur", "Jajpur"],
        sachet="odisha"),
    "brahmani": dict(
        name="Brahmani–Baitarani delta", state="Odisha", river="Brahmani", gauge_name="Jenapur",
        bbox=[86.20, 20.58, 86.90, 21.08], gauge="jenapur",
        gauges={"jenapur": (20.825, 86.175), "akhuapada": (21.025, 86.175)},
        rain_pts=[(20.70, 86.35), (20.70, 86.60), (20.70, 86.80), (20.95, 86.35), (20.95, 86.60), (20.95, 86.80)],
        dry=[2, 3], wet=[6, 7, 8, 9, 10, 11], pbf="eastern-zone",
        districts=["Jajapur", "Jajpur", "Kendrapara", "Bhadrak", "Baleshwar", "Balasore"],
        sachet="odisha"),
    "brahmaputra": dict(
        name="Brahmaputra at Majuli", state="Assam", river="Brahmaputra", gauge_name="Neamatighat",
        bbox=[93.90, 26.70, 94.60, 27.30], gauge="neamatighat",
        gauges={"neamatighat": (26.925, 94.175)},
        rain_pts=[(26.85, 94.05), (26.85, 94.30), (26.85, 94.50), (27.15, 94.05), (27.15, 94.30), (27.15, 94.50)],
        dry=[2, 3], wet=[5, 6, 7, 8, 9, 10], pbf="north-eastern-zone",
        districts=["Majuli", "Jorhat", "Lakhimpur", "Dhemaji", "Sivasagar", "Golaghat"],
        sachet="assam"),
}


def get(key):
    return BASINS[key]
