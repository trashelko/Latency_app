from data_processing import build_spatial_index
from data_query import prompt_for_month

import folium
import numpy as np
import pandas as pd
from folium.plugins import HeatMap, MarkerCluster
from shapely.geometry import Polygon
from matplotlib import colors as mcolors
import matplotlib.pyplot as plt
import pickle
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent.absolute()
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
MAPS_DIR = BASE_DIR / "maps"

def plot_gps_heatmap(df, lat_col='Lat', lon_col='Lon', zoom_start=2, 
                     radius=15, 
                     show_markers=False,
                     gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}):
    
    # Calculate center point for initial view
    center_lat = df[lat_col].mean()
    center_lon = df[lon_col].mean()
    
    # Create base map
    m = folium.Map(location=[center_lat, center_lon], 
                  zoom_start=zoom_start,
                  tiles='OpenStreetMap')
    
    # Prepare data for heatmap
    heat_data = [[row[lat_col], row[lon_col]] for _, row in df.iterrows()]
    
    # Add heatmap layer
    HeatMap(heat_data,
            min_opacity=0.3,
            radius=radius,
            blur=15,
            max_zoom=1,
            gradient=gradient).add_to(m)
    
    # Optionally add marker clusters
    if show_markers:
        marker_cluster = MarkerCluster().add_to(m)
        for idx, row in df.iterrows():
            folium.CircleMarker(
                location=[row[lat_col], row[lon_col]],
                radius=3,
                weight=2,
                color='red',
                fill=True,
                popup=f"Lat: {row[lat_col]:.6f}, Lon: {row[lon_col]:.6f}"
            ).add_to(marker_cluster)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m

def get_color(severity: float, max_severity: float) -> str:
    if severity == 0:
        return 'limegreen'
    
    cmap = mcolors.LinearSegmentedColormap.from_list("", [
        (0.0, 'limegreen'),
        (0.1, 'gold'),     
        (0.3, 'darkorange'),
        (1.0, 'crimson')
    ])
    
    # scale_by = max_severity * 2/3 + 100/3
    # scaled_severity = severity / scale_by

    scaled_severity = severity/100
    return mcolors.rgb2hex(cmap(scaled_severity))

def see_color():
    # See the choice of the gradient for Severity Score
    ratios = np.arange(0, 101, 5) 
    colors = [get_color(r,100) for r in ratios]

    plt.figure(figsize=(10, 2))
    for i, (ratio, color) in enumerate(zip(ratios, colors)):
        plt.bar(i, 1, color=color)
        plt.text(i, -0.1, f'{ratio:.0f}', ha='center', rotation=0)
    plt.title("Severity Score Colorway")
    plt.xticks([])
    plt.yticks([])
    plt.show()

