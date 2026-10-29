"""Model zoo: two from-scratch baselines and five geospatial foundation-model families.

Every model maps the inputs of one chip to 2-class logits [B,2,H,W] (0 dry, 1 water),
so the loss, the checkpoint selection and the scoring are identical for all of them.
Foundation models are built with TerraTorch's EncoderDecoderFactory using the same
UNet-style decoder, so the comparison is between encoders, not decoders.
"""
import torch
import torch.nn as nn

from .data import (S2_BANDS, TERRAMIND_S1GRD_MEAN, TERRAMIND_S1GRD_STD, TERRAMIND_S2L1C_MEAN,
                   TERRAMIND_S2L1C_STD)

HLS6 = ["B02", "B03", "B04", "B8A", "B11", "B12"]          # Prithvi-EO-2.0 input bands
S2_TO_HLS = {"B01": "COASTAL_AEROSOL", "B02": "BLUE", "B03": "GREEN", "B04": "RED", "B05": "RED_EDGE_1",
             "B06": "RED_EDGE_2", "B07": "RED_EDGE_3", "B08": "NIR_BROAD", "B8A": "NIR_NARROW",
             "B09": "WATER_VAPOR", "B10": "CIRRUS", "B11": "SWIR_1", "B12": "SWIR_2"}
# Prithvi-EO-2.0 pre-training statistics (HLS surface reflectance x 1e4), from the model's config.json
PRITHVI_MEAN = [1087.0, 1342.0, 1433.0, 2734.0, 1958.0, 1363.0]
PRITHVI_STD = [2248.0, 2179.0, 2178.0, 1850.0, 1242.0, 1049.0]

VIT_NECK = lambda idx: [  # noqa: E731  ViT tokens -> 4-level feature pyramid
    {"name": "SelectIndices", "indices": idx},
    {"name": "ReshapeTokensToImage"},
    {"name": "LearnedInterpolateToPyramidal"},
]

# name: (description, optical bands, uses radar, stats source, builder kwargs)
SPECS = {
    "cnn": dict(desc="Simple CNN (3 conv layers, from scratch)", s2=S2_BANDS, s1=True, stats="dataset"),
    "unet": dict(desc="U-Net (4 levels, 32 base channels, from scratch)", s2=S2_BANDS, s1=True, stats="dataset"),
    "prithvi": dict(desc="Prithvi-EO-2.0-300M (ViT-L, MAE on global HLS)", s2=HLS6, s1=False, stats="prithvi",
                    tt=dict(backbone="prithvi_eo_v2_300", backbone_bands=[S2_TO_HLS[b] for b in HLS6],
                            backbone_img_size=512, necks=VIT_NECK([5, 11, 17, 23]))),
    "terramind": dict(desc="TerraMind-v1-base (multimodal ViT-B, S2L1C+S1GRD)", s2=S2_BANDS, s1=True,
                      stats="terramind",
                      tt=dict(backbone="terramind_v1_base", backbone_modalities=["S2L1C", "S1GRD"],
                              backbone_merge_method="mean", necks=VIT_NECK([2, 5, 8, 11]))),
    "dofa": dict(desc="DOFA-base (wavelength-conditioned ViT-B, optical+SAR)", s2=S2_BANDS, s1=True,
                 stats="dataset",
                 tt=dict(backbone="dofa_base_patch16_224", backbone_model_bands=[S2_TO_HLS[b] for b in S2_BANDS] + ["VV", "VH"],
                         backbone_img_size=512, backbone_out_indices=[2, 5, 8, 11],
                         necks=VIT_NECK(None)[1:])),
    "clay": dict(desc="Clay-v1-base (wavelength-aware ViT-B MAE)", s2=S2_BANDS, s1=True, stats="dataset",
                 tt=dict(backbone="clay_v1_base", backbone_bands=[S2_TO_HLS[b] for b in S2_BANDS] + ["VV", "VH"],
                         backbone_img_size=512, necks=VIT_NECK([2, 5, 8, 11]))),
    "satlas": dict(desc="Satlas Swin-v2-B (Sentinel-2 multispectral, SatlasPretrain)", s2=S2_BANDS, s1=False,
                   stats="dataset",
                   tt=dict(backbone="satlas_swin_b_sentinel2_si_ms", backbone_model_bands=[S2_TO_HLS[b] for b in S2_BANDS],
                           backbone_out_indices=[1, 3, 5, 7],  # 4 Swin stages, channels-last
                           necks=[{"name": "PermuteDims", "new_order": [0, 3, 1, 2]}])),
    "decur": dict(desc="SSL4EO-S12 DeCUR ResNet-50 (Sentinel-2 all bands)", s2=S2_BANDS, s1=False,
                  stats="dataset",
                  tt=dict(backbone="ssl4eos12_resnet50_sentinel2_all_decur",
                          backbone_model_bands=[S2_TO_HLS[b] for b in S2_BANDS],
                          backbone_out_indices=[1, 2, 3, 4])),
}


