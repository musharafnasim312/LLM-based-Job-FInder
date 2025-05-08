import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime
import time

JOBS_DATA_FILE = os.path.join(os.path.dirname(__file__), 'jobs_data.json') # New file for API data

def load_api_key():
    """Loads the HasData API key from .env file."""
    load_dotenv()
    api_key = os.getenv("HASDATA_API_KEY")
    if not api_key:
        print("Error: HASDATA_API_KEY not found in .env file.")
        print("Please ensure your .env file exists in the same directory as this script and contains:")
        print("HASDATA_API_KEY='your_actual_api_key'")
        return None
    return api_key

def get_indeed_job_details_from_api(job_url_or_jk, api_key):
    """Fetches job details from HasData Indeed API for a given job URL or job key (jk)."""
    if not job_url_or_jk:
        print("Error: Job URL or JK cannot be empty.")
        return None

    # Construct the full Indeed job URL if only JK is provided
    if not job_url_or_jk.startswith("http"):
        indeed_job_url = f"https://www.indeed.com/viewjob?jk={job_url_or_jk}"
    else:
        indeed_job_url = job_url_or_jk

    api_endpoint = "https://api.hasdata.com/scrape/indeed/job"
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }
    params = {
        'url': indeed_job_url
    }

    print(f"Requesting job details for: {indeed_job_url} from HasData API...")
    try:
        response = requests.get(api_endpoint, headers=headers, params=params, timeout=60) # 60 second timeout
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        
        print("API Response Status Code:", response.status_code)
        # It's good practice to check if the response content type is JSON if expected
        if 'application/json' in response.headers.get('Content-Type', ''):
            job_details = response.json()
            return job_details
        else:
            print("Error: API response is not in JSON format.")
            print("Response text:", response.text[:500]) # Print a snippet of the response
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response Content: {response.text[:500]}") # Show part of the error response from API
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected error occurred with the request: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"Error decoding JSON response from API: {json_err}")
        print(f"Response text: {response.text[:500]}")
    return None

