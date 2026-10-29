"""Sen1Floods11 data layer shared by every model in the project.

One cache, one split definition, one validity rule, one normalisation routine.
Every model reads chips through `FloodChips`, so differences in scores come
from the models, not from data handling.

Raw layout (Hugging Face copy blumenstiel/Sen1Floods11, v1.1):
    sen1floods11_v1.1/data/S2L1CHand/<chip>_S2Hand.tif     13 bands, TOA reflectance x 1e4 (int16)
    sen1floods11_v1.1/data/S1GRDHand/<chip>_S1Hand.tif     VV, VH backscatter in dB (float32)
    sen1floods11_v1.1/data/LabelHand/<chip>_LabelHand.tif  1 water, 0 dry, -1 unknown
    sen1floods11_v1.1/data/JRCWaterHand/<chip>_JRCWaterHand.tif  JRC permanent water
    sen1floods11_v1.1/splits/flood_{train,valid,test,bolivia}_data.txt
"""
import glob
import json
import os

import numpy as np
import torch
from torch.utils.data import Dataset

S2_BANDS = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"]
S1_BANDS = ["VV", "VH"]
ALL_BANDS = S2_BANDS + S1_BANDS          # channel order of the cached 15-band cube
CENTRAL_WAVELENGTH_UM = {                 # used by wavelength-aware models (DOFA, Clay)
    "B01": 0.443, "B02": 0.490, "B03": 0.560, "B04": 0.665, "B05": 0.705, "B06": 0.740,
    "B07": 0.783, "B08": 0.842, "B8A": 0.865, "B09": 0.945, "B10": 1.375, "B11": 1.610,
    "B12": 2.190, "VV": 5.405e4, "VH": 5.405e4,
}
# Pre-training statistics published with TerraMind (S2L1C, S1GRD) -- same values as the mentor notebook.
TERRAMIND_S2L1C_MEAN = [2357.089, 2137.385, 2018.788, 2082.986, 2295.651, 2854.537, 3122.849,
                        3040.560, 3306.481, 1473.847, 506.070, 2472.825, 1838.929]
TERRAMIND_S2L1C_STD = [1624.683, 1675.806, 1557.708, 1833.702, 1823.738, 1733.977, 1732.131,
                       1679.732, 1727.260, 1024.687, 442.165, 1331.411, 1160.419]
TERRAMIND_S1GRD_MEAN = [-12.599, -20.293]
TERRAMIND_S1GRD_STD = [5.195, 5.890]

RADAR_NODATA_DB = -80.0     # Sen1Floods11 marks missing radar with very low values


def chip_event(chip_id):
    """Sen1Floods11 chip ids start with the event name (one flood event per country prefix)."""
    return chip_id.split("_")[0]


