import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# --- 1. Station Data ---
stations_data = {
    'station_id': [1, 2, 3, 4, 5, 6, 7],
    'station_name': ['Bhopal Junction', 'Habibganj', 'Obaidullaganj', 'Barkheda', 'Budni', 'Hoshangabad', 'Itarsi Junction'],
    'distance_from_start_km': [0, 6, 36, 57, 74, 81, 92],
    'number_of_platforms': [6, 5, 2, 2, 2, 3, 8],
    'number_of_tracks': [12, 10, 4, 4, 4, 6, 16]
}
stations_df = pd.DataFrame(stations_data)
stations_df.to_csv('stations.csv', index=False)

# --- 2. Track Data ---
tracks_data = []
for i in range(len(stations_data['station_id']) - 1):
    maintenance_status = random.choice(['no', 'yes'])
    tracks_data.append({
        'track_id': i + 1,
        'start_station_id': stations_data['station_id'][i],
        'end_station_id': stations_data['station_id'][i+1],
        'distance_km': stations_data['distance_from_start_km'][i+1] - stations_data['distance_from_start_km'][i],
        'track_condition': random.choice(['good', 'degraded', 'under-maintenance']),
        'geographical_condition': random.choice(['clear', 'rain', 'storm', 'fog']),
        'maintenance_status': maintenance_status,
        'expected_delay_minutes': random.randint(15, 60) if maintenance_status == 'yes' else 0
    })
tracks_df = pd.DataFrame(tracks_data)
tracks_df.to_csv('tracks.csv', index=False)

# --- 3. Train Data (Time-Series) with UP and DOWN trains ---
trains_data = []
start_time = datetime(2025, 9, 17, 0, 0)
num_trains = 10

for i in range(num_trains):
    train_id = 12000 + i
    train_type = random.choice(['Express', 'Passenger', 'Freight', 'Special'])
    priority = {'Special': 1, 'Express': 2, 'Passenger': 3, 'Freight': 4}
    direction = random.choice(['UP', 'DOWN'])

    base_speed = {
        'Express': 80,
        'Passenger': 60,
        'Freight': 50,
        'Special': 90
    }
    speed = base_speed[train_type] - random.randint(0, 10)

    current_time = start_time + timedelta(minutes=random.randint(0, 240))
    total_delay = 0

    station_indices = range(len(stations_df)) if direction == 'DOWN' else reversed(range(len(stations_df)))

    for j in station_indices:
        station_id = stations_df['station_id'][j]
        
        # Scheduled times
        if (direction == 'DOWN' and j > 0) or (direction == 'UP' and j < len(stations_df) - 1):
            if direction == 'DOWN':
                prev_station_dist = stations_df['distance_from_start_km'][j-1]
                curr_station_dist = stations_df['distance_from_start_km'][j]
            else: # UP
                prev_station_dist = stations_df['distance_from_start_km'][j+1]
                curr_station_dist = stations_df['distance_from_start_km'][j]
            
            distance = abs(curr_station_dist - prev_station_dist)
            travel_time_minutes = int((distance / speed) * 60)
            current_time += timedelta(minutes=travel_time_minutes)

        scheduled_arrival = current_time
        stoppage_minutes = random.randint(2, 10) if train_type != 'Freight' else random.randint(15, 30)
        scheduled_departure = scheduled_arrival + timedelta(minutes=stoppage_minutes)

        # Actual times with delays
        delay_this_leg = random.randint(0, 5) # Base delay
        crew_availability = random.choices(['available', 'not available'], weights=[0.95, 0.05])[0]
        train_maintenance_status = random.choices(['ok', 'minor_fault', 'major_fault'], weights=[0.9, 0.08, 0.02])[0]

        if crew_availability == 'not available': delay_this_leg += random.randint(15, 45)
        if train_maintenance_status == 'minor_fault': delay_this_leg += random.randint(10, 30)
        elif train_maintenance_status == 'major_fault': delay_this_leg += random.randint(60, 120)
            
        total_delay += delay_this_leg
        actual_arrival = scheduled_arrival + timedelta(minutes=total_delay)
        actual_departure = scheduled_departure + timedelta(minutes=total_delay)

        trains_data.append({
            'timestamp': actual_arrival.isoformat(),
            'train_id': train_id,
            'train_type': train_type,
            'direction': direction,
            'priority_level': priority.get(train_type, 5),
            'locomotive_type': random.choice(['Electric', 'Diesel', 'Hybrid']),
            'speed_profile_kph': speed,
            'station_id': station_id,
            'scheduled_arrival': scheduled_arrival.isoformat(),
            'scheduled_departure': scheduled_departure.isoformat(),
            'actual_arrival': actual_arrival.isoformat(),
            'actual_departure': actual_departure.isoformat(),
            'crew_availability': crew_availability,
            'train_maintenance_status': train_maintenance_status
        })
        current_time = scheduled_departure

trains_df = pd.DataFrame(trains_data)
trains_df.to_csv('trains.csv', index=False)

# --- 4. Signal Data ---
signals_data = []
for _, track in tracks_df.iterrows():
    for i in range(3): # 3 signals per track
        status = random.choices(['green', 'yellow', 'red'], weights=[0.7, 0.2, 0.1])[0]
        reason = 'n/a'
        if status == 'red':
            reason = random.choice(['train ahead', 'track maintenance', 'accident', 'congestion'])
        
        signals_data.append({
            'signal_id': f"SIG-{track['track_id']}-{i+1}",
            'track_id': track['track_id'],
            'location_km_from_start': track['start_station_id'] + (i * (track['distance_km']/3)),
            'signal_status': status,
            'reason_if_red': reason,
            'timestamp': (start_time + timedelta(minutes=random.randint(0, 1440))).isoformat()
        })
signals_df = pd.DataFrame(signals_data)
signals_df.to_csv('signals.csv', index=False)


# --- 5. Event Data ---
events_data = []
for _ in range(20): # 20 random events
    event_type = random.choice(['weather', 'maintenance', 'accident', 'diversion'])
    event_time = start_time + timedelta(minutes=random.randint(0, 1440))
    
    description = ''
    if event_type == 'weather':
        weather = random.choice(['heavy rain', 'fog'])
        description = f"{weather.capitalize()} event, speed reduction advised."
    elif event_type == 'maintenance':
        track_id = random.randint(1, len(tracks_df))
        duration = random.randint(30, 180)
        description = f"Urgent track maintenance on track {track_id} for {duration} minutes."
    elif event_type == 'accident':
        train_id = 12000 + random.randint(0, num_trains-1)
        description = f"Minor accident involving train {train_id}."
    elif event_type == 'diversion':
        train_id = 12000 + random.randint(0, num_trains-1)
        description = f"Train {train_id} diverted via loop line due to congestion."

    events_data.append({
        'timestamp': event_time.isoformat(),
        'event_type': event_type,
        'description': description
    })
events_df = pd.DataFrame(events_data)
events_df.to_csv('events.csv', index=False)

print("Synthetic dataset generated successfully with UP and DOWN trains.")