import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

try:
    from PIL import Image, ImageDraw
except ImportError:
    pass

LAT, LON = 69.6492, 18.9553  # Tromsø
USER_AGENT = "NookDashboard/1.0 (+https://github.com/dinbruker)"
TIMEZONE = ZoneInfo("Europe/Oslo")
AVINOR_URL = "https://asrv.avinor.no/XmlFeed/v1.0?airport=TOS"

# En samling med stilrene, svarte/hvite SVG-ikoner som runder perfekt på e-blekk
WEATHER_ICONS = {
    "SUN": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:80px;height:80px;"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path></svg>""",
    "CLOUD": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:80px;height:80px;"><path d="M17.5 19A3.5 3.5 0 0 0 21 15.5c0-2.79-2.54-4.5-5-4.5-.42-3.92-3.84-7-7.75-7A7.32 7.32 0 0 0 2 11.25c0 4.14 3.36 7.5 7.5 7.5h8"></path></svg>""",
    "RAIN": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:80px;height:80px;"><path d="M16 13a4 4 0 0 0-8 0"></path><path d="M12 5v13M8 10v4M16 10v4"></path></svg>""",
    "SNOW": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:80px;height:80px;"><path d="M12 2v20M17 5L7 19M19 17L5 7M22 12H2"></path></svg>""",
    "THUNDER": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:80px;height:80px;"><path d="M19 10.93A7 7 0 0 0 5 11.25c0 4.14 3.36 7.5 7.5 7.5h1.75"></path><path d="m13 22 3-6h-5l3-6"></path></svg>""",
    "FOG": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:80px;height:80px;"><path d="M5 8h14M3 12h18M5 16h14M7 20h10"></path></svg>"""
}

def get_weather():
    headers = {'User-Agent': USER_AGENT}
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={LAT}&lon={LON}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        now = data['properties']['timeseries'][0]['data']['instant']['details']
        temp = round(now['air_temperature'])
        wind = round(now['wind_speed'])
        humidity = round(now['relative_humidity'])
        
        next_hour = data['properties']['timeseries'][0]['data'].get('next_1_hours', {})
        symbol_code = next_hour.get('summary', {}).get('symbol_code', 'unknown')
        
        # Finn ut hvilket ikon som passer best basert på teksten fra Met.no
        symbol_clean = symbol_code.lower()
        if "thunder" in symbol_clean:
            icon_svg = WEATHER_ICONS["THUNDER"]
        elif "snow" in symbol_clean or "sleet" in symbol_clean:
            icon_svg = WEATHER_ICONS["SNOW"]
        elif "rain" in symbol_clean or "shower" in symbol_clean:
            icon_svg = WEATHER_ICONS["RAIN"]
        elif "fog" in symbol_clean:
            icon_svg = WEATHER_ICONS["FOG"]
        elif "clearsky" in symbol_clean or "fair" in symbol_clean:
            icon_svg = WEATHER_ICONS["SUN"]
        else:
            icon_svg = WEATHER_ICONS["CLOUD"] # Default fallback
            
        weather_text = symbol_code.replace("_day", "").replace("_night", "").replace("_", " ").upper()
        return {"temp": f"{temp}°", "wind": f"{wind} m/s", "humidity": f"{humidity}%", "summary": weather_text, "icon": icon_svg}
    except Exception as e:
        return {"temp": "--°", "wind": "- m/s", "humidity": "-%", "summary": "UKJENT VÆR", "icon": WEATHER_ICONS["CLOUD"]}

