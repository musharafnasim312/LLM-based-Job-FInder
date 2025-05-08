# LLM-Powered Job Finder

This project is an API-driven application designed to scrape job listings from Indeed.com (via the HasData API) and provide an intelligent search functionality leveraging a Large Language Model (LLM - Google Gemini) to filter and rank jobs based on relevance to user queries.

## Tech Stack

*   **Backend:** Python, FastAPI
*   **Web Scraping (API-based):** HasData API (for Indeed job listings and job details)
*   **LLM for Search & Filtering:** Google Gemini Pro (via `google-generativeai` SDK)
*   **API Interaction:** `requests` library
*   **Environment Management:** `python-dotenv` for API keys
*   **Server:** Uvicorn

## Features

*   **Indeed Job Scraping:** 
    *   Utilizes HasData API to fetch job listings based on keywords and location.
    *   Paginates through search results to gather multiple job URLs.
    *   Fetches detailed information for each job URL using a separate HasData API endpoint.
    *   Saves scraped job data to a local JSON file (`jobs_data.json`).
*   **LLM-Powered Job Search:**
    *   Provides an API endpoint (`/search`) to query the scraped jobs.
    *   Accepts multiple criteria: position, experience, salary (handled as a preference), job nature (remote/onsite), location, and skills.
    *   Uses Google Gemini to analyze job descriptions and details against user criteria for relevance.
    *   Returns a list of jobs deemed most relevant by the LLM.
*   **API for Scraper Control:**
    *   An endpoint (`/scrape`) to (conceptually) trigger the scraping process (currently, the main scraping logic is in `indeed_api_scraper.py` which is run manually).

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd LLM-based-Job-FInder 
    ```
    (Replace `<your-repository-url>` with the actual URL of your Git repository)

2.  **Create a Virtual Environment:**
    It's highly recommended to use a virtual environment.
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    Ensure you have a `requirements.txt` file with all necessary packages. If not, you might need to create it based on the imports in the Python files (e.g., `fastapi`, `uvicorn`, `requests`, `python-dotenv`, `google-generativeai`).
    The `requirements.txt` should look something like this:
    ```txt
    fastapi
    uvicorn[standard]
    requests
    python-dotenv
    google-generativeai
    ```
    Install using:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up Environment Variables:**
    Create a `.env` file in the project root directory. This file should contain your API keys:
    ```env
    HASDATA_API_KEY="your_hasdata_api_key_here"
    GOOGLE_API_KEY="your_google_gemini_api_key_here"
    ```
    Replace `your_hasdata_api_key_here` and `your_google_gemini_api_key_here` with your actual API keys.
    *   **HasData API Key:** Obtain from your HasData dashboard.
    *   **Google API Key:** Obtain from Google AI Studio (for Gemini).

## How to Use

### 1. Scraping Job Data from Indeed

The `indeed_api_scraper.py` script is responsible for fetching job data.

*   **Configure:** Open `indeed_api_scraper.py` and modify the following parameters in the `if __name__ == "__main__":` block:
    *   `SEARCH_KEYWORD`: The job title or keyword to search for (e.g., "software engineer").
    *   `SEARCH_LOCATION`: The location to search in (e.g., "New York, NY", "remote").
    *   `SEARCH_DOMAIN`: The Indeed domain to use (e.g., "www.indeed.com", "pk.indeed.com").
    *   `MAX_JOBS_TO_SCRAPE`: The maximum number of job details to fetch (e.g., 100).
    *   `JOBS_PER_PAGE`: Number of jobs the HasData listing API returns per page (e.g., 15 or 25, check API behavior).
*   **Run the Scraper:**
    Execute the script from your terminal (ensure your virtual environment is active):
    ```bash
    python indeed_api_scraper.py
    ```
    This script will:
    1.  Call the HasData Indeed "Listing" API (`/scrape/indeed/listing`) to get a list of job URLs based on your keywords and location, handling pagination via the `start` parameter.
    2.  For each job URL obtained, it will then call the HasData Indeed "Job Detail" API (`/scrape/indeed/job`) to get comprehensive details for that specific job.
    3.  The collected job details will be saved (or appended) to `jobs_data.json` in a structured format.

### 2. Running the FastAPI Application

Once you have scraped some job data (i.e., `jobs_data.json` is populated), you can run the FastAPI server to use the search functionality.

*   **Start the Server:**
    Use Uvicorn to run the FastAPI application (from the project root directory):
    ```bash
    uvicorn main:app --reload
    ```
    The `--reload` flag enables auto-reloading when you make code changes.
*   **Access the API:**
    The API will typically be available at `http://127.0.0.1:8000`.
    *   **API Docs:** Open `http://127.0.0.1:8000/docs` in your browser to see the Swagger UI for interactive API documentation and testing.

