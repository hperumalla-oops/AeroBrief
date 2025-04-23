import re
import requests
import os
import json



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

def fetch_sigmet(airport_id, altitude=None):

    base_url = "https://aviationweather.gov/api/data/airsigmet"
    params = {
        #"ids": airport_id,
        "format": "json"
    }
    if altitude:
        flight_level = int(altitude / 100)
        params["level"] = flight_level

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()

        try:
            print(response.json()[0]['rawAirSigmet'])
            return response.json()
            ##print(response.json())
        except ValueError:
            return {
                "error": "Response is not valid JSON",
                "raw": response.text
            }

    except requests.exceptions.RequestException as e:
        return {
            "error": "Request failed",
            "details": str(e)
        }

import re

def parse_sigmet(text):
    output_lines = []

    sigmet_id = re.search(r'CONVECTIVE SIGMET (\d+[A-Z])', text)
    valid_until = re.search(r'VALID UNTIL (\d{4})Z', text)
    movement = re.search(r'MOV FROM (\d{3})(\d{2})KT', text)
    tops = re.search(r'TOPS TO FL(\d+)', text)
    area_match = re.search(r'FROM (.+?)DMSHG', text, re.DOTALL)
    outlook_time = re.search(r'OUTLOOK VALID (\d{6})-(\d{6})', text)
    outlook_area = re.search(r'OUTLOOK VALID.*?FROM (.+?)WST', text, re.DOTALL)


    if sigmet_id:
        output_lines.append(f"SIGMET ID: {sigmet_id.group(1)} (Convective, Central Region)")

    if valid_until:
        output_lines.append(f"Valid Until: {valid_until.group(1)} UTC")

    if area_match:
        area_points = area_match.group(1).strip().replace("\n", " ").split("-")
        output_lines.append("\nAffected Area (polygon points):")
        for point in area_points:
            output_lines.append(f" - {point.strip()}")

    if "DMSHG AREA TS" in text:
        output_lines.append("\nWeather: Area-wide thunderstorms (diminishing)")

    if movement:
        output_lines.append(f"Movement: From {movement.group(1)}° at {movement.group(2)} knots")

    if tops:
        output_lines.append(f"Cloud Tops: Up to FL{tops.group(1)} (approx. {int(tops.group(1)) * 100} ft)")

    if outlook_time and outlook_area:
        outlook_coords = outlook_area.group(1).strip().replace("\n", " ").split("-")
        output_lines.append(f"\nOutlook Forecast Time: {outlook_time.group(1)} UTC to {outlook_time.group(2)} UTC")
        output_lines.append("Forecast Area:")
        for point in outlook_coords:
            output_lines.append(f" - {point.strip()}")

    output_lines.append("\nAdditional SIGMETs may be issued. Refer to SPC for updates.")

    return "\n".join(output_lines)


def sigmet_json_generator(ap):
    with open(ap) as airports:
        ap = json.load(airports)

    sigmet=[]
    for a in ap['waypoints']:
        print(a['airport_id'])
        x=fetch_sigmet(a['airport_id'])
        coords=x[0]['coords']
        severity=x[0]['severity']
        print(coords)
        sigmet_english=parse_sigmet(x[0]['rawAirSigmet'])
        print(sigmet_english)
        

        sigmet.append({
            "sigmet_eng": sigmet_english,
            "coords": coords,
            "severity":severity
            })

        output_data = {"sigmet": sigmet}

        with open("sigmets_new.json", "w") as f:
            json.dump(output_data, f, indent=2)


