from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import json
import os

# Project-specific imports
from scraper import run_scrapers, load_scraped_data, JOBS_DATA_FILE # JOBS_DATA_FILE is used for direct loading
from llm_processor import filter_jobs_with_llm

app = FastAPI(
    title="Job Finder API",
    version="0.2.0",
    description="API to scrape job listings and search them using LLM-powered relevance filtering."
)

# --- Pydantic Models ---
class JobSearchCriteria(BaseModel):
    position: Optional[str] = None
    experience: Optional[str] = None
    salary: Optional[str] = None
    jobNature: Optional[str] = None  # onsite/remote
    location: Optional[str] = None
    skills: Optional[str] = None

class Job(BaseModel):
    job_title: str
    company: str
    experience: Optional[str] = None
    jobNature: Optional[str] = None
    location: str
    salary: Optional[str] = None
    apply_link: str
    description: Optional[str] = None # Added for LLM context
    skills_extracted: Optional[List[str]] = None # Added for LLM context
    source: Optional[str] = None # To indicate LinkedIn, Indeed, etc.

class JobSearchResponse(BaseModel):
    relevant_jobs: List[Job]
    total_found: int
    message: Optional[str] = None

class ScraperRunParams(BaseModel):
    position: str
    location: str
    # pages: Optional[int] = 1 # If you want to control depth from API

class ScraperStatusResponse(BaseModel):
    status: str
    message: Optional[str] = None
    new_jobs_found: Optional[int] = None
    data_file: Optional[str] = None 

# --- API Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Job Finder API! Use /docs for API documentation."}

@app.post("/scrape", response_model=ScraperStatusResponse)
async def trigger_scraper_run(params: ScraperRunParams):
    """
    Triggers the web scrapers to find new jobs based on position and location.
    Note: Current scrapers are illustrative simulations.
    """
    if not params.position or not params.location:
        raise HTTPException(status_code=400, detail="Position and location are required to run scrapers.")
    
    # In a real app, you might run this as a background task
    result = await run_scrapers(position=params.position, location=params.location)
    
    if result.get("status") == "success":
        return ScraperStatusResponse(
            status="success", 
            message=f"Scraping process completed. {result.get('new_jobs_found', 0)} new jobs added.",
            new_jobs_found=result.get('new_jobs_found'),
            data_file=result.get('saved_to')
        )
    elif result.get("status") == "no_new_jobs":
        return ScraperStatusResponse(
            status="no_new_jobs", 
            message="Scraping process completed. No new unique jobs found.",
            data_file=JOBS_DATA_FILE
        )
    else:
        return ScraperStatusResponse(
            status="skipped_or_error", 
            message=result.get("message", "Scraper run was skipped or an error occurred."),
            data_file=JOBS_DATA_FILE
        )

@app.post("/search", response_model=JobSearchResponse)
async def search_jobs(criteria: JobSearchCriteria):
    print("\n--- DEBUG: MAIN.PY: /search endpoint CALLED ---")
    """
    Searches for jobs based on provided criteria.
    Loads data from the local JSON file and uses LLM for relevance filtering.
    """
    print(f"Received search criteria: {criteria.model_dump_json(indent=2)}")

    # 1. Load jobs from jobs_data.json
    print("--- DEBUG: MAIN.PY: Calling load_scraped_data --- ")
    all_jobs = load_scraped_data() # This is from scraper.py
    print(f"--- DEBUG: MAIN.PY: load_scraped_data returned {len(all_jobs)} jobs ---")

    if not all_jobs:
        return JobSearchResponse(relevant_jobs=[], total_found=0, message="No jobs available in the database. Try running the scraper first.")

    # 2. Filter with LLM if criteria are provided
    # Convert criteria model to dict for the LLM processor
    criteria_dict = criteria.model_dump(exclude_none=True)

    if not criteria_dict: # No criteria provided, return all jobs (or a subset for pagination later)
        # Potentially add pagination here if returning all jobs is too much
        return JobSearchResponse(relevant_jobs=[Job(**job) for job in all_jobs[:50]], total_found=len(all_jobs), message="No search criteria provided; returning up to 50 available jobs.")

    # Pass the job data and criteria to the LLM processor
    # 3. Call the LLM processor
    print(f"--- DEBUG: MAIN.PY: About to call filter_jobs_with_llm with {len(all_jobs)} jobs. Criteria: {criteria.model_dump_json()} ---")
    relevant_jobs_from_llm = await filter_jobs_with_llm(all_jobs, criteria_dict)
    print(f"--- DEBUG: MAIN.PY: filter_jobs_with_llm returned {len(relevant_jobs_from_llm)} jobs ---")

    # Convert dicts back to Job models for the response
    # Ensure that only jobs matching the Pydantic model are returned
    validated_relevant_jobs = []
    for job_data in relevant_jobs_from_llm:
        try:
            # Ensure all required fields for Job model are present, or provide defaults if appropriate
            # For now, we rely on the LLM returning the correct structure.
            # Add more robust validation if needed.
            validated_relevant_jobs.append(Job(**job_data))
        except Exception as e:
            print(f"Warning: LLM returned a job that doesn't match Job model: {job_data}. Error: {e}")
            continue # Skip this job
            
    return JobSearchResponse(relevant_jobs=validated_relevant_jobs, total_found=len(validated_relevant_jobs))


if __name__ == "__main__":
    # This part is for running with `python main.py` directly, though `uvicorn` is preferred.
    import uvicorn
    print("Starting Uvicorn server. Access API at http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
