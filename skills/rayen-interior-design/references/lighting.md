# Lighting design

## Targets (typical maintained illuminance, EN 12464-1 order — confirm project spec)
| Space | lx | UGR ≤ | Ra ≥ |
|---|---|---|---|
| Open office / meeting | 500 | 19 | 80 |
| Reception | 300 | 22 | 80 |
| Showroom / retail feature | 500–1000 accent | 22 | 90 |
| Retail general | 300–500 | 22 | 80 |
| Corridor | 100–150 | 25–28 | 40–80 |
| Toilets | 200 | 25 | 80 |
| Restaurant | 150–300 (dimmable) | 22 | 80–90 |
| Commercial kitchen | 500 | 22 | 80 |
| Workshop fine work | 750 | 19 | 80 |
| Parking | 75 | 25 | 40 |

## Method
Layers: ambient → task → accent (3–5× ambient for focal displays) → decorative/feature → emergency.
Lumen method: N = E·A / (Φ·n·UF·MF) — `scripts/lighting_calc.py`. Spacing-to-mounting-height ≤ ~1.5 for uniformity. Final verification with photometric software (DIALux/Relux) using the manufacturer IES/LDT files.
CCT: 2700–3000 K hospitality/majlis, 3000–3500 K retail/reception, 4000 K offices/workshops; keep one CCT per space family. CRI ≥ 90 for food, fashion, cosmetics, artwork.
Glare: deep-recessed / low-UGR optics in offices; no exposed LED dots in reflective surfaces; dim-to-warm in hospitality.
Linear LED in coves/feature walls: minimum distance from diffuser ≈ 1–1.5× LED pitch to avoid dotting; aluminium profile as heat sink; PSU accessible and ventilated; driver within cable-length limits; IP rating for wet zones.
Controls: scenes, DALI/0–10 V or phase dimming compatible drivers, occupancy/daylight sensors in offices.
Energy: LPD (W/m²) limits per SBC 601 — RAYEN reports LPD per room; compliance TO BE CONFIRMED.
Emergency lighting & exit signs per SBC 801 and Civil Defense — coordinate positions on RCP.