def get_next_flight():
    try:
        response = requests.get(AVINOR_URL, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        flights = []
        
        for flight in root.findall('.//flight'):
            arr_dep_node = flight.find('arr_dep')
            if arr_dep_node is not None and arr_dep_node.text == 'A':
                flight_id_node = flight.find('flight_id')
                airport_node = flight.find('airport')
                sched_time_node = flight.find('schedule_time')
                
                if flight_id_node is not None and airport_node is not None and sched_time_node is not None:
                    flights.append({
                        "time_raw": sched_time_node.text,
                        "id": flight_id_node.text.strip(),
                        "origin": airport_node.text.upper().strip()
                    })
        
        if not flights:
            return {"time": "--:--", "id": "Ingen fly funnet", "origin": "FRA: -", "raw_id": ""}
            
        flights.sort(key=lambda x: x["time_raw"])
        
        nå_utc = datetime.now(ZoneInfo("UTC"))
        grense_fortid = nå_utc - timedelta(hours=2)
        
        kommende_fly = []
        for f in flights:
            fly_tid = datetime.fromisoformat(f["time_raw"].replace('Z', '+00:00'))
            if fly_tid > grense_fortid:
                kommende_fly.append(f)
                
        neste = kommende_fly[0] if kommende_fly else flights[0]
        dt_lokal = datetime.fromisoformat(neste["time_raw"].replace('Z', '+00:00')).astimezone(TIMEZONE)
        status_tid = dt_lokal.strftime("%H:%M")
        
        return {
            "time": status_tid,
            "id": f"FLIGHT: {neste['id']}",
            "origin": f"FRA: {neste['origin']}",
            "raw_id": neste['id']
        }
    except Exception as e:
        print(f"Feil ved parsing av Avinor XML: {e}")
        return {"time": "--:--", "id": "Feil ved henting", "origin": "FRA: -", "raw_id": ""}

def generate_html():
    now_local = datetime.now(TIMEZONE)
    current_date = now_local.strftime("%A, %B %d").upper()
    weather = get_weather()
    flight = get_next_flight()
    
    html_content = """<!DOCTYPE html>
<html lang="no">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nook Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Open Sans', sans-serif;
            background-color: #ffffff;
            color: #000000;
            margin: 0;
            padding: 40px 20px;
            width: 600px;
            height: 800px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .top-section { text-align: center; margin-top: 20px; }
        .clock { font-size: 110px; font-weight: 700; letter-spacing: -2px; margin: 0; line-height: 1; }
        .date { font-size: 22px; font-weight: 400; color: #555555; margin-top: 15px; letter-spacing: 1px; }
        .divider { border-top: 1px solid #e0e0e0; width: 85%; margin: 40px auto; }
        .bottom-section { display: flex; flex: 1; padding: 0 20px; }
        .column { flex: 1; display: flex; flex-direction: column; }
        .left-column { padding-right: 20px; border-right: 1px solid #e0e0e0; }
        .right-column { padding-left: 30px; }
        .label-top { font-size: 16px; font-weight: 700; letter-spacing: 2px; margin: 0 0 5px 0; }
        .label-sub { font-size: 14px; font-weight: 400; color: #777777; margin: 0 0 25px 0; letter-spacing: 1px; }
        .weather-icon-container { margin: 10px 0 15px 0; height: 80px; }
        .huge-data { font-size: 75px; font-weight: 700; margin: 0 0 25px 0; line-height: 1; }
        .detail-text { font-size: 18px; font-weight: 400; margin: 8px 0; color: #222222; }
        .radar-live-badge { display: inline-block; background-color: #000000; color: #ffffff; font-size: 12px; padding: 2px 6px; font-weight: bold; margin-left: 10px; vertical-align: middle; }
        #debug-log { font-size: 10px; color: #aaaaaa; text-align: center; margin-top: 10px; font-family: monospace; }
    </style>
</head>
<body>

    <div class="top-section">
        <h1 class="clock" id="live-clock">--:--</h1>
        <div class="date">__CURRENT_DATE__</div>
    </div>
    
    <div class="divider"></div>
    
    <div class="bottom-section">
        <div class="column left-column">
            <h2 class="label-top">TROMSØ</h2>
            <h3 class="label-sub">__WEATHER_SUMMARY__</h3>
            <div class="weather-icon-container">__WEATHER_ICON__</div>
            <div class="huge-data">__WEATHER_TEMP__</div>
            <div class="detail-text">VIND: __WEATHER_WIND__</div>
            <div class="detail-text">FUKTIGHET: __WEATHER_HUMIDITY__</div>
        </div>
        
        <div class="column right-column">
            <h2 class="label-top">NESTE ANKOMST</h2>
            <h3 class="label-sub" id="flight-status-sub">TOS / ENTC</h3>
            <div style="height: 80px;"></div> <div class="huge-data" id="flight-time">__FLIGHT_TIME__</div>
            <div class="detail-text" id="flight-id">__FLIGHT_ID__</div>
            <div class="detail-text" id="flight-origin">__FLIGHT_ORIGIN__</div>
            <div class="detail-text" id="flight-radar" style="font-weight: bold; margin-top: 15px;">Sjekker radar...</div>
        </div>
    </div>

    <div id="debug-log">System OK</div>

    <script>
        function logg(tekst) {
            document.getElementById("debug-log").innerText = tekst;
        }

        function updateClock() {
            var now = new Date();
            var timer = now.getHours().toString().padStart(2, '0');
            var minutter = now.getMinutes().toString().padStart(2, '0');
            document.getElementById('live-clock').innerText = timer + ":" + minutter;
        }
        setInterval(updateClock, 1000);
        updateClock();

        var tosLat = 69.683;
        var tosLon = 18.919;
        var flynr = "__RAW_FLIGHT_ID__".replace(/\s+/g, '').toUpperCase();
        var radarUrl = "https://corsproxy.io/?https://data-cloud.flightradar24.com/zones/fcgi/feed.js?bounds=72.000,65.000,10.000,30.000%26faa=1%26flight_states=1%26satellite=1%26mlat=1%26flarm=1%26adsb=1%26gnd=1%26air=1%26vehicles=0%26estimated=1";

        function kalkulerAvstand(lat1, lon1, lat2, lon2) {
            var x = (lon2 - lon1) * Math.cos((lat1 + lat2) / 2 * 3.14159265 / 180) * 111.32;
            var y = (lat2 - lat1) * 111.13;
            return Math.sqrt(x * x + y * y);
        }

        function sjekkRadar() {
            if (!flynr || flynr === "") {
                document.getElementById("flight-radar").innerText = "Ingen data";
                return;
            }
            
            logg("Sjekker radar for " + flynr + "...");
            var xhrRadar = new XMLHttpRequest();
            xhrRadar.open("GET", radarUrl + "%26_" + new Date().getTime(), true);
            xhrRadar.onreadystatechange = function () {
                if (xhrRadar.readyState === 4 && xhrRadar.status === 200) {
                    try {
                        var radarData = JSON.parse(xhrRadar.responseText);
                        var match = null;
                        var altSøk1 = flynr.replace("SK", "SAS").replace("WF", "WIF").replace("DY", "NAX").replace("D8", "IBK");
                        var altSøk2 = flynr.replace("SAS", "SK").replace("WIF", "WF").replace("NAX", "DY").replace("IBK", "D8");

                        for (var nøkkel in radarData) {
                            if (nøkkel !== "full_count" && nøkkel !== "version" && nøkkel !== "stats") {
                                var f = radarData[nøkkel];
                                var rutenummer = (f[13] || "").replace(/\s+/g, '').toUpperCase();
                                var callsign = (f[16] || "").replace(/\s+/g, '').toUpperCase();
                                
                                if (rutenummer === flynr || callsign === flynr || 
                                    rutenummer === altSøk1 || callsign === altSøk1 ||
                                    rutenummer === altSøk2 || callsign === altSøk2) {
                                    
                                    match = {
                                        høyde: f[4] === 0 ? "Bakken" : f[4] + " ft",
                                        fart: f[5] + " kt",
                                        avstand: kalkulerAvstand(tosLat, tosLon, f[1], f[2])
                                    };
                                    break;
                                }
                            }
                        }
                        
                        if (match) {
                            document.getElementById("flight-status-sub").innerHTML = "TOS / ENTC <span class='radar-live-badge'>RADAR LIVE</span>";
                            document.getElementById("flight-radar").innerHTML = match.avstand.toFixed(0) + " km unna<br>" + match.høyde + " / " + match.fart;
                            logg("Radar funnet for " + flynr);
                        } else {
                            document.getElementById("flight-status-sub").innerText = "TOS / ENTC";
                            document.getElementById("flight-radar").innerText = "Ikke i radarområdet ennå";
                            logg("Fant ikke flyet i lufta akkurat nå.");
                        }
                    } catch (e) {
                        document.getElementById("flight-radar").innerText = "Radarfeil";
                    }
                }
            };
            xhrRadar.send();
        }

        sjekkRadar();
        setInterval(sjekkRadar, 30000);
    </script>
</body>
</html>
"""
    
    html_content = html_content.replace("__CURRENT_DATE__", current_date)
    html_content = html_content.replace("__WEATHER_SUMMARY__", weather["summary"])
    html_content = html_content.replace("__WEATHER_TEMP__", weather["temp"])
    html_content = html_content.replace("__WEATHER_WIND__", weather["wind"])
    html_content = html_content.replace("__WEATHER_HUMIDITY__", weather["humidity"])
    html_content = html_content.replace("__WEATHER_ICON__", weather["icon"])  # Limer inn det grafiske ikonet
    
    html_content = html_content.replace("__FLIGHT_TIME__", flight["time"])
    html_content = html_content.replace("__FLIGHT_ID__", flight["id"])
    html_content = html_content.replace("__FLIGHT_ORIGIN__", flight["origin"])
    html_content = html_content.replace("__RAW_FLIGHT_ID__", flight["raw_id"])

    with open("time.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("time.html oppdatert med stilrene vaer-ikoner!")

if __name__ == "__main__":
    generate_html()
