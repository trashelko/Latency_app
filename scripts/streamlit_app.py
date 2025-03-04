import streamlit as st
from pathlib import Path
import pandas as pd
# import pickle
# import sys
from datetime import datetime
# import os

from latency_maps import (
    load_month_data, 
    plot_latency, 
    plot_dual_gps_heatmap, 
    plot_gps_per_polygon
)

from config import BASE_DIR, PROCESSED_DATA_DIR, MAPS_DIR, LATENCY_THRESHOLD_HOURS

# Set page configuration
st.set_page_config(
    page_title="GPS Latency Dashboard",
    page_icon="🌐",
    layout="wide"
)

def main():
    # Title and description
    st.title("GPS Latency Monthly Analysis Dashboard")
    # st.markdown("Analyze GPS data latency patterns with interactive maps")
    
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
        ["GPS Latency in Geofences", "GPS Heatmap (dual)", "Geofence Detail"]
    )

    # Add force recreate button
    force_recreate = st.sidebar.button("Refresh Map")
    
    # Load data or display error
    try:
        data = load_month_data(selected_month, customer_name)
        if data is None:
            st.error(f"Data files for {selected_month} are missing. Please process this month's data first.")
            return
        
        gps_df, polygons_df, polygon_dict = data
        
        # # Display basic stats
        # with st.expander("Dataset Statistics", expanded=False):
        #     col1, col2, col3 = st.columns(3)
        #     with col1:
        #         st.metric("Total GPS Points", f"{len(gps_df):,}")
        #     with col2:
        #         st.metric("Total Geofences", f"{len(polygons_df):,}")
        #     with col3:
        #         latency_count = len(gps_df[gps_df['t_diff'] >= pd.Timedelta(hours=24)])
        #         latency_pct = (latency_count / len(gps_df)) * 100
        #         st.metric("High Latency Points (%)", f"{latency_pct:.1f}%")

        # Display consistent statistics section (always visible)
        with st.container():
            # Add a title for the statistics section
            st.subheader(f"Monthly Statistics: {month_name} {year}")
            display_dashboard_statistics(gps_df, polygons_df, customer_name, LATENCY_THRESHOLD_HOURS)
        
        # Based on map type, create the appropriate map
        if map_type == "GPS Latency in Geofences":
            st.subheader(f"GPS Latency in Geofences - {month_name} {year}")
            
            # Check if map already exists
            map_filename = f"{customer_name}_global_latency_{year}_{month}.html"
            map_filepath = MAPS_DIR / map_filename
            
            if map_filepath.exists() and not force_recreate:
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
            
        elif map_type == "GPS Heatmap (dual)":
            st.subheader(f"GPS Heatmap. Latency vs. Normal Reports - {month_name} {year}")
            
            # Check if map already exists
            map_filename = f"{customer_name}_dual_heatmap_{year}_{month}.html"
            map_filepath = MAPS_DIR / map_filename
            
            if map_filepath.exists() and not force_recreate:
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
            
            if map_filepath.exists() and not force_recreate:
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


def display_dashboard_statistics(gps_df, polygons_df, customer_name, latency_threshold_hours):
    """
    Display consistent statistics across all dashboard pages
    
    Args:
        gps_df: Processed GPS DataFrame
        polygons_df: Geofence statistics DataFrame
        customer_name: Name of the customer
        latency_threshold_hours: Threshold in hours to consider high latency
    """
    # Calculate key statistics
    total_gps = len(gps_df)
    unique_devices = gps_df['DeviceID'].nunique()
    total_geofences = len(polygons_df)
    
    # Calculate land-based stats
    land_gps = gps_df[~gps_df['in_Sea']]
    total_land_gps = len(land_gps)
    land_pct = (total_land_gps / total_gps) * 100 if total_gps > 0 else 0
    
    # Calculate latency stats for land-based points only
    latency_threshold = pd.Timedelta(hours=latency_threshold_hours)
    land_latency = land_gps[land_gps['t_diff'] >= latency_threshold]
    latency_count = len(land_latency)
    latency_pct = (latency_count / total_land_gps) * 100 if total_land_gps > 0 else 0
    
    # Create stat cards with an f-string
    html = f"""
    <style>
    .stat-container {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 20px;
    }}
    .stat-card {{
        flex: 1;
        min-width: 200px;
        padding: 15px;
        border-radius: 5px;
        background-color: #f8f9fa;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    .stat-title {{
        font-size: 0.9rem;
        color: #6c757d;
        margin-bottom: 5px;
    }}
    .stat-value {{
        font-size: 1.5rem;
        font-weight: bold;
        color: #495057;
    }}
    .stat-subvalue {{
        font-size: 0.8rem;
        color: #6c757d;
        margin-top: 3px;
    }}
    .land-card {{
        background-color: #f8f8f8;
        border-left: 4px solid #4CAF50;
    }}
    .latency-card {{
        background-color: #f8f8f8;
        border-left: 4px solid #ff9800;
    }}
    </style>
    
    <div class="stat-container">
        <div class="stat-card">
            <div class="stat-title">GPS Reports</div>
            <div class="stat-value">{total_gps:,}</div>
            <div class="stat-subvalue">From {unique_devices:,} unique devices</div>
        </div>
        <div class="stat-card land-card">
            <div class="stat-title">GPS on Land</div>
            <div class="stat-value">{total_land_gps:,}</div>
            <div class="stat-subvalue">{land_pct:.1f}% of total reports</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">{customer_name} Geofences</div>
            <div class="stat-value">{total_geofences:,}</div>
        </div>
        <div class="stat-card latency-card">
            <div class="stat-title">High Latency (≥{latency_threshold_hours}h)</div>
            <div class="stat-value">~{latency_pct:.1f}%</div>
            <div class="stat-subvalue">{round(latency_count/1000)}K of {round(total_land_gps/1000)}K reports on land</div>
        </div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)

if __name__ == "__main__":
    main()