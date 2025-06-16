import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import numpy as np
import time

# --- Configuration ---
INPUT_CSV = 'businesses.csv'
OUTPUT_XLSX = 'prioritized_call_list.xlsx'
CALLS_PER_DAY = 50
SUNBIZ_SEARCH_URL = "https://search.sunbiz.org/Inquiry/CorporationRegistration/ByName"

# --- Scoring Weights ---
CATEGORY_SCORES = {
    'Accountants': 30, 'Financial Advisors': 30, 'Bookkeeping Services': 25,
    'Tax Return Preparation': 25, 'Lawyers': 20, 'Plumbers': 10,
    'Electricians': 10, 'Contractors': 10, 'Landscaping': 10,
    'Restaurants': -20, 'Pizza': -25, 'Hair Salons': -10,
    'Nail Salons': -10, 'default': 0
}

NAME_KEYWORDS = {"inc": 15, "llc": 15, "p.a.": 15, "pa": 15, "group": 15, "associates": 15, "company": 10, "corp": 15}
ADDRESS_KEYWORDS = {"suite": 10, "ste": 10, "floor": 10, "#": 5, " bldg": 10}
NATIONAL_CHAINS = ["h&r block", "jackson hewitt", "edward jones", "morgan stanley", "wells fargo", "raymond james", "ameriprise", "regions financial", "rbc wealth", "subway", "mcdonald's", "starbucks"]
OWNER_FOUND_SCORE = 40
INACTIVE_PENALTY = -1000

def get_sunbiz_details_selenium(driver, business_name, wait):
    """
    The final, working Selenium function to get details from Sunbiz.
    Adapted from the successful test script.
    """
    status = "ERROR"
    officers = []
    HOME_URL = "https://dos.fl.gov/sunbiz/"
    BY_NAME_SELECTOR = "#content > div.row > div.page-content.col-md-8 > ul:nth-child(5) > li:nth-child(1) > a"
    SEARCH_BUTTON_SELECTOR = "//input[@type='submit' and @value='Search Now']"
    
    try:
        driver.get(HOME_URL)
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Search Records"))).click()
        by_name_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, BY_NAME_SELECTOR)))
        target_url = by_name_link.get_attribute("href")
        driver.get(target_url)

        search_box = wait.until(EC.visibility_of_element_located((By.ID, "SearchTerm")))
        search_box.send_keys(business_name)
        wait.until(EC.element_to_be_clickable((By.XPATH, SEARCH_BUTTON_SELECTOR))).click()
        
        wait.until(EC.presence_of_element_located((By.ID, "search-results")))

        # --- NEW: User's optimization to check status on results page ---
        try:
            # The status is in the 3rd column of the first result row
            status_cell = driver.find_element(By.CSS_SELECTOR, "#search-results tbody tr:first-child td:nth-child(3)")
            if "INACT" in status_cell.text:
                return "INACTIVE", [] # Return immediately, don't waste time clicking
        except (NoSuchElementException, TimeoutException):
            # If we can't find this for any reason, proceed as normal.
            pass
        # --- END NEW LOGIC ---

        detail_links = driver.find_elements(By.CSS_SELECTOR, "td > a")
        if not detail_links:
            return "No Results Found", []
        
        detail_url = detail_links[0].get_attribute('href')
        driver.get(detail_url)
        
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.corporationName")))
        
        try:
            status_element = driver.find_element(By.XPATH, "//label[contains(text(),'Status')]/following-sibling::span")
            status = status_element.text.strip()
        except NoSuchElementException:
            status = "Unknown"
            
        try:
            # --- NEW, CORRECT PARSING LOGIC BASED ON USER'S HTML ---
            # Find the parent div containing all officer details
            officer_section = driver.find_element(By.XPATH, "//div[@class='detailSection' and .//span[contains(text(), 'Officer/Director Detail')]]")
            # Get all the text within this section
            full_text = officer_section.text
            
            # Split the text into lines and clean them
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # Loop through the lines to find titles and their corresponding names
            for i, line in enumerate(lines):
                if line.startswith("Title"):
                    # The name is usually the next line, as it's just raw text
                    if i + 1 < len(lines):
                        potential_name = lines[i+1]
                        # A simple check to ensure it's a name and not an address line
                        if potential_name.isupper() and "," in potential_name:
                            officers.append(potential_name.title())

        except (NoSuchElementException, TimeoutException):
            pass # It's okay if a business has no listed officers

        return status, officers

    except Exception:
        # Don't log the full stack trace for a single failed lookup
        return "Scrape Error", []

def main():
    print("Loading data...")
    df = pd.read_csv('businesses.csv')
    df.columns = df.columns.str.strip()
    print(f"Loaded {len(df)} businesses.")

    df['ai_score'] = 0
    df['owner_name'] = ""
    df['sunbiz_status'] = ""
    df['is_chain'] = False

    # --- Set up Selenium WebDriver ---
    print("Setting up Selenium WebDriver...")
    driver = uc.Chrome(options=uc.ChromeOptions(), use_subprocess=True)
    wait = WebDriverWait(driver, 10) # Shorter wait time for main loop

    print("Starting enrichment process. This will be slow but accurate...")
    for index, row in df.iterrows():
        score = 0
        name_lower = str(row['name']).lower()
        
        score += CATEGORY_SCORES.get(str(row['category']), CATEGORY_SCORES['default'])
        if any(chain in name_lower for chain in NATIONAL_CHAINS):
            score += INACTIVE_PENALTY # Use the same penalty to filter chains
            df.at[index, 'is_chain'] = True
            status, owners = "N/A (Chain)", []
        else:
            status, owners = get_sunbiz_details_selenium(driver, row['name'], wait)
            if owners:
                score += OWNER_FOUND_SCORE
            if status == 'INACTIVE':
                score += INACTIVE_PENALTY
        
        df.at[index, 'owner_name'] = ', '.join(owners) if owners else ""
        df.at[index, 'sunbiz_status'] = status
        df.at[index, 'ai_score'] = score
        
        print(f"{index+1}/{len(df)}: {row['name'][:30]:<30} | Status: {status:<10} | Owner(s): {len(owners)}")

    driver.quit()
    print("\nEnrichment complete.")
    
    # --- Final Processing ---
    df_sorted = df.sort_values(by='ai_score', ascending=False).reset_index(drop=True)
    df_sorted['call_day'] = np.arange(len(df_sorted)) // 50 + 1
    df_sorted['status'] = "New"
    df_sorted['notes'] = ""
    
    final_cols = ['call_day', 'ai_score', 'sunbiz_status', 'status', 'notes', 'name', 'owner_name', 'phone', 'category', 'address', 'locality', 'is_chain']
    df_final = df_sorted[[c for c in final_cols if c in df_sorted.columns]]

    df_final.to_excel('prioritized_call_list.xlsx', index=False)
    print("Done! Saved to prioritized_call_list.xlsx")

if __name__ == "__main__":
    main() 