def plot_gps_per_polygon(polygons_df, geofence_name, gps_df,customer_name='Zim', base_zoom=16, 
                        late_H = 24):
    """Plot single polygon with its GPS points"""
    polygon_data = polygons_df[polygons_df['LocationName'] == geofence_name].iloc[0]    

    _, polygon_dict = build_spatial_index(polygons_df)

    # Get the polygon index
    polygon_idx = polygons_df[polygons_df['LocationName'] == geofence_name].index[0]
    _, polygon = polygon_dict[polygon_idx]
    
    # Get and split points
    late_threshold = pd.Timedelta(hours=late_H)
    points = gps_df[gps_df['in_Zim_polygon'] == geofence_name].copy()
    late_points = points[points['t_diff'] >= late_threshold]
    normal_points = points[points['t_diff'] < late_threshold]
    
    # Set up map
    poly_coords = list(polygon.exterior.coords[:-1])
    center_lat = sum(coord[0] for coord in poly_coords) / len(poly_coords)
    center_lon = sum(coord[1] for coord in poly_coords) / len(poly_coords)
    m = folium.Map(location=[float(center_lat), float(center_lon)], zoom_start=base_zoom)
    
    # Color polygon based on severity
    if polygon_data['total_messages'] == 0:
        color = 'darkgray' 
    else:
        max_severity = polygons_df['severity'].max()
        color = get_color(polygon_data['severity'], max_severity)
    
    # Add polygon outline
    folium.Polygon(
        locations=poly_coords,
        color=color,
        weight=4,
        fill=True,
        fill_opacity=0.2,
        popup=f"Location: {geofence_name}"
    ).add_to(m)
    
    # Add points
    for _, row in normal_points.iterrows():
        folium.CircleMarker(
            location=[float(row['Lat']), float(row['Lon'])],
            radius=3,
            color='gray',
            fill=True,
            popup=f"Time diff: {row['t_diff']}"
        ).add_to(m)
    
    for _, row in late_points.iterrows():
        folium.CircleMarker(
            location=[float(row['Lat']), float(row['Lon'])],
            radius=3,
            color='red',
            fill=True,
            popup=f"Time diff: {row['t_diff']}"
        ).add_to(m)
    
    # Add stats box
    title_html = f'''
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 320px; height: 110px; 
                    background-color: white; border:2px solid black; 
                    z-index:9999; font-size:14px; padding: 8px;">
            <b>{geofence_name}</b><br>
            Total points: {polygon_data['total_messages']}. Total devices: {polygon_data['total_devices']}<br>
            Late to normal GPS-coordinates ratio: {polygon_data['latency_messages_ratio']:.1f}%<br>
            Late to normal devices ratio: {polygon_data['latency_device_ratio']:.1f}%<br>
            Severity score: {polygon_data['severity']:.1f}
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    return m


def plot_latency(polygon_dict, polygons_df, center_lat=0, center_lon=0, severe_on_top=False):
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=2)
    
    max_messages = polygons_df['total_messages'].max()
    max_devices = polygons_df['total_devices'].max()
    max_severity = polygons_df['severity'].max()
    
    # Adjusted sizes
    MIN_RADIUS = 3
    MAX_RADIUS = 30
    ZERO_RADIUS = 5
    THRESHOLD = 1000  # number of messages where growth slows significantly
    
    def calculate_radius(messages, max_messages):
        if messages == 0:
            return ZERO_RADIUS
        elif messages <= THRESHOLD:
            # Linear scaling from 3 to 25 for 0-1000 messages
            return MIN_RADIUS + 22 * (messages / THRESHOLD)
        else:
            # Logarithmic scaling from 25 to 30 for 1000+ messages
            remaining_range = MAX_RADIUS - 25
            log_scale = np.log1p(messages - THRESHOLD) / np.log1p(max_messages - THRESHOLD)
            return 25 + remaining_range * log_scale
    
    if severe_on_top:
        polygon_data = [(
            polygons_df.iloc[idx]['severity'],
            idx,
            name,
            poly,
            polygons_df.iloc[idx]
        ) for idx, (name, poly) in polygon_dict.items()]
        iterator = sorted(polygon_data, key=lambda x: x[0])
    else:
        iterator = [(None, idx, name, poly, polygons_df.iloc[idx]) 
                   for idx, (name, poly) in polygon_dict.items()]
    
    for _, idx, geofence_name, poly, poly_data in iterator:
        total_messages = poly_data['total_messages']
        circle_center = poly.centroid
        
        if total_messages == 0:
            radius = ZERO_RADIUS
            color = 'darkgray'
            popup_html = f"""
            <div style='width:300px'>
                <h4>{geofence_name}</h4>
                <p>Total messages: {total_messages}.</p>
            </div>
            """
        else:
            radius = calculate_radius(total_messages, max_messages)

            severity = poly_data['severity']
            color = get_color(severity, max_severity)
            
            popup_html = f"""
            <div style='width:300px'>
                <h4>{geofence_name}</h4>
                <p>
                Total messages: {total_messages}. Total unique devices: {poly_data['total_devices']}<br>
                Late to normal GPS-reports ratio: {poly_data['latency_messages_ratio']:.1f}%<br>
                Late to normal devices ratio: {poly_data['latency_device_ratio']:.1f}%<br>
                Severity score: {poly_data['severity']:.1f}
                </p>
            </div>
            """
        
        folium.CircleMarker(
            location=[circle_center.x, circle_center.y],
            radius=radius,
            color=color,
            weight=2,
            fill=True,
            fill_opacity=0.3,
            popup=folium.Popup(popup_html, max_width=350)
        ).add_to(m)
    
    return m

def plot_dual_gps_heatmap(df, month, latency_H=24, lat_col='Lat', lon_col='Lon', zoom_start=2,
                         radius=15, show_markers=False,
                         latency_gradient = {0.4: '#DC143C', 0.65: '#FF4500',0.85: '#FFD700'},
                         normal_gradient = {0.4: '#4169E1',  0.65: '#20B2AA', 0.85: '#00FF00'}):
    
    # Calculate center point for initial view
    center_lat = df[lat_col].mean()
    center_lon = df[lon_col].mean()
    
    # Create base map
    m = folium.Map(location=[center_lat, center_lon], 
                  zoom_start=zoom_start,
                  tiles='OpenStreetMap')
    
    # Split data into latency and normal points
    latency_condition = df['t_diff'] >= pd.Timedelta(hours=latency_H)
    df_latency = df[latency_condition]
    df_normal = df[~latency_condition]

    print(f"Total points: {len(df)}")
    print(f"Normal points: {len(df_normal)} ({len(df_normal)/len(df)*100:.1f}%)")
    print(f"Latency points: {len(df_latency)} ({len(df_latency)/len(df)*100:.1f}%)")
    
    # Create all feature groups first
    latency_layer = folium.FeatureGroup(name='Latency Points', overlay=True, control=True)
    normal_layer = folium.FeatureGroup(name='Normal Points', overlay=True, control=True)
    
    # Prepare data for both heatmaps
    latency_data = [[row[lat_col], row[lon_col]] for _, row in df_latency.iterrows()]
    normal_data = [[row[lat_col], row[lon_col]] for _, row in df_normal.iterrows()]
    
    # Add normal points heatmap layer - First to render (base layer)
    if len(normal_data) > 0:
        HeatMap(normal_data,
                name='Normal Points',
                min_opacity=0.3,
                radius=radius,
                blur=15,
                max_zoom=1,
                gradient=normal_gradient).add_to(normal_layer)
    
    # Add latency points heatmap layer - Second to render (top layer)
    if len(latency_data) > 0:
        HeatMap(latency_data,
                name='Latency Points',
                min_opacity=0.3,
                radius=radius,
                blur=15,
                max_zoom=1,
                gradient=latency_gradient).add_to(latency_layer)
    
    # Optionally add marker clusters
    if show_markers:
        # Normal points markers
        normal_cluster = MarkerCluster(name='Normal Markers')
        for idx, row in df_normal.iterrows():
            folium.CircleMarker(
                location=[row[lat_col], row[lon_col]],
                radius=3,
                weight=2,
                color='green',
                fill=True,
                popup=f"Normal - Lat: {row[lat_col]:.6f}, Lon: {row[lon_col]:.6f}"
            ).add_to(normal_cluster)
        normal_cluster.add_to(m)
            
        # Latency points markers
        latency_cluster = MarkerCluster(name='Latency Markers')
        for idx, row in df_latency.iterrows():
            folium.CircleMarker(
                location=[row[lat_col], row[lon_col]],
                radius=3,
                weight=2,
                color='red',
                fill=True,
                popup=f"Latency - Lat: {row[lat_col]:.6f}, Lon: {row[lon_col]:.6f}"
            ).add_to(latency_cluster)
        latency_cluster.add_to(m)
    
    # Add the layers to the map in the desired order - latency first (bottom), normal second (top)
    latency_layer.add_to(m)
    normal_layer.add_to(m)
    
    # Add layer control with overlay=True to prevent base layer behavior
    folium.LayerControl(collapsed=False).add_to(m)

    # Add color legends
    normal_colormap = folium.branca.colormap.LinearColormap(
        colors=['#4169E1', '#20B2AA', '#00FF00'],
        vmin=0, vmax=100,
        caption='Normal Points'
    )
    normal_colormap.add_to(m)
    
    latency_colormap = folium.branca.colormap.LinearColormap(
        colors=['#DC143C', '#FF4500', '#FFD700'],
        vmin=0, vmax=100,
        caption='Latency Points'
    )
    latency_colormap.add_to(m)

    title_html = f'''
    <div style="position: fixed; 
                top: 10px; 
                left: 50px; 
                width: 600px; 
                z-index:9999; 
                font-size:16px;
                font-weight: bold;">
                GPS reports - Normal vs High Latency (24h) in {month}
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    return m