def read_split(path):
    ids = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        stem = os.path.splitext(os.path.basename(line.split(",")[0].strip()))[0]
        for suffix in ("_S1Hand", "_S2Hand", "_LabelHand", "_S1GRDHand", "_S2L1CHand"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
        ids.append(stem)
    return ids


def build_cache(root, cache_dir):
    """Read every hand-labelled chip once into memory-mappable arrays (shared by all runs)."""
    import rasterio

    os.makedirs(cache_dir, exist_ok=True)
    data = os.path.join(root, "data")
    label_files = sorted(glob.glob(os.path.join(data, "LabelHand", "*_LabelHand.tif")))
    chips = [os.path.basename(f).replace("_LabelHand.tif", "") for f in label_files]
    n = len(chips)
    s2 = np.lib.format.open_memmap(os.path.join(cache_dir, "s2.npy"), "w+", np.int16, (n, 13, 512, 512))
    s1 = np.lib.format.open_memmap(os.path.join(cache_dir, "s1.npy"), "w+", np.float32, (n, 2, 512, 512))
    lab = np.lib.format.open_memmap(os.path.join(cache_dir, "label.npy"), "w+", np.int8, (n, 512, 512))
    jrc = np.lib.format.open_memmap(os.path.join(cache_dir, "jrc.npy"), "w+", np.uint8, (n, 512, 512))
    meta = []

    def one(folder, pattern):
        hits = glob.glob(os.path.join(data, folder, pattern))
        assert len(hits) == 1, (folder, pattern, hits)
        return hits[0]

    for i, c in enumerate(chips):
        with rasterio.open(one("S2L1CHand", f"{c}_S2*.tif")) as src:
            s2[i] = src.read()
        with rasterio.open(one("S1GRDHand", f"{c}_S1*.tif")) as src:
            s1[i] = src.read().astype(np.float32)
            bounds, crs = list(src.bounds), str(src.crs)
        with rasterio.open(label_files[i]) as src:
            lab[i] = src.read(1)
        jrc_hits = glob.glob(os.path.join(data, "JRCWaterHand", f"{c}_JRC*.tif"))
        if jrc_hits:
            with rasterio.open(jrc_hits[0]) as src:
                jrc[i] = (src.read(1) > 0).astype(np.uint8)
        meta.append({"chip": c, "event": chip_event(c), "bounds": bounds, "crs": crs})
    for a in (s2, s1, lab, jrc):
        a.flush()
    splits = {}
    for name, fn in [("train", "flood_train_data.txt"), ("val", "flood_valid_data.txt"),
                     ("test", "flood_test_data.txt"), ("bolivia", "flood_bolivia_data.txt")]:
        p = os.path.join(root, "splits", fn)
        splits[name] = read_split(p) if os.path.exists(p) else []
    json.dump({"chips": chips, "meta": meta, "splits": splits}, open(os.path.join(cache_dir, "index.json"), "w"))
    return chips


class ChipArray:
    """A cached .npy array read one chip at a time with plain file reads.

    `a[i]` (integer) returns a fresh copy of chip i via os.pread. On the shared lab server,
    page faults on memory-mapped files were ~100x slower than read() (kernel contention),
    so integer access avoids mmap; any other index falls back to the memory map.
    """

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            ver = np.lib.format.read_magic(f)
            hdr = np.lib.format.read_array_header_1_0 if ver == (1, 0) else np.lib.format.read_array_header_2_0
            self.shape, _, self.dtype = hdr(f)
            self.offset = f.tell()
        self.chip_bytes = int(np.prod(self.shape[1:])) * np.dtype(self.dtype).itemsize
        self._fd, self._mm = None, None

    def __len__(self):
        return self.shape[0]

    def __getitem__(self, i):
        if isinstance(i, (int, np.integer)):
            if self._fd is None or self._fd[0] != os.getpid():  # one descriptor per worker process
                self._fd = (os.getpid(), os.open(self.path, os.O_RDONLY))
            buf = os.pread(self._fd[1], self.chip_bytes, self.offset + int(i) * self.chip_bytes)
            return np.frombuffer(buf, dtype=self.dtype).reshape(self.shape[1:]).copy()
        if self._mm is None:
            self._mm = np.load(self.path, mmap_mode="r")
        return self._mm[i]


class Cache:
    """Chip-level access to the cached dataset plus split logic."""

    def __init__(self, cache_dir):
        self.dir = cache_dir
        idx = json.load(open(os.path.join(cache_dir, "index.json")))
        self.chips = idx["chips"]
        self.meta = idx["meta"]
        self.official = idx["splits"]
        self.pos = {c: i for i, c in enumerate(self.chips)}
        self.s2 = ChipArray(os.path.join(cache_dir, "s2.npy"))
        self.s1 = ChipArray(os.path.join(cache_dir, "s1.npy"))
        self.label = ChipArray(os.path.join(cache_dir, "label.npy"))
        self.jrc = ChipArray(os.path.join(cache_dir, "jrc.npy"))

    def split(self, protocol, name):
        """protocol 'official': Sen1Floods11 splits (events shared across splits).
        protocol 'lio' (leave-India-out): India removed from train/val, test = all 68 India chips,
        so the test flood (Assam, Aug 2016) is never seen in training."""
        if protocol == "official":
            return list(self.official[name])
        if protocol == "lio":
            if name == "test":
                return [c for c in self.chips if chip_event(c) == "India"]
            if name in ("train", "val"):
                return [c for c in self.official[name] if chip_event(c) != "India"]
            return list(self.official[name])
        raise ValueError(protocol)

    def channel_stats(self, chip_ids):
        """Per-band mean/std over valid pixels of the given chips (dataset statistics)."""
        idx = [self.pos[c] for c in chip_ids]
        rng = np.random.default_rng(0)
        means, stds = [], []
        for b in range(15):
            vals = []
            for i in idx:
                x = (self.s2[i][b] if b < 13 else self.s1[i][b - 13]).astype(np.float32)[::4, ::4]
                v = x[np.isfinite(x) & ((x > RADAR_NODATA_DB) if b >= 13 else (x > 0))]
                if v.size:
                    vals.append(rng.choice(v, min(v.size, 2000), replace=False))
            v = np.concatenate(vals)
            means.append(float(v.mean()))
            stds.append(float(v.std() + 1e-6))
        return means, stds


def validity(s2, s1):
    """Pixel validity per sensor (True = usable measurement)."""
    v2 = np.isfinite(s2).all(0) & (s2 > 0).any(0)
    v1 = np.isfinite(s1).all(0) & (s1 > RADAR_NODATA_DB).all(0)
    return v2, v1


class FloodChips(Dataset):
    """Returns (inputs, label, index).

    inputs: dict modality -> RAW tensor [C,512,512] ('S2L1C' int16 optical bands,
      'S1GRD' float32 VV/VH in dB). Standardisation happens on the GPU in `Normalizer`
      (cheap for the CPU data loaders); `load()` gives the same result on the CPU.
    Invalid measurements are replaced by the band mean *before* standardisation,
    so they become exactly 0 for every band (fixes the notebook's VH bug).
    label: long tensor [512,512] with 0 dry, 1 water, -1 ignore.
    """

    def __init__(self, cache, chip_ids, s2_bands, use_s1, mean, std, augment=False):
        self.c = cache
        self.ids = list(chip_ids)
        self.s2_idx = [S2_BANDS.index(b) for b in s2_bands]
        self.use_s1 = use_s1
        self.augment = augment
        bands = list(s2_bands) + (S1_BANDS if use_s1 else [])
        full_mean = dict(zip(ALL_BANDS, mean))
        full_std = dict(zip(ALL_BANDS, std))
        self.m2 = np.array([full_mean[b] for b in s2_bands], np.float32)[:, None, None]
        self.d2 = np.array([full_std[b] for b in s2_bands], np.float32)[:, None, None]
        self.m1 = np.array([full_mean[b] for b in S1_BANDS], np.float32)[:, None, None]
        self.d1 = np.array([full_std[b] for b in S1_BANDS], np.float32)[:, None, None]
        self.bands = bands

    def __len__(self):
        return len(self.ids)

    def load(self, k):
        i = self.c.pos[self.ids[k]]
        out = {}
        if self.s2_idx:
            s2 = self.c.s2[i][self.s2_idx].astype(np.float32)
            bad = ~np.isfinite(s2) | (s2 <= 0)
            s2 = np.where(bad, self.m2, s2)
            out["S2L1C"] = (s2 - self.m2) / self.d2
        if self.use_s1:
            s1 = self.c.s1[i].astype(np.float32)
            bad = ~np.isfinite(s1) | (s1 <= RADAR_NODATA_DB)
            s1 = np.where(bad, self.m1, s1)
            out["S1GRD"] = (s1 - self.m1) / self.d1
        y = self.c.label[i].astype(np.int64)
        return out, y

    def load_raw(self, k):
        # Copy the whole chip first (~2 ms); fancy-indexing the memmap directly is ~100x slower.
        i = self.c.pos[self.ids[k]]
        out = {}
        if self.s2_idx:
            s2 = self.c.s2[i]
            out["S2L1C"] = s2 if self.s2_idx == list(range(13)) else np.ascontiguousarray(s2[self.s2_idx])
        if self.use_s1:
            out["S1GRD"] = self.c.s1[i]
        return out, self.c.label[i].astype(np.int8)

    def __getitem__(self, k):
        # augmentation is applied on the GPU (gpu_d4): rotating on the CPU costs ~200 ms per chip
        x, y = self.load_raw(k)
        return {key: torch.from_numpy(v) for key, v in x.items()}, torch.from_numpy(y), k


def gpu_d4(x, y, gen):
    """Random element of the dihedral group D4 per sample, identical for inputs and label."""
    for b in range(y.shape[0]):
        r = int(torch.randint(4, (1,), generator=gen))
        f = bool(torch.rand(1, generator=gen) < 0.5)
        for key in x:
            t = torch.rot90(x[key][b], r, dims=(1, 2))
            x[key][b] = t.flip(2) if f else t.clone()
        t = torch.rot90(y[b], r, dims=(0, 1))
        y[b] = t.flip(1) if f else t.clone()
    return x, y


def radar_to_20m(s1):
    """[B,2,H,W] radar in dB -> the 20 m Sentinel-1 COG overview the atlas reads: 2 x 2 average in linear power
    (invalid pixels left out), bilinear back to 10 m, dB again. Blocks with no valid pixel stay invalid (NaN)."""
    bad = ~torch.isfinite(s1) | (s1 <= RADAR_NODATA_DB)
    lin = torch.where(bad, torch.zeros_like(s1), torch.pow(10.0, s1 / 10.0))
    num = torch.nn.functional.avg_pool2d(lin, 2)
    den = torch.nn.functional.avg_pool2d((~bad).float(), 2)
    avg = torch.where(den > 0, num / den.clamp_min(1e-6), torch.full_like(num, float("nan")))
    up = torch.nn.functional.interpolate(avg, scale_factor=2, mode="bilinear", align_corners=False)
    out = 10.0 * torch.log10(up.clamp_min(1e-6))
    return torch.where(bad | ~torch.isfinite(up), torch.full_like(out, float("nan")), out)


class Normalizer(torch.nn.Module):
    """GPU-side version of FloodChips.load(): fill invalid pixels with the band mean, standardise.
    s1_res=20 first degrades the radar to the 20 m overview (training for the atlas input)."""

    def __init__(self, ds, s1_res=10):
        super().__init__()
        self.s1_res = s1_res
        for n in ("m2", "d2", "m1", "d1"):
            self.register_buffer(n, torch.from_numpy(getattr(ds, n))[None])

    def forward(self, x):
        out = {}
        if "S2L1C" in x:
            s2 = x["S2L1C"].float()
            s2 = torch.where(s2 <= 0, self.m2, s2)
            out["S2L1C"] = (s2 - self.m2) / self.d2
        if "S1GRD" in x:
            s1 = x["S1GRD"].float()
            if self.s1_res == 20:
                s1 = radar_to_20m(s1)
            s1 = torch.where(~torch.isfinite(s1) | (s1 <= RADAR_NODATA_DB), self.m1, s1)
            out["S1GRD"] = (s1 - self.m1) / self.d1
        return out
