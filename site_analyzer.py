import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from urllib.parse import urljoin, urlparse
import re
import time
import sys

# --- Configuration ---
INPUT_FILE = 'final_call_list.csv'
OUTPUT_FILE = 'fully_enriched_call_list.csv'
TEST_MODE = False  # Set to False to run on the full list
TEST_LIMIT = 5    # Number of records to process in test mode

# --- Tech Stack Signatures ---
TECH_SIGNATURES = {
    'WordPress': ['/wp-content/', '/wp-includes/'],
    'Shopify': ['cdn.shopify.com', 'myshopify.com'],
    'Squarespace': ['squarespace.com'],
    'Wix': ['wix.com'],
    'HubSpot': ['hs-scripts.com', 'forms.hsforms.com'],
    'Google Analytics': ['google-analytics.com/ga.js', 'gtag(']
}

def setup_driver():
    """Sets up the undetected_chromedriver."""
    print("Setting up Selenium WebDriver...")
    options = uc.ChromeOptions()
    # When running the full script, headless is much faster.
    # For testing, we want to see the browser.
    if not TEST_MODE:
         options.add_argument('--headless')
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.set_page_load_timeout(15) # Slightly shorter timeout
    return driver

def get_internal_links(driver, base_url):
    """Finds links on the current page that point to the same website."""
    links = set()
    base_netloc = urlparse(base_url).netloc
    keywords = ['about', 'contact', 'team', 'staff', 'service']
    
    for a in driver.find_elements(By.TAG_NAME, 'a'):
        href = a.get_attribute('href')
        if href:
            try:
                parsed_href = urlparse(href)
                # Check if it's an internal link and contains a keyword
                if parsed_href.netloc == base_netloc and any(keyword in href for keyword in keywords):
                    links.add(href)
            except Exception:
                continue # Ignore malformed URLs
    return list(links)

def analyze_website(driver, url):
    """
    Visits a website, finds key internal pages, and scrapes aggregated data.
    **Now with added support for legacy HTML framesets.**
    """
    wait = WebDriverWait(driver, 10)
    full_source = ""
    full_text = ""
    
    # --- Page Loading and Content Gathering ---
    try:
        print(f" - Navigating to homepage: {url}")
        driver.get(url)
        time.sleep(1) # Allow for redirects/settling

        # **FIX 3: Handle websites using Framesets**
        try:
            frames = driver.find_elements(By.TAG_NAME, 'frame')
            if frames:
                print(f"   - Legacy frameset detected. Analyzing {len(frames)} frames.")
                for i in range(len(frames)):
                    try:
                        driver.switch_to.frame(i)
                        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                        full_source += driver.page_source
                        full_text += driver.find_element(By.TAG_NAME, 'body').text
                    except (WebDriverException, TimeoutException) as e:
                        print(f"     - Could not analyze frame {i}. Error: {type(e).__name__}")
                    finally:
                        # CRITICAL: Always switch back to the main document
                        driver.switch_to.default_content()
            else:
                # Standard page: wait for body and get content
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                full_source = driver.page_source
                full_text = driver.find_element(By.TAG_NAME, 'body').text
        
        except (WebDriverException, TimeoutException) as e:
            # Fallback if the body/frame check itself fails
            print(f" - WARNING: Initial page content analysis failed. Error: {type(e).__name__}")
            full_source = driver.page_source # Last resort: get what we can
            
        if not full_source:
             print(f" - FATAL: Could not retrieve any content from {url}.")
             return {'contacts': 'N/A', 'emails': 'N/A', 'tech_stack': 'N/A', 'social_links': 'N/A'}

        # --- Sub-page analysis ---
        internal_links_to_visit = get_internal_links(driver, url)
        print(f" - Found {len(internal_links_to_visit)} key internal pages to analyze.")
        for link in internal_links_to_visit[:2]: # Limit to 2 pages for efficiency
            try:
                print(f" - Analyzing sub-page: {link}")
                driver.get(link)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                full_source += driver.page_source
                full_text += driver.find_element(By.TAG_NAME, 'body').text
            except (WebDriverException, TimeoutException) as e:
                print(f"   - Could not load sub-page {link}. Error: {type(e).__name__}")
                continue
                
    except (WebDriverException, TimeoutException) as e:
        print(f" - FATAL: Could not navigate to {url}. Error: {type(e).__name__}")
        return {'contacts': 'N/A', 'emails': 'N/A', 'tech_stack': 'N/A', 'social_links': 'N/A'}

    # --- Analysis on Aggregated Data ---
    
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', full_source)
    unique_emails = sorted(list(set(e.lower() for e in emails)))

    tech_stack = []
    for tech, signatures in TECH_SIGNATURES.items():
        if any(sig in full_source for sig in signatures):
            tech_stack.append(tech)
    
    social_links = re.findall(r'https?://(?:www\.)?(?:linkedin\.com/company/[^"\']+)|(?:facebook\.com/[^"\']+)|(?:twitter\.com/[^"\']+)', full_source)
    unique_socials = sorted(list(set(social_links)))

    # **FIX 2: Intelligent Contact Filtering**
    contacts = []
    contact_keywords = ['owner', 'founder', 'ceo', 'manager', 'president', 'principal']
    junk_keywords = ['entity', 'subsidiary', 'third-party', 'ownership', 'affiliate']
    
    sentences = re.split(r'[\n.!?]', full_text)
    for sentence in sentences:
        for keyword in contact_keywords:
            if keyword in sentence.lower():
                clean_sentence = ' '.join(sentence.strip().split())
                
                # Check 1: Is it a reasonable length?
                if not (5 < len(clean_sentence) < 300):
                    continue
                
                # Check 2: Does it contain junk words?
                if any(junk in clean_sentence.lower() for junk in junk_keywords):
                    continue
                
                # Check 3: Does it likely refer to a person? (Look for capitalized words)
                has_proper_noun = any(word.istitle() and word.lower() != keyword for word in clean_sentence.split())
                if has_proper_noun:
                    contacts.append(f"{keyword.title()}: {clean_sentence}")
    
    return {
        'emails': ', '.join(unique_emails) if unique_emails else 'N/A',
        'tech_stack': ', '.join(sorted(list(set(tech_stack)))) if tech_stack else 'N/A',
        'social_links': ', '.join(unique_socials) if unique_socials else 'N/A',
        'contacts': ' | '.join(list(set(contacts))) if contacts else 'N/A'
    }

def main():
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: Input file '{INPUT_FILE}' not found. Please ensure it exists.")
        sys.exit(1)

    if TEST_MODE:
        print(f"--- RUNNING IN TEST MODE: Processing first {TEST_LIMIT} records ---")
        df = df.head(TEST_LIMIT)

    driver = setup_driver()
    
    results = []
    for index, row in df.iterrows():
        print(f"\nProcessing ({index + 1}/{len(df)}): {row['name']}")
        website_url = row.get('website')

        if pd.notna(website_url) and website_url.startswith('http'):
            analysis_data = analyze_website(driver, website_url)
        else:
            print(f" - Skipping due to invalid or missing website URL.")
            analysis_data = {'contacts': 'N/A', 'emails': 'N/A', 'tech_stack': 'N/A', 'social_links': 'N/A'}
        
        results.append(analysis_data)
        
    driver.quit()

    results_df = pd.DataFrame(results, index=df.index)
    df_enriched = df.copy()
    for col in results_df.columns:
        df_enriched[col] = results_df[col]
        
    df_enriched.to_csv(OUTPUT_FILE, index=False)
    print(f"\nEnrichment complete. Saved results to '{OUTPUT_FILE}'")

if __name__ == "__main__":
    main() 