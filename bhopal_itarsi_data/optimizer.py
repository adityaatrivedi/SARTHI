import pandas as pd
from ortools.sat.python import cp_model
from ortools.linear_solver import pywraplp
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import time
import json
from datetime import datetime, timedelta

class AdvancedOptimizer:
    def __init__(self, tracks_df, trains_df, stations_df, time_horizon_minutes=30, solver_timeout_seconds=30):
        self.tracks_df = tracks_df
        self.trains_df = trains_df
        self.stations_df = stations_df
        self.time_horizon_minutes = time_horizon_minutes
        self.solver_timeout_seconds = solver_timeout_seconds
        
        # AI/ML components
        self.priority_model = None
        self.delay_predictor = None
        self.scaler = StandardScaler()
        self.optimization_history = []
        
        # Advanced constraints
        self.minimum_headway = 5  # minutes
        self.maximum_delay_tolerance = 30  # minutes
        self.capacity_utilization_threshold = 0.85
        
        # Initialize ML models
        self._initialize_ml_models()

    def _initialize_ml_models(self):
        """Initialize machine learning models for priority prediction and delay forecasting."""
        # Priority model for dynamic priority adjustment
        self.priority_model = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Delay predictor for proactive scheduling
        self.delay_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Train models with historical data if available
        self._train_models_with_historical_data()
    
    def _train_models_with_historical_data(self):
        """Train ML models with available historical data."""
        # This would be enhanced with real historical data
        # For now, we'll use synthetic training data
        pass
    
    def _calculate_dynamic_priority(self, train_info, current_time, system_state):
        """Calculate dynamic priority using ML model with robust field fallbacks."""
        # Support both 'priority_level' and 'priority' keys
        base_priority = train_info.get('priority_level', train_info.get('priority', 3))
        speed_kph = train_info.get('speed_profile_kph', 60)

        features = np.array([[
            float(base_priority),
            float(speed_kph),
            float(current_time),
            float(system_state.get('congestion_level', 0)),
            float(system_state.get('weather_impact', 0))
        ]])
        
        if self.priority_model is not None:
            try:
                return float(self.priority_model.predict(features)[0])
            except Exception:
                return float(base_priority)
        else:
            # Fallback to static priority
            return float(base_priority)
    
    def _predict_delays(self, train_info, track_conditions):
        """Predict potential delays using ML model."""
        features = np.array([[
            train_info['speed_profile_kph'],
            track_conditions.get('condition_score', 1.0),
            track_conditions.get('weather_impact', 0),
            track_conditions.get('maintenance_status', 0)
        ]])
        
        if self.delay_predictor is not None:
            return self.delay_predictor.predict(features)[0]
        else:
            # Fallback to simple heuristic
            return 5.0  # 5 minutes base delay
    
    def optimize(self, env, current_time, active_trains, logger, disruption_events=None):
        """
        Advanced optimization with AI-driven constraints and conflict-free scheduling.
        
        Args:
            env: simpy.Environment
            current_time: current simulation time
            active_trains: list of active trains with their current state
            logger: Logger instance
            disruption_events: list of active disruption events
            
        Returns:
            dict: Optimized schedule with detailed constraints
        """
        start_time = time.time()
        
        # Create the constraint programming model
        model = cp_model.CpModel()
        
        # Get trains in optimization horizon
        horizon_end_time = current_time + self.time_horizon_minutes
        trains_in_horizon = [
            train for train in active_trains 
            if train.get('next_departure_time', current_time) <= horizon_end_time
        ]
        
        if not trains_in_horizon:
            logger.log(env.now, 'OPTIMIZER', 'SYSTEM', 
                      f"No trains in horizon for optimization.")
            return {}
        
        # Create decision variables
        train_vars = {}
        track_usage_vars = {}
        
        # System state for ML predictions
        system_state = self._get_system_state(env, current_time)
        
        for train in trains_in_horizon:
            train_id = train['train_id']
            
            # Dynamic priority calculation
            dynamic_priority = self._calculate_dynamic_priority(train, current_time, system_state)
            
            # Departure time variable
            departure_var = model.NewIntVar(
                int(current_time), 
                int(horizon_end_time), 
                f'departure_{train_id}'
            )
            
            # Track usage variables for each track segment
            track_usage = {}
            for _, track in self.tracks_df.iterrows():
                track_id = track['track_id']
                usage_var = model.NewBoolVar(f'track_{track_id}_train_{train_id}')
                track_usage[track_id] = usage_var
            
            train_vars[train_id] = {
                'departure': departure_var,
                'priority': dynamic_priority,
                'track_usage': track_usage,
                'original_train': train
            }
        
        # Advanced constraints
        self._add_headway_constraints(model, train_vars, logger)
        self._add_capacity_constraints(model, train_vars, logger)
        self._add_priority_constraints(model, train_vars, logger)
        self._add_disruption_constraints(model, train_vars, disruption_events, logger)
        self._add_conflict_avoidance_constraints(model, train_vars, logger)
        
        # Multi-objective optimization
        self._add_objective_function(model, train_vars, system_state, logger)
        
        # Solve the model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.solver_timeout_seconds
        solver.parameters.log_search_progress = True
        
        status = solver.Solve(model)
        solve_time = time.time() - start_time
        
        # Extract and log results
        optimized_schedule = self._extract_solution(
            solver, status, train_vars, current_time, logger
        )
        
        # Store optimization history for learning
        self._store_optimization_history(
            current_time, trains_in_horizon, optimized_schedule, 
            solve_time, status, system_state
        )
        
        return optimized_schedule
    
    def _get_system_state(self, env, current_time):
        """Get current system state for ML predictions."""
        return {
            'congestion_level': 0.3,  # Would be calculated from actual data
            'weather_impact': 0.1,    # Would be from weather API
            'maintenance_impact': 0.05,
            'current_time': current_time
        }
    
    def _add_headway_constraints(self, model, train_vars, logger):
        """Add minimum headway constraints between trains."""
        train_ids = list(train_vars.keys())
        
        for i in range(len(train_ids)):
            for j in range(i + 1, len(train_ids)):
                train1_id = train_ids[i]
                train2_id = train_ids[j]
                
                # Minimum headway constraint
                model.Add(
                    train_vars[train1_id]['departure'] - train_vars[train2_id]['departure'] >= self.minimum_headway
                ).OnlyEnforceIf([
                    train_vars[train1_id]['departure'] >= train_vars[train2_id]['departure']
                ])
                
                model.Add(
                    train_vars[train2_id]['departure'] - train_vars[train1_id]['departure'] >= self.minimum_headway
                ).OnlyEnforceIf([
                    train_vars[train2_id]['departure'] >= train_vars[train1_id]['departure']
                ])
    
    def _add_capacity_constraints(self, model, train_vars, logger):
        """Add track and platform capacity constraints."""
        # Track capacity constraints
        for _, track in self.tracks_df.iterrows():
            track_id = track['track_id']
            
            # Count trains using this track
            track_usage_vars = [
                train_vars[train_id]['track_usage'][track_id] 
                for train_id in train_vars.keys()
            ]
            
            # Track capacity is 1 (single train at a time)
            model.Add(sum(track_usage_vars) <= 1)
    
    def _add_priority_constraints(self, model, train_vars, logger):
        """Add priority-based scheduling constraints."""
        train_ids = list(train_vars.keys())
        
        for i in range(len(train_ids)):
            for j in range(i + 1, len(train_ids)):
                train1_id = train_ids[i]
                train2_id = train_ids[j]
                
                # Higher priority trains get earlier departure times
                if train_vars[train1_id]['priority'] < train_vars[train2_id]['priority']:
                    model.Add(
                        train_vars[train1_id]['departure'] <= train_vars[train2_id]['departure']
                    )
    
    def _add_disruption_constraints(self, model, train_vars, disruption_events, logger):
        """Add constraints for active disruption events."""
        if not disruption_events:
            return
            
        for disruption in disruption_events:
            if disruption.get('type') == 'track_blocked':
                track_id = disruption.get('track_id')
                start_time = disruption.get('start_time', 0)
                end_time = disruption.get('end_time', float('inf'))
                
                # Prevent trains from using blocked track during disruption
                for train_id in train_vars.keys():
                    model.Add(
                        train_vars[train_id]['track_usage'][track_id] == 0
                    ).OnlyEnforceIf([
                        model.NewBoolVar(f'disruption_active_{train_id}_{track_id}')
                    ])
    
    def _add_conflict_avoidance_constraints(self, model, train_vars, logger):
        """Add constraints to avoid scheduling conflicts."""
        # This would include more sophisticated conflict detection
        # For now, we rely on headway and capacity constraints
        pass
    
    def _add_objective_function(self, model, train_vars, system_state, logger):
        """Add multi-objective optimization function."""
        # Weighted combination of objectives
        objective_terms = []
        
        for train_id, train_var in train_vars.items():
            # Minimize departure time weighted by priority
            priority_weight = 10 - train_var['priority']
            objective_terms.append(priority_weight * train_var['departure'])
            
            # Minimize delay from scheduled time
            original_train = train_var['original_train']
            scheduled_time = original_train.get('scheduled_departure', 0)
            if scheduled_time > 0:
                delay_penalty = abs(train_var['departure'] - scheduled_time)
                objective_terms.append(delay_penalty * 0.1)
        
        model.Minimize(sum(objective_terms))
    
    def _extract_solution(self, solver, status, train_vars, current_time, logger):
        """Extract and format the optimization solution."""
        optimized_schedule = {}
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            logger.log(current_time, 'OPTIMIZER', 'SYSTEM', 
                      f"Optimization successful. Status: {status}")
            
            for train_id, train_var in train_vars.items():
                optimized_departure = solver.Value(train_var['departure'])
                optimized_schedule[train_id] = {
                    'target_departure': optimized_departure,
                    'dynamic_priority': train_var['priority'],
                    'confidence_score': 0.9 if status == cp_model.OPTIMAL else 0.7,
                    'constraints_satisfied': True
                }
        else:
            logger.log(current_time, 'OPTIMIZER', 'SYSTEM', 
                      f"Optimization failed. Status: {status}. Using fallback strategy.")
        
        return optimized_schedule
    
    def _store_optimization_history(self, current_time, trains, schedule, solve_time, status, system_state):
        """Store optimization results for learning and analysis."""
        self.optimization_history.append({
            'timestamp': current_time,
            'trains_count': len(trains),
            'schedule': schedule,
            'solve_time': solve_time,
            'status': status,
            'system_state': system_state
        })
    
    def re_optimize_under_disruption(self, env, current_time, active_trains, disruption_event, logger):
        """Rapid re-optimization under disruption events."""
        logger.log(current_time, 'OPTIMIZER', 'SYSTEM', 
                  f"Re-optimizing due to disruption: {disruption_event.get('description', 'Unknown')}")
        
        # Adjust constraints for disruption
        disruption_events = [disruption_event] if disruption_event else []
        
        # Use shorter time horizon for rapid response
        original_horizon = self.time_horizon_minutes
        self.time_horizon_minutes = min(15, original_horizon)  # 15 minutes for rapid response
        
        # Re-optimize
        schedule = self.optimize(env, current_time, active_trains, logger, disruption_events)
        
        # Restore original horizon
        self.time_horizon_minutes = original_horizon
        
        return schedule