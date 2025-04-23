import streamlit as st
import streamlit.components.v1 as components
import json
import uuid
from helper import parse_metar
from sigmet_translation import sigmet_json_generator
from pirep_and_path import generate_quick,lat_log 
from taf import get_formatted_taf
import time


# def fetch_metar():
#     return "this is awesome!!!!!\n"
# Set page configuration
st.set_page_config(layout="wide", page_title="Flight Weather Planning Tool")

airports=[]
# Title of the app
st.title("Flight Weather Planning Tool")

# Initialize session state variables
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
    st.session_state.report = {}

# Callbacks for actions outside the form
if st.session_state.add_airport:
    st.session_state.airports.append({"id": str(uuid.uuid4()), "icao": "", "altitude": ""})
    st.session_state.add_airport = False

if st.session_state.delete_airport is not None:
    st.session_state.airports = [a for a in st.session_state.airports if a["id"] != st.session_state.delete_airport]
    st.session_state.delete_airport = None

# Add Airport button (outside the form)
if st.button("➕ Add Airport"):
    st.session_state.add_airport = True
    st.rerun()

# Airport input fields
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

# Submit button (outside the form)
if st.button("Submit"):
    # Update airport data from form
    for airport in st.session_state.airports:
        airport["icao"] = st.session_state[f"icao_{airport['id']}"]
        airport["altitude"] = st.session_state[f"alt_{airport['id']}"]
        # airport["metar"]=fetch_metar()


        lat, lon= lat_log(airport["icao"])
        airports.append({
        "airport_id": airport["icao"],
        "altitude": airport["altitude"],
        "lat": lat,
        "log": lon
        })

    output_data = {"waypoints": airports}
    with open("airports_st.json", "w") as f:
        json.dump(output_data, f, indent=2)
    
    # Create airport data for display
    st.session_state.airport_data = []
    for airport in st.session_state.airports:
        if airport["icao"]:
            # Mock data - in reality you'd fetch this from your backend
            print(st.session_state.report)
            # st.session_state.report = fetch_metar([airport["icao"]])
            mock_data = {
                "icao": airport["icao"],
                "altitude": airport["altitude"],
                "metar":parse_metar(airport["icao"]),
                "taf": get_formatted_taf(airport["icao"]),
            }
            st.session_state.airport_data.append(mock_data)
    
    st.session_state.submitted = True
    st.rerun()

