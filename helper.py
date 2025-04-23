import re
import requests
from groq import Groq


abbreviations = {
    "ABV": "above",
    "CNL": "cancelled",
    "CTA": "control area",
    "FCST": "forecast",
    "FIR": "Flight Information Region",
    "FL": "flight level",
    "FT": "feet",
    "INTSF": "intensifying",
    "KT": "knots",
    "KMH": "kilometres per hour",
    "M": "meters",
    "MOV": "moving",
    "NC": "no change",
    "NM": "nautical miles",
    "OBS": "observed",
    "SFC": "surface",
    "STNR": "stationary",
    "TOP": "top of cloud",
    "WI": "within",
    "WKN": "weakening",
    "Z": "UTC",
}

weather_codes = {
    "AREA TS": "Area-wide thunderstorms",
    "LINE TS": "Thunderstorm line",
    "EMBD TS": "Embedded thunderstorms",
    "TDO": "Tornado",
    "FC": "Funnel Cloud",
    "WTSPT": "Waterspout",
    "HVY GR": "Heavy hail",
    "OBSC TS": "Obscured thunderstorms",
    "EMBD TSGR": "Embedded thunderstorms with hail",
    "FRQ TS": "Frequent thunderstorms",
    "SQL TS": "Squall line thunderstorms",
    "FRQ TSGR": "Frequent thunderstorms with hail",
    "SQL TSGR": "Squall line thunderstorms with hail",
    "SEV TURB": "Severe turbulence",
    "SEV ICE": "Severe icing",
    "SEV ICE (FZRA)": "Severe icing due to freezing rain",
    "SEV MTW": "Severe mountain wave",
    "HVY DS": "Heavy duststorm",
    "HVY SS": "Heavy sandstorm",
    "RDOACT CLD": "Radioactive cloud"
}
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

def parse_sigmet(text):
    sigmet_id = re.search(r'CONVECTIVE SIGMET (\d+[A-Z])', text)
    valid_until = re.search(r'VALID UNTIL (\d{4})Z', text)
    movement = re.search(r'MOV FROM (\d{3})(\d{2})KT', text)
    tops = re.search(r'TOPS TO FL(\d+)', text)
    area_match = re.search(r'FROM (.+?)DMSHG', text, re.DOTALL)
    outlook_time = re.search(r'OUTLOOK VALID (\d{6})-(\d{6})', text)
    outlook_area = re.search(r'OUTLOOK VALID.*?FROM (.+?)WST', text, re.DOTALL)

    
    if sigmet_id:
        print(f"SIGMET ID: {sigmet_id.group(1)} (Convective, Central Region)")

    if valid_until:
        print(f"Valid Until: {valid_until.group(1)} UTC")

    if area_match:
        area_points = area_match.group(1).strip().replace("\n", " ").split("-")
        print("\nAffected Area (polygon points):")
        for point in area_points:
            print(f" - {point.strip()}")

    if "DMSHG AREA TS" in text:
        print("\nWeather: Area-wide thunderstorms (diminishing)")

    if movement:
        print(f"Movement: From {movement.group(1)}° at {movement.group(2)} knots")

    if tops:
        print(f"Cloud Tops: Up to {tops.group(1)} flight level (approx. {int(tops.group(1))*100} ft)")

    if outlook_time and outlook_area:
        outlook_coords = outlook_area.group(1).strip().replace("\n", " ").split("-")
        print(f"\nOutlook Forecast Time: {outlook_time.group(1)} UTC to {outlook_time.group(2)} UTC")
        print("Forecast Area:")
        for point in outlook_coords:
            print(f" - {point.strip()}")

    print("\nAdditional SIGMETs may be issued. Refer to SPC for updates.")

    
def decode_wind(wind_str):
    match = re.match(r"(\d{3})(\d{2,3})(G\d{2,3})?KT", wind_str)
    if match:
        direction, speed, gust = match.groups()
        wind_desc = f"Wind from {direction}° at {speed} knots"
        if gust:
            wind_desc += f" with gusts to {gust[1:]} knots"
        return wind_desc
    return None

def parse_taf(taf_str):
    words = taf_str.split()
    translation = ""
    
    for word in words:
        if word in taf_dict:
            translation += taf_dict[word]
        elif word.startswith("FM"):
            time = word[2:]
            translation += f"From {time[:2]}:{time[2:]}Z"
        elif decode_wind(word):
            translation.append(decode_wind(word))
        elif re.match(r"\d{4}/\d{4}", word):  # validity period
            start, end = word[:4], word[5:]
            translation += f"Valid from {start[:2]}Z on day {start[2:]} to {end[:2]}Z on day {end[2:]}"
        elif re.match(r"\d{6}Z", word):  # issuance time
            translation += f"Issued at {word[:2]} day, {word[2:4]}:{word[4:6]}Z"
        else:
            translation += word

    return translation 



def fetch_taf(airport_id):
    url = f"https://aviationweather.gov/api/data/taf?ids={airport_id}&format=json"
    response = requests.get(url)
    return response.json()  




