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
import os

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
    **Now with added support for legacy HTML framesets and footer-first analysis.**
    """
    wait = WebDriverWait(driver, 10)
    full_source = ""
    full_text = ""
    
    # --- Page Loading and Initial Content Gathering ---
    try:
        print(f" - Navigating to homepage: {url}")
        driver.get(url)
        time.sleep(2) # Increased sleep to allow for JS-heavy sites to settle.

        # Handle websites using Framesets first
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
                    driver.switch_to.default_content()
        else:
            # Standard page: wait for body and get content
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            full_source = driver.page_source
            full_text = driver.find_element(By.TAG_NAME, 'body').text

    except (WebDriverException, TimeoutException) as e:
        print(f" - FATAL: Could not load homepage {url}. Error: {type(e).__name__}")
        return {'contacts': 'N/A', 'emails': 'N/A', 'tech_stack': 'N/A', 'social_links': 'N/A'}

    if not full_source:
         print(f" - FATAL: Could not retrieve any content from {url}.")
         return {'contacts': 'N/A', 'emails': 'N/A', 'tech_stack': 'N/A', 'social_links': 'N/A'}

    # --- NEW: Footer-First Analysis ---
    try:
        footer = driver.find_element(By.TAG_NAME, 'footer')
        print("   - Found footer. Prioritizing for analysis.")
        # Add footer content to the top of our text for priority.
        full_text = footer.text + "\n" + full_text
        full_source = footer.get_attribute('innerHTML') + "\n" + full_source
    except Exception:
        print("   - No explicit <footer> tag found. Analyzing full page content.")
        pass # It's okay if there's no footer tag, we'll just analyze the whole page.

    # --- Sub-page analysis (now supplemental) ---
    try:
        internal_links_to_visit = get_internal_links(driver, url)
        if internal_links_to_visit:
            print(f" - Found {len(internal_links_to_visit)} key internal pages to supplement analysis.")
            for link in internal_links_to_visit[:2]: # Limit to 2 pages for efficiency
                try:
                    print(f"   - Analyzing sub-page: {link}")
                    driver.get(link)
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    full_source += driver.page_source
                    full_text += driver.find_element(By.TAG_NAME, 'body').text
                except (WebDriverException, TimeoutException) as e:
                    print(f"     - Could not load sub-page {link}. Error: {type(e).__name__}")
                    continue
    except Exception as e:
        print(f"   - Error during sub-page analysis: {type(e).__name__}")

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
    # --- Intelligent Processing: Only target records missing emails from the output file ---
    if not os.path.exists(OUTPUT_FILE):
        print(f"Error: Output file '{OUTPUT_FILE}' not found. This file is required to run the script in its current mode.")
        print("Please run with an existing enriched file or modify the script to start from scratch.")
        sys.exit(1)

    print(f"--- Loading existing data from '{OUTPUT_FILE}' ---")
    try:
        df_master = pd.read_csv(OUTPUT_FILE)
    except Exception as e:
        print(f"Error reading '{OUTPUT_FILE}': {e}")
        sys.exit(1)

    # Ensure 'emails' column exists and fill any actual NaN values with a placeholder for consistent string checks
    if 'emails' not in df_master.columns:
        df_master['emails'] = 'N/A'
    df_master['emails'] = df_master['emails'].fillna('N/A')

    # Define what is considered an "empty" email entry
    is_placeholder = df_master['emails'].str.strip().str.upper() == 'N/A'
    is_empty_string = df_master['emails'].str.strip() == ''
    
    df_to_process = df_master[is_placeholder | is_empty_string].copy()

    if df_to_process.empty:
        print("--- No records with missing emails found. Enrichment is complete. ---")
        return

    print(f"--- Found {len(df_to_process)} records with missing emails to process. ---")

    if TEST_MODE:
        print(f"--- RUNNING IN TEST MODE: Processing first {TEST_LIMIT} records ---")
        df_to_process = df_to_process.head(TEST_LIMIT)
        if df_to_process.empty:
            print("--- No records to process in test mode. ---")
            return

    driver = setup_driver()
    
    # --- Main Processing Loop with In-place Update ---
    for index, row in df_to_process.iterrows():
        # Use .get() for safer access in case a column is missing
        print(f"\nProcessing record for: {row.get('name', 'N/A')} (Index: {index})")
        website_url = row.get('website')

        if pd.notna(website_url) and isinstance(website_url, str) and website_url.startswith('http'):
            analysis_data = analyze_website(driver, website_url)
        else:
            print(f" - Skipping due to invalid or missing website URL: '{website_url}'")
            analysis_data = {'contacts': 'N/A', 'emails': 'N/A', 'tech_stack': 'N/A', 'social_links': 'N/A'}
        
        # Update the master DataFrame in memory
        for col, value in analysis_data.items():
            df_master.loc[index, col] = value
        
        # Save the entire updated DataFrame back to the CSV.
        # This is a safe way to do incremental, in-place updates.
        try:
            df_master.to_csv(OUTPUT_FILE, index=False)
            print(f"   - Successfully updated and saved record {index}.")
        except Exception as e:
            print(f"   - CRITICAL: Could not save progress for record {index}. Error: {e}")
            
    driver.quit()

    print(f"\nEnrichment complete. All targeted records have been processed and saved to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    main() 