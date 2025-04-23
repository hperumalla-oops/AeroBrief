import requests
import re
from datetime import datetime, timedelta
from datetime import datetime, timezone


def get_formatted_taf(airport_code):
    url = f"https://aviationweather.gov/api/data/taf?ids={airport_code}&format=json"
    response = requests.get(url)
    data = response.json()
    
    if not data:
        return f"No TAF data available for airport '{airport_code}'."
    
    taf_raw = data[0].get("rawTAF", "")
    if not taf_raw:
        return f"TAF data for '{airport_code}' is missing raw text."

    taf_dict = {
        "SKC": "Sky clear",
        "NSC": "No significant clouds",
        "FEW": "Few clouds (1/8 - 2/8)",
        "SCT": "Scattered clouds (3/8 - 4/8)",
        "BKN": "Broken clouds (5/8 - 7/8)",
        "OVC": "Overcast (8/8)",
        "SN": "Snow",
        "RA": "Rain",
        "BR": "Mist",
        "FG": "Fog",
        "HZ": "Haze",
        "-": "Light",
        "+": "Heavy",
        "VC": "In the vicinity",
        "SH": "Showers",
        "TS": "Thunderstorms",
        "DZ": "Drizzle",
        "FM": "From",
        "TEMPO": "Temporary",
        "PROB30": "30% probability",
        "PROB40": "40% probability",
        "P6SM": "Visibility greater than 6 statute miles",
        "VV///": "Vertical visibility unknown",
    }

    def decode_wind(wind_str):
        match = re.match(r"(\d{3})(\d{2,3})(G\d{2,3})?KT", wind_str)
        if match:
            direction, speed, gust = match.groups()
            wind = f"Wind from {direction}° at {speed} knots"
            if gust:
                wind += f" with gusts to {gust[1:]} knots"
            return wind
        return None

    words = taf_raw.split()
    result = [f"Decoded TAF Forecast:", f"- Station: {airport_code.upper()}"]
    segments = []
    current_segment = []

    for word in words:
        if re.match(r"\d{6}Z", word):  # issuance time
            dt = datetime.now(timezone.utc)
            try:
                day, hour, minute = int(word[:2]), int(word[2:4]), int(word[4:6])
                dt = datetime(dt.year, dt.month, day, hour, minute)
            except Exception:
                pass
            result.append(f"- Issued: {dt.strftime('%Y-%m-%d %H:%MZ')}")
        elif re.match(r"\d{4}/\d{4}", word):  # validity
            start, end = word.split("/")
            result.append(f"- Valid Period: From {start[:2]}th at {start[2:]}Z to {end[:2]}th at {end[2:]}Z")
        elif word.startswith("FM") and len(word) >= 7:
            if current_segment:
                segments.append(current_segment)
            current_segment = [f"• From {word[2:4]}th at {word[4:6]}:{word[6:]}Z"]
        elif word in taf_dict:
            current_segment.append(f"– {taf_dict[word]}")
        elif word.startswith("TEMPO") or word.startswith("BECMG") or word.startswith("PROB"):
            if current_segment:
                segments.append(current_segment)
            label = taf_dict.get(word, word)
            current_segment = [f"• {label}"]
        elif decode_wind(word):
            current_segment.append(f"– {decode_wind(word)}")
        elif re.match(r"\d{4}SM", word):
            current_segment.append(f"– Visibility: {int(word[:4]) / 100.0} statute miles")
        else:
            # maybe a cloud code like SCT020
            cloud_match = re.match(r"([A-Z]{3})(\d{3})", word)
            if cloud_match:
                code, altitude = cloud_match.groups()
                meaning = taf_dict.get(code, code)
                current_segment.append(f"– {meaning} at {int(altitude)*100} ft")
    
    if current_segment:
        segments.append(current_segment)

    result.append("- Forecast Segments:")
    for seg in segments:
        result.extend(["  " + line for line in seg])

    return "\n".join(result)

print(get_formatted_taf("KPHX"))