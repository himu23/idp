"""Build the shared memory-mapped cache of Sen1Floods11 and print a data audit."""
import sys, json
import numpy as np
sys.path.insert(0, sys.argv[1])
from floodfm.data import build_cache, Cache, chip_event

root, cache_dir = sys.argv[2], sys.argv[3]
build_cache(root, cache_dir)
c = Cache(cache_dir)
print("chips", len(c.chips))
for proto in ("official", "lio"):
    for s in ("train", "val", "test", "bolivia"):
        ids = c.split(proto, s)
        ev = sorted(set(chip_event(i) for i in ids))
        print(proto, s, len(ids), ev)
audit = {}
for i, ch in enumerate(c.chips):
    e = chip_event(ch)
    lab = np.asarray(c.label[i]); jrc = np.asarray(c.jrc[i])
    a = audit.setdefault(e, {"chips": 0, "water": 0, "dry": 0, "unknown": 0, "perm_water": 0})
    a["chips"] += 1; a["water"] += int((lab == 1).sum()); a["dry"] += int((lab == 0).sum())
    a["unknown"] += int((lab < 0).sum()); a["perm_water"] += int(((lab == 1) & (jrc == 1)).sum())
s1 = np.asarray(c.s1[:, :, ::8, ::8]); s2 = np.asarray(c.s2[:, :, ::8, ::8])
print("S1 range", np.nanmin(s1), np.nanmax(s1), "nan frac", np.isnan(s1).mean(), "<=-80 frac", (s1 <= -80).mean())
print("S2 range", s2.min(), s2.max(), "zero frac", (s2 <= 0).mean())
for e, a in sorted(audit.items()):
    tot = a["water"] + a["dry"]
    print(f"{e:10s} chips {a['chips']:3d} water {a['water']/max(tot,1):.3f} unknown {a['unknown']/(a['chips']*512*512):.3f} "
          f"perm-of-water {a['perm_water']/max(a['water'],1):.3f}")
json.dump(audit, open(cache_dir + "/audit.json", "w"), indent=1)
m, s = c.channel_stats(c.split("official", "train"))
print("train mean", [round(x, 2) for x in m]); print("train std", [round(x, 2) for x in s])
