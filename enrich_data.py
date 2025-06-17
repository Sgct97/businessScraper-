import pandas as pd
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from urllib.parse import quote_plus

# --- Configuration ---
INPUT_FILE = 'prioritized_call_list.xlsx'
OUTPUT_CSV = 'enriched_businesses.csv'
BASE_SEARCH_URL = "https://www.yellowpages.com/search?search_terms={search_term}&geo_location_terms={location}"
TEST_MODE = False # Set to False to run on the full list
TEST_LIMIT = 5 # Number of records to process in test mode

def setup_driver():
    """Sets up the undetected_chromedriver."""
    print("Setting up Selenium WebDriver...")
    options = uc.ChromeOptions()
    # options.add_argument('--headless')
    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver

def find_website(driver, business_name, location):
    """Performs a targeted search on Yellow Pages to find the business website."""
    search_term = quote_plus(business_name)
    location_term = quote_plus(location)
    search_url = BASE_SEARCH_URL.format(search_term=search_term, location=location_term)
    
    driver.get(search_url)
    wait = WebDriverWait(driver, 10)

    try:
        # Step 1: Find the first business listing link and click it
        print(f" - Searching for '{business_name}'...")
        first_listing = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.result a.business-name')))
        print(f" - Clicking into details for '{business_name}'...")
        first_listing.click()
        
        # Step 2: On the details page, find the website link
        print(f" - Looking for website link on details page...")
        website_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.track-visit-website')))
        website = website_link.get_attribute('href')
        print(f" - Found website: {website}")
        return website
    except (NoSuchElementException, TimeoutException):
        print(f" - Could not find website for {business_name} after clicking into details.")
        return 'N/A'
    except Exception as e:
        print(f" - An unexpected error occurred while processing {business_name}: {e}")
        return 'N/A'

def main():
    print(f"Reading businesses from {INPUT_FILE}...")
    try:
        df = pd.read_excel(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: The input file '{INPUT_FILE}' was not found.")
        return
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # Trim the dataframe if in test mode
    if TEST_MODE:
        print(f"--- RUNNING IN TEST MODE: Processing first {TEST_LIMIT} records ---")
        df = df.head(TEST_LIMIT)

    # Assume columns are named 'name' and 'locality' or similar.
    # Adjust these if the column names in your Excel file are different.
    if 'name' not in df.columns or 'locality' not in df.columns:
        print("Error: Input file must contain 'name' and 'locality' columns.")
        print(f"Found columns: {df.columns.tolist()}")
        return

    driver = setup_driver()
    websites = []
    
    print("Starting data enrichment process...")
    for index, row in df.iterrows():
        business_name = row['name']
        location = row['locality']
        print(f"Processing ({index + 1}/{len(df)}): {business_name}...")
        
        website = find_website(driver, business_name, location)
        websites.append(website)
        time.sleep(1) # Small delay between requests

    driver.quit()

    df['website'] = websites
    df.to_csv(OUTPUT_CSV, index=False)
    
    print(f"\nEnrichment complete. Saved {len(df)} businesses with website information to {OUTPUT_CSV}")

if __name__ == "__main__":
    main() 