# Display airport data if submitted
if st.session_state.submitted and st.session_state.airport_data:
    # Display airports side by side
    num_airports = len(st.session_state.airport_data)
    
    # Create columns for airports
    airport_cols = st.columns(num_airports)
    
    # Display airport headers
    for i, col in enumerate(airport_cols):
        if i < len(st.session_state.airport_data):
            airport = st.session_state.airport_data[i]
            col.subheader(f"{airport['icao']} ({airport['altitude']} ft)")
    
    # Create columns for METAR expandables
    metar_cols = st.columns(num_airports)
    for i, col in enumerate(metar_cols):
        if i < len(st.session_state.airport_data):
            airport = st.session_state.airport_data[i]
            with col:
                with st.expander("METAR"):
                    st.text(airport["metar"])
    
    # Create columns for TAF expandables
    taf_cols = st.columns(num_airports)
    for i, col in enumerate(taf_cols):
        if i < len(st.session_state.airport_data):
            airport = st.session_state.airport_data[i]
            with col:
                with st.expander("TAF"):
                    st.text(airport["taf"]) ##########

    # Load and display the map
    # Load your JSON data
    x=generate_quick('airports_st.json')
    # while(x==False):
    #     time.sleep(1)
    try:
        with open('pireps.json', 'r', encoding='utf-8') as f:
            pirep_data = json.load(f)
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
    except Exception as e:
        st.error(f"Error loading sigmet.json: {e}")
        sigmet_data = {"sigmet": []}

    try:
        with open('airports_st.json', 'r', encoding='utf-8') as f:
            airports_data = json.load(f)
    except Exception as e:
        st.error(f"Error loading airports.json: {e}")
        airports_data = {"waypoints": []}

    

    # Read your HTML template and modify it to use the injected data
    with open('index.html', 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Split the HTML at the point where we want to inject our data
    split_point = html_content.find('fetch(\'pirep.json\')')
    if split_point == -1:
        st.error("Could not find the insertion point in HTML")
    else:
        # Take everything before the fetch commands
        html_first_part = html_content[:split_point]
        
        # Find the end of the script tag
        script_end = html_content.find('</script>', split_point)
        html_last_part = html_content[script_end:] if script_end != -1 else ""
        
        # Create new JS that uses our injected data instead of fetching
        new_js = f"""
          // Function to create a slightly upward curved line between two points
        function createCurvedLine(startPoint, endPoint) {{
            const latlngs = [];
            const points = 20; // Number of points to create a smooth curve
            
            // Calculate control point (for upward curve)
            const midLat = (startPoint[0] + endPoint[0]) / 2;
            const midLon = (startPoint[1] + endPoint[1]) / 2;
            const distance = Math.sqrt(
                Math.pow(endPoint[0] - startPoint[0], 2) + 
                Math.pow(endPoint[1] - startPoint[1], 2)
            );
            
            // Make the curve higher for longer distances
            const curveHeight = distance * 0.15; // Controls how much the curve bends upward
            
            // Create a quadratic Bezier curve
            for (let i = 0; i <= points; i++) {{
                const t = i / points;
                
                // Quadratic Bezier curve formula
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

        // Data injected by Streamlit
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

        // Add route weather warnings to the map
        const warnings = {json.dumps(route_weather_data['warnings'])};
        warnings.forEach(p => {{
        if (!p.lat || !p.lon) return;
        const info = `Description: ${{p.description || 'N/A'}}<br>Temp: ${{p.temperature}}°C<br>Windspeed: ${{p.windspeed}}kt<br>code: ${{p.code}}`;

        // Create a warning icon
        const warningIcon = L.divIcon({{
            html: '<i class="fa fa-exclamation-triangle" style="color: #ff0000; font-size: 16px;"></i>',
            className: 'warning-marker',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        }});
  
        L.marker([p.lat, p.lon], {{icon: warningIcon}}).addTo(map).bindPopup(info);
        }});


        // SIGMET data
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

        // Airport data
        const waypoints = {json.dumps(airports_data['waypoints'])};
        
        // Filter airports by altitude
        const lowAltitudeAirports = waypoints.filter(airport => airport.altitude < 9000);
        const highAltitudeAirports = waypoints.filter(airport => airport.altitude >= 9000);
        
        // Add markers for all airports
        lowAltitudeAirports.forEach(airport => {{
            L.marker([airport.lat, airport.log], {{
                icon: L.divIcon({{
                    className: 'airport-marker low-altitude',
                    html: `<div style="width: 10px; height: 10px; background-color: black; transform: rotate(45deg);"></div>`,
                    iconSize: [10, 10]
                }})
            }}).addTo(map).bindPopup(`${{airport.airport_id}}<br>Altitude: ${{airport.altitude}} ft`);
        }});
        
        highAltitudeAirports.forEach(airport => {{
            L.marker([airport.lat, airport.log], {{
                icon: L.divIcon({{
                    className: 'airport-marker high-altitude',
                    html: `<div style="background-color: red; width: 10px; height: 10px; border-radius: 50%;"></div>`,
                    iconSize: [10, 10]
                }})
            }}).addTo(map).bindPopup(`${{airport.airport_id}}<br>Altitude: ${{airport.altitude}} ft`);
        }});
        
        // Draw curved lines between low altitude airports if there are at least 2
        if (lowAltitudeAirports.length >= 2) {{
            // Sort airports west to east for connection
            lowAltitudeAirports.sort((a, b) => a.log - b.log);
            
            // Connect the airports with curved lines
            for (let i = 0; i < lowAltitudeAirports.length - 1; i++) {{
                const start = [lowAltitudeAirports[i].lat, lowAltitudeAirports[i].log];
                const end = [lowAltitudeAirports[i+1].lat, lowAltitudeAirports[i+1].log];
                
                // Create a curved line
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

        # Combine everything
        final_html = html_first_part + new_js + html_last_part

        # Render the combined HTML
        st.subheader("Flight Route Map")

        components.html(final_html, height=600)

    # Information sidebar
    st.sidebar.header("Map Information")
    st.sidebar.info("""
    - Black squares: Low altitude airports (<9000 ft)
    - Red circles: High altitude airports (≥9000 ft)
    - Blue circles: PIREP data points
    - Colored polygons: SIGMET warnings
    """)
    # Display the map
    st.subheader("Flight Route Map")
    # components.html(html_content, height=500)
    
    # Display summary section
    st.subheader("Flight Summary")
    with st.container(border=True):
        st.write("This is the summary of your flight plan based on the weather conditions.")
        
        # In a real app, you would generate this summary based on the weather data
        airport_list = ", ".join([a["icao"] for a in st.session_state.airport_data])
        st.write(f"Flight route: {airport_list}")
        st.write("Weather conditions appear favorable for your flight plan.")
        st.write("No significant weather hazards detected along your route.")
