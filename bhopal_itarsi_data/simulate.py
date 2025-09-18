import simpy
import pandas as pd
import csv
from datetime import datetime
from logger import Logger
from dispatcher import GreedyDispatcher
from optimizer import AdvancedOptimizer
from whatif_simulator import WhatIfSimulator, ScenarioTemplates
from advanced_audit import AdvancedAuditTrail, RealTimeDashboard
from performance_dashboard import PerformanceDashboard

# --- Global State ---
simulation_state = {'speed_multiplier': 1.0}

# --- Simulation Processes ---
def train(env, train_info, stations, tracks, greedy_dispatcher, logger):
    train_id = train_info['train_id']
    direction = train_info['direction']
    speed_kph = train_info['speed_profile_kph']
    priority = train_info['priority_level']

    start_station_name = stations.iloc[0 if direction == 'DOWN' else -1]["station_name"]
    logger.log(env.now, 'TRAIN_START', train_id, f'Train {train_id} (P{priority}, {direction}) starting journey from {start_station_name}')

    track_indices = range(len(tracks)) if direction == 'DOWN' else reversed(range(len(tracks)))

    for i in track_indices:
        track = tracks.iloc[i]
        end_station = stations.iloc[i + 1 if direction == 'DOWN' else i - 1]

        platform_resource = end_station['platform_resource']
        platform_req = platform_resource.request(priority=priority)
        logger.log(env.now, 'PLATFORM_REQUEST', train_id, f'Train {train_id} waiting for platform at {end_station["station_name"]}')
        yield platform_req
        logger.log(env.now, 'PLATFORM_ACQUIRED', train_id, f'Train {train_id} acquired platform at {end_station["station_name"]}')

        # --- Dispatcher Decision ---
        while True:
            decision = greedy_dispatcher.decide(env, train_info, i, logger)
            if decision['decision'] == 'hold':
                hold_duration = decision['duration']
                logger.log(env.now, 'TRAIN_HOLD', train_id, f'Train {train_id} held for {hold_duration} minutes by greedy dispatcher.')
                yield env.timeout(hold_duration)
                # Re-evaluate decision after hold
            elif decision['decision'] == 'proceed':
                line_to_request = decision['line']
                track_resource = track['resources'][line_to_request]
                
                req_start_time = env.now
                with track_resource.request(priority=priority) as line_req:
                    yield line_req
                    wait_time = env.now - req_start_time
                    logger.log(env.now, 'TRACK_ACQUIRED', train_id, f'Train {train_id} (P{priority}) got {line_to_request} line to {end_station["station_name"]}. Waited {wait_time:.2f} mins.', {'track_id': track['track_id'], 'line_type': line_to_request})
                    greedy_dispatcher.update_track_occupancy(track['track_id'], train_id)

                    current_speed_kph = speed_kph * simulation_state['speed_multiplier']
                    travel_time_minutes = (track['distance_km'] / current_speed_kph) * 60
                    yield env.timeout(travel_time_minutes)
                    
                    greedy_dispatcher.update_track_occupancy(track['track_id'], None) # Release track
                    logger.log(env.now, 'TRACK_RELEASED', train_id, f'Train {train_id} arrived at {end_station["station_name"]}', {'track_id': track['track_id'], 'line_type': line_to_request})
                break # Exit while loop after proceeding
            elif decision['decision'] == 'wait':
                # If the dispatcher says wait, it means both lines are busy.
                # The train process will implicitly wait by yielding to the environment
                # and retrying the decision in the next simulation step (or after a small timeout).
                # For now, we'll just yield a small timeout and re-evaluate.
                logger.log(env.now, 'TRAIN_WAIT', train_id, f"Train {train_id} waiting for a line to clear for track {track['track_id']}.")
                yield env.timeout(1) # Wait for 1 minute before re-evaluating

        stoppage_time = 5
        yield env.timeout(stoppage_time)
        if i != (len(tracks) - 1 if direction == 'DOWN' else 0):
            logger.log(env.now, 'PLATFORM_RELEASED', train_id, f'Train {train_id} departing {end_station["station_name"]}', {'station_id': end_station['station_id']})
        platform_resource.release(platform_req)

