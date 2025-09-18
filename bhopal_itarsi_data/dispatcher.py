class GreedyDispatcher:
    def __init__(self, tracks_df, trains_df, stations_df):
        self.tracks_df = tracks_df
        self.trains_df = trains_df
        self.stations_df = stations_df
        # This state needs to be updated by the main simulation loop
        self.track_occupancy = {track_id: None for track_id in self.tracks_df['track_id']}
        # Store target schedule from optimizer
        self.target_schedule = {}

    def set_target_schedule(self, target_schedule):
        """Sets the target schedule from the optimizer."""
        self.target_schedule = target_schedule

    def decide(self, env, train_info, current_track_index, logger):
        """Makes a dispatch decision for a train requesting a track."""
        train_id = train_info['train_id']
        direction = train_info['direction']
        priority = train_info['priority_level']

        # 1. Check if there's a target schedule from the optimizer
        if train_id in self.target_schedule:
            target_departure = self.target_schedule[train_id].get('target_departure')
            if target_departure and env.now < target_departure:
                # Hold the train until the target departure time
                hold_duration = target_departure - env.now
                logger.log(env.now, 'DISPATCH_DECISION', train_id, 
                           f"Train {train_id} (P{priority}) held to meet optimizer target departure at {target_departure:.2f}. Hold duration: {hold_duration:.2f} minutes.")
                return {'decision': 'hold', 'duration': hold_duration}

        # 2. Proactive Hold Logic (Smarter Greedy Rule)
        # Hold low-priority trains for approaching high-priority ones.
        if priority > 2: # Freight or Passenger
            is_high_priority_approaching = self._look_ahead_for_high_priority(current_track_index, direction)
            if is_high_priority_approaching:
                logger.log(env.now, 'DISPATCH_DECISION', train_id, 
                           f"Train {train_id} (P{priority}) held at track {current_track_index} for approaching high-priority train.")
                return {'decision': 'hold', 'duration': 10} # Hold for 10 minutes

        # 3. Priority-aware tie-breaking when both lines are available
        track = self.tracks_df.iloc[current_track_index]
        dedicated_line_name = f'{direction.lower()}_line'
        
        dedicated_resource = track['resources'][dedicated_line_name]
        central_resource = track['resources']['central_line']

        # Both lines available - use priority-aware selection
        if (dedicated_resource.count < dedicated_resource.capacity and 
            central_resource.count < central_resource.capacity):
            # For high-priority trains, prefer dedicated line
            # For low-priority trains, prefer central line to free up dedicated line for others
            if priority <= 2:  # High priority
                logger.log(env.now, 'DISPATCH_DECISION', train_id, 
                           f"Train {train_id} (P{priority}) assigned to dedicated {direction} line for track {track['track_id']} (priority-based selection).")
                return {'decision': 'proceed', 'line': dedicated_line_name}
            else:  # Low priority
                logger.log(env.now, 'DISPATCH_DECISION', train_id, 
                           f"Train {train_id} (P{priority}) assigned to fallback CENTRAL line for track {track['track_id']} (priority-based selection to free dedicated line).")
                return {'decision': 'proceed', 'line': 'central_line'}
        
        # Prefer dedicated line if available
        elif dedicated_resource.count < dedicated_resource.capacity:
            logger.log(env.now, 'DISPATCH_DECISION', train_id, 
                       f"Train {train_id} assigned to dedicated {direction} line for track {track['track_id']}.")
            return {'decision': 'proceed', 'line': dedicated_line_name}
        # Fallback to central line
        elif central_resource.count < central_resource.capacity:
            logger.log(env.now, 'DISPATCH_DECISION', train_id, 
                       f"Train {train_id} assigned to fallback CENTRAL line for track {track['track_id']}. Dedicated line was busy.")
            return {'decision': 'proceed', 'line': 'central_line'}
        # If both are busy, wait. The PriorityResource will handle the queue.
        else:
            logger.log(env.now, 'DISPATCH_DECISION', train_id, 
                       f"Train {train_id} must wait for a free line (Dedicated or Central) for track {track['track_id']}.")
            return {'decision': 'wait'}

    def _look_ahead_for_high_priority(self, current_track_index, direction):
        """Looks at the *previous* track segment to see if a high-priority train is on it."""
        if direction == 'DOWN' and current_track_index > 0:
            prev_track_id = self.tracks_df.iloc[current_track_index - 1]['track_id']
        elif direction == 'UP' and current_track_index < len(self.tracks_df) - 1:
            prev_track_id = self.tracks_df.iloc[current_track_index + 1]['track_id']
        else:
            return False # No previous track to look at

        occupying_train_id_str = self.track_occupancy.get(prev_track_id)
        if occupying_train_id_str:
            try:
                occupying_train_id = int(occupying_train_id_str)
                train_info = self.trains_df[self.trains_df['train_id'] == occupying_train_id].iloc[0]
                if train_info['priority_level'] <= 2: # High-priority (Mail/Express, Rajdhani/Shatabdi)
                    return True
            except (ValueError, IndexError):
                return False # In case of invalid train ID or not found
        return False

    def update_track_occupancy(self, track_id, train_id):
        """To be called by the simulation when a train enters or leaves a track."""
        self.track_occupancy[track_id] = train_id
