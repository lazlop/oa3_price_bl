# WORKS FOR VTN RUNNING ON HA 
# seems to create two events (program exists)
# Not yet sure how to delete events ...
# make sure code doesn't create multiple events when in HA. 

from flask import Flask, render_template, redirect, url_for, jsonify
import flask
import requests
import json
from datetime import datetime, timedelta
import threading
import time
import pprint
import random

# VTN_URL = "http://192.168.122.226:8080/openadr3/3.0.1" on HA
VTN_URL = "http://localhost:8080/openadr3/3.0.1"

HEADERS = {
    "Content-type": "application/json",
    "Authorization": "Bearer bl_token"
}

app = Flask(__name__)

@app.route("/")
def home():
    # Get current prices from the event
    current_prices = get_current_event_prices()
    price_now = current_prices[0]
    
    # Create a card for the pricing information
    cards = [{
        "title": "Pricing Information",
        "color": "rgba(0, 0, 0, 1)",
        "description": f"Current Price: ${price_now:.4f}/kWh",
    }]
    
    return render_template("index.html", cards=cards)


def get_current_event_prices():
    """Get the current pricing event from the VTN and extract price data"""
    response = requests.get(
        f"{VTN_URL}/events",
        headers=HEADERS,
    )
    events = response.json()
    if not events:
        return [0] * 24  # Return default prices if no events
    
    # Get the last event (assuming it's a pricing event, and that new events are appended to end of list)
    event = events[-1]
    event_prices = []
    for interval in event.get("intervals", []):
        for payload in interval.get("payloads", []):
            if payload.get("type") == "PRICE" and payload.get("values"):
                event_prices.append(payload["values"][0])
    
    return event_prices

@app.route('/chart_data')
def data():
    # Get current price data from the event
    current_prices = get_current_event_prices()
    
    # Create dataset only for pricing
    price_data_set = {
        "label": "Price ($/kWh)",
        "data": current_prices,
        "borderColor": "rgba(255, 99, 132, 1)",
        "fill": False
    }
    
    chart_data = {
        "labels": list(range(24)),
        "datasets": [price_data_set],
    }
    return jsonify(chart_data)


def _create_program() -> bool:
    data = load_json("program.json")
    response = requests.post(
        f"{VTN_URL}/programs",
        headers=HEADERS,
        json=data
    )
    if response.status_code == 201:
        print("Created program")
        return True
    # The program was already on the VTN
    if response.status_code == 409:
        print("Program already exists")
        return True

    print("Failed to create program")
    print("Create program, status code:", response.status_code)
    print("Create program, response body:", response.json())
    return False

def _delete_event(event_id = 0) -> bool:
    response = requests.delete(
        f"{VTN_URL}/events/{event_id}",
        headers=HEADERS,
    )
    if response.status_code == 200:
        print("Okay")
        return True
    # The program was already on the VTN
    if response.status_code == 400:
        print("bad request")
        return True

    print("Failed to delete event")
    print("status code:", response.status_code)
    print("response body:", response.json())
    return False
 

# This event publishes pricing information to VENs
def _create_pricing_event(interval_start = 0):
    """post example price, optionally adjusting order of intervals"""
    data = load_json("event_pricing.json")
    
    # Extract pricing data from the event
    intervals = data["intervals"]
    updated_intervals = intervals[interval_start:] + intervals[:interval_start]
    data["intervals"] = updated_intervals
    
    response = requests.post(
        f"{VTN_URL}/events",
        headers=HEADERS,
        json=data
    )
    if response.status_code == 201:
        print("Created pricing event")
        return True
    print("Failed to create pricing event")
    print("Create event, status code:", response.status_code)
    print("Create event, response body:", response.json())


def create_date_string(hour):
    # Use today's date as the base date
    base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Adjust the hour and format as ISO 8601 with milliseconds and 'Z'
    date_string = (base_date + timedelta(hours=hour)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    
    return date_string


def _create_price_interval_for_hour(hour):
    # Get current prices from the event
    current_prices = get_current_event_prices()
    
    return {
        "id": hour,
        "intervalPeriod": {
            "start": create_date_string(hour),
            "duration": "PT1H"
        },
        "payloads": [
            {
                "type": "PRICE",
                "values": [current_prices[hour]]
            },
        ],
    }

def _delete_all_events():
    response = requests.get(
        f"{VTN_URL}/events",
        headers=HEADERS,
    )
    events = response.json()
    if events == []:
        print('No events to delete')
        return
    for event in events:
        print(f"Deleting event {event['id']}")
        _delete_event(event["id"])
        
    last_id = events[-1]["id"]
    
    return last_id

def _post_prices_with_threading():
    while True:
        for i in range(0, 24):
            _create_pricing_event(i)
            time.sleep(5)
            _delete_all_events()

def load_json(file_name):
    with open(file_name, "r") as json_file:
        data = json.load(json_file)
    return data


if __name__ == "__main__":
    _create_program()
    _delete_all_events()
    # Start the worker in a separate thread
    thread = threading.Thread(target=_post_prices_with_threading, daemon=True)
    thread.start()
    app.run(port=8081, debug=True)