def run_simulation(stations_df, tracks_df, trains_df, events_df, log_suffix="greedy"):
    env = simpy.Environment()
    
    # Determine simulation start time for logging
    first_scheduled_arrival_str = trains_df.iloc[0]['scheduled_arrival']
    sim_start_time = datetime.fromisoformat(first_scheduled_arrival_str)
    
    logger = Logger(f'bhopal_itarsi_data/audit_trail_{log_suffix}.log', sim_start_time)

    stations_df['platform_resource'] = [simpy.PriorityResource(env, capacity=row['number_of_platforms']) for _, row in stations_df.iterrows()]
    track_resources = []
    for _ in range(len(tracks_df)):
        track_resources.append({'down_line': simpy.PriorityResource(env, capacity=1), 'up_line': simpy.PriorityResource(env, capacity=1), 'central_line': simpy.PriorityResource(env, capacity=1)})
    tracks_df['resources'] = track_resources

    greedy_dispatcher = GreedyDispatcher(tracks_df, trains_df, stations_df)

    first_events = trains_df.loc[trains_df.groupby('train_id')['timestamp'].idxmin()]
    for _, train_info in first_events.iterrows():
        departure_time = datetime.fromisoformat(train_info['actual_departure'])
        # Use the determined sim_start_time for delay calculation
        delay = max(0, (departure_time - sim_start_time).total_seconds() / 60)
        
        def start_train_process(env, train_info, delay):
            if delay > 0: yield env.timeout(delay)
            env.process(train(env, train_info, stations_df, tracks_df, greedy_dispatcher, logger))

        env.process(start_train_process(env, train_info, delay))
    
    # env.process(event_manager(env, events_df, tracks_df, trains_df)) # Disable events for a clean comparison

    print(f"--- Running {log_suffix.replace('_', ' ').title()} Simulation ---")
    env.run(until=480)

    logger.save_to_csv(f'simulation_log_{log_suffix}.csv')
    print(f"--- {log_suffix.replace('_', ' ').title()} Simulation Finished. Log file 'simulation_log_{log_suffix}.csv' and 'audit_trail_{log_suffix}.log' created. ---")
    return sim_start_time


def simulate_whatif(stations_df, tracks_df, trains_df, events_df, disruption_event, log_suffix="whatif"):
    """Runs a simulation with a specific disruption event."""
    print(f"--- Running What-If Simulation with disruption: {disruption_event['description']} ({log_suffix}) ---")
    env = simpy.Environment()
    
    first_scheduled_arrival_str = trains_df.iloc[0]['scheduled_arrival']
    sim_start_time = datetime.fromisoformat(first_scheduled_arrival_str)
    
    logger = Logger(f'bhopal_itarsi_data/audit_trail_{log_suffix}.log', sim_start_time)

    stations_df['platform_resource'] = [simpy.PriorityResource(env, capacity=row['number_of_platforms']) for _, row in stations_df.iterrows()]
    track_resources = []
    for _ in range(len(tracks_df)):
        track_resources.append({'down_line': simpy.PriorityResource(env, capacity=1), 'up_line': simpy.PriorityResource(env, capacity=1), 'central_line': simpy.PriorityResource(env, capacity=1)})
    tracks_df['resources'] = track_resources

    greedy_dispatcher = GreedyDispatcher(tracks_df, trains_df, stations_df)

    first_events = trains_df.loc[trains_df.groupby('train_id')['timestamp'].idxmin()]
    for _, train_info in first_events.iterrows():
        departure_time = datetime.fromisoformat(train_info['actual_departure'])
        delay = max(0, (departure_time - sim_start_time).total_seconds() / 60)
        
        def start_train_process(env, train_info, delay):
            if delay > 0: yield env.timeout(delay)
            env.process(train(env, train_info, stations_df, tracks_df, greedy_dispatcher, logger))

        env.process(start_train_process(env, train_info, delay))
    
    # Inject disruption event
    def disruption_process(env, disruption):
        yield env.timeout(disruption['time'])
        logger.log(env.now, 'DISRUPTION', 'SYSTEM', disruption['description'])
        # For now, a simple disruption: block a track for a duration
        # In a real scenario, this would interact with track resources
        # For example, by temporarily setting capacity to 0 or holding trains
        print(f"Disruption at {env.now} minutes: {disruption['description']}")
        # Example: Block track 1's down line for 60 minutes
        if 'track_id' in disruption and 'line' in disruption and 'duration' in disruption:
            track_to_block = tracks_df[tracks_df['track_id'] == disruption['track_id']].iloc[0]
            resource_to_block = track_to_block['resources'][disruption['line']]
            
            # Acquire the resource to block it
            with resource_to_block.request(priority=0) as req:
                yield req
                logger.log(env.now, 'TRACK_BLOCKED', disruption['track_id'], f"Track {disruption['track_id']} {disruption['line']} blocked for {disruption['duration']} minutes.")
                yield env.timeout(disruption['duration'])
            logger.log(env.now, 'TRACK_UNBLOCKED', disruption['track_id'], f"Track {disruption['track_id']} {disruption['line']} unblocked.")

    env.process(disruption_process(env, disruption_event))

    env.run(until=480)

    logger.save_to_csv(f'simulation_log_{log_suffix}.csv')
    print(f"--- What-If Simulation Finished. Log file 'simulation_log_{log_suffix}.csv' and 'audit_trail_{log_suffix}.log' created. ---")
    return sim_start_time


