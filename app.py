import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

LAT, LON = 69.6492, 18.9553  # Tromsø
USER_AGENT = "NookDashboard/1.0 (+https://github.com/dinbruker)"
TIMEZONE = ZoneInfo("Europe/Oslo")

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
        summary = next_hour.get('summary', {}).get('symbol_code', 'unknown')
        
        weather_text = summary.replace("_day", "").replace("_night", "").replace("_", " ").upper()
        return {"temp": f"{temp}°", "wind": f"{wind} m/s", "humidity": f"{humidity}%", "summary": weather_text}
    except Exception as e:
        return {"temp": "--°", "wind": "- m/s", "humidity": "-%", "summary": "UKJENT VÆR"}

def get_next_flight():
    try:
        from FlightRadar24 import FlightRadar24API
        fr_api = FlightRadar24API()
        airport_details = fr_api.get_airport_details("ENTC")
        
        if airport_details:
            plugin_data = airport_details.get('pluginData', {})
            schedule = plugin_data.get('schedule', {}) if plugin_data else {}
            arrivals = schedule.get('arrivals', {}).get('data', []) if schedule else []
            
            if arrivals:
                next_flight = arrivals[0]
                flight_info = next_flight.get('flight', {})
                flight_number = flight_info.get('identification', {}).get('number', {}).get('default', '----')
                origin_info = flight_info.get('airport', {}).get('origin', {})
                origin = origin_info.get('name', 'Ukjent').split(" ")[0].upper() if origin_info else "UKJENT"
                sta_epoch = flight_info.get('time', {}).get('scheduled', {}).get('arrival', 0)
                sta_time = datetime.fromtimestamp(sta_epoch, tz=TIMEZONE).strftime('%H:%M') if sta_epoch else "--:--"
                
                return {"time": sta_time, "number": flight_number, "origin": origin}
        return {"time": "--:--", "number": "INGEN FLY", "origin": "-"}
    except Exception as e:
        return {"time": "--:--", "number": "FEIL", "origin": "FLIGHTRADAR NED"}

def generate_html():
    now_local = datetime.now(TIMEZONE)
    current_date = now_local.strftime("%A, %B %d").upper()
    
    weather = get_weather()
    flight = get_next_flight()
    
    html_content = f"""<!DOCTYPE html>
<html lang="no">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nook Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        body {{
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
        }}
        
        .top-section {{
            text-align: center;
            margin-top: 20px;
        }}
        
        .clock {{
            font-size: 110px;
            font-weight: 700;
            letter-spacing: -2px;
            margin: 0;
            line-height: 1;
        }}
        
        .date {{
            font-size: 22px;
            font-weight: 400;
            color: #555555;
            margin-top: 15px;
            letter-spacing: 1px;
        }}
        
        .divider {{
            border-top: 1px solid #e0e0e0;
            width: 85%;
            margin: 40px auto;
        }}
        
        .bottom-section {{
            display: flex;
            flex: 1;
            padding: 0 20px;
        }}
        
        .column {{
            flex: 1;
            display: flex;
            flex-direction: column;
        }}
        
        .left-column {{
            padding-right: 20px;
            border-right: 1px solid #e0e0e0;
        }}
        
        .right-column {{
            padding-left: 30px;
        }}
        
        .label-top {{
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 2px;
            margin: 0 0 5px 0;
        }}
        
        .label-sub {{
            font-size: 14px;
            font-weight: 400;
            color: #777777;
            margin: 0 0 35px 0;
            letter-spacing: 1px;
        }}
        
        .huge-data {{
            font-size: 75px;
            font-weight: 700;
            margin: 0 0 25px 0;
            line-height: 1;
        }}
        
        .detail-text {{
            font-size: 18px;
            font-weight: 400;
            margin: 8px 0;
            color: #222222;
        }}
    </style>
    <meta http-equiv="refresh" content="900">
    
    <script>
        function updateClock() {{
            const now = new Date();
            // Tvinger nettleseren til å vise Tromsø-tid (norsk tid) uansett enhet
            const options = {{ timeZone: 'Europe/Oslo', hour: '2-digit', minute: '2-digit', hour12: false }};
            const timeString = now.toLocaleTimeString('no-NO', options);
            document.getElementById('live-clock').innerText = timeString;
        }}
        // Oppdaterer klokken hvert sekund
        setInterval(updateClock, 1000);
    </script>
</head>
<body onload="updateClock()">

    <div class="top-section">
        <h1 class="clock" id="live-clock">--:--</h1>
        <div class="date">{current_date}</div>
    </div>
    
    <div class="divider"></div>
    
    <div class="bottom-section">
        <div class="column left-column">
            <h2 class="label-top">TROMSØ</h2>
            <h3 class="label-sub">{weather["summary"]}</h3>
            <div class="huge-data">{weather["temp"]}</div>
            <div class="detail-text">VIND: {weather["wind"]}</div>
            <div class="detail-text">FUKTIGHET: {weather["humidity"]}</div>
        </div>
        
        <div class="column right-column">
            <h2 class="label-top">NESTE ANKOMST</h2>
            <h3 class="label-sub">TOS / ENTC</h3>
            <div class="huge-data">{flight["time"]}</div>
            <div class="detail-text">FLIGHT: {flight["number"]}</div>
            <div class="detail-text">FRA: {flight["origin"]}</div>
        </div>
    </div>

</body>
</html>
"""
    with open("time.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("time.html ble generert!")

if __name__ == "__main__":
    generate_html()