## API Endpoints

*   **`GET /`**: Welcome message.
*   **`POST /scrape`**: 
    *   **Request Body:** `{ "position": "string", "location": "string" }`
    *   **Description:** (Conceptual endpoint in `main.py`) Intended to trigger a scraping process. Currently, the primary scraping logic is executed via `indeed_api_scraper.py`. The `main.py` version of `/scrape` uses a simulated scraper for demonstration if `indeed_api_scraper.py` hasn't been run.
*   **`POST /search`**: 
    *   **Request Body (example):**
        ```json
        {
          "position": "software engineer",
          "experience": "3+ years",
          "salary": "80000", 
          "jobNature": "remote",
          "location": "USA",
          "skills": "Python, FastAPI, Docker"
        }
        ```
    *   **Description:** Searches the jobs in `jobs_data.json`. The LLM (Gemini) processes these jobs against the provided criteria and returns a list of jobs it deems most relevant. All fields in the request body are optional. The salary is treated more as a guideline or minimum by the LLM.

## Project Structure

```
LLM-based-Job-FInder/
├── .env                    # Stores API keys (GITIGNORED)
├── .gitignore              # Specifies intentionally untracked files that Git should ignore
├── indeed_api_scraper.py   # Script for scraping jobs from Indeed via HasData API
├── llm_processor.py        # Handles interaction with Google Gemini for job filtering
├── main.py                 # FastAPI application entry point, defines API endpoints
├── scraper.py              # Contains helper functions for loading data, (conceptual scraper logic for API)
├── jobs_data.json          # Stores scraped job data (GITIGNORED)
├── requirements.txt        # Project dependencies
└── README.md               # This file
```

## LLM Integration Details

The `llm_processor.py` file uses the Google Gemini API.

1.  **Initialization:** It initializes the Gemini client using the `GOOGLE_API_KEY` from the `.env` file.
2.  **Prompting:** When the `/search` endpoint is called, a detailed prompt is constructed. This prompt includes:
    *   The user's search criteria.
    *   The list of all jobs scraped from `jobs_data.json`.
    *   Specific instructions for the LLM to act as a job matching assistant, to filter based on *all* criteria, and to return the results in a strict JSON format (`{"relevant_jobs": [...]}`).
3.  **JSON Output:** The Gemini model is configured to return its response as `application/json` to ensure easier parsing.
4.  **Filtering Logic:** The LLM is instructed to find "strong and direct matches." Salary is often a strong filter; if salary expectations are very specific or high, it might result in fewer matches. The prompt emphasizes matching all criteria.

## Future Enhancements

*   **Background Scraping Tasks:** Implement the `/scrape` endpoint in `main.py` to run the `indeed_api_scraper.py` logic as a background task (e.g., using FastAPI's `BackgroundTasks` or Celery).
*   **Multiple Scrapers:** Add scrapers for other job boards (e.g., LinkedIn, Glassdoor) and integrate their data.
*   **Database Integration:** Replace `jobs_data.json` with a proper database (e.g., PostgreSQL, MongoDB) for better data management, scalability, and querying capabilities.
*   **Advanced LLM Prompting:** Refine LLM prompts for more nuanced matching, handling of relative experience, salary negotiation ranges, and alternative skill matching. Consider making salary a "soft" preference rather than a hard filter in the prompt.
*   **User Authentication:** Add user accounts and authentication if the application were to be deployed publicly.
*   **Frontend UI:** Develop a simple frontend (e.g., using Streamlit, React, or Vue.js) to interact with the API more easily.
*   **Pagination for Search Results:** Implement pagination for the `/search` endpoint if a large number of jobs are returned.
*   **Error Handling and Logging:** Enhance error handling and add more robust logging throughout the application.
*   **Create `requirements.txt` Automatically:** Add a step or script to generate `requirements.txt` using `pip freeze > requirements.txt`.
