#!/usr/bin/env python3
"""
Main runner script for the advanced railway operations optimization system.
This script demonstrates all the capabilities including:
- AI-driven optimization
- What-if simulation
- Performance monitoring
- Real-time dashboards
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulate import run_advanced_simulation, run_whatif_analysis
from whatif_simulator import WhatIfSimulator, ScenarioTemplates
from advanced_audit import AdvancedAuditTrail
from performance_dashboard import PerformanceDashboard, StreamlitDashboard
from optimizer import AdvancedOptimizer
from controller_interface import ControllerInterface
from controller_api import ControllerAPI

def run_comprehensive_analysis():
    """Run comprehensive analysis with all advanced features."""
    print("🚂 Advanced Railway Operations Optimization System")
    print("=" * 60)
    
    # Load data
    print("📊 Loading railway data...")
    stations = pd.read_csv("stations.csv")
    tracks = pd.read_csv("tracks.csv")
    trains_df = pd.read_csv("trains.csv")
    events_df = pd.read_csv("events.csv")
    
    print(f"✅ Loaded {len(stations)} stations, {len(tracks)} tracks, {len(trains_df)} train records")
    
    # 1. Run AI-driven optimization simulation
    print("\n🤖 Running AI-Driven Optimization Simulation...")
    sim_start_time, performance_report = run_advanced_simulation(
        stations, tracks, trains_df, events_df, 
        simulation_type="ai_optimized", log_suffix="ai_optimized"
    )
    
    print(f"📈 Performance KPIs:")
    for metric, value in performance_report['kpis'].items():
        print(f"   {metric}: {value:.2f}")
    
    # 2. Run comprehensive what-if analysis
    print("\n🔍 Running What-If Analysis...")
    whatif_simulator = WhatIfSimulator(tracks, trains_df, stations)
    
    # Create multiple scenarios
    scenarios = {
        'baseline': {'name': 'baseline', 'description': 'Baseline scenario'},
        'severe_weather': ScenarioTemplates.weather_disruption_scenario(),
        'maintenance': ScenarioTemplates.maintenance_scenario(),
        'high_priority': ScenarioTemplates.high_priority_scenario(),
        'capacity_reduction': ScenarioTemplates.capacity_reduction_scenario()
    }
    
    # Create and run scenarios
    for name, config in scenarios.items():
        whatif_simulator.create_scenario(name, config)
        print(f"   Running scenario: {name}")
        whatif_simulator.run_scenario(name)
    
    # Compare scenarios
    comparison = whatif_simulator.compare_scenarios(list(scenarios.keys()))
    
    print("\n📊 Scenario Comparison Results:")
    for scenario, metrics in comparison['metrics'].items():
        print(f"   {scenario}:")
        print(f"     Punctuality: {metrics['punctuality']:.1f}%")
        print(f"     Avg Delay: {metrics['average_delay']:.1f} min")
        print(f"     Throughput: {metrics['throughput']:.1f} trains/hr")
    
    # 3. Generate performance insights
    print("\n📈 Generating Performance Insights...")
    audit_trail = AdvancedAuditTrail("comprehensive_audit.db")
    performance_dashboard = PerformanceDashboard(audit_trail)
    
    # Create performance report
    performance_report = performance_dashboard.create_performance_report(0, 480)
    
    print("🎯 Performance Recommendations:")
    for rec in performance_report['recommendations']:
        print(f"   • {rec}")
    
    # 4. Demonstrate real-time monitoring
    print("\n📱 Real-Time Monitoring Demo...")
    
    # Simulate real-time updates using PerformanceDashboard helper
    for i in range(5):
        current_time = i * 60  # Every hour
        dashboard_snapshot = performance_dashboard.create_real_time_dashboard(current_time)
        kpis = dashboard_snapshot.get('kpis', {})
        visuals = dashboard_snapshot.get('visualizations', {})
        recs = dashboard_snapshot.get('recommendations', [])
        
        status = kpis.get('system_status', 'Unknown') if isinstance(kpis, dict) else 'Unknown'
        alerts = kpis.get('alerts', []) if isinstance(kpis, dict) else []
        print(f"   Hour {i+1}: System Status = {status}")
        if alerts:
            for alert in alerts:
                print(f"     ⚠️  {alert}")
    
    print("\n✅ Comprehensive analysis completed!")
    return performance_report, comparison

def run_streamlit_dashboard():
    """Launch Streamlit dashboard."""
    print("🚀 Launching Streamlit Dashboard...")
    print("Dashboard will be available at: http://localhost:8501")
    
    # Initialize components
    audit_trail = AdvancedAuditTrail("dashboard_audit.db")
    performance_dashboard = PerformanceDashboard(audit_trail)
    streamlit_dashboard = StreamlitDashboard(performance_dashboard)
    
    # Launch the dashboard
    import subprocess
    subprocess.run(["streamlit", "run", "controller_interface.py"])
    
def run_optimization_benchmark():
    """Run optimization benchmark comparing different approaches."""
    print("⚡ Running Optimization Benchmark...")
    
    # Load data
    stations = pd.read_csv("stations.csv")
    tracks = pd.read_csv("tracks.csv")
    trains_df = pd.read_csv("trains.csv")
    events_df = pd.read_csv("events.csv")
    
    # Test different optimization approaches
    approaches = {
        'greedy': {'timeout': 5, 'horizon': 15},
        'optimized': {'timeout': 30, 'horizon': 30},
        'ai_enhanced': {'timeout': 60, 'horizon': 45}
    }
    
    results = {}
    
    for approach, config in approaches.items():
        print(f"   Testing {approach} approach...")
        
        # Configure optimizer
        optimizer = AdvancedOptimizer(tracks, trains_df, stations)
        optimizer.solver_timeout_seconds = config['timeout']
        optimizer.time_horizon_minutes = config['horizon']
        
        # Run simulation
        sim_start_time, performance_report = run_advanced_simulation(
            stations, tracks, trains_df, events_df,
            simulation_type=approach, log_suffix=approach
        )
        
        results[approach] = performance_report['kpis']
    
    # Compare results
    print("\n📊 Benchmark Results:")
    for approach, kpis in results.items():
        print(f"   {approach.upper()}:")
        print(f"     Punctuality: {kpis['punctuality']:.1f}%")
        print(f"     Avg Delay: {kpis['average_delay']:.1f} min")
        print(f"     Throughput: {kpis['throughput']:.1f} trains/hr")
    
    return results

def run_controller_interface():
    """Launch the controller interface."""
    print("🎛️ Launching Controller Interface...")
    print("Controller interface will be available at: http://localhost:8501")
    
    # Initialize components
    stations = pd.read_csv("stations.csv")
    tracks = pd.read_csv("tracks.csv")
    trains_df = pd.read_csv("trains.csv")
    
    audit_trail = AdvancedAuditTrail("controller_audit.db")
    optimizer = AdvancedOptimizer(tracks, trains_df, stations)
    whatif_simulator = WhatIfSimulator(tracks, trains_df, stations)
    
    # Create controller interface
    controller = ControllerInterface(audit_trail, optimizer, whatif_simulator)
    
    # Launch Streamlit interface
    import subprocess
    subprocess.run(["streamlit", "run", "controller_interface.py"])

def run_controller_api(port=5000):
    """Launch the controller API server."""
    print(f"🚀 Launching Controller API Server on port {port}...")
    print(f"API will be available at: http://localhost:{port}")
    print("API Documentation:")
    print("  GET  /api/status - System status")
    print("  GET  /api/trains - All trains")
    print("  GET  /api/recommendations - AI recommendations")
    print("  POST /api/trains/{id}/hold - Hold train")
    print("  POST /api/trains/{id}/release - Release train")
    print("  POST /api/emergency/activate - Emergency mode")
    
    # Initialize components
    stations = pd.read_csv("stations.csv")
    tracks = pd.read_csv("tracks.csv")
    trains_df = pd.read_csv("trains.csv")
    
    audit_trail = AdvancedAuditTrail("api_audit.db")
    optimizer = AdvancedOptimizer(tracks, trains_df, stations)
    whatif_simulator = WhatIfSimulator(tracks, trains_df, stations)
    
    # Create and run API
    api = ControllerAPI(audit_trail, optimizer, whatif_simulator)
    api.run(host='0.0.0.0', port=port, debug=False)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Advanced Railway Operations Optimization System")
    parser.add_argument('--mode', choices=['full', 'dashboard', 'benchmark', 'whatif', 'controller', 'api'], 
                       default='full', help='Run mode')
    parser.add_argument('--scenario', help='Specific scenario to run (for whatif mode)')
    parser.add_argument('--port', type=int, default=5000, help='Port for API server (for api mode)')
    
    args = parser.parse_args()
    
    if args.mode == 'full':
        run_comprehensive_analysis()
    elif args.mode == 'dashboard':
        run_streamlit_dashboard()
    elif args.mode == 'benchmark':
        run_optimization_benchmark()
    elif args.mode == 'whatif':
        if args.scenario:
            # Run specific scenario
            stations = pd.read_csv("stations.csv")
            tracks = pd.read_csv("tracks.csv")
            trains_df = pd.read_csv("trains.csv")
            events_df = pd.read_csv("events.csv")
            
            whatif_simulator = WhatIfSimulator(tracks, trains_df, stations)
            
            # Create scenario
            if args.scenario == 'weather':
                config = ScenarioTemplates.weather_disruption_scenario()
            elif args.scenario == 'maintenance':
                config = ScenarioTemplates.maintenance_scenario()
            elif args.scenario == 'high_priority':
                config = ScenarioTemplates.high_priority_scenario()
            else:
                print(f"Unknown scenario: {args.scenario}")
                return
            
            whatif_simulator.create_scenario(args.scenario, config)
            results = whatif_simulator.run_scenario(args.scenario)
            print(f"Scenario {args.scenario} completed!")
        else:
            # Run all what-if scenarios
            stations = pd.read_csv("stations.csv")
            tracks = pd.read_csv("tracks.csv")
            trains_df = pd.read_csv("trains.csv")
            events_df = pd.read_csv("events.csv")
            
            comparison = run_whatif_analysis(stations, tracks, trains_df, events_df)
            print("What-if analysis completed!")
    elif args.mode == 'controller':
        run_controller_interface()
    elif args.mode == 'api':
        run_controller_api(args.port)

if __name__ == "__main__":
    main()
