import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

LAT, LON = 69.6492, 18.9553  # Tromsø
USER_AGENT = "NookDashboard/1.0 (+https://github.com/dinbruker)"
TIMEZONE = ZoneInfo("Europe/Oslo")
AVINOR_URL = "https://asrv.avinor.no/XmlFeed/v1.0?airport=TOS"

WEATHER_UNICODE = {
    "SUN": "☀️",
    "CLOUD": "☁️",
    "RAIN": "🌧️",
    "SNOW": "🌨️",
    "THUNDER": "⛈️",
    "FOG": "🌫️",
    "UNKNOWN": "✨"
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
        symbol_code = next_hour.get('summary', {}).get('symbol_code', 'unknown').lower()
        
        if "thunder" in symbol_code:
            icon = WEATHER_UNICODE["THUNDER"]
        elif "snow" in symbol_code or "sleet" in symbol_code:
            icon = WEATHER_UNICODE["SNOW"]
        elif "rain" in symbol_code or "shower" in symbol_code or "drizzle" in symbol_code:
            icon = WEATHER_UNICODE["RAIN"]
        elif "fog" in symbol_code or "misted" in symbol_code:
            icon = WEATHER_UNICODE["FOG"]
        elif "clear" in symbol_code or "fair" in symbol_code:
            icon = WEATHER_UNICODE["SUN"]
        else:
            icon = WEATHER_UNICODE["CLOUD"]
            
        weather_text = symbol_code.replace("_day", "").replace("_night", "").replace("_", " ").upper()
        return {"temp": f"{temp}°", "wind": f"{wind} m/s", "humidity": f"{humidity}%", "summary": weather_text, "icon": icon}
    except Exception as e:
        return {"temp": "--°", "wind": "- m/s", "humidity": "-%", "summary": "UKJENT VÆR", "icon": "☁️"}

def get_next_flights():
    try:
        response = requests.get(AVINOR_URL, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        flights = []
        
        for flight in root.findall('.//flight'):
            arr_dep_node = flight.find('arr_dep')
            if arr_dep_node is not None and arr_dep_node.text == 'A':
                flight_id = flight.find('flight_id')
                airport = flight.find('airport')
                sched_time = flight.find('schedule_time')
                
                if flight_id is not None and airport_node is not None and sched_time is not None:
                    flights.append({
                        "time_raw": sched_time.text,
                        "id": flight_id.text.strip(),
                        "origin": airport.text.upper().strip()
                    })
        
        flights.sort(key=lambda x: x["time_raw"])
        
        nå_utc = datetime.now(ZoneInfo("UTC"))
        grense_fortid = nå_utc - timedelta(minutes=30)
        
        kommende = [f for f in flights if datetime.fromisoformat(f["time_raw"].replace('Z', '+00:00')) > grense_fortid]
        if not kommende:
            kommende = flights[:5]
            
        js_flights = []
        for f in kommende[:5]:
            dt_lokal = datetime.fromisoformat(f["time_raw"].replace('Z', '+00:00')).astimezone(TIMEZONE)
            js_flights.append({
                "id": f["id"],
                "time": dt_lokal.strftime("%H:%M"),
                "origin": f["origin"]
            })
        return js_flights
    except Exception as e:
        print(f"Feil ved Avinor-henting: {e}")
        return []

def generate_html():
    now_local = datetime.now(TIMEZONE)
    current_date = now_local.strftime("%A, %B %d").upper()
    weather = get_weather()
    flights_list = get_next_flights()
    
    import json
    flights_json = json.dumps(flights_list)
    
    html_content = """<!DOCTYPE html>
<html lang="no">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="300">
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
        .label-sub { font-size: 14px; font-weight: 400; color: #777777; margin: 0 0 10px 0; letter-spacing: 1px; }
        .weather-icon { font-size: 65px; margin: 10px 0; line-height: 1; }
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
            <div class="weather-icon">__WEATHER_ICON__</div>
            <div class="huge-data">__WEATHER_TEMP__</div>
            <div class="detail-text">VIND: __WEATHER_WIND__</div>
            <div class="detail-text">FUKTIGHET: __WEATHER_HUMIDITY__</div>
        </div>
        
        <div class="column right-column">
            <h2 class="label-top">NESTE ANKOMST</h2>
            <h3 class="label-sub" id="flight-status-sub">TOS / ENTC</h3>
            <div style="height: 75px;"></div>
            <div class="huge-data" id="flight-time">--:--</div>
            <div class="detail-text" id="flight-id">Laster rutetider...</div>
            <div class="detail-text" id="flight-origin">FRA: -</div>
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
            var timer = now.getHours().toString();
            var minutter = now.getMinutes().toString();
            if (timer.length < 2) timer = "0" + timer;
            if (minutter.length < 2) minutter = "0" + minutter;
            document.getElementById('live-clock').innerText = timer + ":" + minutter;
        }
        setInterval(updateClock, 1000);
        updateClock();

        var tosLat = 69.683;
        var tosLon = 18.919;
        var avinorFlights = __FLIGHTS_JSON__;
        var radarUrl = "https://corsproxy.io/?https://data-cloud.flightradar24.com/zones/fcgi/feed.js?bounds=72.000,65.000,10.000,30.000%26faa=1%26flight_states=1%26satellite=1%26mlat=1%26flarm=1%26adsb=1%26gnd=1%26air=1%26vehicles=0%26estimated=1";

        function kalkulerAvstand(lat1, lon1, lat2, lon2) {
            var x = (lon2 - lon1) * Math.cos((lat1 + lat2) / 2 * 3.14159265 / 180) * 111.32;
            var y = (lat2 - lat1) * 111.13;
            return Math.sqrt(x * x + y * y);
        }

        function sjekkRadarOgOppdater() {
            if (!avinorFlights || avinorFlights.length === 0) {
                document.getElementById("flight-id").innerText = "Ingen ruter tilgjengelig";
                return;
            }

            logg("Sjekker radarfeeden live...");
            var xhrRadar = new XMLHttpRequest();
            xhrRadar.open("GET", radarUrl + "%26_" + new Date().getTime(), true);
            xhrRadar.onreadystatechange = function () {
                if (xhrRadar.readyState === 4 && xhrRadar.status === 200) {
                    try {
                        var radarData = JSON.parse(xhrRadar.responseText);
                        var activeMatch = null;
                        var activeFlightInfo = null;

                        for (var i = 0; i < avinorFlights.length; i++) {
                            var avinorFly = avinorFlights[i];
                            var fId = avinorFly.id.replace(/\s+/g, '').toUpperCase();
                            var altSøk1 = fId.replace("SK", "SAS").replace("WF", "WIF").replace("DY", "NAX").replace("D8", "IBK");
                            var altSøk2 = fId.replace("SAS", "SK").replace("WIF", "WF").replace("NAX", "DY").replace("IBK", "D8");

                            for (var nøkkel in radarData) {
                                if (nøkkel !== "full_count" && nøkkel !== "version" && nøkkel !== "stats") {
                                    var f = radarData[nøkkel];
                                    var rutenummer = (f[13] || "").replace(/\s+/g, '').toUpperCase();
                                    var callsign = (f[16] || "").replace(/\s+/g, '').toUpperCase();

                                    if (rutenummer === fId || callsign === fId || 
                                        rutenummer === altSøk1 || callsign === altSøk1 ||
                                        rutenummer === altSøk2 || callsign === altSøk2) {
                                        
                                        activeMatch = {
                                            høyde: f[4] === 0 ? "Bakken" : f[4] + " ft",
                                            fart: f[5] + " kt",
                                            avstand: kalkulerAvstand(tosLat, tosLon, f[1], f[2])
                                        };
                                        activeFlightInfo = avinorFly;
                                        break;
                                    }
                                }
                            }
                            if (activeMatch) break;
                        }

                        if (activeMatch && activeFlightInfo) {
                            document.getElementById("flight-time").innerText = activeFlightInfo.time;
                            document.getElementById("flight-id").innerText = "FLIGHT: " + activeFlightInfo.id;
                            document.getElementById("flight-origin").innerText = "FRA: " + activeFlightInfo.origin;
                            document.getElementById("flight-status-sub").innerHTML = "TOS / ENTC <span class='radar-live-badge'>RADAR LIVE</span>";
                            document.getElementById("flight-radar").innerHTML = activeMatch.avstand.toFixed(0) + " km unna<br>" + activeMatch.høyde + " / " + activeMatch.fart;
                            logg("Viser live flygning: " + activeFlightInfo.id);
                        } else {
                            var standardFly = avinorFlights[0];
                            document.getElementById("flight-time").innerText = standardFly.time;
                            document.getElementById("flight-id").innerText = "FLIGHT: " + standardFly.id;
                            document.getElementById("flight-origin").innerText = "FRA: " + standardFly.origin;
                            document.getElementById("flight-status-sub").innerText = "TOS / ENTC";
                            document.getElementById("flight-radar").innerText = "Ikke i radarområdet ennå";
                            logg("Ingen aktive fly på radarkartet.");
                        }

                    } catch (e) {
                        logg("Radarfeil i JSON-parsing");
                    }
                }
            };
            xhrRadar.send();
        }

        // Tvinger en full sideoppdatering via JavaScript hvert 5. minutt (300000 ms) i tilfelle meta-taggen svikter
        setTimeout(function() {
            window.location.reload(true);
        }, 300000);

        sjekkRadarOgOppdater();
        setInterval(sjekkRadarOgOppdater, 30000);
    </script>
</body>
</html>
"""
    
    html_content = html_content.replace("__CURRENT_DATE__", current_date)
    html_content = html_content.replace("__WEATHER_SUMMARY__", weather["summary"])
    html_content = html_content.replace("__WEATHER_TEMP__", weather["temp"])
    html_content = html_content.replace("__WEATHER_WIND__", weather["wind"])
    html_content = html_content.replace("__WEATHER_HUMIDITY__", weather["humidity"])
    html_content = html_content.replace("__WEATHER_ICON__", weather["icon"]) 
    html_content = html_content.replace("__FLIGHTS_JSON__", flights_json)

    with open("time.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("time.html generert med automatisk sideoppdatering aktivert!")

if __name__ == "__main__":
    generate_html()
