import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_yellow_pages():
    options = uc.ChromeOptions()
    # options.add_argument('--headless') # To see the browser, comment this line out
    driver = uc.Chrome(options=options)

    # Restoring the full list of targeted search terms
    search_terms = [
        "Accountants", "Financial Advisors", "Bookkeeping Services",
        "Doctors", "Dentists", "Medical Clinics", "Chiropractors", "Physical Therapy", "Wellness Center",
        "Boutiques", "Clothing Stores", "Gift Shops", "Furniture Stores",
        "Restaurants", "Cafes", "Bars", "Hotels",
        "Law Firms", "Insurance Agencies", "Real Estate Agents", "Marketing Agencies",
        "Plumbers", "Electricians", "HVAC Contractors", "Landscaping Services", "Pool Cleaning Services", "Roofing Contractors"
    ]
    # Targeting Pinellas County specifically
    location = "Pinellas County, FL"
    base_url = "https://www.yellowpages.com"
    all_businesses = []

    for term in search_terms:
        print(f"Scraping {term} in {location}...")
        driver.get(f"{base_url}/search?search_terms={term}&geo_location_terms={location}")
        
        # Expanding results to 10 pages per term for a full run
        max_pages_per_term = 10
        page = 1
        while page <= max_pages_per_term:
            print(f"Scraping page {page} for {term}...")
            try:
                # Wait for the search results to load
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "v-card"))
                )
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                cards = soup.find_all('div', class_='v-card')

                if not cards:
                    print("No business cards found.")
                    break

                for card in cards:
                    phone_number = card.find('div', class_='phones phone primary').text.strip() if card.find('div', class_='phones phone primary') else 'N/A'
                    
                    # Filtering for 727 area code
                    if not phone_number.startswith('(727)'):
                        continue

                    all_businesses.append({
                        'name': card.find('a', class_='business-name').text.strip() if card.find('a', class_='business-name') else 'N/A',
                        'phone': phone_number,
                        'address': card.find('div', class_='street-address').text.strip() if card.find('div', class_='street-address') else 'N/A',
                        'locality': card.find('div', class_='locality').text.strip() if card.find('div', class_='locality') else 'N/A',
                        'category': term
                    })
                
                # Check for the 'next' button and click it
                next_button = driver.find_elements(By.CSS_SELECTOR, 'a.next.ajax-page')
                if next_button:
                    page += 1
                    if page > max_pages_per_term:
                        break
                    driver.execute_script("arguments[0].click();", next_button[0])
                    time.sleep(5)  # Wait for the next page to load
                else:
                    print("No next page button found.")
                    break
            
            except Exception as e:
                print(f"An error occurred: {e}")
                break

    driver.quit()
    return all_businesses

def main():
    businesses = scrape_yellow_pages()
    if businesses:
        df = pd.DataFrame(businesses)
        df.to_csv('businesses.csv', index=False)
        print(f"Scraped {len(businesses)} businesses and saved to businesses.csv")
    else:
        print("No businesses were scraped.")

if __name__ == "__main__":
    main() 