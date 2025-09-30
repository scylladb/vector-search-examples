import pandas as pd

def create_sample_data(input_csv, output_csv, filter_column, filter_value, sample_size=30000):
    """
    Read CSV, filter by column value, take first N rows, and export to new CSV.
    
    Args:
        input_csv (str): Path to input CSV file
        output_csv (str): Path to output CSV file
        filter_column (str): Column name to filter on
        filter_value: Value to filter by
        sample_size (int): Number of rows to take (default 30000)
    """
    print(f"Reading {input_csv}...")
    df = pd.read_csv(input_csv)
    
    print(f"Original dataset size: {len(df)} rows")
    
    # Filter by column value
    filtered_df = df[df[filter_column] == False]
    print(f"After filtering by {filter_column}={filter_value}: {len(filtered_df)} rows")
    
    # Take first N rows
    sample_df = filtered_df.head(sample_size)
    print(f"Taking first {sample_size} rows: {len(sample_df)} rows")
    
    # Export to new CSV (preserves all original columns and data)
    sample_df.to_csv(output_csv, index=False)
    print(f"Sample data exported to {output_csv}")

if __name__ == "__main__":
    # Example usage
    INPUT_CSV = "data/movies.csv"
    OUTPUT_CSV = "data/movies_sample.csv"
    FILTER_COLUMN = "adult"  # Column to filter on
    FILTER_VALUE = False   # Value to filter by
    
    create_sample_data(INPUT_CSV, OUTPUT_CSV, FILTER_COLUMN, FILTER_VALUE, 100000)