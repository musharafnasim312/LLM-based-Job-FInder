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
    """Scrapes job listings from LinkedIn."""
    print(f"Scraping LinkedIn for '{position}' in '{location}'...")
    jobs = []
    driver = get_driver(headless=False) # Run non-headless for LinkedIn
    if not driver:
        return jobs # WebDriver initialization failed

    base_url = "https://www.linkedin.com/jobs/search/?keywords={}&location={}&f_TPR=&sortBy=R&position=1&pageNum={}" 
    
    try:
        for page_num in range(max_pages): # LinkedIn uses pageNum starting from 0 in URL
            url = base_url.format(position.replace(' ', '%20'), location.replace(' ', '%20'), page_num)
            print(f"Navigating to LinkedIn page {page_num+1}: {url}")
            driver.get(url)
            time.sleep(5) # LinkedIn can be slower and has more dynamic content

            # Scroll to load more jobs if necessary (LinkedIn often uses infinite scroll)
            print("Scrolling to load more LinkedIn jobs...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            for i in range(3): # Scroll a few times to try and load more jobs
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2.5) # Wait for new jobs to load
                new_height = driver.execute_script("return document.body.scrollHeight")
                print(f"Scroll attempt {i+1}: new_height={new_height}, last_height={last_height}")
                if new_height == last_height and i > 0: # Break if height doesn't change after first scroll
                    print("No new content loaded by scrolling.")
                    break
                last_height = new_height

            # CSS Selectors for LinkedIn - these are also subject to change.
            cards = driver.find_elements(By.CSS_SELECTOR, 'div.base-card--link') # More specific card selector
            print(f"Found {len(cards)} job cards on LinkedIn page {page_num+1}")

            if not cards and page_num == 0: # Check for sign-in overlay on first page
                try:
                    print("No job cards found, checking for LinkedIn sign-in overlay...")
                    # LinkedIn might show a sign-in prompt that covers jobs
                    # This is a guess, actual element might differ
                    if "linkedin.com/login" in driver.current_url or "linkedin.com/authwall" in driver.current_url:
                         print("LinkedIn redirected to login/authwall. Cannot scrape without login.")
                         break # Stop trying this site if login is required
                    # Add more checks if needed for other types of overlays
                except Exception as e_overlay:
                    print(f"Could not check for LinkedIn overlay: {e_overlay}")


            for card in cards:
                try:
                    title = card.find_element(By.CSS_SELECTOR, 'h3.base-search-card__title').text.strip()
                    # Ensure the company link is correctly identified.
                    company_element = card.find_element(By.CSS_SELECTOR, 'h4.base-search-card__subtitle a.hidden-nested-link')
                    company = company_element.text.strip()
                    loc = card.find_element(By.CSS_SELECTOR, 'span.job-search-card__location').text.strip()
                    link = card.find_element(By.CSS_SELECTOR, 'a.base-card__full-link').get_attribute('href')
                    
                    # LinkedIn salary and detailed description are often not on the search results page directly
                    # or require clicking into the job. This basic scraper focuses on search results.
                    jobs.append({
                        'job_title': title,
                        'company': company,
                        'location': loc,
                        'salary': 'Check link', # Placeholder
                        'description': 'Check link', # Placeholder
                        'apply_link': link,
                        'source': 'linkedin'
                    })
                except Exception as e:
                    print(f"Error extracting details from a LinkedIn job card: {e} - Card HTML: {card.get_attribute('outerHTML')[:200]}") # Print part of card HTML for debugging
    except Exception as e_outer:
        print(f"An error occurred during the LinkedIn scraping process: {e_outer}")
    finally:
        if driver:
            print("Finished scraping LinkedIn. WebDriver for LinkedIn will close, browser window might remain open.")
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