def load_month_data(year_month, customer_name='Zim'):
    """
    Load all data files of a required month.
    """
    year, month = year_month.split('-')
    
    # Construct filenames
    gps_filename = f"processed_gps_data_{customer_name}_{year}_{month}.csv"
    stats_filename = f"processed_geofence_stats_{customer_name}_{year}_{month}.csv"
    dict_filename = f"polygon_dict_{customer_name}.pkl"
    
    # Construct file paths
    gps_filepath = PROCESSED_DATA_DIR / gps_filename
    stats_filepath = PROCESSED_DATA_DIR / stats_filename
    dict_filepath = PROCESSED_DATA_DIR / dict_filename
    
    # Check if files exist
    missing_files = []
    if not gps_filepath.exists():
        missing_files.append(gps_filename)
    if not stats_filepath.exists():
        missing_files.append(stats_filename)
    if not dict_filepath.exists():
        missing_files.append(dict_filename)
    
    if missing_files:
        print(f"Error: The following files are missing for {year_month}:")
        for file in missing_files:
            print(f"  - {file}")
        print(f"Please make sure data for {year_month} has been processed.")
        return None
    
    # Load the data
    print(f"Loading data for {year_month}...")
    gps_df = pd.read_csv(gps_filepath)
    polygons_df = pd.read_csv(stats_filepath)
    
    with open(dict_filepath, 'rb') as f:
        polygon_dict = pickle.load(f)
    
    # Convert t_diff to timedelta
    gps_df['t_diff'] = pd.to_timedelta(gps_df['t_diff'])
    
    return gps_df, polygons_df, polygon_dict

