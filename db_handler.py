import pandas as pd

def load_products(csv_path: str):
    """
    Loads the CSV into a pandas DataFrame.
    Returns the DataFrame.
    """
    df = pd.read_csv(csv_path)
    return df

def search_parts(df, make=None, model=None, category=None):
    """
    Filters parts based on the given criteria.
    If a parameter is None, it won't filter by that criterion.
    Returns a filtered DataFrame (which might be empty if no matches).
    """
    filtered_df = df.copy()

    # Filter by vehicle make
    if make:
        # We'll do a case-insensitive match
        mask_make = filtered_df['VehicleMake'].str.lower() == make.lower()
        filtered_df = filtered_df[mask_make]

    # Filter by vehicle model
    if model:
        mask_model = filtered_df['VehicleModel'].str.lower() == model.lower()
        filtered_df = filtered_df[mask_model]

    # Filter by category
    if category:
        mask_cat = filtered_df['Category'].str.lower() == category.lower()
        filtered_df = filtered_df[mask_cat]

    return filtered_df
