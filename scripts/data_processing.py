from data_query import get_default_month, prompt_for_month
from config import BASE_DIR,RAW_DATA_DIR,PROCESSED_DATA_DIR,DEFAULT_CUSTOMER

# Essential libraries
import pandas as pd
from pathlib import Path
import numpy as np
import datetime
import pickle
import argparse
from datetime import datetime
# import random
import warnings

# Spatial analysis
from shapely.geometry import Point, Polygon
from rtree import index

import geopandas as gpd

# Utilities
from typing import List, Tuple, Dict, Optional

# from global_land_mask import globe

# # Set up paths for the project
# BASE_DIR = Path(__file__).parent.parent.absolute()
# RAW_DATA_DIR = BASE_DIR / "data" / "raw"
# PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

def detect_date_format(date_series):
    for fmt in ["%Y-%m-%d %H:%M:%S.%f",'%d/%m/%Y %H:%M','%m/%d/%Y %H:%M']:
        try:
            pd.to_datetime(date_series, format=fmt)
            return fmt
        except ValueError: 
            continue
    return None

def extract_GPS(payload_col):
    coords_df = payload_col.str.extract(r'GPS Data: (-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?),(-?\d+(?:\.\d+)?)')
    coords_df.columns = ['Lat', 'Lon']
    return coords_df['Lat'].astype(float), coords_df['Lon'].astype(float)

def convert_to_polygon(polygon_str: str) -> List[List[float]]:
    coords = [float(x) for x in polygon_str.split(',')]
    return [[coords[i], coords[i+1]] for i in range(0, len(coords), 2)]

def build_spatial_index(polygons_df: pd.DataFrame) -> Tuple[index.Index, Dict]:
    idx = index.Index()
    polygon_dict = {}
    
    polygons_df['Polygon_coords'] = polygons_df['Polygon'].apply(convert_to_polygon)
    
    for i, row in polygons_df.iterrows():
        coords = np.array(row['Polygon_coords'])
        bounds = (
            coords[:, 1].min(), coords[:, 0].min(),  # minx, miny
            coords[:, 1].max(), coords[:, 0].max()   # maxx, maxy
        )
        polygon = Polygon(coords)
        idx.insert(i, bounds)
        polygon_dict[i] = (row['LocationName'], polygon)
    
    return idx, polygon_dict

def build_and_save_persistent_spatial_index(customer_name="Zim"):
    """
    Build and save a persistent spatial index and polygon dictionary
    that doesn't need to be recreated monthly.
    """
    
    # # Set up paths for the project
    # BASE_DIR = Path(__file__).parent.parent.absolute()
    # RAW_DATA_DIR = BASE_DIR / "data" / "raw"
    # PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
    # PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load polygons data
    filename = f"geofences_{customer_name}.csv"
    filepath = RAW_DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"{customer_name} geofences data file not found: {filepath}")
    
    polygons_df = pd.read_csv(filepath, usecols=['LocationName', 'Polygon'])
    print(f"Building persistent spatial index for {len(polygons_df)} {customer_name} geofences")
    
    # Build the spatial index and polygon dictionary
    spatial_idx, polygon_dict = build_spatial_index(polygons_df)
    
    # Save as persistent files (no month/year in filename)
    spatial_idx_path = PROCESSED_DATA_DIR / f"spatial_idx_{customer_name}.pkl"
    polygon_dict_path = PROCESSED_DATA_DIR / f"polygon_dict_{customer_name}.pkl"
    
    # Save polygon dictionary
    with open(polygon_dict_path, 'wb') as f:
        pickle.dump(polygon_dict, f)
    
    # Save spatial index (if needed - depends on how you use it)
    with open(spatial_idx_path, 'wb') as f:
        pickle.dump(spatial_idx, f)
    
    print(f"Saved spatial index and polygon dictionary for latest {customer_name} geofences.")
    # print(f"  - Spatial index: {spatial_idx_path}")
    # print(f"  - Polygon dict: {polygon_dict_path}")
    
    return spatial_idx, polygon_dict

