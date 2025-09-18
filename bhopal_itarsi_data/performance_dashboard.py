import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from typing import Dict, List, Any, Optional
import streamlit as st
from advanced_audit import AdvancedAuditTrail, RealTimeDashboard

class PerformanceDashboard:
    """
    Comprehensive performance dashboard with real-time KPIs,
    visualizations, and continuous improvement insights.
    """
    
    def __init__(self, audit_trail: AdvancedAuditTrail):
        self.audit_trail = audit_trail
        self.dashboard_data = {}
        self.visualizations = {}
        
    def create_real_time_dashboard(self, current_time: float) -> Dict[str, Any]:
        """Create real-time performance dashboard."""
        dashboard = RealTimeDashboard(self.audit_trail)
        dashboard.update_dashboard(current_time)
        
        return {
            'timestamp': current_time,
            'kpis': dashboard.get_dashboard_data(),
            'visualizations': self._generate_real_time_visualizations(current_time),
            'recommendations': self._generate_improvement_recommendations(current_time)
        }
    
    def _generate_real_time_visualizations(self, current_time: float) -> Dict[str, Any]:
        """Generate real-time visualizations."""
        # Get data for last 2 hours
        window_start = current_time - 120
        window_end = current_time
        
        # Create performance trend chart
        trend_data = self._get_performance_trend_data(window_start, window_end)
        
        # Create resource utilization heatmap
        utilization_data = self._get_utilization_heatmap_data(window_start, window_end)
        
        # Create delay distribution chart
        delay_data = self._get_delay_distribution_data(window_start, window_end)
        
        return {
            'performance_trend': trend_data,
            'utilization_heatmap': utilization_data,
            'delay_distribution': delay_data
        }
    
    def _get_performance_trend_data(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Get performance trend data for visualization."""
        # This would query the audit trail database for trend data
        # For now, return sample data structure
        return {
            'timestamps': list(range(int(start_time), int(end_time), 10)),
            'punctuality': np.random.uniform(70, 95, 12),
            'average_delay': np.random.uniform(5, 25, 12),
            'throughput': np.random.uniform(1.5, 3.0, 12)
        }
    
    def _get_utilization_heatmap_data(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Get resource utilization heatmap data."""
        # Sample data for demonstration
        stations = ['Bhopal Junction', 'Habibganj', 'Obaidullaganj', 'Barkheda', 'Budni', 'Hoshangabad', 'Itarsi Junction']
        tracks = ['Track 1', 'Track 2', 'Track 3', 'Track 4', 'Track 5', 'Track 6']
        
        utilization_matrix = np.random.uniform(0.3, 0.9, (len(stations), len(tracks)))
        
        return {
            'stations': stations,
            'tracks': tracks,
            'utilization_matrix': utilization_matrix.tolist()
        }
    
    def _get_delay_distribution_data(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Get delay distribution data."""
        # Sample delay data
        delays = np.random.exponential(10, 100)  # Exponential distribution of delays
        delay_categories = ['0-5 min', '5-10 min', '10-15 min', '15-20 min', '20+ min']
        delay_counts = [
            np.sum((delays >= 0) & (delays < 5)),
            np.sum((delays >= 5) & (delays < 10)),
            np.sum((delays >= 10) & (delays < 15)),
            np.sum((delays >= 15) & (delays < 20)),
            np.sum(delays >= 20)
        ]
        
        return {
            'categories': delay_categories,
            'counts': delay_counts
        }
    
    def _generate_improvement_recommendations(self, current_time: float) -> List[Dict[str, Any]]:
        """Generate improvement recommendations based on current performance."""
        recommendations = []
        
        # Get current KPIs
        kpis = self.audit_trail.calculate_kpis(current_time - 60, current_time)
        
        # Punctuality recommendations
        if kpis['punctuality'] < 85:
            recommendations.append({
                'type': 'punctuality',
                'priority': 'high',
                'title': 'Improve Punctuality',
                'description': f"Current punctuality is {kpis['punctuality']:.1f}%. Consider optimizing scheduling algorithms.",
                'actions': [
                    'Implement dynamic priority adjustment',
                    'Optimize headway constraints',
                    'Improve conflict resolution algorithms'
                ]
            })
        
        # Delay recommendations
        if kpis['average_delay'] > 15:
            recommendations.append({
                'type': 'delay',
                'priority': 'high',
                'title': 'Reduce Average Delay',
                'description': f"Average delay is {kpis['average_delay']:.1f} minutes. Review operational efficiency.",
                'actions': [
                    'Implement predictive delay modeling',
                    'Optimize track allocation',
                    'Improve maintenance scheduling'
                ]
            })
        
        # Throughput recommendations
        if kpis['throughput'] < 2.5:
            recommendations.append({
                'type': 'throughput',
                'priority': 'medium',
                'title': 'Increase Throughput',
                'description': f"Current throughput is {kpis['throughput']:.1f} trains/hour. Consider capacity optimization.",
                'actions': [
                    'Optimize platform allocation',
                    'Implement dynamic routing',
                    'Improve train scheduling density'
                ]
            })
        
        return recommendations
    
    def create_performance_report(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Create comprehensive performance report."""
        report = self.audit_trail.generate_performance_report(start_time, end_time)
        
        # Add visualizations
        report['visualizations'] = {
            'kpi_trends': self._create_kpi_trend_chart(start_time, end_time),
            'decision_analysis': self._create_decision_analysis_chart(start_time, end_time),
            'resource_utilization': self._create_utilization_chart(start_time, end_time)
        }
        
        # Add benchmarking
        report['benchmarking'] = self._perform_benchmarking(report['kpis'])
        
        return report
    
    def _create_kpi_trend_chart(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Create KPI trend visualization."""
        # Sample implementation - would use actual data in production
        time_points = np.linspace(start_time, end_time, 20)
        
        return {
            'type': 'line_chart',
            'data': {
                'timestamps': time_points.tolist(),
                'punctuality': np.random.uniform(70, 95, 20).tolist(),
                'average_delay': np.random.uniform(5, 25, 20).tolist(),
                'throughput': np.random.uniform(1.5, 3.0, 20).tolist()
            },
            'title': 'Performance Trends Over Time'
        }
    
    def _create_decision_analysis_chart(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Create decision analysis visualization."""
        # Sample decision types and their performance
        decision_types = ['SCHEDULING', 'ROUTING', 'HOLDING', 'PRIORITY']
        success_rates = [0.85, 0.92, 0.78, 0.88]
        avg_confidence = [0.82, 0.89, 0.75, 0.86]
        
        return {
            'type': 'bar_chart',
            'data': {
                'decision_types': decision_types,
                'success_rates': success_rates,
                'avg_confidence': avg_confidence
            },
            'title': 'Decision Performance Analysis'
        }
    
    def _create_utilization_chart(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Create resource utilization visualization."""
        resources = ['Platforms', 'Tracks', 'Signals', 'Stations']
        utilization = [0.75, 0.82, 0.68, 0.71]
        
        return {
            'type': 'gauge_chart',
            'data': {
                'resources': resources,
                'utilization': utilization
            },
            'title': 'Resource Utilization'
        }
    
    def _perform_benchmarking(self, current_kpis: Dict[str, float]) -> Dict[str, Any]:
        """Perform benchmarking against industry standards."""
        industry_standards = {
            'punctuality': 85.0,  # Industry standard
            'average_delay': 12.0,  # minutes
            'throughput': 2.5,  # trains/hour
            'utilization': 75.0  # percentage
        }
        
        benchmarking = {}
        for metric, current_value in current_kpis.items():
            if metric in industry_standards:
                standard = industry_standards[metric]
                performance_ratio = current_value / standard
                
                if performance_ratio >= 1.0:
                    status = "Above Standard"
                elif performance_ratio >= 0.8:
                    status = "Near Standard"
                else:
                    status = "Below Standard"
                
                benchmarking[metric] = {
                    'current': current_value,
                    'standard': standard,
                    'ratio': performance_ratio,
                    'status': status
                }
        
        return benchmarking

class StreamlitDashboard:
    """Streamlit-based interactive dashboard."""
    
    def __init__(self, performance_dashboard: PerformanceDashboard):
        self.performance_dashboard = performance_dashboard
    
    def create_streamlit_app(self):
        """Create Streamlit dashboard application."""
        st.set_page_config(
            page_title="Railway Operations Dashboard",
            page_icon="🚂",
            layout="wide"
        )
        
        st.title("🚂 Railway Operations Performance Dashboard")
        
        # Sidebar controls
        st.sidebar.header("Controls")
        time_window = st.sidebar.selectbox(
            "Time Window",
            ["Last Hour", "Last 4 Hours", "Last 24 Hours", "Custom"]
        )
        
        if time_window == "Custom":
            start_time = st.sidebar.time_input("Start Time")
            end_time = st.sidebar.time_input("End Time")
        else:
            # Calculate time window
            now = datetime.now()
            if time_window == "Last Hour":
                start_time = now - timedelta(hours=1)
            elif time_window == "Last 4 Hours":
                start_time = now - timedelta(hours=4)
            else:  # Last 24 Hours
                start_time = now - timedelta(hours=24)
            end_time = now
        
        # Main dashboard
        self._display_kpi_cards()
        self._display_performance_charts()
        self._display_recommendations()
        self._display_alerts()
    
    def _display_kpi_cards(self):
        """Display KPI cards."""
        st.header("Key Performance Indicators")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Punctuality",
                value="87.5%",
                delta="2.3%"
            )
        
        with col2:
            st.metric(
                label="Average Delay",
                value="12.3 min",
                delta="-1.2 min"
            )
        
        with col3:
            st.metric(
                label="Throughput",
                value="2.8 trains/hr",
                delta="0.3"
            )
        
        with col4:
            st.metric(
                label="Utilization",
                value="78.2%",
                delta="3.1%"
            )
    
    def _display_performance_charts(self):
        """Display performance charts."""
        st.header("Performance Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Punctuality Trend")
            # Sample chart data
            chart_data = pd.DataFrame({
                'Time': pd.date_range(start='2025-01-01', periods=24, freq='H'),
                'Punctuality': np.random.uniform(70, 95, 24)
            })
            st.line_chart(chart_data.set_index('Time'))
        
        with col2:
            st.subheader("Delay Distribution")
            delay_data = pd.DataFrame({
                'Category': ['0-5 min', '5-10 min', '10-15 min', '15-20 min', '20+ min'],
                'Count': [45, 32, 18, 12, 8]
            })
            st.bar_chart(delay_data.set_index('Category'))
    
    def _display_recommendations(self):
        """Display improvement recommendations."""
        st.header("Improvement Recommendations")
        
        recommendations = [
            {
                'title': 'Optimize Scheduling Algorithm',
                'priority': 'High',
                'description': 'Current punctuality is below target. Consider implementing dynamic priority adjustment.',
                'impact': 'Expected 5-10% improvement in punctuality'
            },
            {
                'title': 'Increase Track Capacity',
                'priority': 'Medium',
                'description': 'Resource utilization is high. Consider capacity expansion.',
                'impact': 'Expected 15-20% increase in throughput'
            }
        ]
        
        for rec in recommendations:
            priority_color = "red" if rec['priority'] == 'High' else "orange"
            st.markdown(f"""
            <div style="border-left: 4px solid {priority_color}; padding-left: 10px; margin: 10px 0;">
                <h4>{rec['title']}</h4>
                <p><strong>Priority:</strong> {rec['priority']}</p>
                <p>{rec['description']}</p>
                <p><strong>Expected Impact:</strong> {rec['impact']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    def _display_alerts(self):
        """Display system alerts."""
        st.header("System Alerts")
        
        alerts = [
            {'type': 'warning', 'message': 'Track 3 utilization above 90%'},
            {'type': 'info', 'message': 'Weather advisory: Light rain expected'},
            {'type': 'success', 'message': 'Maintenance completed on Track 1'}
        ]
        
        for alert in alerts:
            alert_type = alert['type']
            if alert_type == 'warning':
                st.warning(alert['message'])
            elif alert_type == 'info':
                st.info(alert['message'])
            else:
                st.success(alert['message'])

# Example usage and integration
def create_dashboard_app():
    """Create the complete dashboard application."""
    # Initialize components
    audit_trail = AdvancedAuditTrail()
    performance_dashboard = PerformanceDashboard(audit_trail)
    streamlit_dashboard = StreamlitDashboard(performance_dashboard)
    
    return streamlit_dashboard