def main():
    CUSTOMER_NAME = 'Zim'
    
    # Prompt user for month
    year_month = prompt_for_month()
    year, month = year_month.split('-')
    month_name = datetime.strptime(month, "%m").strftime("%B") # Convert month number to month name
    
    # Load data for the specified month
    data = load_month_data(year_month, CUSTOMER_NAME)
    if data is None:
        print("Some data files are missing.")
        sys.exit(1)
        
    # Unpack the data
    gps_df, polygons_df, polygon_dict = data
    
    # Plot the specific geofence
    geofence_name = 'CNSNH-TWB'
    print(f"Plotting {month_name} {year} data for geofence {geofence_name}.")
    
    # Check if geofence exists
    if geofence_name not in polygons_df['LocationName'].values:
        print(f"Error: Geofence '{geofence_name}' not found.")
        # available_geofences = polygons_df['LocationName'].tolist()
        # print(f"Available geofences: {', '.join(available_geofences[:10])}")
        # if len(available_geofences) > 10:
        #     print(f"...and {len(available_geofences) - 10} more.")
        # sys.exit(1)
    
    # Create the map
    map = plot_gps_per_polygon(
        polygons_df=polygons_df,
        geofence_name=geofence_name,
        gps_df=gps_df,
        customer_name=CUSTOMER_NAME,
        base_zoom=16,
        late_H=24
    )
    
    # Save the map
    MAPS_DIR.mkdir(exist_ok=True)
    
    map_filename = f"{CUSTOMER_NAME}_geofence_{geofence_name}_{year}_{month}.html"
    map_filepath = MAPS_DIR / map_filename
    
    map.save(str(map_filepath))
    print(f"Map saved to: {map_filepath}. Open in browser to view.")
    
    # Return filepath for browser opening if needed
    return map_filepath

if __name__ == "__main__":
    map_path = main()
