import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_webdriver():
    """Sets up the undetected ChromeDriver."""
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver

def get_sunbiz_details_user_flow(driver, business_name):
    """
    This function follows the user's explicit navigation instructions.
    """
    status = "ERROR"
    officers = []
    HOME_URL = "https://dos.fl.gov/sunbiz/"

    try:
        logging.info(f"Navigating to Sunbiz home page: {HOME_URL}")
        driver.get(HOME_URL)
        wait = WebDriverWait(driver, 20)

        # Step 1: Click "Search Records" in the main navigation
        logging.info("Finding and clicking 'Search Records'...")
        search_records_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Search Records")))
        search_records_link.click()

        # Step 2: On the next page, click "By Name" using the user's selector path
        logging.info("Finding and clicking 'By Name' link using user's selector...")
        by_name_selector = "#content > div.row > div.page-content.col-md-8 > ul:nth-child(5) > li:nth-child(1) > a"
        by_name_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, by_name_selector)))
        by_name_link.click()

        # Step 3: The form is inside an iframe. We must switch to it first.
        logging.info("Switching to iframe to access the search form...")
        # It's good practice to wait for the iframe to be present before switching
        iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(iframe)

        # Step 4: Now on the correct search page, perform the search
        logging.info("Inside iframe. Finding form elements...")
        search_box = wait.until(EC.presence_of_element_located((By.ID, "SearchTerm")))
        search_button = wait.until(EC.element_to_be_clickable((By.ID, "searchByName")))
        
        search_box.send_keys(business_name)
        search_button.click()
        
        # Step 5: After search, we must switch back to the main content to read results
        logging.info("Switching back to default content to read results...")
        driver.switch_to.default_content()
        
        # Step 6: Process results
        logging.info("Search submitted. Waiting for results list...")
        wait.until(EC.presence_of_element_located((By.ID, "search-results")))
        
        detail_links = driver.find_elements(By.CSS_SELECTOR, "td > a")
        if not detail_links:
            return "No Results Found", []
        
        # We need to get the URL here because the page context will be lost
        detail_url = detail_links[0].get_attribute('href')
        
        # The rest of the logic can now proceed
        logging.info(f"Navigating to detail page: {detail_url}")
        driver.get(detail_url)
        
        # Step 7: Parse the detail page
        logging.info("Parsing detail page...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.corporationName")))
        
        try:
            status_element = driver.find_element(By.XPATH, "//label[contains(text(),'Status')]/following-sibling::span")
            status = status_element.text.strip()
        except NoSuchElementException:
            status = "Unknown"
            
        try:
            officer_elements = driver.find_elements(By.XPATH, "//div[div[@class='label' and contains(text(), 'Title')]]/div[@class='value']")
            for elem in officer_elements:
                name = elem.text.strip()
                if name:
                    officers.append(name.title())
        except NoSuchElementException:
            pass # No officers found is acceptable

        return status, officers

    except Exception as e:
        logging.critical(f"A critical error occurred: {e}")
        driver.save_screenshot('user_flow_error.png')
        return "Critical Error", []

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    driver = None
    try:
        driver = setup_webdriver()
        test_business = "Nemes & West"
        
        status, officers = get_sunbiz_details_user_flow(driver, test_business)
        
        print("\n--- RESULTS (USER FLOW) ---")
        print(f"Business Searched: {test_business}")
        print(f"Status:            {status}")
        if officers:
            print(f"Officers:          {', '.join(officers)}")
        else:
            print("Officers:          None")
        print("---------------------------")

    finally:
        if driver:
            logging.info("Quitting driver.")
            driver.quit() 