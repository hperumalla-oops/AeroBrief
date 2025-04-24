import json
import requests
import os
from geopy.distance import geodesic
import numpy as np
import re
import time


weather_code_descriptions = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm: Slight or moderate",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

severe_weather_codes = {3,81,82, 86, 95, 96, 99,45, 48,51, 53, 55,56, 57,61, 63, 65,66, 67,71, 73, 75,77,80,85}


def summarize_pirep(raw):
    if not raw or not isinstance(raw, str):
        return "No PIREP information available."

    summary = []

    if "UUA" in raw:
        summary.append("⚠️ Urgent PIREP – hazardous conditions reported")

    # Location
    ov_match = re.search(r"/OV\s+([A-Z0-9]+)", raw)
    if ov_match:
        summary.append(f"Location: near {ov_match.group(1)}")

    # Time
    tm_match = re.search(r"/TM\s+(\d{4})", raw)
    if tm_match:
        summary.append(f"Time: {tm_match.group(1)} Zulu")

    # Altitude
    fl_match = re.search(r"/FL(\d+)", raw)
    if fl_match:
        alt = int(fl_match.group(1)) * 100
        summary.append(f"Altitude: {alt} ft")

    # Aircraft type
    tp_match = re.search(r"/TP\s*([A-Z0-9\-]+)", raw)
    if tp_match:
        summary.append(f"Aircraft: {tp_match.group(1)}")

    # Sky condition
    sky_match = re.findall(r"/SK\s+([A-Z]+)(\d+)", raw)
    if sky_match:
        conditions = "; ".join([f"{code} at {int(height) * 100} ft" for code, height in sky_match])
        summary.append(f"Sky: {conditions}")

    # Turbulence
    tb_match = re.search(r"/TB\s+(.+?)(?=\s*/|$)", raw)
    if tb_match:
        summary.append(f"Turbulence: {tb_match.group(1).strip()}")

    # Icing
    ic_match = re.search(r"/IC\s+(.+?)(?=\s*/|$)", raw)
    if ic_match:
        summary.append(f"Icing: {ic_match.group(1).strip()}")

    # Weather
    wx_match = re.search(r"/WX\s+([\w\s\-]+)", raw)
    if wx_match:
        summary.append(f"Weather: {wx_match.group(1).strip()}")

    # Remarks
    rm_match = re.search(r"/RM\s+(.+?)(?=$|\s*/)", raw)
    if rm_match:
        summary.append(f"Remarks: {rm_match.group(1).strip()}")

    return "; ".join(summary) if summary else "Unable to summarize PIREP."