def run_advanced_simulation(stations_df, tracks_df, trains_df, events_df, 
                           simulation_type="optimized", log_suffix="advanced"):
    """
    Run advanced simulation with AI-driven optimization and comprehensive monitoring.
    """
    print(f"\n--- Running {simulation_type.title()} Simulation with Advanced Features ---")
    
    env = simpy.Environment()
    
    # Initialize advanced components
    audit_trail = AdvancedAuditTrail(f"audit_trail_{log_suffix}.db")
    optimizer = AdvancedOptimizer(tracks_df, trains_df, stations_df)
    dispatcher = GreedyDispatcher(tracks_df, trains_df, stations_df)
    performance_dashboard = PerformanceDashboard(audit_trail)
    
    # Setup logging
    first_scheduled_arrival_str = trains_df.iloc[0]['scheduled_arrival']
    sim_start_time = datetime.fromisoformat(first_scheduled_arrival_str)
    logger = Logger(f'audit_trail_{log_suffix}.log', sim_start_time)
    
    # Setup resources
    stations_df['platform_resource'] = [
        simpy.PriorityResource(env, capacity=row['number_of_platforms']) 
        for _, row in stations_df.iterrows()
    ]
    
    track_resources = []
    for _ in range(len(tracks_df)):
        track_resources.append({
            'down_line': simpy.PriorityResource(env, capacity=1),
            'up_line': simpy.PriorityResource(env, capacity=1),
            'central_line': simpy.PriorityResource(env, capacity=1)
        })
    tracks_df['resources'] = track_resources
    
    # Enhanced train process with optimization
    def advanced_train_process(env, train_info, stations_df, tracks_df, 
                              dispatcher, optimizer, audit_trail, logger):
        train_id = train_info['train_id']
        direction = train_info['direction']
        speed_kph = train_info['speed_profile_kph']
        priority = train_info['priority_level']
        
        start_station_name = stations_df.iloc[0 if direction == 'DOWN' else -1]["station_name"]
        logger.log(env.now, 'TRAIN_START', train_id, 
                  f'Train {train_id} (P{priority}, {direction}) starting journey from {start_station_name}')
        
        # Log decision start
        audit_trail.log_audit_event(env.now, 'TRAIN_START', train_id, 
                                   decision_type='SCHEDULING', 
                                   decision_details=f'Starting train {train_id}')
        
        track_indices = range(len(tracks_df)) if direction == 'DOWN' else reversed(range(len(tracks_df)))
        
        for i in track_indices:
            track = tracks_df.iloc[i]
            end_station = stations_df.iloc[i + 1 if direction == 'DOWN' else i - 1]
            
            # Platform request
            platform_resource = end_station['platform_resource']
            platform_req = platform_resource.request(priority=priority)
            logger.log(env.now, 'PLATFORM_REQUEST', train_id, 
                      f'Train {train_id} waiting for platform at {end_station["station_name"]}')
            yield platform_req
            logger.log(env.now, 'PLATFORM_ACQUIRED', train_id, 
                      f'Train {train_id} acquired platform at {end_station["station_name"]}')
            
            # Get optimization decision
            active_trains = [{'train_id': train_id, 'priority': priority, 'next_departure_time': env.now}]
            start_opt_time = env.now
            optimized_schedule = optimizer.optimize(env, env.now, active_trains, logger)
            opt_time = env.now - start_opt_time
            
            # Log optimization decision
            audit_trail.log_decision(env.now, 'OPTIMIZATION', train_id,
                                  {'train_info': train_info, 'track_id': track['track_id']},
                                  optimized_schedule.get(train_id, {}),
                                  confidence_score=0.85, execution_time=opt_time, success=True)
            
            dispatcher.set_target_schedule(optimized_schedule)
            
            # Dispatch decision
            while True:
                decision = dispatcher.decide(env, train_info, i, logger)
                if decision['decision'] == 'hold':
                    hold_duration = decision['duration']
                    logger.log(env.now, 'TRAIN_HOLD', train_id, 
                              f'Train {train_id} held for {hold_duration} minutes by optimizer.')
                    
                    # Log hold decision
                    audit_trail.log_audit_event(env.now, 'TRAIN_HOLD', train_id,
                                              track_id=track['track_id'],
                                              decision_type='HOLDING',
                                              decision_details=f'Held for {hold_duration} minutes',
                                              performance_impact=hold_duration)
                    
                    yield env.timeout(hold_duration)
                elif decision['decision'] == 'proceed':
                    line_to_request = decision['line']
                    track_resource = track['resources'][line_to_request]
                    
                    req_start_time = env.now
                    with track_resource.request(priority=priority) as line_req:
                        yield line_req
                        wait_time = env.now - req_start_time
                        logger.log(env.now, 'TRACK_ACQUIRED', train_id, 
                                  f'Train {train_id} (P{priority}) got {line_to_request} line to {end_station["station_name"]}. Waited {wait_time:.2f} mins.')
                        
                        # Log track acquisition
                        audit_trail.log_audit_event(env.now, 'TRACK_ACQUIRED', train_id,
                                                  track_id=track['track_id'],
                                                  decision_type='ROUTING',
                                                  decision_details=f'Assigned to {line_to_request}',
                                                  performance_impact=wait_time)
                        
                        dispatcher.update_track_occupancy(track['track_id'], train_id)
                        
                        travel_time_minutes = (track['distance_km'] / speed_kph) * 60
                        yield env.timeout(travel_time_minutes)
                        
                        dispatcher.update_track_occupancy(track['track_id'], None)
                        logger.log(env.now, 'TRACK_RELEASED', train_id, 
                                  f'Train {train_id} arrived at {end_station["station_name"]}')
                        
                        # Log track release
                        audit_trail.log_audit_event(env.now, 'TRACK_RELEASED', train_id,
                                                  track_id=track['track_id'],
                                                  decision_type='ROUTING',
                                                  decision_details='Track released')
                    break
                elif decision['decision'] == 'wait':
                    logger.log(env.now, 'TRAIN_WAIT', train_id, 
                              f'Train {train_id} waiting for a line to clear for track {track["track_id"]}.')
                    yield env.timeout(1)
            
            # Station dwell time
            stoppage_time = 5
            yield env.timeout(stoppage_time)
            if i != (len(tracks_df) - 1 if direction == 'DOWN' else 0):
                logger.log(env.now, 'PLATFORM_RELEASED', train_id, 
                          f'Train {train_id} departing {end_station["station_name"]}')
            platform_resource.release(platform_req)
    
    # Start train processes
    first_events = trains_df.loc[trains_df.groupby('train_id')['timestamp'].idxmin()]
    for _, train_info in first_events.iterrows():
        departure_time = datetime.fromisoformat(train_info['actual_departure'])
        delay = max(0, (departure_time - sim_start_time).total_seconds() / 60)
        
        def start_train_process(env, train_info, delay):
            if delay > 0:
                yield env.timeout(delay)
            env.process(advanced_train_process(env, train_info, stations_df, tracks_df,
                                             dispatcher, optimizer, audit_trail, logger))
        
        env.process(start_train_process(env, train_info, delay))
    
    # Run simulation
    env.run(until=480)
    
    # Generate performance report
    performance_report = performance_dashboard.create_performance_report(0, env.now)
    
    # Save results
    logger.save_to_csv(f'simulation_log_{log_suffix}.csv')
    audit_trail.export_audit_data(f'audit_data_{log_suffix}')
    
    print(f"--- {simulation_type.title()} Simulation Finished ---")
    print(f"Performance Report: {performance_report['kpis']}")
    
    return sim_start_time, performance_report

