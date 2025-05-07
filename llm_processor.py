import os
import google.generativeai as genai
from dotenv import load_dotenv
from typing import List, Dict
import json
import re

# Load environment variables (especially GOOGLE_API_KEY)
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
model = None # Initialize model as None

if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY not found in .env file. LLM features will not work.")
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        # For text-only input, use gemini-pro
        # For multimodal input, use gemini-1.5-flash or gemini-1.5-pro (or the latest models)
        model = genai.GenerativeModel(model_name="gemini-1.5-flash") # Using flash for speed, consider pro for quality
        print("Gemini client initialized successfully.")
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")


async def filter_jobs_with_llm(jobs_data: List[Dict], criteria: Dict) -> List[Dict]:
    print("\n*** DEBUG: LLM_PROCESSOR.PY (GEMINI): filter_jobs_with_llm CALLED ***")
    if not model:
        print("*** DEBUG: LLM_PROCESSOR.PY (GEMINI): Gemini model NOT INITIALIZED. Returning all jobs. Check GOOGLE_API_KEY. ***")
        # Depending on desired behavior, you might return all jobs, or an empty list.
        # For now, returning all jobs if LLM is not available.
        return jobs_data 
    if not jobs_data:
        print("*** DEBUG: LLM_PROCESSOR.PY (GEMINI): No jobs_data received. Returning empty list. ***")
        return []

    print(f"*** DEBUG: LLM_PROCESSOR.PY (GEMINI): Filtering {len(jobs_data)} jobs. Criteria: {json.dumps(criteria, indent=2)} ***")

    # Prepare a prompt for the Gemini LLM
    # Gemini prefers a more direct instruction for JSON output.
    # The prompt will include instructions to format the output as a JSON object
    # with a specific key 'relevant_jobs' containing a list of job objects.

    # Create a string representation of the jobs list
    # To avoid making the prompt too long, we might send a subset or summarize if the list is huge.
    # For now, sending all jobs as in the original OpenAI version.
    jobs_string_list = []
    for i, job in enumerate(jobs_data):
        jobs_string_list.append(f"Job {i+1}: {json.dumps(job, indent=2)}")
    
    jobs_block = "\n".join(jobs_string_list)

    prompt = f"""
You are an expert job matching assistant. Your task is to analyze a list of job postings and filter them based on the user's search criteria.

User's Search Criteria:
{json.dumps(criteria, indent=2)}

Job Listings:
{jobs_block}

Instructions:
1. Carefully review each job listing against all aspects of the user's search criteria. When matching the user's 'position' or keyword-based criteria, consider both the job_title and the job_description for relevance.
2. Identify only the jobs that are a strong and direct match to ALL provided criteria.
3. If the user provides a 'description' in their search criteria, ensure the job's 'description' aligns well with it.
4. Pay very close attention to the job's 'description' and any 'skills_extracted' when matching against the user's 'position' and 'skills' criteria. The relevance to the job description is highly important.
5. Return your response STRICTLY as a single JSON object.
6. This JSON object must have one top-level key: "relevant_jobs".
7. The value of "relevant_jobs" must be a JSON list of job objects.
8. Each job object in this list must be identical in structure to the input job objects (i.e., include all original fields like "job_title", "company", "location", "salary", "apply_link", "description", "source", and any others present in the input).
9. If no jobs are a strong match, the "relevant_jobs" list should be empty ([]).
10. Do NOT include any explanations, apologies, or introductory text outside of the JSON object. The entire response should be only the JSON object.

Example of expected JSON output format:
{{
  "relevant_jobs": [
    {{
      "job_title": "Example Matched Job",
      "company": "Example Corp",
      // ... other fields from the original job data ...
    }},
    // ... other matched jobs ...
  ]
}}

Provide ONLY the JSON object containing the strongly matching jobs.
    """
    
    print(f"\n--- DEBUG: LLM_PROCESSOR.PY (GEMINI): LLM PROMPT (first 500 chars) ---\n{prompt[:500]}...\n--- END LLM PROMPT ---")

    try:
        # Forcing JSON output with Gemini can be done by specifying the MIME type
        # or by very clear instructions in the prompt.
        # The `generation_config` can be used for more control if needed.
        # model.generate_content also supports `generation_config=genai.types.GenerationConfig(...)`
        
        # It's better to use generate_content_async for FastAPI async functions if available and makes sense.
        # For simplicity, using synchronous generate_content here. If performance is critical, explore async.
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                # candidate_count=1, # default
                # stop_sequences=[],
                # max_output_tokens=2048, # adjust as needed
                temperature=0.1, # Lower temperature for more deterministic JSON output
                # top_p=,
                # top_k=,
                response_mime_type="application/json" # Request JSON output
            )
        )
        
        llm_response_content = response.text # Gemini SDK typically uses response.text
        print(f"\n--- DEBUG: LLM_PROCESSOR.PY (GEMINI): LLM RAW RESPONSE ---\n{llm_response_content}\n--- END LLM RAW RESPONSE ---")

        # Attempt to parse the LLM response as JSON
        try:
            # Sometimes, the LLM might still wrap the JSON in markdown (```json ... ```)
            # Simple regex to strip potential markdown fences
            match = re.search(r"```json\n(.*\n)```", llm_response_content, re.DOTALL)
            if match:
                llm_response_content = match.group(1).strip()
            
            parsed_response = json.loads(llm_response_content)
            if isinstance(parsed_response, dict) and "relevant_jobs" in parsed_response and isinstance(parsed_response["relevant_jobs"], list):
                relevant_jobs = parsed_response["relevant_jobs"]
            else:
                print(f"*** DEBUG: LLM_PROCESSOR.PY (GEMINI): LLM response JSON structure not as expected. Expected dict with 'relevant_jobs' list. Got: {parsed_response} ***")
                relevant_jobs = [] # Fallback to empty list

        except json.JSONDecodeError as e:
            print(f"*** DEBUG: LLM_PROCESSOR.PY (GEMINI): Error decoding LLM JSON response: {e}. Content: {llm_response_content[:200]}... ***")
            relevant_jobs = [] # If parsing fails, return no jobs

        print(f"Gemini LLM identified {len(relevant_jobs)} relevant jobs.")
        return relevant_jobs

    except Exception as e:
        print(f"*** DEBUG: LLM_PROCESSOR.PY (GEMINI): Exception during Gemini API call: {e} ***")
        # Consider if you want to return all jobs, or an empty list, or raise the exception
        return [] # Return empty list or handle error appropriately

