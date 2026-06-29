import os
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from FlightRadar24 import FlightRadar24API

WIDTH, HEIGHT = 800, 600
LAT, LON = 69.6492, 18.9553  # Tromsø
AIRPORT_ICAO = "ENTC"        # Tromsø Lufthavn
USER_AGENT = "NookDashboard/1.0 (+https://github.com/dinbruker)"

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
        return f"{temp}°C\nVind: {wind} m/s"
    except Exception as e:
        return "Vær:\nUtilgjengelig"

def get_next_flight():
    try:
        fr_api = FlightRadar24API()
        airport_details = fr_api.get_airport_details(AIRPORT_ICAO)
        plugin_data = airport_details.get('pluginData', {}) if airport_details else {}
        schedule = plugin_data.get('schedule', {}) if plugin_data else {}
        arrivals = schedule.get('arrivals', {}).get('data', []) if schedule else []
        
        if arrivals:
            next_flight = arrivals[0]
            flight_info = next_flight.get('flight', {})
            flight_number = flight_info.get('identification', {}).get('number', {}).get('default', 'Ukjent')
            origin_info = flight_info.get('airport', {}).get('origin', {})
            origin = origin_info.get('name', 'Ukjent').split(" ")[0] if origin_info else "Ukjent"
            sta_epoch = flight_info.get('time', {}).get('scheduled', {}).get('arrival', 0)
            sta_time = datetime.fromtimestamp(sta_epoch).strftime('%H:%M') if sta_epoch else "--:--"
            return f"{sta_time} - {flight_number}\nFra: {origin}"
        return "Ingen planlagte fly"
    except Exception as e:
        return "Flydata:\nMidlertidig nede"

def generate_image():
    image = Image.new("L", (WIDTH, HEIGHT), color=255)
    draw = ImageDraw.Draw(image)
    
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%A %d. %B")
    
    # Tegner tekst med standardfont (større tekst simuleres med linjer/plassering her for testing)
    draw.text((WIDTH // 2, HEIGHT // 6), f"KLOKKA: {current_time}", fill=0, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 3), current_date, fill=0, anchor="mm")
    
    draw.line([(0, HEIGHT // 2), (WIDTH, HEIGHT // 2)], fill=0, width=3)
    draw.line([(WIDTH // 2, HEIGHT // 2), (WIDTH // 2, HEIGHT)], fill=0, width=3)
    
    draw.text((30, HEIGHT // 2 + 40), "TROMSØ VÆR:", fill=0)
    draw.text((30, HEIGHT // 2 + 80), get_weather(), fill=0)
    
    draw.text((WIDTH // 2 + 30, HEIGHT // 2 + 40), "NESTE ANKOMST:", fill=0)
    draw.text((WIDTH // 2 + 30, HEIGHT // 2 + 80), get_next_flight(), fill=0)
    
    image.save("dashboard.png")
    print("Bildet ble generert!")

if __name__ == "__main__":
    generate_image()
