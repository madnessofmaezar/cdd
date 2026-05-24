import csv
import ephem
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path

CSV_PATH = Path(__file__).parent / "sundata.csv"

data = []
with open(CSV_PATH) as f:
    for row in csv.DictReader(f):
        dt = datetime.strptime(row["Date"], "%Y-%m-%d").date()
        rh, rm, rs = map(int, row["Sunrise"].split(":"))
        sh, sm, ss = map(int, row["Sunset"].split(":"))
        data.append({
            "date": dt,
            "rise": rh * 3600 + rm * 60 + rs,
            "set":  sh * 3600 + sm * 60 + ss,
        })

N    = len(data)
SECS = 86400

# Build image: rows = seconds of day, cols = days
img = np.zeros((SECS, N), dtype=np.float32)
for i, d in enumerate(data):
    img[d["rise"]:d["set"], i] = 1.0

fig, ax = plt.subplots(figsize=(15, 6))
fig.patch.set_facecolor("#111")
ax.set_facecolor("#111")

ax.imshow(
    img,
    aspect="auto",
    origin="upper",
    cmap="gray",
    extent=[0, N, SECS, 0],
    interpolation="nearest",
    vmin=0,
    vmax=1,
)

# Y axis — time of day
hour_ticks = list(range(0, 25, 3))
def fmt_hour(h):
    if h == 0 or h == 24: return "midnight"
    if h == 12:            return "noon"
    return f"{h % 12} {'am' if h < 12 else 'pm'}"

ax.set_yticks([h * 3600 for h in hour_ticks])
ax.set_yticklabels([fmt_hour(h) for h in hour_ticks], color="#aaa", fontsize=8)
ax.set_ylim(SECS, 0)
ax.yaxis.set_tick_params(length=0)

for h in hour_ticks:
    ax.axhline(h * 3600, color="#333", linewidth=0.4, zorder=0)

# X axis — month labels
month_ticks, month_labels = [], []
seen = set()
for i, d in enumerate(data):
    key = (d["date"].year, d["date"].month)
    if key not in seen:
        seen.add(key)
        month_ticks.append(i)
        if d["date"].month == 1 or i == 0:
            month_labels.append(d["date"].strftime("%b '%y"))
        else:
            month_labels.append(d["date"].strftime("%b"))

ax.set_xticks(month_ticks)
ax.set_xticklabels(month_labels, color="#aaa", fontsize=8)
ax.xaxis.set_tick_params(length=3, color="#444")
ax.set_xlim(0, N)

for t in month_ticks[1:]:
    ax.axvline(t, color="#333", linewidth=0.5, zorder=0)

for spine in ax.spines.values():
    spine.set_edgecolor("#333")

# ── Extremes (solid lines, labels at top) ─────────────────────────────────
SUMMER = "#ffcc00"
WINTER = "#4499ff"

earliest_rise = min(range(N), key=lambda i: data[i]["rise"])
latest_rise   = max(range(N), key=lambda i: data[i]["rise"])
earliest_set  = min(range(N), key=lambda i: data[i]["set"])
latest_set    = max(range(N), key=lambda i: data[i]["set"])

extremes = [
    (earliest_rise, SUMMER, "earliest\nsunrise"),
    (latest_set,    SUMMER, "latest\nsunset"),
    (latest_rise,   WINTER, "latest\nsunrise"),
    (earliest_set,  WINTER, "earliest\nsunset"),
]

for idx, color, label in extremes:
    date_str = data[idx]["date"].strftime("%b-%d")
    ax.axvline(idx, color=color, linewidth=0.9, alpha=0.85, zorder=4)
    ax.text(idx + 1.5, 18 * 60, f"{label}\n{date_str}", color=color, fontsize=6.5,
            va="top", linespacing=1.4, zorder=5)

# ── Solstices & equinoxes (dashed lines, labels at bottom) ────────────────
date_to_idx = {d["date"]: i for i, d in enumerate(data)}
start, end = data[0]["date"], data[-1]["date"]

astro_events = []
d = ephem.Date(f"{start.year}/{start.month}/{start.day}")
while True:
    next_sol = ephem.next_solstice(d)
    next_eq  = ephem.next_equinox(d)
    if next_sol < next_eq:
        evt_date = next_sol.datetime().date()
        is_summer = evt_date.month in (6, 7)
        label = "summer solstice" if is_summer else "winter solstice"
        color = SUMMER if is_summer else WINTER
        d = next_sol + 1
        kind = "solstice"
    else:
        evt_date = next_eq.datetime().date()
        is_spring = evt_date.month in (3, 4)
        label = "spring equinox" if is_spring else "fall equinox"
        color = "#44cc66" if is_spring else "#ff8800"
        d = next_eq + 1
        kind = "equinox"
    if evt_date > end:
        break
    astro_events.append((evt_date, color, label, kind))

for evt_date, color, label, kind in astro_events:
    idx = date_to_idx.get(evt_date)
    if idx is None:
        continue
    date_str = evt_date.strftime("%b-%d")
    ls    = "-"      if kind == "solstice" else "--"
    alpha = 0.85     if kind == "solstice" else 0.6
    dashes = (None, None) if kind == "solstice" else (4, 3)
    ax.axvline(idx, color=color, linewidth=0.9, alpha=alpha, zorder=4,
               linestyle=ls, dashes=dashes)
    ax.text(idx + 1.5, SECS - 18 * 60, f"{label}\n{date_str}", color=color,
            fontsize=6.5, va="bottom", linespacing=1.4, zorder=5)

ax.set_title("Daylight  ·  Jun 2026 – Jun 2027", color="#ccc",
             fontsize=11, pad=10, loc="left")

# ── Interactive hover ──────────────────────────────────────────────────────
vline = ax.axvline(x=-10, color="#f90", linewidth=0.8, alpha=0.85, zorder=5)

annot = ax.annotate(
    "",
    xy=(0, 0),
    xytext=(12, -8),
    textcoords="offset points",
    bbox=dict(boxstyle="round,pad=0.5", fc="#1a1a1a", ec="#555", lw=0.8),
    fontsize=8.5,
    color="#ddd",
    zorder=10,
)
annot.set_visible(False)

def fmt_time(secs):
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    p = "am" if h < 12 else "pm"
    return f"{h % 12 or 12}:{m:02d}:{s:02d} {p}"

def on_move(event):
    if event.inaxes != ax or event.xdata is None:
        annot.set_visible(False)
        vline.set_xdata([-10])
        fig.canvas.draw_idle()
        return

    idx = max(0, min(N - 1, int(event.xdata)))
    d = data[idx]
    dl_total = d["set"] - d["rise"]
    dl_h, rem = divmod(dl_total, 3600)
    dl_m, dl_s = divmod(rem, 60)

    text = (
        f"{d['date'].strftime('%a, %b %-d %Y')}\n"
        f"Sunrise  {fmt_time(d['rise'])}\n"
        f"Sunset   {fmt_time(d['set'])}\n"
        f"Day      {dl_h}h {dl_m:02d}m {dl_s:02d}s"
    )

    annot.set_text(text)
    annot.xy = (event.xdata, event.ydata)
    annot.set_position((-145 if idx / N > 0.75 else 12, -8))
    annot.set_visible(True)
    vline.set_xdata([idx])
    fig.canvas.draw_idle()

def on_leave(event):
    annot.set_visible(False)
    vline.set_xdata([-10])
    fig.canvas.draw_idle()

fig.canvas.mpl_connect("motion_notify_event", on_move)
fig.canvas.mpl_connect("axes_leave_event", on_leave)

plt.tight_layout()
plt.show()