# def load_persistent_spatial_index(customer_name="Zim"):
#     """
#     Load the persistent spatial index and polygon dictionary.
#     """
    
#     # # Set up paths for the project
#     # BASE_DIR = Path(__file__).parent.parent.absolute()
#     # PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
    
#     # File paths
#     spatial_idx_path = PROCESSED_DATA_DIR / f"spatial_idx_{customer_name}.pkl"
#     polygon_dict_path = PROCESSED_DATA_DIR / f"polygon_dict_{customer_name}.pkl"
    
#     # Check if files exist
#     if not spatial_idx_path.exists() or not polygon_dict_path.exists():
#         print(f"Persistent spatial index not found. Creating new one...")
#         return build_and_save_persistent_spatial_index(customer_name)
    
#     # Load files
#     with open(spatial_idx_path, 'rb') as f:
#         spatial_idx = pickle.load(f)
    
#     with open(polygon_dict_path, 'rb') as f:
#         polygon_dict = pickle.load(f)
    
#     # print(f"Loaded persistent spatial index for {customer_name}")
#     return spatial_idx, polygon_dict

def find_containing_polygon(points: np.ndarray, idx: index.Index, polygon_dict: Dict) -> List[Optional[str]]:
    results = []
    batch_size = 10000
    
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        for lat, lon in batch:
            point = Point(lat, lon)  # Maintain this ordering
            bounds = (lon, lat, lon, lat)  # But swap for rtree query
            location = None
            for idx_val in idx.intersection(bounds):
                loc_name, poly = polygon_dict[idx_val]
                if poly.contains(point):
                    location = loc_name
                    break
            results.append(location)
    
    return results

def process_gps_data(gps_data: pd.DataFrame, spatial_idx: index.Index, polygon_dict: Dict,
                     customer_name=DEFAULT_CUSTOMER,  
                     land_geometry=None, buffer_degrees=0.1) -> pd.DataFrame:
    """
    Process GPS data and create two columns -- if GPS-coordinate is in customer geofence and if at sea.
    """
    df = gps_data.copy()
    
    # Process timestamps
    receive_fmt = detect_date_format(df['ReceiveTimeUTC'])
    event_fmt = detect_date_format(df['EventTimeUTC'])
    df['ReceiveTimeUTC'] = pd.to_datetime(df['ReceiveTimeUTC'], format=receive_fmt)
    df['EventTimeUTC'] = pd.to_datetime(df['EventTimeUTC'], format=event_fmt)
    df['t_diff'] = df['ReceiveTimeUTC'] - df['EventTimeUTC']
    
    # Extract GPS coordinates
    df['Lat'], df['Lon'] = extract_GPS(df['PayloadData'])
    
    # Find containing polygons
    points = df[['Lat', 'Lon']].values
    df[f'in_{customer_name}_polygon'] = find_containing_polygon(points, spatial_idx, polygon_dict)
    
    # If land geometry is provided, determine if points are in sea
    if land_geometry is not None:
        # Convert points to GeoDataFrame for spatial join
        points_gdf = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy(df['Lon'], df['Lat']),
            crs=land_geometry.crs
        )
        points_gdf['original_idx'] = df.index
        
        # Create buffered land
        buffered_land = gpd.GeoDataFrame(
            geometry=land_geometry.buffer(buffer_degrees),
            crs=land_geometry.crs
        )
        
        # Spatial join
        joined = gpd.sjoin(points_gdf, buffered_land, how='left', predicate='within')
        
        # Create a dictionary mapping from original index to sea status
        is_sea_dict = {idx: pd.isna(land_idx) for idx, land_idx in 
                       zip(joined['original_idx'], joined.index_right)}
        
        # Apply the dictionary to create the new column
        df['in_Sea'] = df.index.map(lambda i: is_sea_dict.get(i, True))
    
    return df

def calculate_severity(latency_msg_ratio: float, total_messages: int, max_messages: int,
                      latency_dev_ratio: float, total_devices: int, max_devices: int) -> float:
    volume_factor = np.log10(total_messages * total_devices + 0.1) / np.log10(max_messages * max_devices)
    return round(((latency_msg_ratio + latency_dev_ratio) / 2) * volume_factor, 1)

