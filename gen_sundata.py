import csv
import ephem
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from pathlib import Path

LAT       = '40.75203'
LON       = '-74.93142'
ELEVATION = 10                      # meters, approximate
TZ        = ZoneInfo('America/New_York')
START     = date(2026, 6, 1)
END       = date(2027, 6, 30)
OUT       = Path(__file__).parent / 'sundata.csv'

observer          = ephem.Observer()
observer.lat      = LAT
observer.lon      = LON
observer.elevation = ELEVATION
sun               = ephem.Sun()

rows = []
d = START
while d <= END:
    # Anchor to local noon → UTC so previous_rising/next_setting land on the right day
    local_noon = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=TZ)
    utc_noon   = local_noon.astimezone(ZoneInfo('UTC'))
    observer.date = ephem.Date(utc_noon.strftime('%Y/%m/%d %H:%M:%S'))

    rise_utc = observer.previous_rising(sun)
    set_utc  = observer.next_setting(sun)

    rise_local = ephem.Date(rise_utc).datetime().replace(tzinfo=ZoneInfo('UTC')).astimezone(TZ)
    set_local  = ephem.Date(set_utc).datetime().replace(tzinfo=ZoneInfo('UTC')).astimezone(TZ)

    rows.append({
        'Date':    d.strftime('%Y-%m-%d'),
        'Sunrise': rise_local.strftime('%H:%M:%S'),
        'Sunset':  set_local.strftime('%H:%M:%S'),
    })
    d += timedelta(days=1)

with open(OUT, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['Date', 'Sunrise', 'Sunset'])
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} rows to {OUT}")
