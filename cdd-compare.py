import ephem
import numpy as np
import matplotlib.pyplot as plt
from datetime import date, timedelta, datetime, timezone
from zoneinfo import ZoneInfo

LON         = '-74.93142'
ELEVATION   = 10
START       = date(2026, 6, 1)
END         = date(2027, 6, 30)
SECS        = 86400
STANDARD_TZ = timezone(timedelta(hours=-5))  # always UTC-5, no DST

LATS = [0, 7.5, 15, 22.5, 30, 37.5, 45, 52.5, 60, 67.5, 75, 82.5, 90]

# Dates
dates = []
d = START
while d <= END:
    dates.append(d)
    d += timedelta(days=1)
N = len(dates)

# Colors: red (equator) to blue (pole)
def lat_color(i, total):
    t = i / (total - 1)
    return (1 - t, 0.0, t)

def get_sun_times(lat):
    obs           = ephem.Observer()
    obs.lat       = str(float(lat))
    obs.lon       = LON
    obs.elevation = ELEVATION
    sun           = ephem.Sun()
    rise_arr, set_arr = [], []

    for d in dates:
        local_noon = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=STANDARD_TZ)
        utc_noon   = local_noon.astimezone(ZoneInfo('UTC'))
        obs.date   = ephem.Date(utc_noon.strftime('%Y/%m/%d %H:%M:%S'))

        try:
            r  = obs.previous_rising(sun)
            rl = ephem.Date(r).datetime().replace(tzinfo=ZoneInfo('UTC')).astimezone(STANDARD_TZ)
            rs = rl.hour * 3600 + rl.minute * 60 + rl.second
        except ephem.AlwaysUpError:
            rs = 0          # polar day — treat as rising at midnight
        except ephem.NeverUpError:
            rs = np.nan     # polar night

        try:
            s  = obs.next_setting(sun)
            sl = ephem.Date(s).datetime().replace(tzinfo=ZoneInfo('UTC')).astimezone(STANDARD_TZ)
            ss = sl.hour * 3600 + sl.minute * 60 + sl.second
        except ephem.AlwaysUpError:
            ss = SECS       # polar day — treat as setting at midnight
        except ephem.NeverUpError:
            ss = np.nan     # polar night

        rise_arr.append(rs)
        set_arr.append(ss)

    rise = np.array(rise_arr, dtype=float)
    set_ = np.array(set_arr,  dtype=float)
    return clean(rise), clean(set_)

def clean(arr, max_delta=2700):
    """Replace points that jump unrealistically from both neighbors with NaN."""
    arr = arr.copy()
    for i in range(1, len(arr) - 1):
        if np.isnan(arr[i]):
            continue
        prev = next((arr[j] for j in range(i-1, -1, -1) if not np.isnan(arr[j])), None)
        nxt  = next((arr[j] for j in range(i+1, len(arr)) if not np.isnan(arr[j])), None)
        if prev is not None and nxt is not None:
            if abs(arr[i] - prev) > max_delta and abs(arr[i] - nxt) > max_delta:
                arr[i] = np.nan
    return arr

# ── Plot ───────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(15, 6))
fig.patch.set_facecolor("#111")
ax.set_facecolor("#111")

all_data = {}
x = np.arange(N)

for i, lat in enumerate(LATS):
    print(f"Computing {lat}°N...")
    rise, set_ = get_sun_times(lat)
    all_data[lat] = (rise, set_)
    color = lat_color(i, len(LATS))
    lw = 1.2 if lat in (LATS[0], LATS[-1]) else 0.9
    ax.plot(x, rise,  color=color, linewidth=lw, alpha=0.9, label=f"{lat}°N")
    ax.plot(x, set_,  color=color, linewidth=lw, alpha=0.9)

# Y axis
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

# X axis
month_ticks, month_labels = [], []
seen = set()
for i, d in enumerate(dates):
    key = (d.year, d.month)
    if key not in seen:
        seen.add(key)
        month_ticks.append(i)
        month_labels.append(d.strftime("%b '%y") if (d.month == 1 or i == 0) else d.strftime("%b"))

ax.set_xticks(month_ticks)
ax.set_xticklabels(month_labels, color="#aaa", fontsize=8)
ax.xaxis.set_tick_params(length=3, color="#444")
ax.set_xlim(0, N)
for t in month_ticks[1:]:
    ax.axvline(t, color="#333", linewidth=0.5, zorder=0)

for spine in ax.spines.values():
    spine.set_edgecolor("#333")

ax.legend(loc='upper right', fontsize=7, facecolor='#1a1a1a', edgecolor='#444',
          labelcolor='white', framealpha=0.8)
ax.set_title("Sunrise & Sunset by Latitude  ·  Jun 2026 – Jun 2027",
             color="#ccc", fontsize=11, pad=10, loc="left")

# ── Hover ──────────────────────────────────────────────────────────────────
vline = ax.axvline(x=-10, color="#f90", linewidth=0.8, alpha=0.85, zorder=5)
annot = ax.annotate("", xy=(0, 0), xytext=(12, -8), textcoords="offset points",
    bbox=dict(boxstyle="round,pad=0.5", fc="#1a1a1a", ec="#555", lw=0.8),
    fontsize=7.5, color="#ddd", zorder=10)
annot.set_visible(False)

def fmt_time(s):
    if np.isnan(s): return "——"
    s = int(s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    p = "am" if h < 12 else "pm"
    return f"{h % 12 or 12}:{m:02d}:{sec:02d} {p}"

def on_move(event):
    if event.inaxes != ax or event.xdata is None:
        annot.set_visible(False)
        vline.set_xdata([-10])
        fig.canvas.draw_idle()
        return
    idx = max(0, min(N - 1, int(event.xdata)))
    lines = [dates[idx].strftime('%a, %b %-d %Y')]
    for lat in LATS:
        r, s = all_data[lat]
        lines.append(f"{lat:>4}°N  {fmt_time(r[idx])} → {fmt_time(s[idx])}")
    annot.set_text('\n'.join(lines))
    annot.xy = (event.xdata, event.ydata)
    annot.set_position((-210 if idx / N > 0.72 else 12, -8))
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
