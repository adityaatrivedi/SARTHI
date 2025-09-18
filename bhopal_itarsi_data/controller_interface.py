import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from typing import Dict, List, Any, Optional, Tuple
import time
from visualize import build_interactive_train_schedule, build_time_station_line_chart

class ControllerInterface:
    """
    User-friendly interface for railway controllers with clear recommendations,
    explanations, and override capabilities.
    """
    
    def __init__(self, audit_trail, optimizer, whatif_simulator):
        self.audit_trail = audit_trail
        self.optimizer = optimizer
        self.whatif_simulator = whatif_simulator
        self.current_recommendations = []
        self.override_history = []
        self.system_status = "NORMAL"
        
    def create_controller_dashboard(self):
        """Create the main controller dashboard interface."""
        st.set_page_config(
            page_title="Railway Operations Control Center",
            page_icon="🚂",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS for better styling
        st.markdown("""
        <style>
        .main-header {
            background: linear-gradient(90deg, #1f4e79, #2d5a87);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        .status-card {
            background: #f8f9fa;
            border-left: 4px solid #28a745;
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 5px;
        }
        .alert-card {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 5px;
        }
        .critical-card {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 5px;
        }
        .recommendation-card {
            background: #d1ecf1;
            border-left: 4px solid #17a2b8;
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 5px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Main header
        st.markdown("""
        <div class="main-header">
            <h1>🚂 Railway Operations Control Center</h1>
            <p>Real-time monitoring, optimization, and control for railway operations</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sidebar controls
        self._create_sidebar()
        
        # Main dashboard content
        self._create_main_dashboard()
        
    def _create_sidebar(self):
        """Create the sidebar with controls and system status."""
        with st.sidebar:
            st.header("🎛️ Control Panel")
            
            # System status
            st.subheader("System Status")
            status_color = {
                "NORMAL": "🟢",
                "WARNING": "🟡", 
                "CRITICAL": "🔴",
                "MAINTENANCE": "🔧"
            }
            
            current_status = self._get_system_status()
            st.markdown(f"**Status:** {status_color.get(current_status, '⚪')} {current_status}")
            
            # Quick actions
            st.subheader("Quick Actions")
            
            if st.button("🔄 Refresh System", use_container_width=True):
                st.rerun()
            
            if st.button("🚨 Emergency Override", use_container_width=True):
                self._handle_emergency_override()
            
            if st.button("📊 Generate Report", use_container_width=True):
                self._generate_control_report()
            
            # Time controls
            st.subheader("Time Controls")
            current_time = st.time_input("Current Time", value=datetime.now().time())
            simulation_speed = st.slider("Simulation Speed", 1, 10, 1)
            
            # Filter options
            st.subheader("View Filters")
            show_alerts = st.checkbox("Show Alerts", value=True)
            show_recommendations = st.checkbox("Show Recommendations", value=True)
            show_performance = st.checkbox("Show Performance", value=True)
            
            # Override controls
            st.subheader("Override Controls")
            override_mode = st.selectbox(
                "Override Mode",
                ["Auto", "Manual", "Emergency"],
                help="Auto: System recommendations only\nManual: Controller approval required\nEmergency: Immediate override capability"
            )
            
            if st.button("💾 Save Current State", use_container_width=True):
                self._save_current_state()
    
    def _create_main_dashboard(self):
        """Create the main dashboard content."""
        # Top row - System overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            self._display_system_status_card()
        
        with col2:
            self._display_performance_summary()
        
        with col3:
            self._display_active_trains()
        
        with col4:
            self._display_alerts_summary()
        
        # Middle row - Recommendations and decisions
        st.header("🎯 Recommendations & Decisions")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._display_recommendations()
        
        with col2:
            self._display_decision_interface()
        
        # Bottom row - Detailed views
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Performance", "🚂 Train Status", "🛤️ Infrastructure", "📈 Analytics"])
        st.markdown("---")
        st.subheader("🗺️ Interactive Train Schedule")
        self._display_interactive_schedule()
        st.subheader("📈 Time vs Station Line View")
        self._display_time_station_chart()
        
        with tab1:
            self._display_performance_tab()
        
        with tab2:
            self._display_train_status_tab()
        
        with tab3:
            self._display_infrastructure_tab()
        
        with tab4:
            self._display_analytics_tab()
    
    def _display_system_status_card(self):
        """Display system status card."""
        st.subheader("System Status")
        
        status = self._get_system_status()
        kpis = self._get_current_kpis()
        
        if status == "NORMAL":
            st.markdown('<div class="status-card">', unsafe_allow_html=True)
        elif status == "WARNING":
            st.markdown('<div class="alert-card">', unsafe_allow_html=True)
        else:
            st.markdown('<div class="critical-card">', unsafe_allow_html=True)
        
        st.metric("Punctuality", f"{kpis.get('punctuality', 0):.1f}%")
        st.metric("Avg Delay", f"{kpis.get('average_delay', 0):.1f} min")
        st.metric("Throughput", f"{kpis.get('throughput', 0):.1f} trains/hr")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _display_performance_summary(self):
        """Display performance summary."""
        st.subheader("Performance Summary")
        
        # Get performance data
        performance_data = self._get_performance_data()
        
        # Create performance indicators
        punctuality = performance_data.get('punctuality', 0)
        avg_delay = performance_data.get('average_delay', 0)
        throughput = performance_data.get('throughput', 0)
        
        # Performance indicators
        if punctuality >= 90:
            punctuality_status = "🟢 Excellent"
        elif punctuality >= 80:
            punctuality_status = "🟡 Good"
        else:
            punctuality_status = "🔴 Needs Attention"
        
        if avg_delay <= 10:
            delay_status = "🟢 Excellent"
        elif avg_delay <= 20:
            delay_status = "🟡 Good"
        else:
            delay_status = "🔴 Needs Attention"
        
        st.write(f"**Punctuality:** {punctuality_status}")
        st.write(f"**Delays:** {delay_status}")
        st.write(f"**Throughput:** {throughput:.1f} trains/hr")
    
    def _display_active_trains(self):
        """Display active trains information."""
        st.subheader("Active Trains")
        
        active_trains = self._get_active_trains()
        
        if active_trains:
            for train in active_trains[:5]:  # Show first 5
                train_id = train.get('train_id', 'Unknown')
                status = train.get('status', 'Unknown')
                delay = train.get('delay', 0)
                
                if delay > 15:
                    status_icon = "🔴"
                elif delay > 5:
                    status_icon = "🟡"
                else:
                    status_icon = "🟢"
                
                st.write(f"{status_icon} Train {train_id}: {status}")
        else:
            st.write("No active trains")
    
    def _display_alerts_summary(self):
        """Display alerts summary."""
        st.subheader("Alerts")
        
        alerts = self._get_current_alerts()
        
        if alerts:
            for alert in alerts[:3]:  # Show first 3
                alert_type = alert.get('type', 'info')
                message = alert.get('message', 'Unknown alert')
                
                if alert_type == 'critical':
                    st.markdown(f"🔴 **{message}**")
                elif alert_type == 'warning':
                    st.markdown(f"🟡 **{message}**")
                else:
                    st.markdown(f"🔵 {message}")
        else:
            st.write("No active alerts")
    
    def _display_recommendations(self):
        """Display AI-generated recommendations."""
        st.subheader("🤖 AI Recommendations")
        
        recommendations = self._get_current_recommendations()
        
        if recommendations:
            for i, rec in enumerate(recommendations):
                with st.expander(f"Recommendation {i+1}: {rec.get('title', 'Unknown')}"):
                    st.write(f"**Priority:** {rec.get('priority', 'Medium')}")
                    st.write(f"**Description:** {rec.get('description', 'No description')}")
                    st.write(f"**Expected Impact:** {rec.get('impact', 'Unknown')}")
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"✅ Accept", key=f"accept_{i}"):
                            self._accept_recommendation(rec)
                    
                    with col2:
                        if st.button(f"❌ Reject", key=f"reject_{i}"):
                            self._reject_recommendation(rec)
                    
                    with col3:
                        if st.button(f"⏸️ Defer", key=f"defer_{i}"):
                            self._defer_recommendation(rec)
        else:
            st.write("No current recommendations")
    
    def _display_decision_interface(self):
        """Display decision interface for manual overrides."""
        st.subheader("🎛️ Manual Controls")
        
        # Train control
        st.write("**Train Control**")
        train_id = st.selectbox("Select Train", self._get_train_options())
        
        if train_id:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("⏸️ Hold Train"):
                    self._hold_train(train_id)
            
            with col2:
                if st.button("▶️ Release Train"):
                    self._release_train(train_id)
        
        # Track control
        st.write("**Track Control**")
        track_id = st.selectbox("Select Track", self._get_track_options())
        
        if track_id:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🚫 Block Track"):
                    self._block_track(track_id)
            
            with col2:
                if st.button("✅ Unblock Track"):
                    self._unblock_track(track_id)
        
        # Priority override
        st.write("**Priority Override**")
        priority_override = st.selectbox(
            "Override Priority",
            ["Normal", "High", "Emergency"],
            help="Override train priority for special circumstances"
        )
        
        if st.button("🔧 Apply Priority Override"):
            self._apply_priority_override(train_id, priority_override)
    
    def _display_performance_tab(self):
        """Display performance analytics tab."""
        st.header("📊 Performance Analytics")
        
        # Performance trends
        performance_data = self._get_performance_trends()
        
        if performance_data:
            # Create performance chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=performance_data['timestamps'],
                y=performance_data['punctuality'],
                mode='lines+markers',
                name='Punctuality',
                line=dict(color='green')
            ))
            
            fig.add_trace(go.Scatter(
                x=performance_data['timestamps'],
                y=performance_data['average_delay'],
                mode='lines+markers',
                name='Average Delay',
                line=dict(color='red'),
                yaxis='y2'
            ))
            
            fig.update_layout(
                title="Performance Trends",
                xaxis_title="Time",
                yaxis_title="Punctuality (%)",
                yaxis2=dict(title="Average Delay (min)", overlaying="y", side="right"),
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # KPI summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Current Punctuality", f"{performance_data.get('current_punctuality', 0):.1f}%")
        
        with col2:
            st.metric("Current Delay", f"{performance_data.get('current_delay', 0):.1f} min")
        
        with col3:
            st.metric("Current Throughput", f"{performance_data.get('current_throughput', 0):.1f} trains/hr")
    
    def _display_train_status_tab(self):
        """Display train status tab."""
        st.header("🚂 Train Status")
        
        # Active trains table
        active_trains = self._get_active_trains()
        
        if active_trains:
            df = pd.DataFrame(active_trains)
            
            # Add status indicators
            df['Status_Icon'] = df['delay'].apply(
                lambda x: "🔴" if x > 15 else "🟡" if x > 5 else "🟢"
            )
            
            st.dataframe(df, use_container_width=True)
            
            # Train details
            selected_train = st.selectbox("Select Train for Details", df['train_id'].tolist())
            
            if selected_train:
                train_details = self._get_train_details(selected_train)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Train Information**")
                    st.write(f"Train ID: {train_details.get('train_id', 'Unknown')}")
                    st.write(f"Type: {train_details.get('type', 'Unknown')}")
                    st.write(f"Priority: {train_details.get('priority', 'Unknown')}")
                    st.write(f"Current Station: {train_details.get('current_station', 'Unknown')}")
                
                with col2:
                    st.write("**Performance Metrics**")
                    st.write(f"Delay: {train_details.get('delay', 0):.1f} minutes")
                    st.write(f"Speed: {train_details.get('speed', 0):.1f} km/h")
                    st.write(f"Next Station: {train_details.get('next_station', 'Unknown')}")
                    st.write(f"ETA: {train_details.get('eta', 'Unknown')}")
        else:
            st.write("No active trains")
    
    def _display_infrastructure_tab(self):
        """Display infrastructure status tab."""
        st.header("🛤️ Infrastructure Status")
        
        # Track status
        track_status = self._get_track_status()
        
        if track_status:
            # Create track status map
            fig = go.Figure()
            
            for track in track_status:
                status = track.get('status', 'unknown')
                color = {
                    'available': 'green',
                    'occupied': 'red',
                    'maintenance': 'orange',
                    'blocked': 'darkred'
                }.get(status, 'gray')
                
                fig.add_trace(go.Scatter(
                    x=[track.get('start_x', 0)],
                    y=[track.get('start_y', 0)],
                    mode='markers',
                    marker=dict(size=10, color=color),
                    name=f"Track {track.get('track_id', 'Unknown')}",
                    text=f"Track {track.get('track_id', 'Unknown')}: {status}"
                ))
            
            fig.update_layout(
                title="Track Status Map",
                xaxis_title="Position X",
                yaxis_title="Position Y",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Station status
        station_status = self._get_station_status()
        
        if station_status:
            st.subheader("Station Status")
            
            for station in station_status:
                station_name = station.get('name', 'Unknown')
                platform_usage = station.get('platform_usage', 0)
                capacity = station.get('capacity', 1)
                utilization = (platform_usage / capacity) * 100
                
                if utilization > 90:
                    status_icon = "🔴"
                elif utilization > 70:
                    status_icon = "🟡"
                else:
                    status_icon = "🟢"
                
                st.write(f"{status_icon} {station_name}: {platform_usage}/{capacity} platforms ({utilization:.1f}% utilization)")
    
    def _display_analytics_tab(self):
        """Display analytics tab."""
        st.header("📈 Advanced Analytics")
        
        # Decision analysis
        st.subheader("Decision Analysis")
        
        decision_stats = self._get_decision_statistics()
        
        if decision_stats:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Decisions", decision_stats.get('total_decisions', 0))
            
            with col2:
                st.metric("Success Rate", f"{decision_stats.get('success_rate', 0):.1f}%")
            
            with col3:
                st.metric("Avg Confidence", f"{decision_stats.get('avg_confidence', 0):.2f}")
        
        # Performance benchmarking
        st.subheader("Performance Benchmarking")
        
        benchmark_data = self._get_benchmark_data()
        
        if benchmark_data:
            # Create benchmark chart
            fig = go.Figure()
            
            metrics = ['Punctuality', 'Average Delay', 'Throughput', 'Utilization']
            current_values = [
                benchmark_data.get('current_punctuality', 0),
                benchmark_data.get('current_delay', 0),
                benchmark_data.get('current_throughput', 0),
                benchmark_data.get('current_utilization', 0)
            ]
            industry_standards = [
                benchmark_data.get('industry_punctuality', 85),
                benchmark_data.get('industry_delay', 12),
                benchmark_data.get('industry_throughput', 2.5),
                benchmark_data.get('industry_utilization', 75)
            ]
            
            fig.add_trace(go.Bar(
                name='Current Performance',
                x=metrics,
                y=current_values,
                marker_color='lightblue'
            ))
            
            fig.add_trace(go.Bar(
                name='Industry Standard',
                x=metrics,
                y=industry_standards,
                marker_color='lightgray'
            ))
            
            fig.update_layout(
                title="Performance vs Industry Standards",
                xaxis_title="Metrics",
                yaxis_title="Values",
                barmode='group'
            )
            
            st.plotly_chart(fig, use_container_width=True)

    def _display_interactive_schedule(self):
        """Render interactive Plotly train schedule with hover details."""
        st.caption("Hover over segments to see details. Select a log file to visualize.")
        default_log = "simulation_log_ai_optimized.csv"
        log_file = st.text_input("Simulation log CSV path", value=default_log)
        stations_csv = st.text_input("Stations CSV path", value="stations.csv")
        start_time = st.text_input("Simulation start time (ISO)", value=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat())
        if st.button("Render Schedule"):
            try:
                fig = build_interactive_train_schedule(log_file, stations_csv, start_time)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Failed to build schedule: {e}")

    def _display_time_station_chart(self):
        """Render time vs station line chart with precise ticks."""
        st.caption("Line chart with 10-min major and 2-min minor ticks; stations on Y-axis.")
        default_log = "simulation_log_ai_optimized.csv"
        log_file = st.text_input("Line chart - Simulation log CSV path", value=default_log, key="line_log")
        stations_csv = st.text_input("Line chart - Stations CSV path", value="stations.csv", key="line_stations")
        start_time = st.text_input("Line chart - Simulation start time (ISO)", value=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat(), key="line_start")
        if st.button("Render Line Chart"):
            try:
                fig = build_time_station_line_chart(log_file, stations_csv, start_time)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Failed to build line chart: {e}")
    
    # Helper methods for data retrieval and actions
    def _get_system_status(self):
        """Get current system status."""
        # This would integrate with the actual system
        return "NORMAL"
    
    def _get_current_kpis(self):
        """Get current KPIs."""
        # This would integrate with the audit trail
        return {
            'punctuality': 87.5,
            'average_delay': 12.3,
            'throughput': 2.8,
            'utilization': 78.2
        }
    
    def _get_active_trains(self):
        """Get active trains data."""
        # This would integrate with the simulation
        return [
            {'train_id': '12001', 'status': 'In Transit', 'delay': 5.2},
            {'train_id': '12002', 'status': 'At Station', 'delay': 0.0},
            {'train_id': '12003', 'status': 'Delayed', 'delay': 18.5}
        ]
    
    def _get_current_alerts(self):
        """Get current alerts."""
        return [
            {'type': 'warning', 'message': 'Track 3 utilization above 90%'},
            {'type': 'info', 'message': 'Weather advisory: Light rain expected'}
        ]
    
    def _get_current_recommendations(self):
        """Get current AI recommendations."""
        return [
            {
                'title': 'Optimize Train 12001 Schedule',
                'priority': 'High',
                'description': 'Train 12001 is experiencing delays. Recommend holding for 5 minutes to allow priority train to pass.',
                'impact': 'Expected 15% improvement in overall punctuality'
            },
            {
                'title': 'Increase Track 2 Capacity',
                'priority': 'Medium',
                'description': 'Track 2 utilization is high. Consider opening additional line.',
                'impact': 'Expected 20% increase in throughput'
            }
        ]
    
    def _get_train_options(self):
        """Get available train options for manual control."""
        return ['12001', '12002', '12003', '12004', '12005']
    
    def _get_track_options(self):
        """Get available track options for manual control."""
        return ['Track 1', 'Track 2', 'Track 3', 'Track 4', 'Track 5', 'Track 6']
    
    def _get_performance_data(self):
        """Get performance data."""
        return {
            'punctuality': 87.5,
            'average_delay': 12.3,
            'throughput': 2.8
        }
    
    def _get_performance_trends(self):
        """Get performance trends data."""
        # Sample data - would be from actual system
        timestamps = pd.date_range(start='2025-01-01', periods=24, freq='H')
        return {
            'timestamps': timestamps,
            'punctuality': np.random.uniform(80, 95, 24),
            'average_delay': np.random.uniform(5, 25, 24),
            'current_punctuality': 87.5,
            'current_delay': 12.3,
            'current_throughput': 2.8
        }
    
    def _get_track_status(self):
        """Get track status data."""
        return [
            {'track_id': 1, 'status': 'available', 'start_x': 0, 'start_y': 0},
            {'track_id': 2, 'status': 'occupied', 'start_x': 1, 'start_y': 0},
            {'track_id': 3, 'status': 'maintenance', 'start_x': 2, 'start_y': 0},
            {'track_id': 4, 'status': 'available', 'start_x': 0, 'start_y': 1},
            {'track_id': 5, 'status': 'blocked', 'start_x': 1, 'start_y': 1},
            {'track_id': 6, 'status': 'available', 'start_x': 2, 'start_y': 1}
        ]
    
    def _get_station_status(self):
        """Get station status data."""
        return [
            {'name': 'Bhopal Junction', 'platform_usage': 4, 'capacity': 6},
            {'name': 'Habibganj', 'platform_usage': 3, 'capacity': 5},
            {'name': 'Itarsi Junction', 'platform_usage': 6, 'capacity': 8}
        ]
    
    def _get_decision_statistics(self):
        """Get decision statistics."""
        return {
            'total_decisions': 156,
            'success_rate': 89.2,
            'avg_confidence': 0.85
        }
    
    def _get_benchmark_data(self):
        """Get benchmark data."""
        return {
            'current_punctuality': 87.5,
            'current_delay': 12.3,
            'current_throughput': 2.8,
            'current_utilization': 78.2,
            'industry_punctuality': 85.0,
            'industry_delay': 12.0,
            'industry_throughput': 2.5,
            'industry_utilization': 75.0
        }
    
    def _get_train_details(self, train_id):
        """Get detailed information for a specific train."""
        return {
            'train_id': train_id,
            'type': 'Express',
            'priority': 'High',
            'current_station': 'Habibganj',
            'delay': 5.2,
            'speed': 80.5,
            'next_station': 'Obaidullaganj',
            'eta': '14:35'
        }
    
    # Action methods
    def _accept_recommendation(self, recommendation):
        """Accept a recommendation."""
        st.success(f"✅ Accepted: {recommendation.get('title', 'Unknown')}")
        # Implement recommendation logic here
    
    def _reject_recommendation(self, recommendation):
        """Reject a recommendation."""
        st.warning(f"❌ Rejected: {recommendation.get('title', 'Unknown')}")
        # Implement rejection logic here
    
    def _defer_recommendation(self, recommendation):
        """Defer a recommendation."""
        st.info(f"⏸️ Deferred: {recommendation.get('title', 'Unknown')}")
        # Implement deferral logic here
    
    def _hold_train(self, train_id):
        """Hold a train."""
        st.success(f"⏸️ Train {train_id} held")
        # Implement train hold logic here
    
    def _release_train(self, train_id):
        """Release a train."""
        st.success(f"▶️ Train {train_id} released")
        # Implement train release logic here
    
    def _block_track(self, track_id):
        """Block a track."""
        st.warning(f"🚫 Track {track_id} blocked")
        # Implement track blocking logic here
    
    def _unblock_track(self, track_id):
        """Unblock a track."""
        st.success(f"✅ Track {track_id} unblocked")
        # Implement track unblocking logic here
    
    def _apply_priority_override(self, train_id, priority):
        """Apply priority override."""
        st.success(f"🔧 Priority override applied to Train {train_id}: {priority}")
        # Implement priority override logic here
    
    def _handle_emergency_override(self):
        """Handle emergency override."""
        st.error("🚨 Emergency override activated!")
        # Implement emergency override logic here
    
    def _generate_control_report(self):
        """Generate control report."""
        st.success("📊 Control report generated!")
        # Implement report generation logic here
    
    def _save_current_state(self):
        """Save current system state."""
        st.success("💾 Current state saved!")
        # Implement state saving logic here

def create_controller_app():
    """Create the controller application."""
    # This would initialize the actual components
    # For demo purposes, we'll use None
    audit_trail = None
    optimizer = None
    whatif_simulator = None
    
    controller = ControllerInterface(audit_trail, optimizer, whatif_simulator)
    controller.create_controller_dashboard()

if __name__ == "__main__":
    create_controller_app()
