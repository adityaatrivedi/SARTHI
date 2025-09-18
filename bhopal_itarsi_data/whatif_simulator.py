import pandas as pd
import numpy as np
import simpy
from datetime import datetime, timedelta
import json
import re
from typing import Dict, List, Any, Optional
from optimizer import AdvancedOptimizer
from logger import Logger
from dispatcher import GreedyDispatcher

class WhatIfSimulator:
    """
    Advanced what-if simulation framework for evaluating alternative scenarios,
    routing strategies, and operational decisions.
    """
    
    def __init__(self, tracks_df, trains_df, stations_df):
        self.tracks_df = tracks_df
        self.trains_df = trains_df
        self.stations_df = stations_df
        self.scenarios = {}
        self.results = {}
        
    def create_scenario(self, scenario_name: str, scenario_config: Dict[str, Any]) -> None:
        """
        Create a new what-if scenario.
        
        Args:
            scenario_name: Unique name for the scenario
            scenario_config: Configuration dictionary with scenario parameters
        """
        self.scenarios[scenario_name] = {
            'config': scenario_config,
            'created_at': datetime.now(),
            'status': 'created'
        }
        
    def run_scenario(self, scenario_name: str, simulation_duration: int = 480) -> Dict[str, Any]:
        """
        Run a what-if scenario simulation.
        
        Args:
            scenario_name: Name of the scenario to run
            simulation_duration: Duration of simulation in minutes
            
        Returns:
            Dictionary with simulation results
        """
        if scenario_name not in self.scenarios:
            raise ValueError(f"Scenario '{scenario_name}' not found")
            
        scenario = self.scenarios[scenario_name]
        config = scenario['config']
        
        # Create simulation environment
        env = simpy.Environment()
        
        # Setup logging
        logger = Logger(f'whatif_audit_{scenario_name}.log', datetime.now())
        
        # Apply scenario modifications
        modified_tracks, modified_trains, modified_stations = self._apply_scenario_modifications(
            config, env, logger
        )
        
        # Initialize optimizer and dispatcher
        optimizer = AdvancedOptimizer(modified_tracks, modified_trains, modified_stations)
        dispatcher = GreedyDispatcher(modified_tracks, modified_trains, modified_stations)
        
        # Run simulation
        results = self._run_scenario_simulation(
            env, modified_tracks, modified_trains, modified_stations,
            optimizer, dispatcher, logger, simulation_duration, config
        )
        
        # Store results
        self.results[scenario_name] = {
            'scenario_config': config,
            'simulation_results': results,
            'completed_at': datetime.now(),
            'status': 'completed'
        }
        
        scenario['status'] = 'completed'
        
        return results
    
    def _apply_scenario_modifications(self, config: Dict[str, Any], env, logger) -> tuple:
        """Apply scenario-specific modifications to the system."""
        modified_tracks = self.tracks_df.copy()
        modified_trains = self.trains_df.copy()
        modified_stations = self.stations_df.copy()
        
        # Apply track modifications
        if 'track_modifications' in config:
            for track_id, modifications in config['track_modifications'].items():
                track_idx = modified_tracks[modified_tracks['track_id'] == track_id].index
                if not track_idx.empty:
                    for key, value in modifications.items():
                        modified_tracks.loc[track_idx[0], key] = value
                        logger.log(env.now, 'SCENARIO_MODIFICATION', 'SYSTEM',
                                 f"Modified track {track_id}: {key} = {value}")
        
        # Apply train modifications
        if 'train_modifications' in config:
            for train_id, modifications in config['train_modifications'].items():
                train_idx = modified_trains[modified_trains['train_id'] == train_id].index
                if not train_idx.empty:
                    for key, value in modifications.items():
                        modified_trains.loc[train_idx[0], key] = value
                        logger.log(env.now, 'SCENARIO_MODIFICATION', 'SYSTEM',
                                 f"Modified train {train_id}: {key} = {value}")
        
        # Apply station modifications
        if 'station_modifications' in config:
            for station_id, modifications in config['station_modifications'].items():
                station_idx = modified_stations[modified_stations['station_id'] == station_id].index
                if not station_idx.empty:
                    for key, value in modifications.items():
                        modified_stations.loc[station_idx[0], key] = value
                        logger.log(env.now, 'SCENARIO_MODIFICATION', 'SYSTEM',
                                 f"Modified station {station_id}: {key} = {value}")
        
        return modified_tracks, modified_trains, modified_stations
    
    def _run_scenario_simulation(self, env, tracks_df, trains_df, stations_df,
                               optimizer, dispatcher, logger, duration, config):
        """Run the actual simulation for the scenario."""
        
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
        
        # Apply disruption events if specified
        if 'disruption_events' in config:
            for disruption in config['disruption_events']:
                env.process(self._disruption_process(env, disruption, logger))
        
        # Start train processes
        first_events = trains_df.loc[trains_df.groupby('train_id')['timestamp'].idxmin()]
        for _, train_info in first_events.iterrows():
            departure_time = datetime.fromisoformat(train_info['actual_departure'])
            delay = max(0, (departure_time - datetime.now()).total_seconds() / 60)
            
            def start_train_process(env, train_info, delay):
                if delay > 0:
                    yield env.timeout(delay)
                env.process(self._train_process(env, train_info, stations_df, tracks_df, 
                                             dispatcher, optimizer, logger))
            
            env.process(start_train_process(env, train_info, delay))
        
        # Run simulation
        env.run(until=duration)
        
        # Save results
        logger.save_to_csv(f'whatif_simulation_log_{config.get("name", "scenario")}.csv')
        
        return {
            'simulation_log': logger.simulation_log,
            'final_time': env.now,
            'total_trains': len(first_events)
        }
    
    def _disruption_process(self, env, disruption, logger):
        """Handle disruption events during simulation."""
        yield env.timeout(disruption['start_time'])
        
        logger.log(env.now, 'DISRUPTION_START', 'SYSTEM', 
                  f"Disruption: {disruption['description']}")
        
        # Apply disruption effects
        if disruption['type'] == 'track_blocked':
            track_id = disruption['track_id']
            track = self.tracks_df[self.tracks_df['track_id'] == track_id].iloc[0]
            resource = track['resources'][disruption['line']]
            
            # Block the resource
            with resource.request(priority=0) as req:
                yield req
                yield env.timeout(disruption['duration'])
        
        logger.log(env.now, 'DISRUPTION_END', 'SYSTEM', 
                  f"Disruption ended: {disruption['description']}")
    
    def _train_process(self, env, train_info, stations_df, tracks_df, dispatcher, optimizer, logger):
        """Enhanced train process with optimization integration."""
        train_id = train_info['train_id']
        direction = train_info['direction']
        speed_kph = train_info['speed_profile_kph']
        priority = train_info['priority_level']
        
        start_station_name = stations_df.iloc[0 if direction == 'DOWN' else -1]["station_name"]
        logger.log(env.now, 'TRAIN_START', train_id, 
                  f'Train {train_id} (P{priority}, {direction}) starting journey from {start_station_name}')
        
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
            optimized_schedule = optimizer.optimize(env, env.now, active_trains, logger)
            dispatcher.set_target_schedule(optimized_schedule)
            
            # Dispatch decision
            while True:
                decision = dispatcher.decide(env, train_info, i, logger)
                if decision['decision'] == 'hold':
                    hold_duration = decision['duration']
                    logger.log(env.now, 'TRAIN_HOLD', train_id, 
                              f'Train {train_id} held for {hold_duration} minutes by optimizer.')
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
                        dispatcher.update_track_occupancy(track['track_id'], train_id)
                        
                        travel_time_minutes = (track['distance_km'] / speed_kph) * 60
                        yield env.timeout(travel_time_minutes)
                        
                        dispatcher.update_track_occupancy(track['track_id'], None)
                        logger.log(env.now, 'TRACK_RELEASED', train_id, 
                                  f'Train {train_id} arrived at {end_station["station_name"]}')
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
    
    def compare_scenarios(self, scenario_names: List[str]) -> Dict[str, Any]:
        """
        Compare multiple scenarios and generate analysis.
        
        Args:
            scenario_names: List of scenario names to compare
            
        Returns:
            Comparison analysis results
        """
        if not all(name in self.results for name in scenario_names):
            missing = [name for name in scenario_names if name not in self.results]
            raise ValueError(f"Scenarios not found: {missing}")
        
        comparison = {
            'scenarios': scenario_names,
            'metrics': {},
            'recommendations': []
        }
        
        # Calculate metrics for each scenario
        for scenario_name in scenario_names:
            results = self.results[scenario_name]['simulation_results']
            metrics = self._calculate_scenario_metrics(results)
            comparison['metrics'][scenario_name] = metrics
        
        # Generate recommendations
        comparison['recommendations'] = self._generate_recommendations(comparison['metrics'])
        
        return comparison
    
    def _calculate_scenario_metrics(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate performance metrics for a scenario."""
        log = results['simulation_log']
        
        # Calculate average delay
        delays = []
        for event in log:
            if event['event_type'] == 'TRAIN_HOLD':
                # Extract delay from hold events
                delay_match = re.search(r'held for (\d+\.?\d*) minutes', event['description'])
                if delay_match:
                    delays.append(float(delay_match.group(1)))
        
        avg_delay = np.mean(delays) if delays else 0
        
        # Calculate throughput
        total_trains = results['total_trains']
        simulation_time = results['final_time']
        throughput = total_trains / (simulation_time / 60) if simulation_time > 0 else 0
        
        # Calculate punctuality
        on_time_trains = sum(1 for delay in delays if delay <= 5)  # Within 5 minutes
        punctuality = on_time_trains / len(delays) if delays else 1.0
        
        return {
            'average_delay': avg_delay,
            'throughput': throughput,
            'punctuality': punctuality,
            'total_trains': total_trains,
            'simulation_time': simulation_time
        }
    
    def _generate_recommendations(self, metrics: Dict[str, Dict[str, float]]) -> List[str]:
        """Generate recommendations based on scenario comparison."""
        recommendations = []
        
        # Find best performing scenario for each metric
        best_delay = min(metrics.items(), key=lambda x: x[1]['average_delay'])
        best_throughput = max(metrics.items(), key=lambda x: x[1]['throughput'])
        best_punctuality = max(metrics.items(), key=lambda x: x[1]['punctuality'])
        
        recommendations.append(f"Best delay performance: {best_delay[0]} (avg delay: {best_delay[1]['average_delay']:.2f} min)")
        recommendations.append(f"Best throughput: {best_throughput[0]} ({best_throughput[1]['throughput']:.2f} trains/hour)")
        recommendations.append(f"Best punctuality: {best_punctuality[0]} ({best_punctuality[1]['punctuality']:.2%})")
        
        return recommendations

# Predefined scenario templates
class ScenarioTemplates:
    """Collection of predefined scenario templates for common what-if analyses."""
    
    @staticmethod
    def weather_disruption_scenario():
        """Scenario with severe weather conditions."""
        return {
            'name': 'severe_weather',
            'description': 'Simulation with severe weather conditions affecting operations',
            'track_modifications': {
                1: {'geographical_condition': 'storm', 'expected_delay_minutes': 30},
                2: {'geographical_condition': 'storm', 'expected_delay_minutes': 25}
            },
            'disruption_events': [
                {
                    'type': 'weather_impact',
                    'start_time': 60,
                    'duration': 120,
                    'description': 'Severe storm affecting track conditions',
                    'speed_reduction': 0.5
                }
            ]
        }
    
    @staticmethod
    def maintenance_scenario():
        """Scenario with track maintenance activities."""
        return {
            'name': 'track_maintenance',
            'description': 'Simulation with scheduled track maintenance',
            'track_modifications': {
                3: {'maintenance_status': 'yes', 'expected_delay_minutes': 45}
            },
            'disruption_events': [
                {
                    'type': 'track_blocked',
                    'track_id': 3,
                    'line': 'down_line',
                    'start_time': 90,
                    'duration': 180,
                    'description': 'Track 3 down line blocked for maintenance'
                }
            ]
        }
    
    @staticmethod
    def high_priority_scenario():
        """Scenario with increased high-priority train traffic."""
        return {
            'name': 'high_priority_traffic',
            'description': 'Simulation with increased high-priority train traffic',
            'train_modifications': {
                12000: {'priority_level': 1, 'speed_profile_kph': 100},
                12001: {'priority_level': 1, 'speed_profile_kph': 95}
            }
        }
    
    @staticmethod
    def capacity_reduction_scenario():
        """Scenario with reduced station/platform capacity."""
        return {
            'name': 'capacity_reduction',
            'description': 'Simulation with reduced station capacity',
            'station_modifications': {
                1: {'number_of_platforms': 3},  # Reduced from 6
                7: {'number_of_platforms': 4}    # Reduced from 8
            }
        }