def interpolate_points(start, end, interval_nm=50):
    total_distance = geodesic(start, end).nm
    steps = max(2, int(total_distance // interval_nm) + 1)
    lats = np.linspace(start[0], end[0], steps)
    lons = np.linspace(start[1], end[1], steps)
    return list(zip(lats, lons))

def find_weather_warnings_between_airports(airport1_json, airport2_json, threshold_nm=100, output_filename="pireps.json"):

    try:
        lat1 = airport1_json["weather"][0]["metar"][0]["lat"]
        lon1 = airport1_json["weather"][0]["metar"][0]["lon"]
        lat2 = airport2_json["weather"][0]["metar"][0]["lat"]
        lon2 = airport2_json["weather"][0]["metar"][0]["lon"]
    except Exception as e:
        print("Error parsing airport coordinates:", e)
        return []

    route_points = interpolate_points((lat1, lon1), (lat2, lon2))
    x=fetch_weather_for_route_points(route_points, output_filename="route_weather.json")
    while(x==False):
        time.sleep(1)
    
    
    pireps = []
    if "pirep" in airport1_json["weather"][0]:
        pireps.extend(airport1_json["weather"][0]["pirep"])
    if "pirep" in airport2_json["weather"][0]:
        pireps.extend(airport2_json["weather"][0]["pirep"])

    seen = set()
    warnings = []

    for pt in route_points:
        for pirep in pireps:
            try:
                pirep_lat = pirep["lat"]
                pirep_lon = pirep["lon"]
                distance = geodesic(pt, (pirep_lat, pirep_lon)).nm
                if distance <= threshold_nm:
                    
                    unique_key = (
                        round(pt[0], 4), round(pt[1], 4),
                        round(pirep_lat, 4), round(pirep_lon, 4),
                        pirep.get("rawOb", "")
                    )
                    if unique_key not in seen:
                        seen.add(unique_key)
                        warnings.append({
                            "distance_to_pirep_nm": round(distance, 1),
                            "pirep_raw": pirep.get("rawOb", "No raw PIREP available"),
                            "summary": summarize_pirep(pirep.get("rawOb", "")),
                            "lat": pirep_lat, 
                            "lon": pirep_lon
                        })
            except:
                continue

    output_data = {"pireps": warnings}
    
    
    
    with open(output_filename, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"✅ Saved {len(warnings)} unique weather warning points to {output_filename}")
    return True

def fetch_weather_for_route_points(route_points, output_filename="route_weather.json"):
    import requests
    import time

    weather_data = []

    for i, (lat, lon) in enumerate(route_points):
        try:
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": True
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            weather = data.get("current_weather", {})
            code = weather.get("weathercode")
            description = weather_code_descriptions.get(code, "Unknown weather code")
            is_severe = code in severe_weather_codes

            if(is_severe):
                weather_data.append({
                "point_index": i,
                "lat": lat,
                "lon": lon,
                    "code": code,
                    "description": description,
                    "temperature": weather.get("temperature"),
                    "windspeed": weather.get("windspeed"),
                    "is_severe": is_severe
                
            })
            time.sleep(0.5)  
        except Exception as e:
            weather_data.append({
                "point_index": i,
                "lat": lat,
                "lon": lon,
                "error": str(e)
            })

    output_data = {"warnings": weather_data}

    with open(output_filename, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"✅ Saved weather data for {len(route_points)} points to {output_filename}")
    return True


def fetch_metar(airport_id):
    url = f"https://aviationweather.gov/api/data/metar?ids={airport_id}&format=json"
    response = requests.get(url)
    return response.json()

def fetch_taf(airport_id):
    url = f"https://aviationweather.gov/api/data/taf?ids={airport_id}&format=json"
    response = requests.get(url)
    
    return response.json()

def fetch_pirep(airport_id):
    url = f"https://aviationweather.gov/api/data/pirep?ids={airport_id}&format=json"
    response1 = requests.get(url)
    response1=response1.json()
    return response1


def lat_log(airport_id):
    url = f"https://aviationweather.gov/api/data/airport?ids={airport_id}&format=json"
    response = requests.get(url)
    response=response.json()
    #print(response)
    coords = [response[0]['lat'],response[0]['lon']]
    return coords



def generate_quick(file_path):

    with open(file_path, 'r') as f:
        data = json.load(f)
    
    waypoints = data.get("waypoints", [])
    
    final_json_list=[]
    for waypoint in waypoints:
        airport_id = waypoint.get("airport_id")
        altitude=waypoint.get("altitude")
        output_airport_data={}
        weather_data = []
        print(f"📍 Airport: {airport_id}]")
    
        metar = fetch_metar(airport_id)
        taf = fetch_taf(airport_id)
        pirep = fetch_pirep(airport_id)
        lat,log=lat_log(airport_id)

        weather_data.append({
            "airport_id": airport_id,
            "altitude": altitude,
            "lat":lat,
            "log":log,
            "metar": metar,
            "taf": taf,
            "pirep": pirep,

        })
        print("weather collected")
        
        output_airport_data={"weather": weather_data}

        final_json_list.append(output_airport_data)
        print("weather appended")

        


    print("lenght of list",len(final_json_list))
     


    x=find_weather_warnings_between_airports(final_json_list[0],final_json_list[-1])
    return x



