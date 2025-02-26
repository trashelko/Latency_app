"""
TO ADD in the future

    1. Query for customer geofences
    2. Parameterize for customer query for GPS data
    3. Future-future: deal with increasing number of trackers (increased size of GPS data)
"""

from credentials import (
    DB_NEW_CONFIG
)

# Essetial libraries
import pandas as pd
import time
from pathlib import Path
import argparse
from datetime import datetime

# Database connectivity
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError

# Set up paths for the project
BASE_DIR = Path(__file__).parent.parent.absolute()
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

# Ensure raw data directory exists
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_db_connection(config):
    """Creates and returns a SQLAlchemy database engine."""
    return create_engine(
        f"mssql+pyodbc://{config['username']}:{config['password']}@"
        f"{config['server']}/{config['database']}?"
        f"driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
        f"&connection_timeout=30"
    )

def get_gps_data(year_month, max_retries=3, retry_delay=5, customer_name="Zim"):
    """
    Retrieves GPS data from the Bursts table for a specific month with retry logic.
    
    Args:
        year_month: Month in 'YYYY-MM' format
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        customer_name: Name of the customer to filter by
        
    Returns:
        DataFrame containing the query results
    """
    # Parse year and month
    try:
        year, month = map(int, year_month.split('-'))
        # Determine the first and last day of the month
        if month == 12:
            next_month_year = year + 1
            next_month = 1
        else:
            next_month_year = year
            next_month = month + 1
            
        date_from = f"{year}-{month:02d}-01"
        date_to = f"{next_month_year}-{next_month:02d}-01"
    except ValueError:
        raise ValueError("Invalid year_month format. Expected 'YYYY-MM'")
    
    query = """
        DECLARE @StartDate DATETIME2 = ?;
        DECLARE @EndDate DATETIME2 = ?;
        DECLARE @CustomerName NVARCHAR(100) = ?;
        
        SELECT
            [CustomerName],
            [DeviceID], 
            [DeviceName],
            [ReceiveTimeUTC],
            [EventTimeUTC],
            [FPort],
            [PayloadData]
        FROM [dbo].[Bursts]
        WHERE
            CustomerName = @CustomerName
            AND DeviceID LIKE 'A0%'
            AND FPort = 2
            AND EventTimeUTC >= @StartDate
            AND EventTimeUTC < @EndDate
            AND PayloadData LIKE '%GPS Data:%'
        ORDER BY DeviceID, EventTimeUTC DESC;
        """
    
    params = (f"{date_from} 00:00:00", f"{date_to} 00:00:00", customer_name)
    
    # Initialize retry counter
    retry_count = 0
    last_error = None
    
    # Retry loop
    while retry_count < max_retries:
        try:
            # Create a new engine for each attempt
            engine = get_db_connection(DB_NEW_CONFIG)
            
            # Try to establish connection
            with engine.connect() as connection:
                print(f"Fetching GPS data for {customer_name} from {date_from} to {date_to}...")
                # Execute query and return results
                return pd.read_sql(query, connection, params=params)
                
        except (OperationalError, SQLAlchemyError) as e:
            last_error = e
            retry_count += 1
            
            if retry_count < max_retries:
                print(f"Connection error: {e}")
                print(f"Retrying in {retry_delay} seconds... (Attempt {retry_count}/{max_retries})")
                time.sleep(retry_delay)
                # Increase delay for each retry (exponential backoff)
                retry_delay *= 1.5
            else:
                print(f"Max retries ({max_retries}) reached. Could not establish connection.")
    
    # If we've exhausted all retries, raise the last error
    raise last_error

def save_gps_data(df, customer_name, year_month):
    """
    Saves GPS data to a CSV file in the raw data directory.
    
    Args:
        df: DataFrame containing GPS data
        customer_name: Name of the customer
        year_month: Month in 'YYYY-MM' format
        
    Returns:
        Path to the saved file
    """
    year, month = year_month.split('-')
    filename = f"gps_data_{customer_name}_{year}_{month}.csv"
    filepath = RAW_DATA_DIR / filename
    
    df.to_csv(filepath, index=False)

    month_name = datetime.strptime(month, "%m").strftime("%B") # Convert month number to month name
    print(f"Saved {month_name}'s GPS data to {filepath}.")
    return filepath

def prompt_for_month():
    """Prompts the user to input a month in YYYY-MM format."""
    current_month = datetime.now().strftime("%Y-%m")
    print("\n=== Query GPS Data ===")
    print(f"Please enter the month you want to extract data for.")
    print(f"Format: YYYY-MM (e.g., 2025-01 for January 2025)")
    print(f"Press Enter to use current month ({current_month})")
    
    while True:
        user_input = input("Month [YYYY-MM]: ").strip()
        
        # Use current month if user just presses Enter
        if user_input == "":
            return current_month
            
        # Validate the format
        try:
            datetime.strptime(user_input, "%Y-%m")
            return user_input
        except ValueError:
            print("Invalid format! Please use YYYY-MM format (e.g., 2025-01)")

def get_default_month():
    """Determines default month based on current date."""
    now = datetime.now()
    # If day of month <= 10, use previous month
    if now.day <= 10:
        # Handle January case
        if now.month == 1:
            return f"{now.year-1}-12"
        else:
            return f"{now.year}-{now.month-1:02d}"
    else:
        return f"{now.year}-{now.month:02d}"

def main():
    """Main function to run the script with smart month selection."""
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
    
    print(f"Extracting GPS data for {args.customer} in {year_month}...")
    
    try:
        # Get the data
        df = get_gps_data(year_month, customer_name=args.customer)
        
        # Save the data
        if not df.empty:
            save_gps_data(df, args.customer, year_month)
            # print(f"Successfully saved {len(df)} records to:")
            # print(f"  {filepath}")
        else:
            print(f"No GPS data found for {args.customer} in {year_month}")
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())