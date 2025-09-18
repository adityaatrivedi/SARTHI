"""
Controller API for programmatic access to railway operations control.
Provides RESTful API endpoints for external systems and mobile applications.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import threading
import time

class ControllerAPI:
    """
    RESTful API for railway operations control with clear recommendations,
    explanations, and override capabilities.
    """
    
    def __init__(self, audit_trail, optimizer, whatif_simulator):
        self.audit_trail = audit_trail
        self.optimizer = optimizer
        self.whatif_simulator = whatif_simulator
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for web interface
        
        # API state
        self.active_overrides = {}
        self.emergency_mode = False
        self.controller_sessions = {}
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        # System status and monitoring
        @self.app.route('/api/status', methods=['GET'])
        def get_system_status():
            """Get current system status and KPIs."""
            return jsonify(self._get_system_status())
        
        @self.app.route('/api/kpis', methods=['GET'])
        def get_kpis():
            """Get current KPIs."""
            return jsonify(self._get_current_kpis())
        
        @self.app.route('/api/alerts', methods=['GET'])
        def get_alerts():
            """Get current alerts and warnings."""
            return jsonify(self._get_current_alerts())
        
        # Train operations
        @self.app.route('/api/trains', methods=['GET'])
        def get_trains():
            """Get all trains with their current status."""
            return jsonify(self._get_all_trains())
        
        @self.app.route('/api/trains/<train_id>', methods=['GET'])
        def get_train_details(train_id):
            """Get detailed information for a specific train."""
            return jsonify(self._get_train_details(train_id))
        
        @self.app.route('/api/trains/<train_id>/hold', methods=['POST'])
        def hold_train(train_id):
            """Hold a specific train."""
            data = request.get_json() or {}
            reason = data.get('reason', 'Manual hold by controller')
            duration = data.get('duration', 10)  # minutes
            
            result = self._hold_train(train_id, reason, duration)
            return jsonify(result)
        
        @self.app.route('/api/trains/<train_id>/release', methods=['POST'])
        def release_train(train_id):
            """Release a held train."""
            result = self._release_train(train_id)
            return jsonify(result)
        
        @self.app.route('/api/trains/<train_id>/priority', methods=['PUT'])
        def update_train_priority(train_id):
            """Update train priority."""
            data = request.get_json()
            new_priority = data.get('priority')
            reason = data.get('reason', 'Priority override by controller')
            
            result = self._update_train_priority(train_id, new_priority, reason)
            return jsonify(result)
        
        # Track operations
        @self.app.route('/api/tracks', methods=['GET'])
        def get_tracks():
            """Get all tracks with their current status."""
            return jsonify(self._get_all_tracks())
        
        @self.app.route('/api/tracks/<track_id>/block', methods=['POST'])
        def block_track(track_id):
            """Block a specific track."""
            data = request.get_json() or {}
            reason = data.get('reason', 'Manual block by controller')
            duration = data.get('duration', 30)  # minutes
            
            result = self._block_track(track_id, reason, duration)
            return jsonify(result)
        
        @self.app.route('/api/tracks/<track_id>/unblock', methods=['POST'])
        def unblock_track(track_id):
            """Unblock a specific track."""
            result = self._unblock_track(track_id)
            return jsonify(result)
        
        # Recommendations and decisions
        @self.app.route('/api/recommendations', methods=['GET'])
        def get_recommendations():
            """Get AI-generated recommendations."""
            return jsonify(self._get_current_recommendations())
        
        @self.app.route('/api/recommendations/<rec_id>/accept', methods=['POST'])
        def accept_recommendation(rec_id):
            """Accept a specific recommendation."""
            result = self._accept_recommendation(rec_id)
            return jsonify(result)
        
        @self.app.route('/api/recommendations/<rec_id>/reject', methods=['POST'])
        def reject_recommendation(rec_id):
            """Reject a specific recommendation."""
            data = request.get_json() or {}
            reason = data.get('reason', 'Rejected by controller')
            
            result = self._reject_recommendation(rec_id, reason)
            return jsonify(result)
        
        @self.app.route('/api/recommendations/<rec_id>/defer', methods=['POST'])
        def defer_recommendation(rec_id):
            """Defer a specific recommendation."""
            data = request.get_json() or {}
            defer_until = data.get('defer_until')
            
            result = self._defer_recommendation(rec_id, defer_until)
            return jsonify(result)
        
        # Override capabilities
        @self.app.route('/api/overrides', methods=['GET'])
        def get_active_overrides():
            """Get all active overrides."""
            return jsonify(self._get_active_overrides())
        
        @self.app.route('/api/overrides', methods=['POST'])
        def create_override():
            """Create a new override."""
            data = request.get_json()
            override_type = data.get('type')
            target_id = data.get('target_id')
            reason = data.get('reason')
            duration = data.get('duration')
            
            result = self._create_override(override_type, target_id, reason, duration)
            return jsonify(result)
        
        @self.app.route('/api/overrides/<override_id>', methods=['DELETE'])
        def remove_override(override_id):
            """Remove an active override."""
            result = self._remove_override(override_id)
            return jsonify(result)
        
        # Emergency operations
        @self.app.route('/api/emergency/activate', methods=['POST'])
        def activate_emergency_mode():
            """Activate emergency mode."""
            data = request.get_json() or {}
            reason = data.get('reason', 'Emergency activation by controller')
            
            result = self._activate_emergency_mode(reason)
            return jsonify(result)
        
        @self.app.route('/api/emergency/deactivate', methods=['POST'])
        def deactivate_emergency_mode():
            """Deactivate emergency mode."""
            result = self._deactivate_emergency_mode()
            return jsonify(result)
        
        # What-if scenarios
        @self.app.route('/api/scenarios', methods=['GET'])
        def get_scenarios():
            """Get available what-if scenarios."""
            return jsonify(self._get_available_scenarios())
        
        @self.app.route('/api/scenarios/<scenario_id>/run', methods=['POST'])
        def run_scenario(scenario_id):
            """Run a specific scenario."""
            data = request.get_json() or {}
            duration = data.get('duration', 60)  # minutes
            
            result = self._run_scenario(scenario_id, duration)
            return jsonify(result)
        
        # Analytics and reporting
        @self.app.route('/api/analytics/performance', methods=['GET'])
        def get_performance_analytics():
            """Get performance analytics."""
            start_time = request.args.get('start_time')
            end_time = request.args.get('end_time')
            
            result = self._get_performance_analytics(start_time, end_time)
            return jsonify(result)
        
        @self.app.route('/api/analytics/decisions', methods=['GET'])
        def get_decision_analytics():
            """Get decision analytics."""
            start_time = request.args.get('start_time')
            end_time = request.args.get('end_time')
            
            result = self._get_decision_analytics(start_time, end_time)
            return jsonify(result)
        
        # Controller session management
        @self.app.route('/api/session/login', methods=['POST'])
        def login_controller():
            """Login a controller session."""
            data = request.get_json()
            controller_id = data.get('controller_id')
            name = data.get('name')
            
            result = self._login_controller(controller_id, name)
            return jsonify(result)
        
        @self.app.route('/api/session/logout', methods=['POST'])
        def logout_controller():
            """Logout a controller session."""
            data = request.get_json()
            session_id = data.get('session_id')
            
            result = self._logout_controller(session_id)
            return jsonify(result)
        
        # Real-time updates (WebSocket would be better, but using polling for simplicity)
        @self.app.route('/api/updates', methods=['GET'])
        def get_updates():
            """Get real-time updates."""
            last_update = request.args.get('last_update')
            
            result = self._get_updates_since(last_update)
            return jsonify(result)
    
    # Implementation methods
    def _get_system_status(self):
        """Get current system status."""
        return {
            'status': 'NORMAL' if not self.emergency_mode else 'EMERGENCY',
            'timestamp': datetime.now().isoformat(),
            'active_controllers': len(self.controller_sessions),
            'active_overrides': len(self.active_overrides),
            'system_health': self._calculate_system_health()
        }
    
    def _get_current_kpis(self):
        """Get current KPIs."""
        # This would integrate with the actual audit trail
        return {
            'punctuality': 87.5,
            'average_delay': 12.3,
            'throughput': 2.8,
            'utilization': 78.2,
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_current_alerts(self):
        """Get current alerts."""
        alerts = []
        
        # System alerts
        if self.emergency_mode:
            alerts.append({
                'id': 'emergency_mode',
                'type': 'critical',
                'message': 'Emergency mode is active',
                'timestamp': datetime.now().isoformat()
            })
        
        # Performance alerts
        kpis = self._get_current_kpis()
        if kpis['punctuality'] < 80:
            alerts.append({
                'id': 'low_punctuality',
                'type': 'warning',
                'message': f'Punctuality below 80%: {kpis["punctuality"]:.1f}%',
                'timestamp': datetime.now().isoformat()
            })
        
        if kpis['average_delay'] > 20:
            alerts.append({
                'id': 'high_delay',
                'type': 'warning',
                'message': f'Average delay above 20 minutes: {kpis["average_delay"]:.1f} min',
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    def _get_all_trains(self):
        """Get all trains with their status."""
        # This would integrate with the actual simulation
        return [
            {
                'train_id': '12001',
                'type': 'Express',
                'priority': 'High',
                'current_station': 'Habibganj',
                'next_station': 'Obaidullaganj',
                'status': 'In Transit',
                'delay': 5.2,
                'speed': 80.5,
                'eta_next_station': '14:35',
                'is_held': False,
                'hold_reason': None
            },
            {
                'train_id': '12002',
                'type': 'Passenger',
                'priority': 'Medium',
                'current_station': 'Bhopal Junction',
                'next_station': 'Habibganj',
                'status': 'At Station',
                'delay': 0.0,
                'speed': 0.0,
                'eta_next_station': '14:40',
                'is_held': False,
                'hold_reason': None
            },
            {
                'train_id': '12003',
                'type': 'Freight',
                'priority': 'Low',
                'current_station': 'Itarsi Junction',
                'next_station': 'Hoshangabad',
                'status': 'Delayed',
                'delay': 18.5,
                'speed': 45.0,
                'eta_next_station': '15:20',
                'is_held': True,
                'hold_reason': 'Waiting for priority train'
            }
        ]
    
    def _get_train_details(self, train_id):
        """Get detailed information for a specific train."""
        trains = self._get_all_trains()
        train = next((t for t in trains if t['train_id'] == train_id), None)
        
        if not train:
            return {'error': 'Train not found'}, 404
        
        # Add additional details
        train['route_history'] = self._get_train_route_history(train_id)
        train['performance_metrics'] = self._get_train_performance_metrics(train_id)
        train['recommendations'] = self._get_train_recommendations(train_id)
        
        return train
    
    def _hold_train(self, train_id, reason, duration):
        """Hold a specific train."""
        # Log the action
        self.audit_trail.log_audit_event(
            datetime.now().timestamp(),
            'TRAIN_HOLD',
            train_id,
            decision_type='MANUAL_OVERRIDE',
            decision_details=f'Held by controller: {reason}',
            performance_impact=duration
        )
        
        # Create override
        override_id = f"hold_{train_id}_{int(time.time())}"
        self.active_overrides[override_id] = {
            'type': 'train_hold',
            'target_id': train_id,
            'reason': reason,
            'duration': duration,
            'created_at': datetime.now().isoformat(),
            'created_by': 'controller'
        }
        
        return {
            'success': True,
            'message': f'Train {train_id} held for {duration} minutes',
            'override_id': override_id,
            'reason': reason
        }
    
    def _release_train(self, train_id):
        """Release a held train."""
        # Find and remove hold override
        hold_overrides = [k for k, v in self.active_overrides.items() 
                         if v['type'] == 'train_hold' and v['target_id'] == train_id]
        
        for override_id in hold_overrides:
            del self.active_overrides[override_id]
        
        # Log the action
        self.audit_trail.log_audit_event(
            datetime.now().timestamp(),
            'TRAIN_RELEASE',
            train_id,
            decision_type='MANUAL_OVERRIDE',
            decision_details='Released by controller'
        )
        
        return {
            'success': True,
            'message': f'Train {train_id} released',
            'overrides_removed': len(hold_overrides)
        }
    
    def _update_train_priority(self, train_id, new_priority, reason):
        """Update train priority."""
        # Log the action
        self.audit_trail.log_audit_event(
            datetime.now().timestamp(),
            'PRIORITY_OVERRIDE',
            train_id,
            decision_type='MANUAL_OVERRIDE',
            decision_details=f'Priority changed to {new_priority}: {reason}'
        )
        
        # Create override
        override_id = f"priority_{train_id}_{int(time.time())}"
        self.active_overrides[override_id] = {
            'type': 'priority_override',
            'target_id': train_id,
            'new_priority': new_priority,
            'reason': reason,
            'created_at': datetime.now().isoformat(),
            'created_by': 'controller'
        }
        
        return {
            'success': True,
            'message': f'Train {train_id} priority updated to {new_priority}',
            'override_id': override_id,
            'reason': reason
        }
    
    def _get_all_tracks(self):
        """Get all tracks with their status."""
        return [
            {
                'track_id': 1,
                'name': 'Track 1',
                'status': 'available',
                'current_train': None,
                'next_available': datetime.now().isoformat(),
                'utilization': 0.65
            },
            {
                'track_id': 2,
                'name': 'Track 2',
                'status': 'occupied',
                'current_train': '12001',
                'next_available': (datetime.now() + timedelta(minutes=15)).isoformat(),
                'utilization': 0.85
            },
            {
                'track_id': 3,
                'name': 'Track 3',
                'status': 'maintenance',
                'current_train': None,
                'next_available': (datetime.now() + timedelta(hours=2)).isoformat(),
                'utilization': 0.0
            }
        ]
    
    def _block_track(self, track_id, reason, duration):
        """Block a specific track."""
        # Log the action
        self.audit_trail.log_audit_event(
            datetime.now().timestamp(),
            'TRACK_BLOCK',
            track_id,
            decision_type='MANUAL_OVERRIDE',
            decision_details=f'Blocked by controller: {reason}'
        )
        
        # Create override
        override_id = f"block_{track_id}_{int(time.time())}"
        self.active_overrides[override_id] = {
            'type': 'track_block',
            'target_id': track_id,
            'reason': reason,
            'duration': duration,
            'created_at': datetime.now().isoformat(),
            'created_by': 'controller'
        }
        
        return {
            'success': True,
            'message': f'Track {track_id} blocked for {duration} minutes',
            'override_id': override_id,
            'reason': reason
        }
    
    def _unblock_track(self, track_id):
        """Unblock a specific track."""
        # Find and remove block override
        block_overrides = [k for k, v in self.active_overrides.items() 
                          if v['type'] == 'track_block' and v['target_id'] == track_id]
        
        for override_id in block_overrides:
            del self.active_overrides[override_id]
        
        # Log the action
        self.audit_trail.log_audit_event(
            datetime.now().timestamp(),
            'TRACK_UNBLOCK',
            track_id,
            decision_type='MANUAL_OVERRIDE',
            decision_details='Unblocked by controller'
        )
        
        return {
            'success': True,
            'message': f'Track {track_id} unblocked',
            'overrides_removed': len(block_overrides)
        }
    
    def _get_current_recommendations(self):
        """Get current AI recommendations."""
        return [
            {
                'id': 'rec_001',
                'title': 'Optimize Train 12001 Schedule',
                'priority': 'High',
                'description': 'Train 12001 is experiencing delays. Recommend holding for 5 minutes to allow priority train to pass.',
                'impact': 'Expected 15% improvement in overall punctuality',
                'confidence': 0.85,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(minutes=10)).isoformat()
            },
            {
                'id': 'rec_002',
                'title': 'Increase Track 2 Capacity',
                'priority': 'Medium',
                'description': 'Track 2 utilization is high. Consider opening additional line.',
                'impact': 'Expected 20% increase in throughput',
                'confidence': 0.72,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(minutes=15)).isoformat()
            }
        ]
    
    def _accept_recommendation(self, rec_id):
        """Accept a specific recommendation."""
        # Log the action
        self.audit_trail.log_audit_event(
            datetime.now().timestamp(),
            'RECOMMENDATION_ACCEPTED',
            rec_id,
            decision_type='CONTROLLER_DECISION',
            decision_details='Recommendation accepted by controller'
        )
        
        return {
            'success': True,
            'message': f'Recommendation {rec_id} accepted',
            'action_taken': 'Implementing recommendation'
        }
    
    def _reject_recommendation(self, rec_id, reason):
        """Reject a specific recommendation."""
        # Log the action
        self.audit_trail.log_audit_event(
            datetime.now().timestamp(),
            'RECOMMENDATION_REJECTED',
            rec_id,
            decision_type='CONTROLLER_DECISION',
            decision_details=f'Recommendation rejected: {reason}'
        )
        
        return {
            'success': True,
            'message': f'Recommendation {rec_id} rejected',
            'reason': reason
        }
    
    def _defer_recommendation(self, rec_id, defer_until):
        """Defer a specific recommendation."""
        # Log the action
        self.audit_trail.log_audit_event(
            datetime.now().timestamp(),
            'RECOMMENDATION_DEFERRED',
            rec_id,
            decision_type='CONTROLLER_DECISION',
            decision_details=f'Recommendation deferred until {defer_until}'
        )
        
        return {
            'success': True,
            'message': f'Recommendation {rec_id} deferred',
            'defer_until': defer_until
        }
    
    def _get_active_overrides(self):
        """Get all active overrides."""
        return list(self.active_overrides.values())
    
    def _create_override(self, override_type, target_id, reason, duration):
        """Create a new override."""
        override_id = f"{override_type}_{target_id}_{int(time.time())}"
        
        self.active_overrides[override_id] = {
            'id': override_id,
            'type': override_type,
            'target_id': target_id,
            'reason': reason,
            'duration': duration,
            'created_at': datetime.now().isoformat(),
            'created_by': 'controller'
        }
        
        return {
            'success': True,
            'override_id': override_id,
            'message': f'Override created for {target_id}'
        }
    
    def _remove_override(self, override_id):
        """Remove an active override."""
        if override_id in self.active_overrides:
            del self.active_overrides[override_id]
            return {'success': True, 'message': f'Override {override_id} removed'}
        else:
            return {'success': False, 'message': f'Override {override_id} not found'}
    
    def _activate_emergency_mode(self, reason):
        """Activate emergency mode."""
        self.emergency_mode = True
        
        # Log the action
        self.audit_trail.log_audit_event(
            datetime.now().timestamp(),
            'EMERGENCY_ACTIVATED',
            'SYSTEM',
            decision_type='EMERGENCY_OVERRIDE',
            decision_details=f'Emergency mode activated: {reason}'
        )
        
        return {
            'success': True,
            'message': 'Emergency mode activated',
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
    
    def _deactivate_emergency_mode(self):
        """Deactivate emergency mode."""
        self.emergency_mode = False
        
        # Log the action
        self.audit_trail.log_audit_event(
            datetime.now().timestamp(),
            'EMERGENCY_DEACTIVATED',
            'SYSTEM',
            decision_type='EMERGENCY_OVERRIDE',
            decision_details='Emergency mode deactivated'
        )
        
        return {
            'success': True,
            'message': 'Emergency mode deactivated',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_available_scenarios(self):
        """Get available what-if scenarios."""
        return [
            {
                'id': 'weather_disruption',
                'name': 'Severe Weather',
                'description': 'Simulate operations under severe weather conditions',
                'duration': 120,
                'impact': 'High'
            },
            {
                'id': 'maintenance',
                'name': 'Track Maintenance',
                'description': 'Simulate scheduled track maintenance',
                'duration': 180,
                'impact': 'Medium'
            },
            {
                'id': 'high_priority',
                'name': 'High Priority Traffic',
                'description': 'Simulate increased high-priority train traffic',
                'duration': 60,
                'impact': 'Low'
            }
        ]
    
    def _run_scenario(self, scenario_id, duration):
        """Run a specific scenario."""
        # This would integrate with the whatif_simulator
        return {
            'success': True,
            'message': f'Scenario {scenario_id} started',
            'duration': duration,
            'estimated_completion': (datetime.now() + timedelta(minutes=duration)).isoformat()
        }
    
    def _get_performance_analytics(self, start_time, end_time):
        """Get performance analytics."""
        # This would integrate with the audit trail
        return {
            'period': {
                'start': start_time,
                'end': end_time
            },
            'kpis': {
                'punctuality': 87.5,
                'average_delay': 12.3,
                'throughput': 2.8,
                'utilization': 78.2
            },
            'trends': {
                'punctuality_trend': 'improving',
                'delay_trend': 'stable',
                'throughput_trend': 'increasing'
            }
        }
    
    def _get_decision_analytics(self, start_time, end_time):
        """Get decision analytics."""
        # This would integrate with the audit trail
        return {
            'period': {
                'start': start_time,
                'end': end_time
            },
            'total_decisions': 156,
            'success_rate': 89.2,
            'avg_confidence': 0.85,
            'decision_types': {
                'scheduling': 45,
                'routing': 38,
                'holding': 28,
                'priority': 25,
                'emergency': 20
            }
        }
    
    def _login_controller(self, controller_id, name):
        """Login a controller session."""
        session_id = f"session_{controller_id}_{int(time.time())}"
        
        self.controller_sessions[session_id] = {
            'controller_id': controller_id,
            'name': name,
            'login_time': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat()
        }
        
        return {
            'success': True,
            'session_id': session_id,
            'message': f'Controller {name} logged in successfully'
        }
    
    def _logout_controller(self, session_id):
        """Logout a controller session."""
        if session_id in self.controller_sessions:
            del self.controller_sessions[session_id]
            return {'success': True, 'message': 'Controller logged out successfully'}
        else:
            return {'success': False, 'message': 'Session not found'}
    
    def _get_updates_since(self, last_update):
        """Get updates since a specific timestamp."""
        # This would provide real-time updates
        return {
            'timestamp': datetime.now().isoformat(),
            'updates': [
                {
                    'type': 'train_status_change',
                    'train_id': '12001',
                    'new_status': 'In Transit',
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'type': 'new_recommendation',
                    'recommendation_id': 'rec_003',
                    'title': 'Optimize Track Allocation',
                    'timestamp': datetime.now().isoformat()
                }
            ]
        }
    
    def _calculate_system_health(self):
        """Calculate overall system health."""
        kpis = self._get_current_kpis()
        
        # Simple health calculation
        health_score = 0
        if kpis['punctuality'] >= 85:
            health_score += 25
        if kpis['average_delay'] <= 15:
            health_score += 25
        if kpis['throughput'] >= 2.5:
            health_score += 25
        if kpis['utilization'] <= 85:
            health_score += 25
        
        return {
            'score': health_score,
            'status': 'Excellent' if health_score >= 90 else 'Good' if health_score >= 70 else 'Fair' if health_score >= 50 else 'Poor'
        }
    
    def _get_train_route_history(self, train_id):
        """Get train route history."""
        return [
            {'station': 'Bhopal Junction', 'arrival': '13:00', 'departure': '13:05'},
            {'station': 'Habibganj', 'arrival': '13:15', 'departure': '13:18'},
            {'station': 'Obaidullaganj', 'arrival': '13:45', 'departure': '13:50'}
        ]
    
    def _get_train_performance_metrics(self, train_id):
        """Get train performance metrics."""
        return {
            'on_time_performance': 0.85,
            'average_delay': 8.5,
            'speed_compliance': 0.92,
            'fuel_efficiency': 0.78
        }
    
    def _get_train_recommendations(self, train_id):
        """Get recommendations for a specific train."""
        return [
            {
                'type': 'speed_adjustment',
                'description': 'Consider increasing speed to 85 km/h',
                'impact': 'Reduce delay by 3 minutes'
            },
            {
                'type': 'route_optimization',
                'description': 'Alternative route available via Track 4',
                'impact': 'Reduce travel time by 5 minutes'
            }
        ]
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the API server."""
        print(f"🚀 Starting Controller API server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def create_controller_api(audit_trail, optimizer, whatif_simulator):
    """Create and return the controller API instance."""
    return ControllerAPI(audit_trail, optimizer, whatif_simulator)

if __name__ == "__main__":
    # Demo mode - create API with None components
    api = ControllerAPI(None, None, None)
    api.run(debug=True)
