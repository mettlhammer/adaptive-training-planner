# adaptive_training_app.py
# Adaptive Trainings-App mit Streamlit + Intervals.icu API + Automatischer Username-Abruf

import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Adaptive Training Planner", layout="centered")
st.title("🚴‍♂️ Adaptive Training Planner")

session = requests.Session()

st.sidebar.header("🔐 API-Key Test")
api_key_test = st.sidebar.text_input("Intervals.icu API Key testen", type="password")

if st.sidebar.button("Test starten") and api_key_test:
    user_check = session.get("https://intervals.icu/api/v1/athletes", auth=("API_KEY", api_key_test))
    if user_check.status_code == 200:
        username = user_check.json()[0].get("username")
        user_data = session.get(f"https://intervals.icu/api/v1/athlete/{username}", auth=("API_KEY", api_key_test))
        if user_data.status_code == 200:
            athlete = user_data.json()
            st.sidebar.success(f"✅ Erfolgreich! Benutzer: {athlete.get('username')}, FTP: {athlete.get('ftp')}W")
        else:
            st.sidebar.error("❌ Zugriff auf Benutzerprofil verweigert.")
            st.sidebar.code(f"Status: {user_data.status_code}\n{user_data.text}")
    else:
        st.sidebar.error("❌ API-Key ungültig oder Zugriff auf Athletenliste verweigert.")
        st.sidebar.code(f"Status: {user_check.status_code}\n{user_check.text}")

st.header("📅 Wochenplanung")

api_key = st.text_input("🔐 Intervals.icu API Key (für Planung)", type="password")

renntage_input = st.text_area(
    "🏁 Renntage eintragen (Format: YYYY-MM-DD: Name, ein Eintrag pro Zeile)",
    """2025-05-11: Limburg Gravel
2025-05-18: Rund um Köln Velodrom 120
2025-05-31: 3Rides Gravel"""
)

start_date = st.date_input("📅 Wochenstart", datetime.today())

if st.button("📊 Plan generieren") and api_key:
    athletes = session.get("https://intervals.icu/api/v1/athletes", auth=("API_KEY", api_key))
    if athletes.status_code != 200 or not athletes.json():
        st.error("Fehler beim Abrufen der Athleten. Bitte API-Key überprüfen.")
        st.code(f"Status: {athletes.status_code}\n{athletes.text}")
        st.stop()

    username = athletes.json()[0].get("username")
    r = session.get(f"https://intervals.icu/api/v1/athlete/{username}", auth=("API_KEY", api_key))
    if r.status_code != 200:
        st.error("Fehler beim Abrufen der Athlete-Daten.")
        st.code(f"Status: {r.status_code}\n{r.text}")
        st.stop()

    athlete_data = r.json()
    ftp = athlete_data.get("ftp", 250)
    ctl = athlete_data.get("ctl", 0)
    atl = athlete_data.get("atl", 0)
    tsb = ctl - atl

    renntage = {}
    for line in renntage_input.strip().split("\n"):
        if ":" in line:
            date, name = line.split(":", 1)
            renntage[date.strip()] = name.strip()

    end_date = start_date + timedelta(days=6)
    url = f"https://intervals.icu/api/v1/wellness?start={start_date - timedelta(days=6)}&end={end_date}"
    r = session.get(url, auth=("API_KEY", api_key))
    if r.status_code != 200:
        st.error("Fehler beim Abrufen der Wellnessdaten.")
        st.code(f"Status: {r.status_code}\n{r.text}")
        st.stop()

    wellness_data = {entry["date"]: entry for entry in r.json()}

    rows = []
    st.subheader("🗓️ Wochenplan")

    for i in range(7):
        day = start_date + timedelta(days=i)
        day_str = day.isoformat()
        race_name = renntage.get(day_str, None)

        hrv = wellness_data.get(day_str, {}).get("hrv")
        sleep = wellness_data.get(day_str, {}).get("sleep")

        if race_name:
            rec = f"🏁 Rennen: {race_name}"
            wtype = "Wettkampf"
        elif tsb < -25 or (hrv and hrv < 6) or (sleep and sleep < 6):
            rec = "🔵 Aktive Erholung oder Ruhetag"
            wtype = "Ruhetag"
        elif tsb > 10 and (hrv and hrv > 7) and (sleep and sleep >= 7):
            rec = "🟢 3x10 min Sweet Spot oder VO2max"
            wtype = "Sweet Spot"
        else:
            rec = "🟡 2x15 min Sweet Spot oder lockere Endurance"
            wtype = "Endurance"

        st.write(f"**{day.strftime('%A, %d.%m.%Y')}** — {rec}")
        rows.append({"Date": day_str, "Workout Type": wtype, "Description": rec})

    st.markdown(f"**📊 TSB:** {tsb:.1f}, **CTL:** {ctl:.1f}, **ATL:** {atl:.1f}, **FTP:** {ftp}")
    df = pd.DataFrame(rows)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Wochenplan als CSV herunterladen", csv, "training_plan.csv", "text/csv")