def run_whatif_analysis(stations_df, tracks_df, trains_df, events_df):
    """Run comprehensive what-if analysis with multiple scenarios."""
    print("\n--- Running What-If Analysis ---")
    
    whatif_simulator = WhatIfSimulator(tracks_df, trains_df, stations_df)
    
    # Create scenarios
    scenarios = {
        'baseline': {'name': 'baseline', 'description': 'Baseline scenario'},
        'weather_disruption': ScenarioTemplates.weather_disruption_scenario(),
        'maintenance': ScenarioTemplates.maintenance_scenario(),
        'high_priority': ScenarioTemplates.high_priority_scenario(),
        'capacity_reduction': ScenarioTemplates.capacity_reduction_scenario()
    }
    
    # Create scenarios in simulator
    for name, config in scenarios.items():
        whatif_simulator.create_scenario(name, config)
    
    # Run scenarios
    results = {}
    for scenario_name in scenarios.keys():
        print(f"Running scenario: {scenario_name}")
        results[scenario_name] = whatif_simulator.run_scenario(scenario_name)
    
    # Compare scenarios
    comparison = whatif_simulator.compare_scenarios(list(scenarios.keys()))
    
    print("What-If Analysis Results:")
    for scenario, metrics in comparison['metrics'].items():
        print(f"{scenario}: Punctuality={metrics['punctuality']:.1f}%, "
              f"Avg Delay={metrics['average_delay']:.1f}min, "
              f"Throughput={metrics['throughput']:.1f} trains/hr")
    
    return comparison

