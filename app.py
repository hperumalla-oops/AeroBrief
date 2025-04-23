import streamlit as st
import streamlit.components.v1 as components
import json
import uuid
from helper import parse_metar,summary,warning_level
from sigmet_translation import sigmet_json_generator
from pirep_and_path import generate_quick,lat_log 
from taf import get_formatted_taf
import time



st.set_page_config(layout="wide", page_title="Flight Weather Planning Tool")

airports=[]

st.title("Flight Weather Planning Tool")


if 'airports' not in st.session_state:
    st.session_state.airports = [{"id": str(uuid.uuid4()), "icao": "", "altitude": ""}]
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'add_airport' not in st.session_state:
    st.session_state.add_airport = False
if 'delete_airport' not in st.session_state:
    st.session_state.delete_airport = None
if 'airport_data' not in st.session_state:
    st.session_state.airport_data = []
if 'report' not in st.session_state:
    st.session_state.report = ''


if st.session_state.add_airport:
    st.session_state.airports.append({"id": str(uuid.uuid4()), "icao": "", "altitude": ""})
    st.session_state.add_airport = False

if st.session_state.delete_airport is not None:
    st.session_state.airports = [a for a in st.session_state.airports if a["id"] != st.session_state.delete_airport]
    st.session_state.delete_airport = None

if st.button("➕ Add Airport"):
    st.session_state.add_airport = True
    st.rerun()


for i, airport in enumerate(st.session_state.airports):
    cols = st.columns([3, 2, 1])
    with cols[0]:
        st.text_input("ICAO", value=airport["icao"], key=f"icao_{airport['id']}", 
                      on_change=lambda a_id=airport["id"], field="icao": setattr(
                          st.session_state, f"icao_{a_id}", st.session_state[f"icao_{a_id}"]))
    
    with cols[1]:
        st.text_input("Altitude (ft)", value=airport["altitude"], key=f"alt_{airport['id']}", 
                      on_change=lambda a_id=airport["id"], field="altitude": setattr(
                          st.session_state, f"alt_{a_id}", st.session_state[f"alt_{a_id}"]))
    
    with cols[2]:
        if len(st.session_state.airports) > 1:
            if st.button("❌", key=f"del_{airport['id']}"):
                st.session_state.delete_airport = airport["id"]
                st.rerun()


if st.button("Submit"):
    for airport in st.session_state.airports:
        airport["icao"] = st.session_state[f"icao_{airport['id']}"]
        airport["altitude"] = st.session_state[f"alt_{airport['id']}"]
        # airport["metar"]=fetch_metar()


        lat, lon= lat_log(airport["icao"])
        airports.append({
        "airport_id": airport["icao"],
        "altitude": airport["altitude"],
        "lat": lat,
        "log": lon,
        'warning_level': warning_level(['airport_id'])
        })

    output_data = {"waypoints": airports}
    with open("airports_st.json", "w") as f:
        json.dump(output_data, f, indent=2)
    
    st.session_state.airport_data = []
    for airport in st.session_state.airports:
        if airport["icao"]:
            k = parse_metar(airport["icao"])
            l = get_formatted_taf(airport["icao"])
            mock_data = {
                "icao": airport["icao"],
                "altitude": airport["altitude"],
                "metar":k,
                "taf": l
            }
            st.session_state.report += '\n'
            st.session_state.report += k
            st.session_state.report += '\n'
            st.session_state.report += l
            st.session_state.airport_data.append(mock_data)
    
    st.session_state.submitted = True
    st.rerun()

