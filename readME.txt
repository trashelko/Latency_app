To do:
1. Create a function to query ZIM/client geofences. Necessary if/when well is expected new geofences to be added.
2. Change the format for storing raw and processed GPS-data (from .csv to, say, .parquet). Necessary when number of trackers increases.\
3. Create app for triggering pre-mature (before the end of the month) analysis.
4. SAVE polygon_dict associated with each geofence to processed data folder.\
5. Don't save polygon_dict every month but rather every time customer geofences charges


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
 	- column 
\outl0\strokewidth0 \strokec3 t_diff: 
\f1\b0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 time between 
\f3\b \cb6 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec3 ReceiveTimeUTC
\f1\b0 \cb5 \kerning1\expnd0\expndtw0 \outl0\strokewidth0  and 
\f3\b \cb6 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec3 EventTimeUTC\

\f1\b0 \cb5 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 	- column 
\f3\b \cb6 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec3 in_ZIM_polygon
\f1\b0 \cb5 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 : None or 
\f3\b \cb6 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec3 LocationName 
\f1\b0 \cb5 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 of ZIM geofence of this GPS-coordinate\
	- column 
\f3\b \cb6 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec3 in_Sea
\f1\b0 \cb5 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 : False/True for if the GPS-coordinate is at sea. This is decided based on Natural Earth dataset for land under the resolution of 10m + a 0.1 degree buffer (to cover all/most inconsistencies on coastlines).\
	\cb1 \
\pard\pardeftab720\partightenfactor0

\f2 \cf0 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec3 \
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f1 \cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 \

\f2 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec3 \
}