def model_stats(name, dataset_mean, dataset_std):
    """Normalisation stats for the 15-band cube, matched to the model's pre-training where known."""
    spec = SPECS[name]
    mean, std = list(dataset_mean), list(dataset_std)
    if spec["stats"] == "terramind":
        mean = TERRAMIND_S2L1C_MEAN + TERRAMIND_S1GRD_MEAN
        std = TERRAMIND_S2L1C_STD + TERRAMIND_S1GRD_STD
    elif spec["stats"] == "prithvi":
        for b, m, s in zip(HLS6, PRITHVI_MEAN, PRITHVI_STD):
            mean[S2_BANDS.index(b)] = m
            std[S2_BANDS.index(b)] = s
    return mean, std


class SimpleCNN(nn.Module):
    def __init__(self, cin, width=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(cin, width, 3, padding=1), nn.BatchNorm2d(width), nn.ReLU(),
            nn.Conv2d(width, width, 3, padding=1), nn.BatchNorm2d(width), nn.ReLU(),
            nn.Conv2d(width, 2, 3, padding=1))

    def forward(self, x):
        return self.net(x)


class UNet(nn.Module):
    def __init__(self, cin, base=32, depth=4):
        super().__init__()

        def block(a, b):
            return nn.Sequential(nn.Conv2d(a, b, 3, padding=1), nn.BatchNorm2d(b), nn.ReLU(inplace=True),
                                 nn.Conv2d(b, b, 3, padding=1), nn.BatchNorm2d(b), nn.ReLU(inplace=True))

        ch = [base * 2 ** i for i in range(depth + 1)]
        self.down = nn.ModuleList([block(cin, ch[0])] + [block(ch[i], ch[i + 1]) for i in range(depth)])
        self.pool = nn.MaxPool2d(2)
        self.up = nn.ModuleList([nn.ConvTranspose2d(ch[i + 1], ch[i], 2, stride=2) for i in reversed(range(depth))])
        self.dec = nn.ModuleList([block(ch[i] * 2, ch[i]) for i in reversed(range(depth))])
        self.head = nn.Conv2d(ch[0], 2, 1)

    def forward(self, x):
        skips = []
        for i, d in enumerate(self.down):
            x = d(x if i == 0 else self.pool(x))
            skips.append(x)
        x = skips.pop()
        for up, dec in zip(self.up, self.dec):
            x = dec(torch.cat([up(x), skips.pop()], 1))
        return self.head(x)


class Wrapped(nn.Module):
    """Uniform interface: forward(dict of modality tensors) -> logits [B,2,H,W]."""

    def __init__(self, name, net, multimodal):
        super().__init__()
        self.name, self.net, self.multimodal = name, net, multimodal

    def forward(self, x):
        if self.multimodal:
            out = self.net(x)
        else:
            out = self.net(torch.cat([x[k] for k in ("S2L1C", "S1GRD") if k in x], 1))
        return out.output if hasattr(out, "output") else out

    def backbone_parameters(self):
        enc = getattr(self.net, "encoder", None)
        return list(enc.parameters()) if enc is not None else []


def build(name, s1=None, s2=None):
    """Build a model. s1/s2 override the spec's modalities (used by the modality ablation)."""
    spec = SPECS[name]
    use_s1 = spec["s1"] if s1 is None else s1
    s2_bands = spec["s2"] if s2 is None else s2
    cin = len(s2_bands) + (2 if use_s1 else 0)
    if name == "cnn":
        return Wrapped(name, SimpleCNN(cin), False)
    if name == "unet":
        return Wrapped(name, UNet(cin), False)
    from terratorch.models import EncoderDecoderFactory

    kw = dict(spec["tt"])
    if name == "terramind":
        mods = ([] if not s2_bands else ["S2L1C"]) + (["S1GRD"] if use_s1 else [])
        kw["backbone_modalities"] = mods
    vit = name in ("prithvi", "terramind", "dofa", "clay")
    net = EncoderDecoderFactory().build_model(
        task="segmentation", backbone_pretrained=True, decoder="UNetDecoder",
        decoder_channels=[512, 256, 128, 64] if vit else [256, 128, 64, 32],
        num_classes=2, head_dropout=0.1, **kw)
    return Wrapped(name, net, multimodal=(name == "terramind"))
