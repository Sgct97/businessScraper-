import pandas as pd
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- Configuration ---
OUTPUT_CSV = 'businesses.csv'
PAGES_TO_SCRAPE = 10  # Set how many pages to scrape for each category
AREA_CODE_FILTER = '(727)'

CATEGORIES = [
    "Accountants", "Financial Advisors", "Bookkeeping Services", "Tax Return Preparation",
    "Lawyers", "Insurance", "Real Estate Agents", "Mortgage Brokers", "Marketing Agencies",
    "IT Services", "Web Designers", "Graphic Designers", "Printing Services", "Architects",
    "Engineers", "Contractors", "Electricians", "Plumbers", "HVAC", "Roofing Contractors",
    "Landscaping", "Cleaning Services", "Security Services", "Business Consultants", "Photographers"
]
BASE_URL = "https://www.yellowpages.com/pinellas-county-fl/"

def setup_driver():
    """Sets up the undetected_chromedriver."""
    print("Setting up Selenium WebDriver...")
    options = uc.ChromeOptions()
    # options.add_argument('--headless') # Run in headless mode if you don't need to see the browser
    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver

def scrape_page(driver):
    """Scrapes all business listings from the current page."""
    results = []
    try:
        listings = driver.find_elements(By.CSS_SELECTOR, 'div.v-card')
        for listing in listings:
            try:
                name = listing.find_element(By.CSS_SELECTOR, 'a.business-name span').text
                phone_element = listing.find_element(By.CSS_SELECTOR, 'div.phones.phone.primary')
                phone = phone_element.text if phone_element else 'N/A'

                if AREA_CODE_FILTER not in phone:
                    continue

                street = listing.find_element(By.CSS_SELECTOR, 'div.street-address').text
                locality = listing.find_element(By.CSS_SELECTOR, 'div.locality').text
                address = f"{street}, {locality}"
                category_tags = listing.find_elements(By.CSS_SELECTOR, 'div.categories a')
                category = category_tags[0].text if category_tags else 'N/A'

                results.append([name, phone, address, locality, category])
            except NoSuchElementException:
                continue # Skip if a card is missing some info
    except Exception as e:
        print(f"An error occurred while scraping the page: {e}")
    return results


def main():
    driver = setup_driver()
    wait = WebDriverWait(driver, 10)
    all_businesses = []
    
    print("Starting the scraping process...")

    for category in CATEGORIES:
        print(f"\n--- Scraping Category: {category} ---")
        url = f"{BASE_URL}{category.replace(' ', '-')}"
        
        try:
            driver.get(url)
        except Exception as e:
            print(f"Could not load page for {category}. Error: {e}")
            continue

        for page in range(1, PAGES_TO_SCRAPE + 1):
            print(f"Scraping page {page}/{PAGES_TO_SCRAPE}...")
            
            # Wait for the results to be present
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.v-card')))
            except TimeoutException:
                print("Timed out waiting for page content. Moving to next category.")
                break

            page_results = scrape_page(driver)
            all_businesses.extend(page_results)
            print(f"Found {len(page_results)} new businesses on this page. Total so far: {len(all_businesses)}")
            
            # Navigate to the next page
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, 'a.next.ajax-page')
                if next_button.is_displayed() and next_button.is_enabled():
                    next_button.click()
                    time.sleep(3) # Wait for page to load
                else:
                    print("Next button not found or disabled. End of results for this category.")
                    break
            except NoSuchElementException:
                print("No 'Next' button found. End of results for this category.")
                break
    
    driver.quit()

    if all_businesses:
        df = pd.DataFrame(all_businesses, columns=['name', 'phone', 'address', 'locality', 'category'])
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"\nScraping complete. Saved {len(df)} businesses to {OUTPUT_CSV}")
    else:
        print("\nScraping complete. No businesses were found.")


if __name__ == "__main__":
    main() 