import csv
import ephem
from datetime import date, timedelta, datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

LAT       = '40.75203'
LON       = '-74.93142'
ELEVATION = 10                       # meters, approximate
START     = date(2026, 6, 1)
END       = date(2027, 6, 30)
OUT       = Path(__file__).parent / 'sundata.csv'

USE_DST     = False  # True  = local wall-clock time (EDT in summer, EST in winter)
                     # False = standard time year-round (EST / UTC-5)

LOCAL_TZ    = ZoneInfo('America/New_York')
STANDARD_TZ = timezone(timedelta(hours=-5))  # always UTC-5, guaranteed no DST

observer           = ephem.Observer()
observer.lat       = LAT
observer.lon       = LON
observer.elevation = ELEVATION
sun                = ephem.Sun()

rows = []
d = START
while d <= END:
    tz = LOCAL_TZ if USE_DST else STANDARD_TZ
    local_noon = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=tz)
    utc_noon   = local_noon.astimezone(ZoneInfo('UTC'))
    observer.date = ephem.Date(utc_noon.strftime('%Y/%m/%d %H:%M:%S'))

    rise_utc = observer.previous_rising(sun)
    set_utc  = observer.next_setting(sun)

    rise_local = ephem.Date(rise_utc).datetime().replace(tzinfo=ZoneInfo('UTC')).astimezone(tz)
    set_local  = ephem.Date(set_utc).datetime().replace(tzinfo=ZoneInfo('UTC')).astimezone(tz)

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

mode = "local time (DST-aware)" if USE_DST else "standard time (no DST)"
print(f"Wrote {len(rows)} rows to {OUT}  [{mode}]")
