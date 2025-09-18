import csv
from datetime import datetime, timedelta

class Logger:
    def __init__(self, file_path, sim_start_time):
        self.file_path = file_path
        self.sim_start_time = sim_start_time
        self.simulation_log = []
        # Clear the log file at the beginning of a simulation run
        with open(self.file_path, 'w') as f:
            f.write("--- Simulation Audit Trail ---\n")

    def get_formatted_time(self, sim_time_minutes):
        """Converts simulation minutes to a formatted time string."""
        sim_time_delta = timedelta(minutes=sim_time_minutes)
        real_time = self.sim_start_time + sim_time_delta
        return real_time.strftime('%H:%M')

    def log(self, sim_time, event_type, item_id, description, details=None):
        """Logs a human-readable event to the audit trail file."""
        formatted_time = self.get_formatted_time(sim_time)
        log_entry = f"[{formatted_time}] ({event_type}) {description}"
        
        with open(self.file_path, 'a') as f:
            f.write(log_entry + '\n')
            
        # Also save a structured log for potential CSV export
        self.simulation_log.append({
            'timestamp': sim_time,
            'event_type': event_type,
            'item_id': str(item_id),
            'description': description,
            'details': str(details) if details else ''
        })

    def save_to_csv(self, file_path):
        """Saves the structured simulation log to a CSV file."""
        if not self.simulation_log:
            return
        
        with open(file_path, 'w', newline='') as csvfile:
            fieldnames = self.simulation_log[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.simulation_log)