if __name__ == '__main__':
    import asyncio
    async def test_llm_filter_example():
        if not GOOGLE_API_KEY or not model:
            print("Skipping LLM test: GOOGLE_API_KEY not set up or model not initialized.")
            return

        sample_jobs = [
            {
                "job_title": "Software Engineer Gemini Sample", 
                "company": "GeminiTestCo", 
                "experience": "3 years", 
                "location": "Mountain View, CA", 
                "salary": "150,000 USD", 
                "apply_link": "http://example.com/geminijob1",
                "description": "Seeking a skilled Software Engineer with experience in Python and cloud technologies for our team in Mountain View.",
                "skills_extracted": ["Python", "Cloud", "API Design"],
                "source": "manual_gemini_test"
            },
            {
                "job_title": "Frontend Developer", 
                "company": "WebWidgets Inc.", 
                "experience": "1-2 years", 
                "location": "Remote", 
                "salary": "Competitive", 
                "apply_link": "http://example.com/frontendjob",
                "description": "Exciting opportunity for a Frontend Developer to work with React and modern web technologies.",
                "skills_extracted": ["React", "JavaScript", "HTML", "CSS"],
                "source": "manual_gemini_test"
            }
        ]

        test_criteria_1 = {
            "position": "Software Engineer", 
            "skills": "Python, Cloud", 
            "location": "Mountain View"
        }
        test_criteria_2 = {
            "position": "Frontend Developer",
            "jobNature": "Remote"
        }
        
        print("\n--- Testing Gemini LLM Filter (Direct Function Call Example 1) ---")
        filtered_jobs_1 = await filter_jobs_with_llm(sample_jobs, test_criteria_1)
        print("--- Gemini LLM Filter Test Results 1 ---")
        if filtered_jobs_1:
            for job in filtered_jobs_1:
                print(json.dumps(job, indent=2))
        else:
            print("No jobs returned by Gemini LLM filter for criteria 1 or an error occurred.")

        print("\n--- Testing Gemini LLM Filter (Direct Function Call Example 2) ---")
        filtered_jobs_2 = await filter_jobs_with_llm(sample_jobs, test_criteria_2)
        print("--- Gemini LLM Filter Test Results 2 ---")
        if filtered_jobs_2:
            for job in filtered_jobs_2:
                print(json.dumps(job, indent=2))
        else:
            print("No jobs returned by Gemini LLM filter for criteria 2 or an error occurred.")

    # To run this example test (ensure GOOGLE_API_KEY is set in .env):
    # asyncio.run(test_llm_filter_example())
    # print("To test LLM processing with Gemini: \n1. Ensure GOOGLE_API_KEY is in .env. \n2. Populate jobs_data.json (e.g., via the /scrape API endpoint). \n3. Test through the /search API endpoint. \n4. (Optional) Uncomment and run `asyncio.run(test_llm_filter_example())` for a direct function call test with sample data.")
    if GOOGLE_API_KEY and model:
        print("\nTo run the test example directly, uncomment the asyncio.run line in `if __name__ == '__main__':` block.")
    else:
        print("\nPlease ensure GOOGLE_API_KEY is set in your .env file for the test example to run.")
    pass