def save_job_details(job_detail_data):
    """Saves the scraped job details to a JSON file, appending to existing data."""
    all_jobs_data = {'jobs': []}
    if os.path.exists(JOBS_DATA_FILE):
        try:
            with open(JOBS_DATA_FILE, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
                if isinstance(current_data, dict) and 'jobs' in current_data:
                    all_jobs_data['jobs'].extend(current_data['jobs'])
        except (json.JSONDecodeError, FileNotFoundError):
            print(f"Warning: {JOBS_DATA_FILE} not found or contains invalid JSON. A new file will be created.")

    # We need to know the structure of job_detail_data from HasData API
    # Let's assume for now it returns a dictionary for a single job that we can append.
    # We will need to map its fields to our desired structure:
    # {'job_title': ..., 'company': ..., 'location': ..., 'salary': ..., 'description': ..., 'apply_link': ..., 'source': 'indeed_api'}

    # --- Placeholder: Adapt this mapping based on actual API response structure ---
    if job_detail_data and isinstance(job_detail_data, dict):
        # --- Corrected mapping based on actual API response structure ---
        # The main job data seems to be under a top-level 'job' key in the API response.
        job_data = job_detail_data.get('job')
        request_meta = job_detail_data.get('requestMetadata')

        if not job_data:
            print("Error: 'job' key not found in API response. Cannot map fields.")
            return

        # Extract location from description if possible
        job_location = "Location Not Provided by API"
        if job_data.get('description'):
            desc_lines = job_data.get('description', '').split('\n')
            for line in desc_lines:
                if line.startswith("Work Location:"):
                    job_location = line.replace("Work Location:", "").strip()
                    break
        
        apply_url = request_meta.get('url', 'Apply URL Not Provided by API') if request_meta else 'Apply URL Not Provided by API'

        mapped_job = {
            'job_title': job_data.get('title', 'Title Not Provided'),
            'company': job_data.get('company', 'Company Not Provided by API'), # Assuming 'company' might exist, fallback if not
            'location': job_location,
            'salary': job_data.get('salary', 'Salary Not Specified by API'), # Assuming 'salary' might exist, fallback if not
            'description': job_data.get('description', 'Description Not Provided'),
            'apply_link': apply_url,
            'source': 'indeed_hasdata_api'
        }
        # Add new job, preventing duplicates based on apply_link and source
        existing_links_and_sources = {(job.get('apply_link'), job.get('source')) for job in all_jobs_data['jobs']}
        if (mapped_job.get('apply_link'), mapped_job.get('source')) not in existing_links_and_sources:
            all_jobs_data['jobs'].append(mapped_job)
            newly_added_count = 1
        else:
            print(f"Job from {mapped_job.get('apply_link')} already exists. Skipping.")
            newly_added_count = 0
    else:
        print("No valid job detail data to save or data is not a dictionary.")
        return
    # --- End Placeholder ---

    if newly_added_count > 0:
        with open(JOBS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_jobs_data, f, indent=2, ensure_ascii=False)
        print(f"Added {newly_added_count} new job. Total jobs in {JOBS_DATA_FILE}: {len(all_jobs_data['jobs'])}")
    elif newly_added_count == 0 and mapped_job.get('apply_link') != 'Not Provided': # Only print if it wasn't skipped due to bad data
        print("Job already exists or was not added. No changes made to the JSON file.")

def get_job_listings_from_hasdata(api_key, keyword, location, domain="www.indeed.com", start_offset=0):
    """Fetches job listings from HasData Indeed Listing API."""
    api_endpoint = "https://api.hasdata.com/scrape/indeed/listing"
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }
    params = {
        'keyword': keyword,
        'location': location,
        'domain': domain,
        'start': start_offset
    }

    print(f"Requesting job listings for keyword: '{keyword}', location: '{location}', start: {start_offset} from HasData API...")
    try:
        response = requests.get(api_endpoint, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        print("Listing API Response Status Code:", response.status_code)
        if 'application/json' in response.headers.get('Content-Type', ''):
            return response.json()
        else:
            print("Error: Listing API response is not in JSON format.")
            print("Response text:", response.text[:500])
            return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred with Listing API: {http_err}")
        print(f"Response Content: {response.text[:500]}")
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected error occurred with Listing API request: {req_err}")
    return None

if __name__ == "__main__":
    api_key = load_api_key()
    if not api_key:
        exit()

    # --- User Definable Search Parameters ---
    SEARCH_KEYWORD = "python developer"  # Or get from input: input("Enter search keyword: ")
    SEARCH_LOCATION = "remote"       # Or get from input: input("Enter search location: ")
    SEARCH_DOMAIN = "www.indeed.com"   # e.g., "www.indeed.com", "pk.indeed.com"
    MAX_JOBS_TO_SCRAPE = 100           # Target number of jobs to get details for
    JOBS_PER_PAGE = 15                 # Assumption for Indeed pagination via API, adjust if known
    # --- End User Definable Search Parameters ---

    print(f"--- Starting Job Scraping --- ")
    print(f"Keyword: '{SEARCH_KEYWORD}', Location: '{SEARCH_LOCATION}', Domain: '{SEARCH_DOMAIN}'")
    print(f"Targeting up to {MAX_JOBS_TO_SCRAPE} jobs.")

    collected_job_identifiers = [] # To store URLs or JKs
    current_offset = 0
    max_pages_to_try = (MAX_JOBS_TO_SCRAPE // JOBS_PER_PAGE) + 5 # Try a few extra pages

    print("\n--- Phase 1: Collecting Job Listings --- ")
    for page_num in range(max_pages_to_try):
        if len(collected_job_identifiers) >= MAX_JOBS_TO_SCRAPE:
            print(f"Collected target number of job identifiers ({len(collected_job_identifiers)}). Moving to detail fetching.")
            break

        print(f"Fetching listing page {page_num + 1} (offset: {current_offset})...")
        listings_response = get_job_listings_from_hasdata(
            api_key, 
            SEARCH_KEYWORD, 
            SEARCH_LOCATION, 
            domain=SEARCH_DOMAIN, 
            start_offset=current_offset
        )

        if listings_response and 'jobs' in listings_response and listings_response['jobs']:
            jobs_on_page = listings_response['jobs']
            print(f"Found {len(jobs_on_page)} job(s) on this listing page.")
            for job_listing in jobs_on_page:
                if 'url' in job_listing and job_listing['url']:
                    # We can use the direct URL for the details API if it's a full URL
                    # Or extract JK if needed: url_parts = urlparse(job_listing['url']); params = parse_qs(url_parts.query); jk = params.get('jk',[None])[0]
                    job_url = job_listing['url'] 
                    if job_url not in collected_job_identifiers: # Avoid duplicates if any across pages
                         collected_job_identifiers.append(job_url)
                    if len(collected_job_identifiers) >= MAX_JOBS_TO_SCRAPE:
                        break 
                else:
                    print("Warning: Job listing found without a 'url'. Skipping.")
            current_offset += JOBS_PER_PAGE # Increment for next page
        else:
            print("No more job listings found or an error occurred. Stopping listing collection.")
            break
        
        if len(collected_job_identifiers) < MAX_JOBS_TO_SCRAPE and listings_response and not listings_response.get('pagination', {}).get('nextPage'):
            print("No next page indicated by API, assuming end of results.")
            break

        time.sleep(1) # Be polite to the listing API

    print(f"\n--- Phase 1 Complete: Collected {len(collected_job_identifiers)} unique job URLs/identifiers. ---")

    if not collected_job_identifiers:
        print("No job identifiers collected. Exiting.")
        exit()

    print("\n--- Phase 2: Fetching Full Job Details for Each Listing --- ")
    total_jobs_processed = 0
    for i, job_identifier in enumerate(collected_job_identifiers):
        print(f"\nProcessing job {i+1}/{len(collected_job_identifiers)}: {job_identifier}")
        details = get_indeed_job_details_from_api(job_identifier, api_key)
        if details:
            # The raw `details` from the job detail API is what we want to save
            save_job_details(details) 
            total_jobs_processed +=1
        else:
            print(f"Failed to retrieve details for job: {job_identifier}")
        
        # Polite delay between calls to the details API
        if i < len(collected_job_identifiers) - 1: # Don't sleep after the last one
            print("Waiting 1 second before next detail request...")
            time.sleep(1)
            
    print(f"\n--- Phase 2 Complete: Processed details for {total_jobs_processed} jobs. --- ")
    print(f"Script finished. Check '{JOBS_DATA_FILE}' for results.")