def fetch_pirep(airport_id):
    url = f"https://aviationweather.gov/api/data/pirep?ids={airport_id}&format=json"
    response1 = requests.get(url)
    response1=response1.json()
    return response1

def fetch_sigmet(airport_id, altitude=None):
    base_url = "https://aviationweather.gov/api/data/airsigmet"
    params = {
        "format": "json"
    }

    response = requests.get(base_url, params=params, timeout=10)
    print(response.json()[0]['rawAirSigmet'])
    response.json()




def fetch_metar(airport_id):
    url = f"https://aviationweather.gov/api/data/metar?ids={airport_id}&format=json"
    response = requests.get(url)
    return response.json()

def parse_metar(airport_id,yes=0):
    metar_list = fetch_metar(airport_id)

    if not metar_list or not isinstance(metar_list, list):
        return f"No valid METAR data returned for {airport_id}."

    metar_entry = metar_list[0]  # Use only the first METAR

    if yes:
        #print(metar_entry)
        return metar_entry['rawOb']

    result = {}

    result["Type"] = "Routine METAR report" if metar_entry.get("metarType") == "METAR" else "Special METAR report"
    result["Station"] = metar_entry.get("icaoId", "Unknown")
    result["Time"] = metar_entry.get("reportTime", "Unknown")

    wdir = metar_entry.get("wdir")
    wspd = metar_entry.get("wspd")
    wgst = metar_entry.get("wgst")
    if wdir is not None and wspd is not None:
        wind = f"{wdir}° at {wspd} knots"
        if wgst:
            wind += f" with gusts to {wgst} knots"
        result["Wind"] = wind

    vis = metar_entry.get("visib")
    if vis is not None:
        result["Visibility"] = f"{vis} statute miles"

    wx = metar_entry.get("wxString")
    if wx:
        result["Weather"] = wx

    clouds = metar_entry.get("clouds", [])
    if clouds:
        layers = []
        cover_dict = {
            "FEW": "Few clouds",
            "SCT": "Scattered clouds",
            "BKN": "Broken clouds",
            "OVC": "Overcast"
        }
        for cloud in clouds:
            cover = cloud.get("cover")
            base = cloud.get("base")
            if cover and base is not None:
                desc = f"{cover_dict.get(cover, cover)} at {base * 100} feet"
                layers.append(desc)
        result["Sky"] = "; ".join(layers)

    temp = metar_entry.get("temp")
    dewp = metar_entry.get("dewp")
    if temp is not None:
        result["Temperature"] = f"{temp:.1f}°C"
    if dewp is not None:
        result["Dewpoint"] = f"{dewp:.1f}°C"

    alt = metar_entry.get("altim")
    if alt is not None:
        result["Altimeter"] = f"{alt} hPa"

    slp = metar_entry.get("slp")
    if slp is not None:
        result["Sea Level Pressure"] = f"{slp} hPa"

    final = "\nDecoded METAR Report:\n"
    for key, value in result.items():
        final += f"{key} {value}\n"

    return final
    
    data = fetch_metar(airport_id)
    metar_entry = data.get("metar", [])[0]  # Get the first (and only) METAR entry

    result = {}

    result["Type"] = "Routine METAR report" if metar_entry.get("metarType") == "METAR" else "Special METAR report"
    result["Station"] = metar_entry.get("icaoId", "Unknown")
    result["Time"] = metar_entry.get("reportTime", "Unknown")

    wdir = metar_entry.get("wdir")
    wspd = metar_entry.get("wspd")
    wgst = metar_entry.get("wgst")
    if wdir is not None and wspd is not None:
        wind = f"{wdir}° at {wspd} knots"
        if wgst:
            wind += f" with gusts to {wgst} knots"
        result["Wind"] = wind

    vis = metar_entry.get("visib")
    if vis is not None:
        result["Visibility"] = f"{vis} statute miles"

    wx = metar_entry.get("wxString")
    if wx:
        result["Weather"] = wx

    clouds = metar_entry.get("clouds", [])
    if clouds:
        layers = []
        cover_dict = {
            "FEW": "Few clouds",
            "SCT": "Scattered clouds",
            "BKN": "Broken clouds",
            "OVC": "Overcast"
        }
        for cloud in clouds:
            cover = cloud.get("cover")
            base = cloud.get("base")
            if cover and base is not None:
                desc = f"{cover_dict.get(cover, cover)} at {base * 100} feet"
                layers.append(desc)
        result["Sky"] = "; ".join(layers)

    temp = metar_entry.get("temp")
    dewp = metar_entry.get("dewp")
    if temp is not None:
        result["Temperature"] = f"{temp:.1f}°C"
    if dewp is not None:
        result["Dewpoint"] = f"{dewp:.1f}°C"

    alt = metar_entry.get("altim")
    if alt is not None:
        result["Altimeter"] = f"{alt} hPa"

    slp = metar_entry.get("slp")
    if slp is not None:
        result["Sea Level Pressure"] = f"{slp} hPa"

    final = "\nDecoded METAR Report:\n"
    for key, value in result.items():
        final += f"{key} {value}\n"

    return final


