
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import ast
import re
import sys # Import sys to handle command-line arguments

def analyze_delays(trains_df, suffix):
    print(f"Analyzing delays for {suffix}...")
    trains_df['scheduled_arrival'] = pd.to_datetime(trains_df['scheduled_arrival'])
    trains_df['actual_arrival'] = pd.to_datetime(trains_df['actual_arrival'])
    trains_df['delay'] = (trains_df['actual_arrival'] - trains_df['scheduled_arrival']).dt.total_seconds() / 60
    avg_delay = trains_df.groupby('train_type')['delay'].mean().reset_index()
    avg_delay.rename(columns={'delay': 'average_delay_minutes'}, inplace=True)
    avg_delay.to_csv(f'average_delays_{suffix}.csv', index=False)
    print(f"  -> Saved 'average_delays_{suffix}.csv'")

def analyze_utilization(log_df, stations_df, tracks_df, total_time, suffix):
    # ... (This function remains the same, just add suffix to output file)
    print(f"Analyzing resource utilization for {suffix}...")
    utilization_data = []
    log_df['details'] = log_df['details'].astype(str)
    for _, track in tracks_df.iterrows():
        for line_type in ['up_line', 'down_line', 'central_line']:
            track_id = track['track_id']
            line_name = f"Track {track_id} ({line_type})"
            acquired_events = log_df[(log_df['event_type'] == 'TRACK_ACQUIRED') & (log_df['details'].str.contains(f"'track_id': {track_id}")) & (log_df['details'].str.contains(f"'{line_type}'"))]
            released_events = log_df[(log_df['event_type'] == 'TRACK_RELEASED') & (log_df['details'].str.contains(f"'track_id': {track_id}")) & (log_df['details'].str.contains(f"'{line_type}'"))]
            total_usage_time = 0
            for _, acq in acquired_events.iterrows():
                rel_events = released_events[(released_events['item_id'] == acq['item_id']) & (released_events['timestamp'] > acq['timestamp'])]
                if not rel_events.empty:
                    rel = rel_events.iloc[0]
                    total_usage_time += (rel['timestamp'] - acq['timestamp'])
            utilization_pct = (total_usage_time / total_time) * 100 if total_time > 0 else 0
            utilization_data.append({'resource_type': 'Track', 'resource_name': line_name, 'utilization_percent': utilization_pct})
    utilization_df = pd.DataFrame(utilization_data)
    utilization_df.to_csv(f'utilization_metrics_{suffix}.csv', index=False)
    print(f"  -> Saved 'utilization_metrics_{suffix}.csv'")

def generate_train_graph(log_df, stations_df, suffix):
    # ... (This function remains the same, just add suffix to output file)
    print(f"Generating train schedule graph for {suffix}...")
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(20, 10))
    station_map = stations_df.set_index('station_name')['distance_from_start_km'].to_dict()
    wait_times = {}
    for _, row in log_df[log_df['event_type'] == 'TRACK_ACQUIRED'].iterrows():
        wait_match = re.search(r'Waited (\d+\.\d+) mins', row['description'])
        if wait_match and float(wait_match.group(1)) > 0.1:
            train_id = row['item_id']
            if train_id not in wait_times:
                wait_times[train_id] = []
            wait_times[train_id].append({'start': row['timestamp'] - float(wait_match.group(1)), 'end': row['timestamp']})
    for train_id, group in log_df.groupby('item_id'):
        if train_id == 'SYSTEM': continue
        path_points = []
        train_events = group.sort_values('timestamp').to_dict('records')
        for event in train_events:
            event_type = event['event_type']
            timestamp = event['timestamp']
            description = event['description']
            details_str = event['details']
            if event_type == 'TRAIN_START':
                start_station_name = description.split(' from ')[-1]
                path_points.append({'timestamp': timestamp, 'distance': station_map[start_station_name]})
            elif event_type == 'TRACK_RELEASED':
                station_name = description.split(' at ')[-1]
                path_points.append({'timestamp': timestamp, 'distance': station_map[station_name]})
            elif event_type == 'PLATFORM_RELEASED':
                details = ast.literal_eval(details_str)
                station_id = details['station_id']
                station_name = stations_df[stations_df['station_id'] == station_id].iloc[0]['station_name']
                path_points.append({'timestamp': timestamp, 'distance': station_map[station_name]})
        if not path_points: continue
        path_df = pd.DataFrame(path_points).sort_values('timestamp').drop_duplicates()
        for i in range(len(path_df) - 1):
            p1 = path_df.iloc[i]
            p2 = path_df.iloc[i+1]
            is_conflict_halt = False
            if p1['distance'] == p2['distance']:
                if train_id in wait_times:
                    for wait in wait_times[train_id]:
                        if p1['timestamp'] <= wait['end'] and p2['timestamp'] >= wait['start']:
                            is_conflict_halt = True
                            break
            if is_conflict_halt:
                ax.plot([p1['timestamp'], p2['timestamp']], [p1['distance'], p2['distance']], color='red', linewidth=4, marker='o')
            else:
                ax.plot([p1['timestamp'], p2['timestamp']], [p1['distance'], p2['distance']], color='#1f77b4', marker='o', linestyle='-')
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], color='#1f77b4', lw=2, label='Train Path (Motion & Scheduled Halt)'), Line2D([0], [0], color='red', lw=4, label='Conflict Halt (Waiting for Track)')]
    ax.set_yticks(stations_df['distance_from_start_km'])
    ax.set_yticklabels(stations_df['station_name'])
    ax.set_ylabel('Station')
    ax.set_xlabel('Time (minutes)')
    ax.set_title(f'Time-Distance Train Graph ({suffix})')
    ax.invert_yaxis()
    ax.legend(handles=legend_elements, title="Legend", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f'train_schedule_graph_{suffix}.png')
    print(f"  -> Saved 'train_schedule_graph_{suffix}.png'")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 metrics.py <log_file_name.csv>")
        sys.exit(1)

    log_file = sys.argv[1]
    suffix = log_file.replace('simulation_log_', '').replace('.csv', '')
    
    print(f"--- Starting Metrics Analysis for {suffix} ---")
    log_df = pd.read_csv(log_file)
    trains_df = pd.read_csv('trains.csv')
    stations_df = pd.read_csv('stations.csv')
    tracks_df = pd.read_csv('tracks.csv')

    total_simulation_time = log_df['timestamp'].max()

    analyze_delays(trains_df, suffix)
    analyze_utilization(log_df, stations_df, tracks_df, total_simulation_time, suffix)
    # Congestion heatmap is less useful for comparison, so we can skip it for now.
    generate_train_graph(log_df, stations_df, suffix)
    
    print(f"--- Analysis for {suffix} Complete ---")