def get_geofence_stats(polygons_df: pd.DataFrame, gps_data: pd.DataFrame, 
                       customer_name=DEFAULT_CUSTOMER,
                       latency_threshold: int = 24) -> pd.DataFrame:
    result_df = polygons_df.copy()
    stats = []
    
    for polygon_name in polygons_df['LocationName']:
        gps_in_polygon = gps_data[gps_data[f'in_{customer_name}_polygon'] == polygon_name]
        polygon_latency = gps_in_polygon['t_diff'] >= pd.Timedelta(hours=latency_threshold)
        
        all_devices = gps_in_polygon['DeviceID'].unique()
        latency_devices = gps_in_polygon.loc[polygon_latency, 'DeviceID'].unique()
        
        total_msgs = len(gps_in_polygon)
        latency_msgs = polygon_latency.sum()
        
        stats.append({
            'total_messages': total_msgs,
            'total_devices': len(all_devices),
            'latency_messages': latency_msgs,
            'latency_devices': len(latency_devices),
            'latency_messages_ratio': round(latency_msgs / total_msgs * 100 if total_msgs > 0 else 0, 1),
            'latency_device_ratio': round(len(latency_devices) / len(all_devices) * 100 if len(all_devices) > 0 else 0, 1),
            'device_ids': list(all_devices) if len(all_devices) > 0 else None,
            'latency_device_ids': list(latency_devices) if len(latency_devices) > 0 else None
        })
    
    for col in stats[0].keys():
        result_df[col] = [stat[col] for stat in stats]
    
    max_messages = result_df['total_messages'].max()
    max_devices = result_df['total_devices'].max()
    
    result_df['severity'] = result_df.apply(
        lambda row: calculate_severity(
            row['latency_messages_ratio'], row['total_messages'], max_messages,
            row['latency_device_ratio'], row['total_devices'], max_devices
        ), axis=1
    )
    
    return result_df

