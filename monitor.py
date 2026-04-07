import firebase_admin
from flask import Flask
from firebase_admin import credentials, db
import json
import os
import time
from datetime import datetime
import threading
import pytz

# ---------------------------
# Timezone Setup (IST)
# ---------------------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Python Monitor Running"

# ---------------------------
# Firebase Setup
# ---------------------------
IST = pytz.timezone("Asia/Kolkata")

firebase_key_json = os.environ.get("FIREBASE_KEY")

cred_dict = json.loads(firebase_key_json)

cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(
    cred,
    {
        "databaseURL": "https://homesync-2205-default-rtdb.asia-southeast1.firebasedatabase.app/"
    }
)

devices_ref = db.reference("devices")
logs_ref = db.reference("logs")
stats_ref = db.reference("stats")
automation_ref = db.reference("automation")
system_ref = db.reference("system")

previous_states = {}
device_start_times = {}

def monitor_loop():
    while True:

        devices = devices_ref.get()
        
        total_usage = stats_ref.child("total_usage").get() or {}
        power_usage = stats_ref.child("power_consumption").get() or {}
        if not total_usage:
                total_usage = {}

        if not power_usage:
                power_usage = {}

        current_time = datetime.now(IST)
        current_time_str = current_time.strftime("%H:%M:%S")

        for device, data in devices.items():

            state = data["state"]
            power_rating = data.get("power_rating", 10)

            if device not in previous_states:
                previous_states[device] = state

            # ---------------------------
            # Detect ON
            # ---------------------------

            if state and not previous_states[device]:

                device_start_times[device] = current_time

                logs_ref.push({
                    "device": device,
                    "state": True,
                    "timestamp": current_time_str
                })

            # ---------------------------
            # Detect OFF
            # ---------------------------

            if not state and previous_states[device]:

                if device in device_start_times:

                    duration = (
                        current_time
                        - device_start_times[device]
                    ).total_seconds()

                    # Update usage_duration
                    devices_ref.child(device).update({
                        "usage_duration": duration
                    })

                    # Update total usage
                    total_usage[device] = (
                        total_usage.get(device, 0)
                        + duration
                    )

                    # Calculate power consumption
                    power_used = (
                        power_rating
                        * duration
                    ) / 3600

                    power_usage[device] = (
                        power_usage.get(device, 0)
                        + power_used
                    )

                    stats_ref.child("total_usage").update({
                        device: total_usage[device]
                    })

                    stats_ref.child("power_consumption").update({
                        device: power_usage[device]
                    })

                    logs_ref.push({
                        "device": device,
                        "state": False,
                        "timestamp": current_time_str,
                        "duration": duration
                    })

            previous_states[device] = state

        # ---------------------------
        # Automation Check
        # ---------------------------

        automation_data = automation_ref.get() or {}

        for device, auto in automation_data.items():

            auto_on = auto.get("auto_on")
            auto_off = auto.get("auto_off")

            if auto_on == current_time_str:

                devices_ref.child(device).update({
                    "state": True,
                    "last_updated": current_time_str
                })

            if auto_off == current_time_str:

                devices_ref.child(device).update({
                    "state": False,
                    "last_updated": current_time_str
                })

        # ---------------------------
        # Update System Sync
        # ---------------------------

        system_ref.update({
            "last_sync": current_time_str
        })

        time.sleep(5)

threading.Thread(target=monitor_loop).start()
port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)