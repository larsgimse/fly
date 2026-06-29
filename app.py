import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

# --- KONFIGURASJON ---
WIDTH, HEIGHT = 800, 600  
LAT, LON = 69.6492, 18.9553  # Tromsø
USER_AGENT = "NookDashboard/1.0 (+https://github.com/dinbruker)"
FONT_FILE_BOLD = "OpenSans-Bold.ttf"

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
        
        # Henter også værsymbolet (f.eks. 'clearsky_day')
        next_hour = data['properties']['timeseries'][0]['data'].get('next_1_hours', {})
        summary = next_hour.get('summary', {}).get('symbol_code', 'unknown')
        
        return {"temp": f"{temp}°", "wind": f"{wind} m/s", "humidity": f"{humidity}%", "summary": summary}
    except Exception as e:
        print(f"Feil ved henting av vær: {e}")
        return {"temp": "--°", "wind": "- m/s", "humidity": "-\%", "summary": "unknown"}

def get_next_flight():
    try:
        from FlightRadar24 import FlightRadar24API
        fr_api = FlightRadar24API()
        airport_details = fr_api.get_airport_details("ENTC")
        
        if not airport_details:
            return None
            
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
        return None
    except Exception as e:
        print(f"Feil ved henting av flydata: {e}")
        return None

def generate_image():
    try:
        # 1. Hvit bakgrunn for e-blekk looken
        image = Image.new("L", (WIDTH, HEIGHT), color=255)
        draw = ImageDraw.Draw(image)
        
        # Last inn fonter med varierte størrelser for god typografi
        if os.path.exists(FONT_FILE_BOLD):
            font_clock = ImageFont.truetype(FONT_FILE_BOLD, 130)     # Store, men elegante tall
            font_date = ImageFont.truetype(FONT_FILE_BOLD, 30)       # Tynnere og renere
            font_huge_temp = ImageFont.truetype(FONT_FILE_BOLD, 90)  # Stor temperatur som på bildet
            font_main = ImageFont.truetype(FONT_FILE_BOLD, 22)       # Detaljtekst
            font_title = ImageFont.truetype(FONT_FILE_BOLD, 18)      # Små merkelapper (caps)
        else:
            font_clock = font_date = font_huge_temp = font_main = font_title = ImageFont.load_default()
        
        # Tidsdata
        now_local = datetime.now(TIMEZONE)
        current_time = now_local.strftime("%H:%M")
        current_date = now_local.strftime("%A, %B %d").upper()
        
        # --- TOPPBAR: Klokke og Dato (Sentrert og minimalistisk) ---
        draw.text((WIDTH // 2, 70), current_time, fill=0, font=font_clock, anchor="mm")
        draw.text((WIDTH // 2, 150), current_date, fill=0, font=font_date, anchor="mm")
        
        # En veldig tynn og lekker skillelinje under klokken
        draw.line([(80, 190), (WIDTH - 80, 190)], fill=200, width=1)
        
        # --- HENT DATA ---
        weather = get_weather()
        flight = get_next_flight()
        
        # --- NEDRE VENSTRE: TROMSØ VÆR ---
        # "San Diego"-stilen: Stor temperatur, vær-type under
        draw.text((100, 240), "TROMSØ", fill=0, font=font_title)
        draw.text((100, 270), weather["summary"].replace("_", " ").upper(), fill=100, font=font_title)
        draw.text((100, 370), weather["temp"], fill=0, font=font_huge_temp)
        
        # Sekundær værinfo (Vind og fuktighet) stilt opp med tynn tekst
        draw.text((100, 440), f"VIND: {weather['wind']}", fill=0, font=font_main)
        draw.text((100, 470), f"FUKTIGHET: {weather['humidity']}", fill=0, font=font_main)
        
        # En tynn vertikal deler i midten
        draw.line([(WIDTH // 2, 230), (WIDTH // 2, 520)], fill=200, width=1)
        
        # --- NEDRE HØYRE: NESTE FLYANKOMST ---
        draw.text((WIDTH // 2 + 60, 240), "NESTE ANKOMST", fill=0, font=font_title)
        draw.text((WIDTH // 2 + 60, 270), "TOS / ENTC", fill=100, font=font_title)
        
        if flight:
            # Stor tid for ankomst for å matche temperatur-vekten på venstre side
            draw.text((WIDTH // 2 + 60, 370), flight["time"], fill=0, font=font_huge_temp)
            draw.text((WIDTH // 2 + 60, 440), f"FLIGHT: {flight['number']}", fill=0, font=font_main)
            draw.text((WIDTH // 2 + 60, 470), f"FRA: {flight['origin']}", fill=0, font=font_main)
        else:
            draw.text((WIDTH // 2 + 60, 350), "Ingen aktive data", fill=100, font=font_main)
            
        # Lagre bildet
        image.save("dashboard.png")
        print("Stilrent dashboard generert!")
        
    except Exception as e:
        print(f"Feil: {e}")
        img = Image.new("L", (WIDTH, HEIGHT), color=255)
        img.save("dashboard.png")

if __name__ == "__main__":
    generate_image()
