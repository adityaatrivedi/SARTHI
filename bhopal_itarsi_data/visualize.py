import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime, timedelta
import re  # Add import for regex

def plot_train_schedule(log_files_info, title="Train Schedule Comparison", output_filename="train_schedule_comparison.png", start_time_str=None):
    # log_files_info is a list of tuples: [(log_file_path, label, color, linestyle)]
    
    if not log_files_info:
        print("No log files provided for plotting.")
        return

    fig, ax = plt.subplots(figsize=(18, 10))
    
    # Determine simulation start time
    if start_time_str:
        sim_start_datetime = datetime.fromisoformat(start_time_str)
    else:
        print("Error: Simulation start time must be provided.")
        return

    all_train_ids = set()
    processed_data = []

    for log_file_path, label, color, linestyle in log_files_info:
        try:
            df = pd.read_csv(log_file_path)
        except FileNotFoundError:
            print(f"Warning: Log file not found: {log_file_path}. Skipping.")
            continue

        train_movement_df = df[df['event_type'].isin(['TRAIN_START', 'TRACK_ACQUIRED', 'TRACK_RELEASED', 'PLATFORM_ACQUIRED', 'PLATFORM_RELEASED', 'TRAIN_HOLD'])]
        
        if train_movement_df.empty:
            print(f"No relevant events found in {log_file_path}")
            continue

        # Fix the SettingWithCopyWarning
        train_movement_df = train_movement_df.copy()
        train_movement_df['absolute_time'] = train_movement_df['timestamp'].apply(lambda x: sim_start_datetime + timedelta(minutes=x))

        for train_id in train_movement_df['item_id'].unique():
            all_train_ids.add(train_id)
            train_df = train_movement_df[train_movement_df['item_id'] == train_id].sort_values(by='timestamp')
            
            current_location = None
            start_event_time = None
            
            # Track segments for this train in this scenario
            segments = []

            for _, row in train_df.iterrows():
                event_type = row['event_type']
                absolute_time = row['absolute_time']
                description = row['description']

                if event_type == 'TRAIN_START':
                    current_location = description.split('from ')[1].split(' ')[0]
                    start_event_time = absolute_time
                elif event_type == 'TRACK_ACQUIRED':
                    if current_location and start_event_time:
                        segments.append({'type': 'travel', 'start': start_event_time, 'end': absolute_time, 'location': current_location})
                    current_location = description.split('to ')[1].split('.')[0]
                    start_event_time = absolute_time
                elif event_type == 'TRACK_RELEASED':
                    if current_location and start_event_time:
                        segments.append({'type': 'travel', 'start': start_event_time, 'end': absolute_time, 'location': current_location})
                    current_location = description.split('arrived at ')[1].split(' ')[0]
                    start_event_time = absolute_time
                elif event_type == 'PLATFORM_ACQUIRED':
                    if current_location and start_event_time:
                        segments.append({'type': 'travel', 'start': start_event_time, 'end': absolute_time, 'location': current_location})
                    start_event_time = absolute_time
                elif event_type == 'PLATFORM_RELEASED':
                    if current_location and start_event_time:
                        segments.append({'type': 'dwell', 'start': start_event_time, 'end': absolute_time, 'location': description.split('departing ')[1].split(' ')[0]})
                    start_event_time = absolute_time
                elif event_type == 'TRAIN_HOLD':
                    # A hold event means the train is stationary. We can represent this as a dwell.
                    # The duration of the hold is in the description, e.g., "held for 10 minutes"
                    hold_match = re.search(r'held for (\d+\.?\d*) minutes', description)
                    if hold_match:
                        hold_duration = float(hold_match.group(1))
                        hold_end_time = absolute_time # The log entry is when the hold decision is made
                        hold_start_time = absolute_time - timedelta(minutes=hold_duration) # This is an approximation
                        # We need to find the actual start of the hold. For now, let's assume the log entry marks the start of the hold.
                        # A better approach would be to log the start and end of the hold explicitly.
                        # For now, let's just mark the point of decision.
                        segments.append({'type': 'hold', 'start': absolute_time, 'end': absolute_time + timedelta(minutes=1), 'location': 'Held'}) # Mark as a short event
                    else:
                        # If we can't parse the duration, just mark it as a point event
                        segments.append({'type': 'hold', 'start': absolute_time, 'end': absolute_time + timedelta(minutes=1), 'location': 'Held'})
            
            # Add the processed segments for this train and scenario
            processed_data.append({'train_id': train_id, 'scenario_label': label, 'color': color, 'linestyle': linestyle, 'segments': segments})

    if not processed_data:
        print("No data to plot.")
        return

    # Convert train IDs to strings to avoid sorting issues
    sorted_train_ids = sorted(list(all_train_ids), key=lambda x: str(x))
    y_pos_map = {train_id: i for i, train_id in enumerate(sorted_train_ids)}
    num_trains = len(all_train_ids)

    # Plotting
    height_per_train = 1.0 / (len(log_files_info) + 1) # Allocate space for each scenario per train
    
    for data_entry in processed_data:
        train_id = data_entry['train_id']
        scenario_label = data_entry['scenario_label']
        color = data_entry['color']
        linestyle = data_entry['linestyle']
        segments = data_entry['segments']

        base_y = y_pos_map[train_id]
        # Offset y position for each scenario to avoid overlap
        scenario_offset = [info[1] for info in log_files_info].index(scenario_label) * height_per_train
        y_center = base_y + scenario_offset + height_per_train / 2

        for segment in segments:
            start_minutes = (segment['start'] - sim_start_datetime).total_seconds() / 60
            end_minutes = (segment['end'] - sim_start_datetime).total_seconds() / 60
            duration_minutes = end_minutes - start_minutes
            
            if duration_minutes > 0:
                if segment['type'] == 'travel':
                    ax.plot([start_minutes, end_minutes], [y_center, y_center], 
                            color=color, linestyle=linestyle, linewidth=4, 
                            label=f'{scenario_label} Train {train_id}' if f'{scenario_label}-{train_id}' not in [str(label) for label in ax.get_legend_handles_labels()[1]] else "")
                elif segment['type'] == 'dwell':
                    ax.plot([start_minutes, end_minutes], [y_center, y_center], 
                            color=color, linestyle='-', linewidth=6, alpha=0.7,
                            label=f'{scenario_label} Train {train_id} Dwell' if f'{scenario_label}-{train_id}-Dwell' not in [str(label) for label in ax.get_legend_handles_labels()[1]] else "")
                elif segment['type'] == 'hold':
                    ax.plot([start_minutes, end_minutes], [y_center, y_center], 
                            color='red', linestyle='--', linewidth=6, alpha=0.8,
                            label=f'{scenario_label} Train {train_id} Held' if f'{scenario_label}-{train_id}-Held' not in [str(label) for label in ax.get_legend_handles_labels()[1]] else "")
                
                # Add text for location/event if needed, adjust position
                # ax.text(start_minutes + duration_minutes / 2, y_center, 
                #         segment['location'], va='center', ha='center', color='white', fontsize=6)

    ax.set_yticks([y_pos_map[tid] + (len(log_files_info) * height_per_train / 2) for tid in sorted_train_ids])
    ax.set_yticklabels([f'Train {tid}' for tid in sorted_train_ids])
    ax.set_xlabel("Time (minutes from simulation start)")
    ax.set_ylabel("Train ID")
    ax.set_title(title)
    ax.grid(True, axis='x', linestyle='--')
    
    # Create custom legend handles for scenarios
    from matplotlib.lines import Line2D
    legend_handles = []
    for log_file_path, label, color, linestyle in log_files_info:
        legend_handles.append(Line2D([0], [0], color=color, linestyle=linestyle, lw=4, label=label))
    
    ax.legend(handles=legend_handles, title="Scenarios", bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig(output_filename)
    plt.close()

if __name__ == "__main__":
    # Example usage for comparison
    # You would get the sim_start_time from your trains.csv or a config
    example_start_time = "2025-09-17T00:00:00" # Assuming simulation starts at midnight

    log_files_to_compare = [
        ('simulation_log_baseline.csv', 'Baseline', 'blue', '-'),
        ('simulation_log_greedy.csv', 'Smarter Greedy', 'green', '--')
    ]

    plot_train_schedule(log_files_to_compare,
                        title="Train Schedule Comparison: Baseline vs. Smarter Greedy",
                        output_filename="train_schedule_comparison.png",
                        start_time_str=example_start_time)

    print("Comparison plot generated: train_schedule_comparison.png")
