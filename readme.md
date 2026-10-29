# Smart Electricity: budget-aware forecasting with IoT meter reading

Status: work in progress (college project). ESP32-CAM firmware is untested on hardware.

## What it does
Reads a meter's display from a photo (YOLO display + digit detectors), validates the
reading, stores it in Firebase, forecasts the cycle's bill with a slab tariff, and warns
when the projected bill exceeds the budget. Models run locally; storage and dashboard are in Firebase.

## Setup (Windows, Python 3.12)
    git clone <this repo>
    cd <repo folder>
    python -m venv venv
    venv\Scripts\activate
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    pip install -r requirements.txt

## Your own Firebase project
1. console.firebase.google.com: Add project, then Build > Firestore Database > Create database.
2. Build > Authentication > enable Email/Password, then add a user.
3. Project settings > Service accounts > Generate new private key, saved as config\firebase_key.json (never commit it).
4. Project settings > General > Add web app. Copy public\firebase-config.example.js to
   public\firebase-config.js and fill in your values.
5. Copy .env.example to .env.
6. Put your project ID in .firebaserc.
7. Install Node.js, then: npm install -g firebase-tools, firebase login, firebase deploy --only hosting,firestore:rules

## Run
    python src\set_device.py meter1 owner_uid=<your uid shown on the dashboard> decimals=1
    python src\submit_test.py "<photo>.jpg"
    python src\worker.py --once

## Notes
- All forecast numbers on SYNTHETIC_* devices are synthetic.
- Default tariff slabs are placeholders, not any utility's rates.
- Datasets and licences: docs\dataset_sources.md

## Licence note
The digit detector was trained on ds5 (CC BY 4.0) and ds6 (BY-NC-SA 4.0). Use is
non-commercial only. See docs/dataset_sources.md.