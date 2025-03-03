To do:
1. Create a function to query ZIM/client geofences. Necessary if/when well is expected new geofences to be added.
2. Change the format for storing raw and processed GPS-data (from .csv to, say, .parquet). Necessary when number of trackers increases.
3. Create app for triggering pre-mature (before the end of the month) analysis.
4. SAVE polygon_dict associated with each geofence to processed data folder.
5. Don't save polygon_dict every month but rather every time customer geofences charges
6. In data_processing add -- if files exist -- don't create them again.


Data pipeline description:
1. Query all rows in the month in question for 
CustomerName = 'Zim'
AND DeviceID LIKE 'A0%'
AND FPort = 2
AND EventTimeUTC >= @StartDate
AND EventTimeUTC <= @EndDate
AND PayloadData LIKE '%GPS Data:%

2. Process the data:
	- extract lat, lon
 	- column t_diff: time between ReceiveTimeUTC and EventTimeUTC
 	- column in_ZIM_polygon: None or LocationName of ZIM geofence of this GPS-coordinate
	- column in_Sea: False/True for if the GPS-coordinate is at sea. This is decided based on Natural Earth dataset for land under the resolution of 10m + a 0.1 degree buffer (to cover all/most inconsistencies on coastlines).