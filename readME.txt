{\rtf1\ansi\ansicpg1252\cocoartf2761
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica-Bold;\f1\fswiss\fcharset0 Helvetica;\f2\fnil\fcharset0 Menlo-Regular;
\f3\fnil\fcharset0 HelveticaNeue-Bold;}
{\colortbl;\red255\green255\blue255;\red255\green255\blue255;\red0\green0\blue0;\red144\green1\blue18;
\red0\green0\blue0;\red111\green111\blue111;\red144\green1\blue18;}
{\*\expandedcolortbl;;\cssrgb\c100000\c100000\c100000;\cssrgb\c0\c0\c0;\cssrgb\c63922\c8235\c8235;
\csgray\c0\c0;\cssrgb\c50980\c50980\c50980\c16078;\cssrgb\c63922\c8235\c8235;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\b\fs32 \cf0 To do:
\f1\b0\fs24 \
1. Create a function to query ZIM/client geofences. Necessary if/when well is expected new geofences to be added.\
2. Change the format for storing raw and processed GPS-data (from .csv to, say, .parquet). Necessary when number of trackers increases.\
3. Create app for triggering pre-mature (before the end of the month) analysis.\
\
4. SAVE 
\f2 \cb2 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec3 polygon_dict 
\f1 \cb1 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 associated with each geofence to processed data folder.\
\
\

\f0\b\fs32 Data pipeline description:
\f1\b0\fs24 \
1. Query all
\f2 \cf4 \cb2 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec4  
\f1 \cf0 \cb1 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 rows in the month in question for \
\pard\pardeftab720\partightenfactor0

\f2 \cf4 \cb2 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec4 	CustomerName = 'Zim'\cf0 \cb1 \strokec3 \
\cf4 \cb2 \strokec4 	AND DeviceID LIKE 'A0%'\cf0 \cb1 \strokec3 \
\cf4 \cb2 \strokec4 	AND FPort = 2\cf0 \cb1 \strokec3 \
\cf4 \cb2 \strokec4 	AND EventTimeUTC >= @StartDate\cf0 \cb1 \strokec3 \
\cf4 \cb2 \strokec4 	AND EventTimeUTC <= @EndDate\cf0 \cb1 \strokec3 \
\cf4 \cb2 \strokec4 	AND PayloadData LIKE '%GPS Data:%'\
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f1 \cf0 \cb1 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 2. Process the data:\
	- extract lat, lon\
\cb5 	- column 
\f3\b \expnd0\expndtw0\kerning0
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