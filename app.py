import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo # Innebygd i Python 3.9+
from PIL import Image, ImageDraw, ImageFont

# --- KONFIGURASJON ---
WIDTH, HEIGHT = 800, 600  
LAT, LON = 69.6492, 18.9553  # Tromsø
USER_AGENT = "NookDashboard/1.0 (+https://github.com/dinbruker)"
FONT_FILE_BOLD = "OpenSans-Bold.ttf"

# Definer tidsone for Tromsø
TIMEZONE = ZoneInfo("Europe/Oslo")

def get_weather():
    headers = {'User-Agent': USER_AGENT}
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={LAT}&lon={LON}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        now = data['properties']['timeseries'][0]['data']['instant']['details']
        temp = now['air_temperature']
        wind = now['wind_speed']
        return f"{temp}°C / {wind} m/s"
    except Exception as e:
        print(f"Feil ved henting av vær: {e}")
        return "Kunne ikke hente vær"

def get_next_flight():
    try:
        from FlightRadar24 import FlightRadar24API
        fr_api = FlightRadar24API()
        airport_details = fr_api.get_airport_details("ENTC")
        
        if not airport_details:
            return "Ingen flydata"
            
        plugin_data = airport_details.get('pluginData', {})
        schedule = plugin_data.get('schedule', {}) if plugin_data else {}
        arrivals = schedule.get('arrivals', {}).get('data', []) if schedule else []
        
        if arrivals:
            next_flight = arrivals[0]
            flight_info = next_flight.get('flight', {})
            flight_number = flight_info.get('identification', {}).get('number', {}).get('default', 'Ukjent')
            
            if len(flight_number) > 8: flight_number = flight_number[:8]

            origin_info = flight_info.get('airport', {}).get('origin', {})
            origin = origin_info.get('name', 'Ukjent').split(" ")[0] if origin_info else "Ukjent"
            if len(origin) > 10: origin = origin[:10]
            
            sta_epoch = flight_info.get('time', {}).get('scheduled', {}).get('arrival', 0)
            
            # Konverter flyplass-tid (epoch) til Tromsø-tidssone
            if sta_epoch:
                sta_time = datetime.fromtimestamp(sta_epoch, tz=TIMEZONE).strftime('%H:%M')
            else:
                sta_time = "--:--"
            
            return f"{sta_time} - {flight_number} - {origin}"
        
        return "Ingen planlagte fly"
    except Exception as e:
        print(f"Feil ved henting av flydata: {e}")
        return "Flydata midlertidig nede"

def generate_image():
    try:
        image = Image.new("L", (WIDTH, HEIGHT), color=255)
        draw = ImageDraw.Draw(image)
        
        if os.path.exists(FONT_FILE_BOLD):
            font_clock = ImageFont.truetype(FONT_FILE_BOLD, 220)  
            font_date = ImageFont.truetype(FONT_FILE_BOLD, 50)   
            font_sub_title = ImageFont.truetype(FONT_FILE_BOLD, 40) 
            font_sub_data = ImageFont.truetype(FONT_FILE_BOLD, 55)  
        else:
            font_clock = font_date = font_sub_title = font_sub_data = ImageFont.load_default()
        
        # --- HENT TID RELEVANT FOR TROMSØ ---
        now_local = datetime.now(TIMEZONE)
        current_time = now_local.strftime("%H:%M")
        current_date = now_local.strftime("%A %d. %B") 

        # --- 1. TIDSENHET (Øverste 2/4) ---
        draw.text((WIDTH // 2, HEIGHT // 5), current_time, fill=0, font=font_clock, anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 - 50), current_date, fill=0, font=font_date, anchor="mm")
        
        # --- Skillelinjer ---
        draw.line([(0, HEIGHT // 2), (WIDTH, HEIGHT // 2)], fill=0, width=5)
        draw.line([(WIDTH // 2, HEIGHT // 2), (WIDTH // 2, HEIGHT)], fill=0, width=5)
        
        # --- 2. VÆR (Nedre venstre 1/4) ---
        weather_info = get_weather()
        draw.text((WIDTH // 4, HEIGHT // 2 + 50), "TROMSØ VÆR:", fill=0, font=font_sub_title, anchor="mm")
        draw.text((WIDTH // 4, HEIGHT * 3 // 4 + 10), weather_info, fill=0, font=font_sub_data, anchor="mm")
        
        # --- 3. FLY (Nedre høyre 1/4) ---
        flight_info = get_next_flight()
        draw.text((WIDTH * 3 // 4, HEIGHT // 2 + 50), "NESTE ANKOMST:", fill=0, font=font_sub_title, anchor="mm")
        draw.text((WIDTH * 3 // 4, HEIGHT * 3 // 4 + 10), flight_info, fill=0, font=font_sub_data, anchor="mm")
        
        image.save("dashboard.png")
        print(f"Bildet ble generert! Klokkeslett i bildet: {current_time}")
        
    except Exception as e:
        print(f"Kritisk feil under bildegenerering: {e}")
        img = Image.new("L", (WIDTH, HEIGHT), color=200)
        draw = ImageDraw.Draw(img)
        draw.text((WIDTH//2, HEIGHT//2), f"Feil: {str(e)}", fill=0, anchor="mm")
        img.save("dashboard.png")

if __name__ == "__main__":
    generate_image()
