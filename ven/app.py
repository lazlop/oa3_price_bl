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
from time import sleep
import pprint
from random import random
import numpy as np

app = Flask(__name__)

VEN_TYPE = "hvac" # "hvac, wh, or hvac"

@app.route("/")
def home():
    return render_template(f"{VEN_TYPE}.html")


# dummy data
def _throttle_generator():
    i = 0
    while True:
        yield round(i%24/24, 2)
        i = i + 1

def _hour_generator():
    i = 0
    while True:
        yield i%24
        i = i + 1

throttle = _throttle_generator()
def _get_current_throttle_amt():
    return next(throttle)

prices = _throttle_generator()
def _get_current_event_price():
    return 1 - next(prices)

hours = _hour_generator()
def _get_current_hour():
    return next(hours)
def create_date_string(hour):
    # Use today's date as the base date
    base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Adjust the hour and format as ISO 8601 with milliseconds and 'Z'
    date_string = (base_date + timedelta(hours=hour)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    
    return date_string


@app.route('/chart_data')
def data():
    # Get current price data from the event
    current_price = _get_current_event_price()
    throttle = _get_current_throttle_amt()    
    hour = _get_current_hour()
    # Calculate min and max for gauge range
    # Using a buffer of 20% below min and above max for better visualization
    min_price = 0
    max_price = 1
    
    # Create gauge chart data
    gauge_data = {
        "currentValue": current_price,
        "min": min_price,
        "max": max_price,
        "currentThrottle": throttle,
        "minThrottle": 0,
        "maxThrottle": 1,
        "currentHour": hour,
        # Static threshold values for price gauge
        "priceLowThreshold": 0.1,  # Static value for low price threshold
        "priceHighThreshold": 0.9,  # Static value for high price threshold
        # Static threshold values for throttle gauge
        "throttleLowThreshold": 0.1,  # Static value for low throttle threshold
        "throttleHighThreshold": 0.9  # Static value for high throttle threshold
    }
    
    return jsonify(gauge_data)

# def cycle_end_uses():
#     global VEN_TYPE
#     while True:
#         for i in range(0,3):
#             VEN_TYPE = ["ev","wh","hvac"][i]
#             print(VEN_TYPE)
#             sleep(10)

if __name__ == "__main__":
    # thread = threading.Thread(target=cycle_end_uses, daemon=True)
    # thread.start()
    app.run(port=8081, debug=True)
