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

def get_sunbiz_details_final_click(driver, business_name):
    """
    Final version using the correct button selector provided by the user.
    """
    status = "ERROR"
    officers = []
    HOME_URL = "https://dos.fl.gov/sunbiz/"
    BY_NAME_SELECTOR = "#content > div.row > div.page-content.col-md-8 > ul:nth-child(5) > li:nth-child(1) > a"
    # Correct button selector based on user's HTML
    SEARCH_BUTTON_SELECTOR = "//input[@type='submit' and @value='Search Now']"

    try:
        logging.info(f"Navigating to Sunbiz home page: {HOME_URL}")
        driver.get(HOME_URL)
        wait = WebDriverWait(driver, 20)

        logging.info("Clicking 'Search Records'...")
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Search Records"))).click()

        logging.info("Navigating to 'By Name' search page...")
        by_name_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, BY_NAME_SELECTOR)))
        target_url = by_name_link.get_attribute("href")
        driver.get(target_url)

        logging.info("On search page, waiting for form...")
        search_box = wait.until(EC.visibility_of_element_located((By.ID, "SearchTerm")))
        
        logging.info(f"Typing '{business_name}'...")
        search_box.send_keys(business_name)
        
        logging.info("Finding and clicking the correct 'Search Now' button...")
        search_button = wait.until(EC.element_to_be_clickable((By.XPATH, SEARCH_BUTTON_SELECTOR)))
        search_button.click()
        
        logging.info("Waiting for results list...")
        wait.until(EC.presence_of_element_located((By.ID, "search-results")))
        
        detail_links = driver.find_elements(By.CSS_SELECTOR, "td > a")
        if not detail_links:
            return "No Results Found", []
        
        detail_url = detail_links[0].get_attribute('href')
        logging.info(f"Navigating to detail page: {detail_url}")
        driver.get(detail_url)
        
        logging.info("Parsing detail page...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.corporationName")))
        
        try:
            status_element = driver.find_element(By.XPATH, "//label[contains(text(),'Status')]/following-sibling::span")
            status = status_element.text.strip()
        except:
            status = "Unknown"
            
        try:
            # This is a more direct way to get all the names under "Officer/Director Detail"
            officer_section = wait.until(EC.presence_of_element_located((By.XPATH, "//div[.='Officer/Director Detail']")))
            name_elements = officer_section.find_elements(By.XPATH, "./following-sibling::div//div[@class='value']")

            for elem in name_elements:
                name = elem.text.strip()
                if name:
                    officers.append(name.title())
        except:
            pass

        return status, officers

    except Exception as e:
        logging.critical(f"A critical error occurred: {e}")
        driver.save_screenshot('final_click_error.png')
        return "Critical Error", []

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    driver = None
    try:
        driver = setup_webdriver()
        test_business = "Nemes & West Accountants Inc"
        
        status, officers = get_sunbiz_details_final_click(driver, test_business)
        
        print("\n--- RESULTS (FINAL CLICK ATTEMPT) ---")
        print(f"Business Searched: {test_business}")
        print(f"Status:            {status}")
        if officers:
            print(f"Officers:          {', '.join(officers)}")
        else:
            print("Officers:          None")
        print("-------------------------------------")

    finally:
        if driver:
            logging.info("Quitting driver.")
            driver.quit() 