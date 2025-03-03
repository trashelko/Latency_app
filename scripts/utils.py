from datetime import datetime

def prompt_for_month():
    """Prompts the user to input a month in YYYY-MM format."""
    current_month = datetime.now().strftime("%Y-%m")
    print(f"Please enter the month in format YYYY-MM (e.g., 2025-01 for January 2025) or press Enter to use current month ({current_month})")
    
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