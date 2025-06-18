import pandas as pd
import sys

# --- Configuration ---
INPUT_FILE = 'sorted_businesses_for_review.csv'
OUTPUT_FILE = 'final_call_list.csv'

def finalize_business_list(input_path, output_path):
    """
    Reads a manually cleaned CSV, de-duplicates it,
    handles multi-location businesses by keeping the highest-scored one,
    sorts by AI score, and saves the final, ready-to-use call list.
    """
    try:
        print(f"Reading manually cleaned data from '{input_path}'...")
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"Error: The input file '{input_path}' was not found.")
        print("Please make sure you have saved the reviewed file.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while reading the CSV: {e}")
        sys.exit(1)

    print(f"Starting with {len(df)} businesses after manual review.")

    # --- Step 1: Handle Straight Duplicates ---
    # Drop exact duplicates based on name and phone number first.
    df.drop_duplicates(subset=['name', 'phone'], inplace=True)
    print(f"List reduced to {len(df)} after removing straight duplicates.")

    # --- Step 2: Handle Multi-Location Businesses (Keep Highest Score) ---
    # First, sort the entire dataframe by 'ai_score' in descending order.
    df_sorted = df.sort_values(by='ai_score', ascending=False)
    
    # Now, drop duplicates based on just the 'name' column. Because the list is
    # already sorted by score, the `keep='first'` argument will automatically
    # preserve the entry with the highest score for each business name.
    df_final = df_sorted.drop_duplicates(subset=['name'], keep='first')
    print(f"List reduced to {len(df_final)} after consolidating multi-location businesses.")

    # --- Step 3: Final Sort & Save ---
    # The list is already sorted, so we can just save it.
    try:
        print(f"Saving the final, cleaned call list to '{output_path}'...")
        df_final.to_csv(output_path, index=False)
        print(f"Success! Your final call list with {len(df_final)} businesses is ready in '{output_path}'.")
    except Exception as e:
        print(f"An error occurred while saving the final CSV: {e}")
        sys.exit(1)

if __name__ == "__main__":
    finalize_business_list(INPUT_FILE, OUTPUT_FILE) 