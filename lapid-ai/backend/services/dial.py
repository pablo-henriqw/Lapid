"""Geometria do “relógio de 24h”: barras radiais que mostram a que horas os relatos chegam."""
import math

CX = CY = 160
R0 = 56      # raio interno
MAXLEN = 74  # comprimento máximo da barra


def _pt(r, deg):
    a = math.radians(deg - 90)  # 0h no topo, sentido horário
    return round(CX + r * math.cos(a), 2), round(CY + r * math.sin(a), 2)


def build_dial(per_hour: dict) -> dict:
    peak = max(per_hour.values(), default=0)
    bars = []
    for h in range(24):
        n = per_hour.get(h, 0)
        deg = h * 15 + 7.5
        length = 5 + (n / peak * MAXLEN if peak else 0)
        x1, y1 = _pt(R0, deg)
        x2, y2 = _pt(R0 + length, deg)
        bars.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "n": n, "label": f"{h:02d}h", "hot": bool(peak) and n == peak})
    sx, sy = _pt(R0 - 12, 315)  # faixa da madrugada: 21h às 06h
    ex, ey = _pt(R0 - 12, 450)
    labels = []
    for h in (0, 6, 12, 18):
        x, y = _pt(R0 + MAXLEN + 18, h * 15)
        labels.append({"x": x, "y": y, "t": f"{h:02d}h"})
    peak_hour = next((b["label"] for b in bars if b["hot"]), None)
    return {
        "bars": bars,
        "labels": labels,
        "night": f"M {sx} {sy} A {R0 - 12} {R0 - 12} 0 0 1 {ex} {ey}",
        "peak_hour": peak_hour,
        "peak": peak,
        "total": sum(per_hour.values()),
    }
