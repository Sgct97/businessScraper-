import pandas as pd
import sys

# --- Configuration ---
INPUT_FILE = 'enriched_businesses.csv'
OUTPUT_FILE = 'sorted_businesses_for_review.csv'

def sort_and_save_csv(input_path, output_path):
    """
    Reads a CSV, sorts it alphabetically by the 'name' column,
    and saves it to a new file.
    """
    try:
        print(f"Reading data from '{input_path}'...")
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"Error: The input file '{input_path}' was not found.")
        print("Please make sure the enrichment script has been run and the file exists.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while reading the CSV: {e}")
        sys.exit(1)

    # Ensure the 'name' column exists
    if 'name' not in df.columns:
        print(f"Error: The required column 'name' was not found in '{input_path}'.")
        sys.exit(1)

    print("Sorting data alphabetically by business name...")
    df_sorted = df.sort_values(by='name', ascending=True, inplace=False)

    try:
        print(f"Saving sorted data to '{output_path}'...")
        df_sorted.to_csv(output_path, index=False)
        print("Done. The file is ready for your manual review.")
    except Exception as e:
        print(f"An error occurred while saving the new CSV: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sort_and_save_csv(INPUT_FILE, OUTPUT_FILE) 