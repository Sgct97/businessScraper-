import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_webdriver():
    """Sets up the undetected ChromeDriver."""
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver

def get_sunbiz_details_nav_by_href(driver, business_name):
    """
    This function implements the new strategy: navigating directly by href
    instead of relying on .click().
    """
    status = "ERROR"
    officers = []
    HOME_URL = "https://dos.fl.gov/sunbiz/"
    BY_NAME_SELECTOR = "#content > div.row > div.page-content.col-md-8 > ul:nth-child(5) > li:nth-child(1) > a"
    
    try:
        logging.info(f"Navigating to Sunbiz home page: {HOME_URL}")
        driver.get(HOME_URL)
        wait = WebDriverWait(driver, 20)

        # Step 1: Click "Search Records"
        logging.info("Finding and clicking 'Search Records'...")
        search_records_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Search Records")))
        search_records_link.click()

        # Step 2: NEW STRATEGY - Find the "By Name" link and get its URL
        logging.info("Finding 'By Name' link to get its href...")
        by_name_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, BY_NAME_SELECTOR)))
        target_url = by_name_link.get_attribute("href")
        logging.info(f"Found target URL. Navigating directly to: {target_url}")
        driver.get(target_url)

        # Step 3: Now on the correct search page, perform the search
        logging.info("On final search page. Finding form elements...")
        search_box = wait.until(EC.visibility_of_element_located((By.ID, "SearchTerm")))
        search_button = wait.until(EC.element_to_be_clickable((By.ID, "searchByName")))
        
        logging.info(f"Typing '{business_name}' and clicking search.")
        search_box.send_keys(business_name)
        search_button.click()
        
        # Step 4: Process results
        logging.info("Waiting for results list...")
        wait.until(EC.presence_of_element_located((By.ID, "search-results")))
        
        detail_links = driver.find_elements(By.CSS_SELECTOR, "td > a")
        if not detail_links:
            return "No Results Found", []
        
        detail_url = detail_links[0].get_attribute('href')
        logging.info(f"Navigating to detail page: {detail_url}")
        driver.get(detail_url)
        
        # Step 5: Parse the detail page
        logging.info("Parsing detail page...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.corporationName")))
        
        try:
            status_element = driver.find_element(By.XPATH, "//label[contains(text(),'Status')]/following-sibling::span")
            status = status_element.text.strip()
        except:
            status = "Unknown"
            
        try:
            officer_elements = driver.find_elements(By.XPATH, "//div[div[@class='label' and contains(text(), 'Title')]]/div[@class='value']")
            for elem in officer_elements:
                name = elem.text.strip()
                if name:
                    officers.append(name.title())
        except:
            pass

        return status, officers

    except Exception as e:
        logging.critical(f"A critical error occurred: {e}")
        driver.save_screenshot('href_nav_error.png')
        return "Critical Error", []

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    driver = None
    try:
        driver = setup_webdriver()
        test_business = "Nemes & West"
        
        status, officers = get_sunbiz_details_nav_by_href(driver, test_business)
        
        print("\n--- RESULTS (NAVIGATE BY HREF) ---")
        print(f"Business Searched: {test_business}")
        print(f"Status:            {status}")
        if officers:
            print(f"Officers:          {', '.join(officers)}")
        else:
            print("Officers:          None")
        print("----------------------------------")

    finally:
        if driver:
            logging.info("Quitting driver.")
            driver.quit() 