def get_processed_gpsData_and_polygons(
    year_month: str,
    customer_name: str = "Zim",
    land_path: str = BASE_DIR / "data" / "ne_10m_land.shp",
    buffer_degrees: float = 0.1,
    latency_threshold: int = 24
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Process GPS data with both polygon containment and sea detection in one call.
    """

    year, month = year_month.split('-')
    month_name = datetime.strptime(month, "%m").strftime("%B") # Convert month number to month name

    # Load GPS data
    filename = f"gps_data_{customer_name}_{year}_{month}.csv"
    filepath = RAW_DATA_DIR / filename

    # print(f"Loading raw GPS data from: {filepath}")
    if not filepath.exists():
        raise FileNotFoundError(f"Raw GPS data file not found: {filepath}\nTry running data_query.py first.")
    
    gps_data = pd.read_csv(filepath)
    print(f"Loaded {len(gps_data)} GPS records for {customer_name} for {month_name} {year} from: {filepath}")
    
    # Load polygons data
    filename = f"geofences_{customer_name}.csv"
    filepath = RAW_DATA_DIR / filename
    # print(f"Loading {customer_name} geofences data from: {filepath}")
    if not filepath.exists():
        raise FileNotFoundError(f"{customer_name} geofences data file not found: {filepath}")
    polygons_df = pd.read_csv(filepath, usecols=['LocationName', 'Polygon']) # Only load necessary columns
    print(f"Loaded {len(polygons_df)} geofences for {customer_name} from {filepath}")

    print(f"Processing GPS data...")
    
    # Initialize spatial indexing for polygons
    print(f"Building spatial index for geofences...")
    # spatial_idx, polygon_dict = load_persistent_spatial_index(customer_name)
    spatial_idx, polygon_dict = build_spatial_index(polygons_df)

    # Load land geometry
    print(f"Loaded land geometry from: {land_path}")
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', 'Geometry is in a geographic CRS')
        land_geometry = gpd.read_file(land_path).geometry
    
    # Process GPS data with both polygon and sea detection
    print("For each GPS-coordinate checking containing geofences and if at sea...")
    processed_gps = process_gps_data(
        gps_data, 
        spatial_idx, 
        polygon_dict,
        land_geometry=land_geometry,
        buffer_degrees=buffer_degrees
    )
    
    # Calculate polygon statistics
    print("Calculating geofence statistics...")
    polygon_stats = get_geofence_stats(
        polygons_df, 
        processed_gps,
        latency_threshold=latency_threshold
    )
    
    print("\nProcessing complete.\n================================\n")
    print(f"Total {len(processed_gps)} GPS records processed.")

    cond_sea = processed_gps['in_Sea']
    cond_polygon = processed_gps[f'in_{customer_name}_polygon'].notna()

    print(f"GPS-coordinated in sea: {sum(cond_sea)} ({round(sum(cond_sea)/len(processed_gps)*100,2)})%.")
    print(f"GPS-coordinated in {customer_name} geofences: {sum(cond_polygon)} ({round(sum(cond_polygon)/len(processed_gps)*100,2)})%.")
    print(f"In sea AND in {customer_name} geofences: {sum(cond_sea & cond_polygon)}. If not zero -- check.",end='\n\n')

    return processed_gps, polygon_stats, polygon_dict

def save_processed_data(processed_gps, polygon_stats, polygon_dict, customer_name, year_month):
    year, month = year_month.split('-')
    
    # Create processed directory if it doesn't exist
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save processed GPS data
    gps_filename = f"processed_gps_data_{customer_name}_{year}_{month}.csv"
    gps_filepath = PROCESSED_DATA_DIR / gps_filename
    processed_gps.to_csv(gps_filepath, index=False)
    
    # Save geofence statistics as CSV
    stats_filename = f"processed_geofence_stats_{customer_name}_{year}_{month}.csv"
    stats_filepath = PROCESSED_DATA_DIR / stats_filename
    polygon_stats.to_csv(stats_filepath, index=False)
    
    # Save polygon dictionary
    dict_filename = f"polygon_dict_{customer_name}.pkl"
    dict_filepath = PROCESSED_DATA_DIR / dict_filename
    with open(dict_filepath, 'wb') as f:
        pickle.dump(polygon_dict, f)
    
    month_name = datetime.strptime(month, "%m").strftime("%B")
    print(f"Saved {month_name}'s processed data for {customer_name}:")
    print(f"  - GPS data: {gps_filepath} ({processed_gps.memory_usage(deep=True).sum() / (1024**2):.1f} MB)")
    print(f"  - Geofence stats: {stats_filepath}")
    print(f"  - Polygon dict: {dict_filepath}")
    
    return gps_filepath, stats_filepath, dict_filepath

def main():
   """Main function to process GPS data for a specific month."""
   
   print("\n=== Process GPS data and create geofence statistics ===")

   parser = argparse.ArgumentParser()
   parser.add_argument(
       "--manual", 
       action="store_true",
       help="Manually select month"
   )
   parser.add_argument(
       "--customer", 
       default="Zim",
       help="Customer name (default: Zim)"
   )
   
   args = parser.parse_args()

   # Determine which month to use
   if args.manual:
       year_month = prompt_for_month()
   else:
       year_month = get_default_month()
   
   print(f"Processing GPS data for {args.customer} in {year_month}...")
   
   try:
       # Get and process the data
       processed_gps, polygon_stats, polygon_dict = get_processed_gpsData_and_polygons(
           year_month, 
           customer_name=args.customer
       )
       
       # Save the processed data
       if not processed_gps.empty:
           save_processed_data(
               processed_gps, 
               polygon_stats, 
               polygon_dict, 
               args.customer, 
               year_month
           )
       else:
           print(f"No processed GPS data generated for {args.customer} in {year_month}")
           
   except FileNotFoundError as e:
       print(f"Error: {e}")
       print("Run data_query.py first to fetch the raw data.")
       return 1
   except Exception as e:
       print(f"Error: {e}")
       return 1
       
   return 0

if __name__ == "__main__":
   exit(main())