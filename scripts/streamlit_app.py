import streamlit as st
from pathlib import Path
import pandas as pd
import pickle
import sys
from datetime import datetime
import os

from latency_maps import (
    load_month_data, 
    plot_latency, 
    plot_dual_gps_heatmap, 
    plot_gps_per_polygon
)

BASE_DIR = Path(__file__).parent.parent.absolute()
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
MAPS_DIR = BASE_DIR / "maps"

# Set page configuration
st.set_page_config(
    page_title="GPS Latency Analysis",
    page_icon="🌐",
    layout="wide"
)

def main():
    # Title and description
    st.title("GPS Latency Analysis Dashboard")
    st.markdown("Analyze GPS data latency patterns with interactive maps")
    
    # Sidebar with controls
    st.sidebar.header("Controls")
    
    # Available months
    available_months = ["2024-11", "2024-12", "2025-01", "2025-02"]
    
    # Month selection
    selected_month = st.sidebar.selectbox(
        "Select Month",
        available_months,
        index=0
    )
    
    year, month = selected_month.split('-')
    month_name = datetime.strptime(month, "%m").strftime("%B")
    
    # Customer selection (for future expansion)
    customer_name = st.sidebar.selectbox(
        "Select Customer",
        ["Zim"],
        index=0
    )
    
    # Map type selection
    map_type = st.sidebar.radio(
        "Select Map Type",
        ["Global Latency Overview", "Dual GPS Heatmap", "Geofence Detail"]
    )
    
    # Load data or display error
    try:
        data = load_month_data(selected_month, customer_name)
        if data is None:
            st.error(f"Data files for {selected_month} are missing. Please process this month's data first.")
            return
        
        gps_df, polygons_df, polygon_dict = data
        
        # Display basic stats
        with st.expander("Dataset Statistics", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total GPS Points", f"{len(gps_df):,}")
            with col2:
                st.metric("Total Geofences", f"{len(polygons_df):,}")
            with col3:
                latency_count = len(gps_df[gps_df['t_diff'] >= pd.Timedelta(hours=24)])
                latency_pct = (latency_count / len(gps_df)) * 100
                st.metric("High Latency Points (%)", f"{latency_pct:.1f}%")
        
        # Based on map type, create the appropriate map
        if map_type == "Global Latency Overview":
            st.subheader(f"Global Latency Overview - {month_name} {year}")
            
            # Check if map already exists
            map_filename = f"{customer_name}_global_latency_{year}_{month}.html"
            map_filepath = MAPS_DIR / map_filename
            
            if map_filepath.exists():
                # Load existing map
                with open(map_filepath, 'r') as f:
                    map_html = f.read()
            else:
                # Create new map
                st.info("Generating map, please wait...")
                map = plot_latency(
                    polygon_dict=polygon_dict,
                    polygons_df=polygons_df,
                    severe_on_top=True
                )
                map_html = map.get_root().render()
                
                # Save the map
                with open(map_filepath, 'w') as f:
                    f.write(map_html)
            
            # Display the map
            st.components.v1.html(map_html, height=600)
            
        elif map_type == "Dual GPS Heatmap":
            st.subheader(f"Dual GPS Heatmap - {month_name} {year}")
            
            # Check if map already exists
            map_filename = f"{customer_name}_dual_heatmap_{year}_{month}.html"
            map_filepath = MAPS_DIR / map_filename
            
            if map_filepath.exists():
                # Load existing map
                with open(map_filepath, 'r') as f:
                    map_html = f.read()
            else:
                # Create new map
                st.info("Generating map, please wait...")
                map = plot_dual_gps_heatmap(
                    df=gps_df[~gps_df['in_Sea']],
                    month=f"{month_name} {year}",
                    latency_H=24,
                    zoom_start=2
                )
                map_html = map.get_root().render()
                
                # Save the map
                with open(map_filepath, 'w') as f:
                    f.write(map_html)
            
            # Display the map
            st.components.v1.html(map_html, height=600)
            
        elif map_type == "Geofence Detail":
            st.subheader(f"Geofence Detail - {month_name} {year}")
            
            # Get list of geofences
            geofence_options = polygons_df['LocationName'].tolist()
            
            # Geofence selection
            selected_geofence = st.selectbox(
                "Select Geofence",
                geofence_options,
                index=0
            )
            
            # Check if map already exists
            map_filename = f"{customer_name}_geofence_{selected_geofence}_{year}_{month}.html"
            map_filepath = MAPS_DIR / map_filename
            
            if map_filepath.exists():
                # Load existing map
                with open(map_filepath, 'r') as f:
                    map_html = f.read()
            else:
                # Create new map
                st.info("Generating map, please wait...")
                map = plot_gps_per_polygon(
                    polygons_df=polygons_df,
                    geofence_name=selected_geofence,
                    gps_df=gps_df,
                    customer_name=customer_name,
                    base_zoom=16,
                    late_H=24
                )
                map_html = map.get_root().render()
                
                # Save the map
                with open(map_filepath, 'w') as f:
                    f.write(map_html)
            
            # Display the map
            st.components.v1.html(map_html, height=600)
            
            # Display geofence stats
            geofence_data = polygons_df[polygons_df['LocationName'] == selected_geofence].iloc[0]
            st.subheader("Geofence Statistics")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Points", geofence_data['total_messages'])
            with col2:
                st.metric("Total Devices", geofence_data['total_devices'])
            with col3:
                st.metric("Late Messages Ratio", f"{geofence_data['latency_messages_ratio']:.1f}%")
            with col4:
                st.metric("Severity Score", f"{geofence_data['severity']:.1f}")
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()