def summary(final):
    client = Groq(api_key='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')
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role":"system", "content": "You brief pilots on the weather and give them the import details of their flight plan DO NOT SAY ANYTHING EXTRA"
        },
        {
            "role":"user", "content": final
        }],
        temperature=1,
        max_completion_tokens=8192,
        top_p=1,
        stream=False,
        stop=None,
    )

    return completion.choices[0].message.content

def warning_level(airport_id):
    metar = parse_metar(airport_id, 1)
    flight_rules = [
        ("1", lambda vis, ceil: vis >= 5 and ceil > 3000),
        ("2", lambda vis, ceil: 3 <= vis < 5 or 1000 < ceil <= 3000),
        ("3", lambda vis, ceil: 1 <= vis < 3 or 500 <= ceil <= 1000),
        ("4", lambda vis, ceil: vis < 1 or ceil < 500),
    ]

    vis_match = re.search(r' (\d+)? ?(\d?/\d)?SM', metar)
    if vis_match:
        whole = int(vis_match.group(1)) if vis_match.group(1) else 0
        frac = vis_match.group(2)
        if frac:
            num, den = map(int, frac.split('/'))
            vis = whole + num / den
        else:
            vis = whole
    else:
        vis = None

    ceil_match = re.search(r'(OVC|BKN)(\d{3})', metar)
    ceil = int(ceil_match.group(2)) * 100 if ceil_match else None

    if vis is None or ceil is None:
        return 5

    for rule, condition in flight_rules:
        if condition(vis, ceil):
            return int(rule)

    return 5


parse_metar("KLAX",1)
# k = fetch_metar(["KANK"])
# print(parse_metar("KANK"))
# print(parse_taf(["KANK"]))


# print(parse_metar("KPHX 210151Z 31006KT 10SM SCT250 28/01 A2990 RMK AO2 SLP113 T02830011"))
# print(parse_taf("KPHX 202328Z 2100/2206 27006KT P6SM FEW250 FM210700 10005KT P6SM SCT250 FM211900 28007KT P6SM BKN250"))
# rawAirSigmet = "WSUS31 KKCI 210155 \nSIGE  \nCONVECTIVE SIGMET...NONE \n \nOUTLOOK VALID 210355-210755 \nFROM 70NE GRB-30E TVC-30SSE DXO-60E CVG-60SSE TTH-70NE GRB \nWST ISSUANCES POSS LT IN PD. REFER TO MOST RECENT ACUS01 KWNS \nFROM STORM PREDICTION CENTER FOR SYNOPSIS AND METEOROLOGICAL \nDETAILS."
# parse_sigmet(rawAirSigmet)
# parse_sigmet("WSUS32 KKCI 210155 \nSIGC  \nCONVECTIVE SIGMET 3C \nVALID UNTIL 0355Z \nWI IL MO AR IA \nFROM 40ENE DBQ-40NW TTH-40N MEM-50SW ARG-STL-50W DBQ-40ENE DBQ \nAREA SEV EMBD TS MOV FROM 24050KT. TOPS ABV FL450. \nTORNADOES...HAIL TO 1.5 IN...WIND GUSTS TO 60KT POSS. \n \nOUTLOOK VALID 210355-210755 \nFROM 70NE GRB-60SSE TTH-30ENE MCB-70ESE PSX-40NNE CRP-30NNW \nELD-30SSE STL-40NW ODI-70NE GRB \nREF WW 155 156. \nWST ISSUANCES EXPD. REFER TO MOST RECENT ACUS01 KWNS FROM STORM \nPREDICTION CENTER FOR SYNOPSIS AND METEOROLOGICAL DETAILS.")
# parse_sigmet("WSUS32 KKCI 210155 \nSIGC  \nCONVECTIVE SIGMET 4C \nVALID UNTIL 0355Z \nLA AR TX \nFROM 30NNW MEM-40ESE IAH-50NNW PSX-60NNE LIT-30NNW MEM \nAREA SEV EMBD TS MOV FROM 22040KT. TOPS ABV FL450. \nHAIL TO 1.5 IN...WIND GUSTS TO 60KT POSS. \n \nOUTLOOK VALID 210355-210755 \nFROM 70NE GRB-60SSE TTH-30ENE MCB-70ESE PSX-40NNE CRP-30NNW \nELD-30SSE STL-40NW ODI-70NE GRB \nREF WW 155 156. \nWST ISSUANCES EXPD. REFER TO MOST RECENT ACUS01 KWNS FROM STORM \nPREDICTION CENTER FOR SYNOPSIS AND METEOROLOGICAL DETAILS.")
# parse_sigmet("WSUS33 KKCI 210155 \nSIGW  \nCONVECTIVE SIGMET 3W \nVALID UNTIL 0355Z \nMT \nFROM 60WNW HVR-50NE GGW-50ENE MLS-40S LWT-60WNW HVR \nAREA EMBD TS MOV FROM 27015KT. TOPS TO FL260. \n \nOUTLOOK VALID 210355-210755 \nTS ARE NOT EXPD TO REQUIRE WST ISSUANCES.")
# api = "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"
