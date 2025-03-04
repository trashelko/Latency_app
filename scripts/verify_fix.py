def debug_spatial_indexing(year_month, customer_name="Zim"):
    """
    Comprehensive debugging function for spatial indexing issues.
    Tests multiple variations of the coordinate handling.
    
    Args:
        year_month: Month in YYYY-MM format
        customer_name: Customer name
    """
    import pandas as pd
    from pathlib import Path
    import numpy as np
    from shapely.geometry import Point, Polygon
    from rtree import index
    import pickle
    import sys
    
    # Import necessary functions
    from data_processing import (
        RAW_DATA_DIR, 
        PROCESSED_DATA_DIR,
        convert_to_polygon,
        extract_GPS
    )
    
    year, month = year_month.split('-')
    
    print(f"\n=== COMPREHENSIVE SPATIAL INDEXING DEBUGGING FOR {year_month} ===\n")
    
    # 1. Load data
    gps_filename = f"gps_data_{customer_name}_{year}_{month}.csv"
    gps_filepath = RAW_DATA_DIR / gps_filename
    
    geofence_filename = f"geofences_{customer_name}.csv"
    geofence_filepath = RAW_DATA_DIR / geofence_filename
    
    if not gps_filepath.exists() or not geofence_filepath.exists():
        print(f"ERROR: Required files not found")
        return
        
    gps_data = pd.read_csv(gps_filepath)
    polygons_df = pd.read_csv(geofence_filepath, usecols=['LocationName', 'Polygon'])
    
    print(f"Loaded {len(gps_data)} GPS records and {len(polygons_df)} geofences")
    
    # 2. Extract GPS coordinates
    lats, lons = extract_GPS(gps_data['PayloadData'])
    gps_data['Lat'] = lats
    gps_data['Lon'] = lons
    
    # 3. Create a small sample of points for faster testing
    sample_size = min(1000, len(gps_data))
    sample_indices = np.random.choice(len(gps_data), sample_size, replace=False)
    sample_points = gps_data.iloc[sample_indices][['Lat', 'Lon']].values
    
    # 4. Define different variations of the build_spatial_index function
    
    # Variation 1: Original with swapped bounds
    def build_spatial_index_v1(polygons_df):
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
    
    # Variation 2: Swapped polygon construction
    def build_spatial_index_v2(polygons_df):
        idx = index.Index()
        polygon_dict = {}
        
        polygons_df['Polygon_coords'] = polygons_df['Polygon'].apply(convert_to_polygon)
        
        for i, row in polygons_df.iterrows():
            coords = np.array(row['Polygon_coords'])
            # Swap coordinates when creating Polygon
            swapped_coords = np.column_stack((coords[:, 1], coords[:, 0]))
            bounds = (
                coords[:, 1].min(), coords[:, 0].min(),
                coords[:, 1].max(), coords[:, 0].max()
            )
            polygon = Polygon(swapped_coords)
            idx.insert(i, bounds)
            polygon_dict[i] = (row['LocationName'], polygon)
        
        return idx, polygon_dict
    
    # Variation 3: Standard GIS order consistency
    def build_spatial_index_v3(polygons_df):
        idx = index.Index()
        polygon_dict = {}
        
        def convert_to_polygon_lon_lat(polygon_str):
            coords = [float(x) for x in polygon_str.split(',')]
            # Swap lat/lon when pairing (standard GIS is lon/lat)
            return [[coords[i+1], coords[i]] for i in range(0, len(coords), 2)]
        
        polygons_df['Polygon_coords'] = polygons_df['Polygon'].apply(convert_to_polygon_lon_lat)
        
        for i, row in polygons_df.iterrows():
            coords = np.array(row['Polygon_coords'])
            bounds = (
                coords[:, 0].min(), coords[:, 1].min(),  # standard GIS: minx(lon), miny(lat)
                coords[:, 0].max(), coords[:, 1].max()   # standard GIS: maxx(lon), maxy(lat)
            )
            polygon = Polygon(coords)
            idx.insert(i, bounds)
            polygon_dict[i] = (row['LocationName'], polygon)
        
        return idx, polygon_dict
    
    # 5. Define consistent find_containing_polygon functions for each variation
    
    def find_containing_polygon_v1(points, idx, polygon_dict):
        results = []
        batch_size = 10000
        
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            for lat, lon in batch:
                point = Point(lat, lon)  # matches original format
                bounds = (lon, lat, lon, lat)  # swapped for rtree query
                location = None
                for idx_val in idx.intersection(bounds):
                    loc_name, poly = polygon_dict[idx_val]
                    if poly.contains(point):
                        location = loc_name
                        break
                results.append(location)
        
        return results
    
    def find_containing_polygon_v2(points, idx, polygon_dict):
        results = []
        batch_size = 10000
        
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            for lat, lon in batch:
                point = Point(lon, lat)  # swapped order
                bounds = (lon, lat, lon, lat)  # standard GIS order
                location = None
                for idx_val in idx.intersection(bounds):
                    loc_name, poly = polygon_dict[idx_val]
                    if poly.contains(point):
                        location = loc_name
                        break
                results.append(location)
        
        return results
    
    def find_containing_polygon_v3(points, idx, polygon_dict):
        results = []
        batch_size = 10000
        
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            for lat, lon in batch:
                point = Point(lon, lat)  # standard GIS order
                bounds = (lon, lat, lon, lat)  # standard GIS order
                location = None
                for idx_val in idx.intersection(bounds):
                    loc_name, poly = polygon_dict[idx_val]
                    if poly.contains(point):
                        location = loc_name
                        break
                results.append(location)
        
        return results
    
    # 6. Test all variations
    variations = [
        ("Variation 1: Swapped bounds only", build_spatial_index_v1, find_containing_polygon_v1),
        ("Variation 2: Swapped polygon construction", build_spatial_index_v2, find_containing_polygon_v2),
        ("Variation 3: Standard GIS order consistency", build_spatial_index_v3, find_containing_polygon_v3)
    ]
    
    best_variation = None
    max_contained = 0
    
    for name, build_fn, find_fn in variations:
        print(f"\nTesting {name}...")
        
        try:
            # Build the spatial index
            spatial_idx, polygon_dict = build_fn(polygons_df)
            
            # Find containing polygons
            results = find_fn(sample_points, spatial_idx, polygon_dict)
            contained_count = sum(1 for r in results if r is not None)
            
            print(f"Points in geofences: {contained_count} out of {sample_size} ({contained_count/sample_size*100:.2f}%)")
            
            if contained_count > max_contained:
                max_contained = contained_count
                best_variation = name
            
            # Additional diagnostics if no points found
            if contained_count == 0:
                # Try direct polygon containment for a few points
                print("Testing direct polygon containment for 10 random points...")
                direct_found = 0
                
                for i in range(min(10, len(sample_points))):
                    lat, lon = sample_points[i]
                    point_lonlat = Point(lon, lat)
                    
                    for _, (loc_name, poly) in polygon_dict.items():
                        if poly.contains(point_lonlat):
                            direct_found += 1
                            print(f"Point ({lat}, {lon}) is in polygon '{loc_name}' using direct check")
                            break
                
                print(f"Direct containment found {direct_found} points in polygons")
                
                # Check if coordinates make sense
                first_poly_name = polygons_df['LocationName'].iloc[0]
                first_poly_str = polygons_df['Polygon'].iloc[0]
                
                print(f"\nAnalyzing first polygon ({first_poly_name}):")
                print(f"Raw polygon string: {first_poly_str[:100]}...")
                
                coords = convert_to_polygon(first_poly_str)
                coords_array = np.array(coords)
                
                print(f"Parsed into {len(coords)} coordinate pairs")
                print(f"First few coordinates: {coords[:3]}")
                print(f"Coordinate ranges: Lat [{coords_array[:, 0].min()}, {coords_array[:, 0].max()}], Lon [{coords_array[:, 1].min()}, {coords_array[:, 1].max()}]")
            
        except Exception as e:
            print(f"ERROR: {e}")
    
    # 7. Report results
    if max_contained > 0:
        print(f"\nBEST RESULT: {best_variation} - found {max_contained} points in geofences")
        print("\nRECOMMENDED FIX: Use the build_spatial_index and find_containing_polygon functions from this variation")
    else:
        print("\nNone of the variations found any points in geofences.")
        print("This suggests a more fundamental issue with the data or processing pipeline.")
        
        # Additional specific checks
        print("\nPerforming additional checks...")
        
        # Look at a few GPS points and polygons to make sure they make geographic sense
        print("\nSample GPS points (Lat, Lon):")
        for i in range(min(5, len(sample_points))):
            print(f"{i+1}: {sample_points[i]}")
        
        # Sample polygon bounds to see if they make sense
        print("\nSample polygon bounds (as stored in the spatial index):")
        spatial_idx, polygon_dict = build_spatial_index_v3(polygons_df)
        
        for i, (name, poly) in list(polygon_dict.items())[:5]:
            print(f"{name}: {poly.bounds}")
        
        print("\nPotential issues to investigate:")
        print("1. Are the GPS coordinates and polygon coordinates in completely different regions?")
        print("2. Has the format of the 'Polygon' column in the geofences CSV changed?")
        print("3. Are the polygons being parsed correctly from their string representation?")
        print("4. Check for any changes in the rtree index behavior or version")
        
    print("\n=== DEBUGGING COMPLETE ===")

# Example usage:
debug_spatial_indexing('2024-11')