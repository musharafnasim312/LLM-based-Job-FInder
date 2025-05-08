import json
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

JOBS_DATA_FILE = os.path.join(os.path.dirname(__file__), 'jobs_data.json')


def save_jobs(jobs):
    """Saves the scraped jobs to a JSON file."""
    with open(JOBS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({'jobs': jobs}, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(jobs)} jobs to {JOBS_DATA_FILE}")

def load_scraped_data():
    """Loads scraped job data from the JSON file."""
    if not os.path.exists(JOBS_DATA_FILE):
        print(f"Data file not found: {JOBS_DATA_FILE}")
        return [] # Return empty list if file doesn't exist
    try:
        with open(JOBS_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('jobs', []) # Return the list of jobs, or empty list if key missing
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {JOBS_DATA_FILE}")
        return [] # Return empty list on error
    except Exception as e:
        print(f"An error occurred while loading data from {JOBS_DATA_FILE}: {e}")
        return []

def get_driver(headless=True):
    """Initializes and returns a Selenium WebDriver instance."""
    options = Options()
    if headless:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu') # Often recommended with headless
    options.add_argument('--no-sandbox') # Bypass OS security model, common in Docker/CI
    options.add_argument('--window-size=1920,1080')
    # The following line keeps the browser open after the script finishes
    options.add_experimental_option("detach", True)
    
    # Automatically downloads and manages ChromeDriver
    # This will use the correct driver for your installed Chrome version (e.g., 131.0.6778.86)
    try:
        # Let Selenium try to manage the driver automatically or find one on PATH
        # This is an alternative if ChromeDriverManager().install() is consistently failing.
        try:
            # Try with a basic service object first
            service = Service()
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e_service:
            print(f"Basic Service() init failed: {e_service}. Trying ChromeDriverManager().install() again as a fallback.")
            # Fallback to explicit ChromeDriverManager if basic Service() fails
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        print("WebDriver initialized. Browser window will remain open after script completion if not in headless mode.")
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        print("Please ensure Google Chrome is installed correctly.")
        print("If issues persist, try running: pip install --upgrade selenium webdriver-manager")
        return None


def scrape_indeed(position, location, max_pages=1):
    """Scrapes job listings from Indeed."""
    print(f"Scraping Indeed for '{position}' in '{location}'...")
    jobs = []
    # Run non-headless to see the browser, especially for debugging selectors
    driver = get_driver(headless=False) 
    if not driver:
        return jobs # WebDriver initialization failed

    base_url = "https://www.indeed.com/jobs?q={}&l={}&start={}"
    
    try:
        for page in range(max_pages):
            start = page * 10 # Indeed uses 10 listings per page
            url = base_url.format(position.replace(' ', '+'), location.replace(' ', '+'), start)
            print(f"Navigating to Indeed page {page+1}: {url}")
            driver.get(url)
            time.sleep(3) # Allow time for the page to load dynamically

            # Find all job cards on the page
            # Note: CSS Selectors are prone to change if Indeed updates its website structure.
            # If scraping fails, these selectors are the first thing to check and update.
            cards = driver.find_elements(By.CSS_SELECTOR, 'div.job_seen_beacon') # Common selector for job cards
            print(f"Found {len(cards)} job cards on Indeed page {page+1}")

            if not cards and page == 0: # Try to handle cookie consent pop-up if it appears
                try:
                    print("No job cards found, checking for cookie consent pop-up...")
                    cookie_button = driver.find_element(By.ID, "onetrust-accept-btn-handler") # Common ID for cookie accept
                    if cookie_button:
                        print("Attempting to click cookie consent button.")
                        cookie_button.click()
                        time.sleep(2) # Wait for pop-up to disappear
                        cards = driver.find_elements(By.CSS_SELECTOR, 'div.job_seen_beacon') # Retry finding cards
                        print(f"Found {len(cards)} job cards after handling cookie consent.")
                except Exception as e_cookie:
                    print(f"Could not find or click cookie consent button (this is okay if no pop-up was present): {e_cookie}")


            for card in cards:
                try:
                    title = card.find_element(By.CSS_SELECTOR, 'h2.jobTitle span').text.strip()
                    company = card.find_element(By.CSS_SELECTOR, 'span.companyName').text.strip()
                    loc = card.find_element(By.CSS_SELECTOR, 'div.companyLocation').text.strip()
                    
                    # Try to get summary from list items, otherwise take whole snippet
                    summary_elements = card.find_elements(By.CSS_SELECTOR, 'div.job-snippet ul li')
                    if summary_elements:
                         summary = '\n'.join([li.text.strip() for li in summary_elements])
                    else:
                        summary = card.find_element(By.CSS_SELECTOR, 'div.job-snippet').text.strip()

                    link_element = card.find_element(By.CSS_SELECTOR, 'a.jcs-JobTitle.tapItem') # More specific selector for link
                    link = link_element.get_attribute('href')

                    salary_elem = card.find_elements(By.CSS_SELECTOR, 'div.salary-snippet-container, div.estimated-salary, span.estimated-salary') # multiple selectors for salary
                    salary = salary_elem[0].text.strip() if salary_elem else 'Not specified'
                    
                    jobs.append({
                        'job_title': title,
                        'company': company,
                        'location': loc,
                        'salary': salary,
                        'description': summary,
                        'apply_link': link,
                        'source': 'indeed'
                    })
                except Exception as e:
                    print(f"Error extracting details from an Indeed job card: {e}")
    except Exception as e_outer:
        print(f"An error occurred during the Indeed scraping process: {e_outer}")
    finally:
        if driver:
            # driver.quit() will close the WebDriver session.
            # If "detach" option is True, the browser window itself will remain open.
            print("Finished scraping Indeed. WebDriver for Indeed will close, browser window might remain open.")
            driver.quit() 
    return jobs

def scrape_linkedin(position, location, max_pages=1):
    """Scrapes job listings from LinkedIn, including detailed descriptions."""
    print(f"Scraping LinkedIn for '{position}' in '{location}'...")
    jobs = []
    # Run non-headless to observe behavior, especially for debugging selectors
    driver = get_driver(headless=False) 
    if not driver:
        print("WebDriver initialization failed for LinkedIn.")
        return jobs

    base_url = "https://www.linkedin.com/jobs/search/?keywords={}&location={}&f_TPR=&sortBy=R&position=1&pageNum={}"
    
    try:
        for page_num in range(max_pages):
            current_page_url = base_url.format(position.replace(' ', '%20'), location.replace(' ', '%20'), page_num)
            print(f"Navigating to LinkedIn page {page_num + 1}: {current_page_url}")
            driver.get(current_page_url)
            time.sleep(5) # Allow time for page to load, ads, pop-ups

            # Scroll to load more jobs
            print("Scrolling to load more LinkedIn jobs...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            for i in range(3): # Scroll a few times
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2.5) # Wait for new jobs to load
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height and i > 0:
                    print("No new content loaded by scrolling.")
                    break
                last_height = new_height

            # Find job cards on the page
            # It's better to target the clickable element that opens the detail view.
            # This selector targets the 'li' element which is usually the container for each job posting.
            job_list_items = driver.find_elements(By.CSS_SELECTOR, 'ul.jobs-search__results-list > li')
            print(f"Found {len(job_list_items)} potential job items on LinkedIn page {page_num + 1}")

            if not job_list_items and page_num == 0:
                if "linkedin.com/login" in driver.current_url or "linkedin.com/authwall" in driver.current_url:
                    print("LinkedIn redirected to login/authwall. Cannot scrape without login.")
                    break 
                # You might add more checks for other overlays or unexpected page states here

            for index, job_item_container in enumerate(job_list_items):
                print(f"Processing job item {index + 1}/{len(job_list_items)}...")
                title, company, loc, card_apply_link, card_salary = "Not found", "Not found", "Not found", "Check link", "Check link"
                
                # Extract basic info from the card first (as a fallback or for initial identification)
                try:
                    title_element = job_item_container.find_element(By.CSS_SELECTOR, 'h3.base-search-card__title')
                    title = title_element.text.strip()
                except: pass
                try:
                    company_element = job_item_container.find_element(By.CSS_SELECTOR, 'h4.base-search-card__subtitle a')
                    company = company_element.text.strip()
                except: pass
                try:
                    loc_element = job_item_container.find_element(By.CSS_SELECTOR, 'span.job-search-card__location')
                    loc = loc_element.text.strip()
                except: pass
                try: # Link from the card itself
                    link_el = job_item_container.find_element(By.CSS_SELECTOR, 'a.base-card__full-link')
                    card_apply_link = link_el.get_attribute('href')
                except: pass
                try: # Salary from the card if present
                    salary_el = job_item_container.find_element(By.CSS_SELECTOR, 'span.job-search-card__salary-info')
                    card_salary = salary_el.text.strip()
                except: pass

                print(f"  Card details: Title: {title}, Company: {company}")

                description = "Check link" # Default description
                final_apply_link = card_apply_link # Use card link as default
                final_salary = card_salary if card_salary and card_salary != "Check link" else "Check link"

                try:
                    # Click the job card (or a specific clickable element within it) to load details
                    # It's often the main 'div' or 'a' tag that represents the card.
                    # Using job_item_container directly if it's the 'li' and clickable.
                    # Sometimes a more specific child element is better to click.
                    clickable_card_element = job_item_container.find_element(By.CSS_SELECTOR, 'div.base-card--link') # Or 'a.base-card__full-link'
                    print(f"  Attempting to click job card for: {title}")
                    driver.execute_script("arguments[0].scrollIntoView(true);", clickable_card_element) # Scroll into view
                    time.sleep(0.5) # Brief pause before click
                    clickable_card_element.click()
                    print("  Card clicked. Waiting for details to load...")
                    time.sleep(4) # INCREASED WAIT for details pane to load reliably

                    # --- Extract from details pane ---
                    # Description (try a few common selectors for LinkedIn)
                    # The main description container is often 'div.jobs-description__content' or similar
                    desc_selectors = [
                        'div.description__text--rich section.jobs-description', # Newer UI often nests it
                        'div.jobs-description__content div.show-more-less-html__markup', # Very common
                        'section.jobs-description .show-more-less-html__markup',
                        'div.description__text',
                        '#job-details' # A general container for job details
                    ]
                    extracted_desc_text = "Check link"
                    for selector in desc_selectors:
                        try:
                            # Wait for the description element to be present in the DOM of the details pane
                            description_element = driver.find_element(By.CSS_SELECTOR, selector)
                            # Use .get_attribute('innerText') or .text.strip()
                            # innerText can be better for preserving line breaks if needed, but .text is simpler.
                            extracted_desc_text = description_element.text.strip()
                            if extracted_desc_text and extracted_desc_text.lower() != "check link" and len(extracted_desc_text) > 50: # Basic check for actual content
                                print(f"  Successfully extracted description (len: {len(extracted_desc_text)}) using selector: {selector}")
                                break 
                        except Exception as e_desc_sel:
                            # print(f"  Description selector {selector} not found or failed: {e_desc_sel}")
                            pass # Silently try next selector
                    
                    description = extracted_desc_text if extracted_desc_text != "Check link" else "Could not extract detailed description."

                    # Salary from details pane (often less reliable than card or not present)
                    # This part is highly prone to change.
                    salary_detail_selectors = [
                        'div.job-details-jobs-unified-top-card__job-insight span.tvm__text', # Example
                        'span.jobs-unified-top-card__salary-info', 
                        'li.job-details-jobs-unified-top-card__job-insight:nth-of-type(1) > span' # More specific
                    ]
                    extracted_salary_detail = "Check link"
                    for selector in salary_detail_selectors:
                        try:
                            salary_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            for el in salary_elements:
                                if el.text and any(char.isdigit() for char in el.text): # Look for digits
                                    extracted_salary_detail = el.text.strip()
                                    print(f"  Extracted salary from details: '{extracted_salary_detail}' using {selector}")
                                    break
                            if extracted_salary_detail != "Check link":
                                break
                        except:
                            pass
                    
                    if extracted_salary_detail != "Check link":
                        final_salary = extracted_salary_detail
                    elif card_salary and card_salary != "Check link":
                        final_salary = card_salary # Fallback to card salary
                        print(f"  Used salary from card: {final_salary}")
                    else:
                        print("  No salary info found on card or in details.")
                        final_salary = "Check link" # Default if nothing found

                    # Try to get a more direct apply link from the details pane if available
                    try:
                        apply_button_details_pane = driver.find_element(By.CSS_SELECTOR, 'div.jobs-apply-button--top-card button.jobs-apply-button')
                        # This usually triggers an "Easy Apply" or takes to next step.
                        # Getting the direct external link can be harder.
                        # For now, we note its presence or can try to get its text.
                        if apply_button_details_pane.is_displayed():
                             print("  'Apply' button found in details pane.")
                        # If it's an <a> tag with href, get it:
                        # apply_link_details = apply_button_details_pane.get_attribute('href')
                        # if apply_link_details: final_apply_link = apply_link_details
                    except:
                        pass # Keep card_apply_link if not found here

                except Exception as e_click_detail:
                    print(f"  Error clicking card or extracting details for '{title}': {e_click_detail}")
                    # If clicking fails, description remains "Check link" or previous value.
                
                # Ensure all fields are strings
                job_details = {
                    'job_title': str(title),
                    'company': str(company),
                    'location': str(loc),
                    'salary': str(final_salary),
                    'description': str(description),
                    'apply_link': str(final_apply_link),
                    'source': 'linkedin'
                }
                jobs.append(job_details)
                print(f"  Processed: '{title}' - Desc len: {len(str(description)) if description else 0} - Salary: '{final_salary}'")
                # Brief pause before processing next card to avoid overwhelming LinkedIn or rapid state changes
                time.sleep(0.5) 

            if page_num < max_pages - 1:
                print("Waiting before loading next LinkedIn page...")
                time.sleep(3)

    except Exception as e_outer:
        print(f"An error occurred during the LinkedIn scraping process: {e_outer}")
    finally:
        if driver:
            print("Finished scraping LinkedIn. WebDriver for LinkedIn will close, browser window might remain open if detach=True.")
            driver.quit()
    return jobs

def run_scrapers(position, location, indeed_pages=1, linkedin_pages=1):
    """Runs all scrapers and saves the combined results."""
    print(f"--- Starting scraper run for: '{position}' in '{location}' ---")
    
    all_jobs = []
    
    # Scrape Indeed
    try:
        print("\n--- Starting Indeed Scraper ---")
        indeed_jobs = scrape_indeed(position, location, max_pages=indeed_pages)
        all_jobs.extend(indeed_jobs)
        print(f"Indeed scraper found {len(indeed_jobs)} jobs.")
    except Exception as e:
        print(f"An error occurred during Indeed scraping task: {e}")

    # Scrape LinkedIn
    try:
        print("\n--- Starting LinkedIn Scraper ---")
        linkedin_jobs = scrape_linkedin(position, location, max_pages=linkedin_pages)
        all_jobs.extend(linkedin_jobs)
        print(f"LinkedIn scraper found {len(linkedin_jobs)} jobs.")
    except Exception as e:
        print(f"An error occurred during LinkedIn scraping task: {e}")
        
    if all_jobs:
        print(f"\n--- Scraper run finished. Total jobs scraped: {len(all_jobs)} ---")
        save_jobs(all_jobs)
    else:
        print("\n--- Scraper run finished. No jobs found or saved. ---")
    
    return all_jobs

if __name__ == '__main__':
    # --- Configuration for the scraper ---
    # Set the job position and location you want to search for.
    # Set how many pages to scrape from each site.
    # Note: Scraping too many pages too quickly can lead to IP blocks or CAPTCHAs.
    
    JOB_POSITION = "software engineer"
    JOB_LOCATION = "london" # Be specific for better results, e.g., "London, UK" or "San Francisco, CA"
    INDEED_PAGES_TO_SCRAPE = 1
    LINKEDIN_PAGES_TO_SCRAPE = 1

    print(f"Script started. To change search parameters, edit them in the `if __name__ == '__main__':` block of scraper.py")
    print(f"Running with Chrome version: Your installed version (webdriver-manager will match)")
    print("The browser window(s) will remain open for inspection after the script. Close them manually when done.\n")
    
    # Run the scrapers with the defined configuration
    run_scrapers(
        position=JOB_POSITION, 
        location=JOB_LOCATION, 
        indeed_pages=INDEED_PAGES_TO_SCRAPE, 
        linkedin_pages=LINKEDIN_PAGES_TO_SCRAPE
    )
    
    print("\nScript finished. Check 'jobs_data.json' for results.")
    print("If browser windows are still open, you can now close them manually.")
