"""Build every model, run one forward/backward pass at 512x512, report size, speed and memory."""
import sys, time, traceback
import torch
sys.path.insert(0, sys.argv[1])
from floodfm.models import SPECS, build

names = sys.argv[2:] or list(SPECS)
for n in names:
    try:
        torch.cuda.reset_peak_memory_stats()
        m = build(n).cuda()
        spec = SPECS[n]
        x = {}
        if spec["s2"]:
            x["S2L1C"] = torch.randn(4, len(spec["s2"]), 512, 512).cuda()
        if spec["s1"]:
            x["S1GRD"] = torch.randn(4, 2, 512, 512).cuda()
        t = time.time()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            y = m(x)
        y.float().mean().backward()
        torch.cuda.synchronize()
        npar = sum(p.numel() for p in m.parameters()) / 1e6
        nbb = sum(p.numel() for p in m.backbone_parameters()) / 1e6
        print(f"OK {n:10s} out={tuple(y.shape)} params={npar:.1f}M backbone={nbb:.1f}M "
              f"step={time.time()-t:.2f}s peak={torch.cuda.max_memory_allocated()/2**30:.1f}GiB", flush=True)
        del m, y
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"FAIL {n}: {type(e).__name__}: {str(e)[:400]}", flush=True)
        traceback.print_exc(limit=3)
