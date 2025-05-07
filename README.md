# Job Finder API

This API scrapes job listings and allows users to search for jobs based on specified criteria. It leverages the Google Gemini large language model (LLM) to refine search results by matching job descriptions and user queries.

## Tech Stack

*   **Backend Framework**: FastAPI
*   **Web Server**: Uvicorn
*   **LLM Integration**: Google Gemini API (via `google-generativeai` Python SDK)
*   **Web Scraping (Simulated)**: Uses `requests`, `beautifulsoup4`, `selenium`, `webdriver-manager` (currently, the scraping logic in `scraper.py` is illustrative and loads data from a local `jobs_data.json` if scraping is skipped or fails).
*   **Environment Management**: `python-dotenv`
*   **Data Storage (Default)**: `jobs_data.json` (stores scraped job data)

## Project Structure

```
.Jobfinder/
├── .env                # Stores API keys and environment variables (e.g., GOOGLE_API_KEY)
├── .env.example        # Example for .env file structure
├── .gitignore          # Specifies intentionally untracked files that Git should ignore
├── README.md           # This file
├── jobs_data.json      # Stores scraped job data (can be populated by the /scrape endpoint)
├── llm_processor.py    # Handles interaction with the Google Gemini API for job filtering
├── main.py             # Main FastAPI application: defines API endpoints and orchestrates logic
├── requirements.txt    # Lists project dependencies
└── scraper.py          # Contains web scraping logic (currently illustrative)
```

## Setup and Running

1.  **Clone the Repository (if applicable)**
    ```bash
    # git clone <repository-url>
    # cd Jobfinder
    ```

2.  **Create and Activate a Virtual Environment (Recommended)**
    ```bash
    python -m venv venv
    ```
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Environment Variables**
    *   Create a `.env` file in the project root directory by copying `.env.example`:
        ```bash
        # On Windows (PowerShell)
        copy .env.example .env
        # On macOS/Linux
        # cp .env.example .env
        ```
    *   Open the `.env` file and add your Google Gemini API Key:
        ```
        GOOGLE_API_KEY='YOUR_GEMINI_API_KEY'
        ```
        Replace `YOUR_GEMINI_API_KEY` with your actual key.

5.  **Run the FastAPI Application**
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    *   `--reload`: Enables auto-reload when code changes are detected.
    *   The API will be available at `http://127.0.0.1:8000`.
    *   Interactive API documentation (Swagger UI) will be at `http://127.0.0.1:8000/docs`.

## How It Works

1.  **Scraping (Illustrative)**: The `/scrape` endpoint (POST request) can be used to trigger (simulated) web scraping for jobs based on a position and location. The scraped data is saved to `jobs_data.json`.
    *   **Example Request Body for `/scrape`**:
        ```json
        {
          "position": "Software Engineer",
          "location": "London"
        }
        ```
2.  **Loading Data**: The `/search` endpoint loads job data from `jobs_data.json`.
3.  **LLM Filtering**: When a user sends a search query to the `/search` endpoint, the criteria are passed along with the loaded job data to the `llm_processor.py`. This module constructs a prompt for the Google Gemini API, asking it to identify jobs that are a "strong match" to the user's criteria.
4.  **Response**: The API returns a JSON list of the jobs deemed relevant by the LLM.

## API Endpoints

*   `GET /`: Welcome message.
*   `POST /scrape`: Triggers the (simulated) job scraping process.
    *   **Request Body**: `ScraperRunParams` model (e.g., `{"position": "string", "location": "string"}`)
    *   **Response Body**: `ScraperStatusResponse` model.
*   `POST /search`: Searches for jobs based on provided criteria using LLM filtering.
    *   **Request Body**: `JobSearchCriteria` model (all fields are optional):
        ```json
        {
          "position": "Full Stack Developer",
          "experience": "2 years",
          "salary": "Competitive",
          "jobNature": "remote",
          "location": "London, United Kingdom",
          "skills": "Python, FastAPI, JavaScript"
        }
        ```
    *   **Response Body**: `JobSearchResponse` model (containing `relevant_jobs` list).

## Key Files and Logic

*   **`main.py`**: Defines the FastAPI app, Pydantic models for request/response validation, and API endpoints. It orchestrates calls to the scraper and LLM processor.
*   **`llm_processor.py`**: 
    *   Initializes the Google Gemini client using the `GOOGLE_API_KEY` from the `.env` file.
    *   The `filter_jobs_with_llm` function takes the list of all jobs and the user's search criteria.
    *   It constructs a detailed prompt instructing the Gemini model (`gemini-1.5-flash` by default) to act as a job matching assistant and return only strongly matching jobs in a specific JSON format (`{"relevant_jobs": [...]}`).
    *   It makes an API call to Gemini, requesting a JSON response using `response_mime_type="application/json"`.
    *   Parses the LLM's response and returns the list of relevant jobs.
*   **`scraper.py`**: Contains functions to simulate scraping (`run_scrapers`) and load data from `jobs_data.json` (`load_scraped_data`). The actual scraping logic is illustrative and would need to be fully implemented for real-world use.
*   **`jobs_data.json`**: A simple JSON file acting as a database for job listings. It's read by `main.py` during a search and can be (over)written by the `scraper.py` module.

## Future Enhancements

*   Implement robust web scraping logic in `scraper.py` for actual job portals (e.g., LinkedIn, Indeed).
*   Improve error handling and logging throughout the application.
*   Add more sophisticated data validation.
*   Consider a more robust database solution (e.g., PostgreSQL, MongoDB) instead of `jobs_data.json` for scalability and better querying capabilities.
*   Implement user authentication if the API needs to be secured.
*   Add pagination to the `/search` endpoint for large result sets.
*   Fine-tune the Gemini LLM prompt in `llm_processor.py` for optimal relevance and explore different Gemini models (e.g., `gemini-1.5-pro` for potentially higher quality, though possibly slower/more expensive).
*   Develop a frontend interface for easier interaction with the API.
