# Essential libraries
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import numpy as np
import datetime
import time
import csv
import re
# import random
import pickle
import warnings

# Visualization and mapping
import folium
from folium.plugins import MarkerCluster, HeatMap, HeatMapWithTime

# Spatial analysis
from shapely.geometry import Point, Polygon, MultiPoint
from rtree import index

import geopandas as gpd

# Utilities
from typing import List, Tuple, Dict, Optional

# from global_land_mask import globe

