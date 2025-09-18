import pandas as pd
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sqlite3
from pathlib import Path
import os

class AdvancedAuditTrail:
    """
    Advanced audit trail system for comprehensive decision tracking,
    performance monitoring, and continuous improvement.
    """
    
    def __init__(self, db_path: str = "audit_trail.db"):
        self.db_path = db_path
        self.audit_events = []
        self.performance_metrics = {}
        self.decision_history = []
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize SQLite database for audit trail storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create audit events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                event_type TEXT,
                train_id TEXT,
                station_id TEXT,
                track_id TEXT,
                decision_type TEXT,
                decision_details TEXT,
                performance_impact REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                metric_name TEXT,
                metric_value REAL,
                metric_unit TEXT,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create decision history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decision_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                decision_id TEXT,
                decision_type TEXT,
                input_parameters TEXT,
                decision_output TEXT,
                confidence_score REAL,
                execution_time REAL,
                success BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_decision(self, timestamp: float, decision_type: str, train_id: str,
                    input_params: Dict[str, Any], output: Dict[str, Any],
                    confidence_score: float, execution_time: float, success: bool):
        """Log a decision with full context and performance metrics."""
        decision_id = f"DEC_{timestamp}_{train_id}_{decision_type}"
        
        # Ensure input/output parameters are JSON serializable
        safe_input = self._to_jsonable(input_params)
        safe_output = self._to_jsonable(output)

        decision_record = {
            'timestamp': timestamp,
            'decision_id': decision_id,
            'decision_type': decision_type,
            'input_parameters': json.dumps(safe_input),
            'decision_output': json.dumps(safe_output),
            'confidence_score': confidence_score,
            'execution_time': execution_time,
            'success': success
        }
        
        self.decision_history.append(decision_record)
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO decision_history 
            (timestamp, decision_id, decision_type, input_parameters, decision_output, 
             confidence_score, execution_time, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, decision_id, decision_type, json.dumps(safe_input),
            json.dumps(safe_output), confidence_score, execution_time, success
        ))
        conn.commit()
        conn.close()

    def _to_jsonable(self, obj: Any) -> Any:
        """Convert complex objects (pandas/numpy/datetime) to JSON-serializable primitives."""
        try:
            json.dumps(obj)
            return obj
        except TypeError:
            pass
        
        # pandas types
        try:
            import pandas as pd  # local import to avoid hard dependency here
            if isinstance(obj, pd.Series):
                return {k: self._to_jsonable(v) for k, v in obj.to_dict().items()}
            if isinstance(obj, pd.DataFrame):
                return [self._to_jsonable(r) for r in obj.to_dict(orient='records')]
        except Exception:
            pass
        
        # numpy types
        try:
            import numpy as np  # local import to avoid hard dependency here
            if isinstance(obj, np.generic):
                return obj.item()
            if isinstance(obj, (np.ndarray,)):
                return obj.tolist()
        except Exception:
            pass
        
        # datetime
        if isinstance(obj, (datetime,)):
            return obj.isoformat()
        
        # containers
        if isinstance(obj, dict):
            return {str(k): self._to_jsonable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [self._to_jsonable(v) for v in obj]
        
        # fallback to string
        return str(obj)
    
    def log_performance_metric(self, timestamp: float, metric_name: str,
                              metric_value: float, metric_unit: str, context: str = ""):
        """Log a performance metric with context."""
        metric_record = {
            'timestamp': timestamp,
            'metric_name': metric_name,
            'metric_value': metric_value,
            'metric_unit': metric_unit,
            'context': context
        }
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO performance_metrics 
            (timestamp, metric_name, metric_value, metric_unit, context)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, metric_name, metric_value, metric_unit, context))
        conn.commit()
        conn.close()
    
    def log_audit_event(self, timestamp: float, event_type: str, train_id: str,
                       station_id: str = None, track_id: str = None,
                       decision_type: str = None, decision_details: str = None,
                       performance_impact: float = None):
        """Log an audit event with comprehensive details."""
        event_record = {
            'timestamp': timestamp,
            'event_type': event_type,
            'train_id': train_id,
            'station_id': station_id,
            'track_id': track_id,
            'decision_type': decision_type,
            'decision_details': decision_details,
            'performance_impact': performance_impact
        }
        
        self.audit_events.append(event_record)
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_events 
            (timestamp, event_type, train_id, station_id, track_id, 
             decision_type, decision_details, performance_impact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, event_type, train_id, station_id, track_id,
              decision_type, decision_details, performance_impact))
        conn.commit()
        conn.close()
    
    def calculate_kpis(self, start_time: float, end_time: float) -> Dict[str, float]:
        """Calculate Key Performance Indicators for a time period."""
        conn = sqlite3.connect(self.db_path)
        
        # Punctuality (percentage of trains on time)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM audit_events 
            WHERE event_type = 'TRAIN_ARRIVAL' AND timestamp BETWEEN ? AND ?
        ''', (start_time, end_time))
        total_arrivals = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM audit_events 
            WHERE event_type = 'TRAIN_ARRIVAL' AND performance_impact <= 5 AND timestamp BETWEEN ? AND ?
        ''', (start_time, end_time))
        on_time_arrivals = cursor.fetchone()[0]
        
        punctuality = (on_time_arrivals / total_arrivals * 100) if total_arrivals > 0 else 0
        
        # Average delay
        cursor.execute('''
            SELECT AVG(performance_impact) FROM audit_events 
            WHERE event_type = 'TRAIN_ARRIVAL' AND timestamp BETWEEN ? AND ?
        ''', (start_time, end_time))
        avg_delay = cursor.fetchone()[0] or 0
        
        # Throughput (trains per hour)
        time_hours = (end_time - start_time) / 60
        throughput = total_arrivals / time_hours if time_hours > 0 else 0
        
        # Resource utilization
        cursor.execute('''
            SELECT COUNT(*) FROM audit_events 
            WHERE event_type = 'TRACK_ACQUIRED' AND timestamp BETWEEN ? AND ?
        ''', (start_time, end_time))
        track_usage = cursor.fetchone()[0]
        
        # Calculate utilization percentage (simplified)
        max_possible_usage = (end_time - start_time) * 6  # Assuming 6 tracks
        utilization = (track_usage / max_possible_usage * 100) if max_possible_usage > 0 else 0
        
        conn.close()
        
        return {
            'punctuality': punctuality,
            'average_delay': avg_delay,
            'throughput': throughput,
            'utilization': utilization
        }
    
    def generate_performance_report(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        kpis = self.calculate_kpis(start_time, end_time)
        
        # Get decision statistics
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT decision_type, COUNT(*), AVG(confidence_score), AVG(execution_time)
            FROM decision_history 
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY decision_type
        ''', (start_time, end_time))
        decision_stats = cursor.fetchall()
        
        cursor.execute('''
            SELECT AVG(confidence_score), AVG(execution_time), COUNT(*)
            FROM decision_history 
            WHERE timestamp BETWEEN ? AND ?
        ''', (start_time, end_time))
        overall_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            'time_period': {
                'start': start_time,
                'end': end_time,
                'duration_hours': (end_time - start_time) / 60
            },
            'kpis': kpis,
            'decision_statistics': {
                'by_type': [
                    {
                        'type': stat[0],
                        'count': stat[1],
                        'avg_confidence': stat[2],
                        'avg_execution_time': stat[3]
                    }
                    for stat in decision_stats
                ],
                'overall': {
                    'avg_confidence': overall_stats[0],
                    'avg_execution_time': overall_stats[1],
                    'total_decisions': overall_stats[2]
                }
            },
            'recommendations': self._generate_recommendations(kpis, decision_stats)
        }
    
    def _generate_recommendations(self, kpis: Dict[str, float], decision_stats: List) -> List[str]:
        """Generate recommendations based on performance analysis."""
        recommendations = []
        
        # Punctuality recommendations
        if kpis['punctuality'] < 80:
            recommendations.append("Punctuality below 80%. Consider optimizing scheduling algorithms.")
        
        # Delay recommendations
        if kpis['average_delay'] > 15:
            recommendations.append("Average delay exceeds 15 minutes. Review track capacity and scheduling.")
        
        # Throughput recommendations
        if kpis['throughput'] < 2:
            recommendations.append("Throughput below 2 trains/hour. Consider increasing track capacity.")
        
        # Utilization recommendations
        if kpis['utilization'] > 90:
            recommendations.append("High resource utilization (>90%). Consider capacity expansion.")
        elif kpis['utilization'] < 50:
            recommendations.append("Low resource utilization (<50%). Consider optimizing train scheduling.")
        
        # Decision quality recommendations
        avg_confidence = np.mean([stat[2] for stat in decision_stats]) if decision_stats else 0
        if avg_confidence < 0.7:
            recommendations.append("Low decision confidence. Consider improving optimization algorithms.")
        
        return recommendations
    
    def export_audit_data(self, output_path: str, start_time: float = None, end_time: float = None):
        """Export audit data to CSV files."""
        # Ensure directory exists
        os.makedirs(output_path, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        
        # Export audit events
        query = "SELECT * FROM audit_events"
        params = []
        if start_time is not None:
            query += " WHERE timestamp >= ?"
            params.append(start_time)
        if end_time is not None:
            query += " AND timestamp <= ?" if start_time is not None else " WHERE timestamp <= ?"
            params.append(end_time)
        
        audit_df = pd.read_sql_query(query, conn, params=params)
        audit_df.to_csv(f"{output_path}/audit_events.csv", index=False)
        
        # Export performance metrics
        query = "SELECT * FROM performance_metrics"
        params = []
        if start_time is not None:
            query += " WHERE timestamp >= ?"
            params.append(start_time)
        if end_time is not None:
            query += " AND timestamp <= ?" if start_time is not None else " WHERE timestamp <= ?"
            params.append(end_time)
        
        metrics_df = pd.read_sql_query(query, conn, params=params)
        metrics_df.to_csv(f"{output_path}/performance_metrics.csv", index=False)
        
        # Export decision history
        query = "SELECT * FROM decision_history"
        params = []
        if start_time is not None:
            query += " WHERE timestamp >= ?"
            params.append(start_time)
        if end_time is not None:
            query += " AND timestamp <= ?" if start_time is not None else " WHERE timestamp <= ?"
            params.append(end_time)
        
        decisions_df = pd.read_sql_query(query, conn, params=params)
        decisions_df.to_csv(f"{output_path}/decision_history.csv", index=False)
        
        conn.close()
        
        return {
            'audit_events': len(audit_df),
            'performance_metrics': len(metrics_df),
            'decisions': len(decisions_df)
        }

class RealTimeDashboard:
    """Real-time dashboard for monitoring system performance."""
    
    def __init__(self, audit_trail: AdvancedAuditTrail):
        self.audit_trail = audit_trail
        self.dashboard_data = {}
    
    def update_dashboard(self, current_time: float):
        """Update dashboard with current system state."""
        # Calculate real-time KPIs
        window_start = current_time - 60  # Last hour
        kpis = self.audit_trail.calculate_kpis(window_start, current_time)
        
        self.dashboard_data = {
            'timestamp': current_time,
            'kpis': kpis,
            'system_status': self._assess_system_status(kpis),
            'alerts': self._check_alerts(kpis)
        }
    
    def _assess_system_status(self, kpis: Dict[str, float]) -> str:
        """Assess overall system status based on KPIs."""
        if kpis['punctuality'] >= 90 and kpis['average_delay'] <= 10:
            return "Excellent"
        elif kpis['punctuality'] >= 80 and kpis['average_delay'] <= 15:
            return "Good"
        elif kpis['punctuality'] >= 70 and kpis['average_delay'] <= 20:
            return "Fair"
        else:
            return "Poor"
    
    def _check_alerts(self, kpis: Dict[str, float]) -> List[str]:
        """Check for system alerts based on KPIs."""
        alerts = []
        
        if kpis['punctuality'] < 70:
            alerts.append("CRITICAL: Punctuality below 70%")
        
        if kpis['average_delay'] > 20:
            alerts.append("WARNING: Average delay exceeds 20 minutes")
        
        if kpis['utilization'] > 95:
            alerts.append("WARNING: Resource utilization exceeds 95%")
        
        return alerts
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data."""
        return self.dashboard_data
