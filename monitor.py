import firebase_admin
from firebase_admin import credentials, db
import json
import os
import time
from datetime import datetime

# Read Firebase key from environment variable
firebase_key_json = os.environ.get("FIREBASE_KEY")

cred_dict = json.loads(firebase_key_json)

cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred, {
    'databaseURL': "YOUR_DATABASE_URL"
})

ref = db.reference("devices")
logs_ref = db.reference("logs")
system_ref = db.reference("system")

previous_states = {}

print("Python Firebase Monitor Started")

while True:

    devices = ref.get()

    for device, data in devices.items():

        state = data["state"]

        if device not in previous_states:
            previous_states[device] = state

        if previous_states[device] != state:

            timestamp = datetime.now().strftime("%H:%M:%S")

            logs_ref.push({
                "device": device,
                "state": state,
                "timestamp": timestamp
            })

            previous_states[device] = state

    system_ref.update({
        "last_sync": datetime.now().strftime("%H:%M:%S")
    })

    time.sleep(5)