if st.session_state.submitted and st.session_state.airport_data:
    num_airports = len(st.session_state.airport_data)
    
    airport_cols = st.columns(num_airports)
    
    for i, col in enumerate(airport_cols):
        if i < len(st.session_state.airport_data):
            airport = st.session_state.airport_data[i]
            col.subheader(f"{airport['icao']} ({airport['altitude']} ft)")
    
    metar_cols = st.columns(num_airports)
    for i, col in enumerate(metar_cols):
        if i < len(st.session_state.airport_data):
            airport = st.session_state.airport_data[i]
            with col:
                with st.expander("METAR"):
                    st.text(airport["metar"])
    
    taf_cols = st.columns(num_airports)
    for i, col in enumerate(taf_cols):
        if i < len(st.session_state.airport_data):
            airport = st.session_state.airport_data[i]
            with col:
                with st.expander("TAF"):
                    st.text(airport["taf"]) ##########


    x=generate_quick('airports_st.json')
    # while(x==False):
    #     time.sleep(1)
    try:
        with open('pireps.json', 'r', encoding='utf-8') as f:
            pirep_data = json.load(f)
        for pirep in pirep_data['pireps']:
            st.session_state.report += "\n"
            st.session_state.report += pirep['summary']
    except Exception as e:
        st.error(f"Error loading pirep.json: {e}")
        pirep_data = {"pirep": []}

    try:
        with open('route_weather.json', 'r', encoding='utf-8') as f:
            route_weather_data = json.load(f)

    except Exception as e:
        st.error(f"Error loading route_weather.json: {e}")
        route_weather_data = {"warnings": []}


    try:
        sigmet_json_generator('airports_st.json')
        with open('sigmets_new.json', 'r', encoding='utf-8') as f:
            sigmet_data = json.load(f)
        for pirep in sigmet_data['sigmet']:
            st.session_state.report += "\n"
            st.session_state.report += pirep['sigmet_eng']
    except Exception as e:
        st.error(f"Error loading sigmet.json: {e}")
        sigmet_data = {"sigmet": []}

    try:
        with open('airports_st.json', 'r', encoding='utf-8') as f:
            airports_data = json.load(f)
    except Exception as e:
        st.error(f"Error loading airports.json: {e}")
        airports_data = {"waypoints": []}

    

    with open('index.html', 'r', encoding='utf-8') as file:
        html_content = file.read()

    split_point = html_content.find('fetch(\'pirep.json\')')
    if split_point == -1:
        st.error("Could not find the insertion point in HTML")
    else:
        html_first_part = html_content[:split_point]
        
        script_end = html_content.find('</script>', split_point)
        html_last_part = html_content[script_end:] if script_end != -1 else ""
        
        new_js = f"""
        function createCurvedLine(startPoint, endPoint) {{
            const latlngs = [];
            const points = 20; 
            
            const midLat = (startPoint[0] + endPoint[0]) / 2;
            const midLon = (startPoint[1] + endPoint[1]) / 2;
            const distance = Math.sqrt(
                Math.pow(endPoint[0] - startPoint[0], 2) + 
                Math.pow(endPoint[1] - startPoint[1], 2)
            );
            
            const curveHeight = distance * 0.15; 
            
            for (let i = 0; i <= points; i++) {{
                const t = i / points;
                
                const lat = (1-t)*(1-t)*startPoint[0] + 
                           2*(1-t)*t*(midLat + curveHeight) + 
                           t*t*endPoint[0];
                           
                const lon = (1-t)*(1-t)*startPoint[1] + 
                           2*(1-t)*t*midLon + 
                           t*t*endPoint[1];
                           
                latlngs.push([lat, lon]);
            }}
            
            return latlngs;
        }}

        const pireps = {json.dumps(pirep_data['pireps'])};
        pireps.forEach(p => {{
        if (!p.lat || !p.lon) return;
        const info = `${{p.summary || 'N/A'}}`;

        L.circleMarker([p.lat, p.lon], {{
            radius: 5,
            fillColor: "blue",
            color: "black",
            weight: 1,
            fillOpacity: 0.8
        }}).addTo(map).bindPopup(info);
        }});

        const warnings = {json.dumps(route_weather_data['warnings'])};
        warnings.forEach(p => {{
        if (!p.lat || !p.lon) return;
        const info = `Description: ${{p.description || 'N/A'}}<br>Temp: ${{p.temperature}}°C<br>Windspeed: ${{p.windspeed}}kt<br>code: ${{p.code}}`;

        L.circleMarker([p.lat, p.lon], {{
            radius: 7,
            fillColor: "yellow",
            color: "yellow",
            weight: 1,
            fillOpacity: 0.8
        }}).addTo(map).bindPopup(info);
  
        }});


        const sigmets = {json.dumps(sigmet_data['sigmet'])};
        sigmets.forEach(p => {{
            if (!p.coords || p.coords.length < 3) return; // Need at least 3 points
            
            const info = `${{p.sigmet_eng || 'N/A'}}`;
            
            const latlngs = p.coords.map(c => [c.lat, c.lon]);
            
            const color = getSeverityColor(p.severity);
            
            L.polygon(latlngs, {{
                color: color,
                weight: 2,
                fillOpacity: 0.4
            }}).addTo(map).bindPopup(info);
        }});

        const waypoints = {json.dumps(airports_data['waypoints'])};
        
        const lowAltitudeAirports = waypoints.filter(airport => airport.altitude < 9000);
        const highAltitudeAirports = waypoints.filter(airport => airport.altitude >= 9000);
        
        lowAltitudeAirports.forEach(airport => {{
            L.marker([airport.lat, airport.log]).addTo(map).bindPopup(`${{airport.airport_id}}<br>Altitude: ${{airport.altitude}} ft`);

        }});
        
        highAltitudeAirports.forEach(airport => {{
            L.marker([airport.lat, airport.log]).addTo(map).bindPopup(`${{airport.airport_id}}<br>Altitude: ${{airport.altitude}} ft`);
        }});

        lowAltitudeAirports.concat(highAltitudeAirports).forEach(airport => {{
        const warningLevel = airport.warning_level || 5; 
        let circleColor = 'grey'; 
        let circleLabel = 'UNKNOWN';
        
        switch(warningLevel) {{
            case 1:
            circleColor = '#00FF00'; // Green for VFR
            circleLabel = 'VFR';
            break;
            case 2:
            circleColor = '#FFFF00'; // Yellow for MVFR
            circleLabel = 'MVFR';
            break;
            case 3:
            circleColor = '#FF9900'; // Orange for IFR
            circleLabel = 'IFR';
            break;
            case 4:
            circleColor = '#FF0000'; // Red for LIFR
            circleLabel = 'LIFR';
            break;
        }}
        
        L.circle([airport.lat, airport.log], {{
            color: circleColor,
            fillColor: circleColor,
            fillOpacity: 0.2,
            radius: 5000, // 5km radius, adjust as needed
            weight: 1
        }}).addTo(map).bindTooltip(circleLabel);
        }});

        
        
        if (lowAltitudeAirports.length >= 2) {{
            lowAltitudeAirports.sort((a, b) => a.log - b.log);
            
            for (let i = 0; i < lowAltitudeAirports.length - 1; i++) {{
                const start = [lowAltitudeAirports[i].lat, lowAltitudeAirports[i].log];
                const end = [lowAltitudeAirports[i+1].lat, lowAltitudeAirports[i+1].log];
                
                const latlngs = createCurvedLine(start, end);
                
                L.polyline(latlngs, {{
                    color: 'black',
                    weight: 3,
                    opacity: 0.7,
                    curvature: 0.3
                }}).addTo(map);
            }}
        }}
        """
        

        final_html = html_first_part + new_js + html_last_part

        st.subheader("Flight Route Map")

        components.html(final_html, height=600)

    st.sidebar.header("Map Information")
    st.sidebar.info("""
    - Markers: All Airports
    - Blue circles: PIREP data points
    - Colored polygons: SIGMET warnings
    - Yellow circles: en-route warnings
    """)
    st.subheader("Flight Route Map")
    # components.html(html_content, height=500)
    
    st.subheader("Flight Summary")
    with st.container(border=True):
        final = summary(st.session_state.report)
        st.markdown(final)
        
   