if __name__ == "__main__":
    stations = pd.read_csv("stations.csv")
    tracks = pd.read_csv("tracks.csv")
    trains_df = pd.read_csv("trains.csv")
    events_df = pd.read_csv("events.csv")

    # Run baseline simulation
    print("\n--- Running Baseline Simulation ---")
    sim_start_time_baseline = run_simulation(stations, tracks, trains_df, events_df, log_suffix="baseline")

    # Run advanced AI-driven simulation
    print("\n--- Running Advanced AI-Driven Simulation ---")
    sim_start_time_advanced, performance_report = run_advanced_simulation(
        stations, tracks, trains_df, events_df, simulation_type="optimized", log_suffix="optimized"
    )

    # Run what-if analysis
    whatif_results = run_whatif_analysis(stations, tracks, trains_df, events_df)

    # Generate comparison plots
    print("\n--- Generating Visualizations ---")
    from visualize import plot_train_schedule

    # Comparison of Baseline vs Advanced
    log_files_to_compare = [
        ('simulation_log_baseline.csv', 'Baseline', 'blue', '-'),
        ('simulation_log_optimized.csv', 'AI-Optimized', 'green', '--')
    ]
    plot_train_schedule(log_files_to_compare,
                        title="Train Schedule Comparison: Baseline vs. AI-Optimized",
                        output_filename="train_schedule_comparison.png",
                        start_time_str=sim_start_time_baseline.isoformat())

    print("Advanced simulation and analysis completed!")
    print(f"Performance KPIs: {performance_report['kpis']}")
    print("What-If Analysis completed with multiple scenarios.")