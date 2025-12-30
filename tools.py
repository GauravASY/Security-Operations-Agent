from agents import function_tool
from vectorstore import collection
import requests
import psycopg2
import json
import chromadb
from database import DB_CONFIG, TARGET_DB

# Connect to DBs
chroma_client = chromadb.PersistentClient(path="./my_local_db")
collection = chroma_client.get_or_create_collection(name="pdf_knowledge_base_v2")

@function_tool
async def get_list_of_jobs(job_title:str, location:str, experience:str, country:str = 'in', employment_type:str = 'FULLTIME'):
    """
    Returns a list of jobs
    Args:
        job_title (str): The job title to search for
        location (str): The location to search for
        country (str): The country to search for
        employment_type (str): The employment type to search for. For example 'FULLTIME', 'PARTTIME', 'CONTRACTOR', 'INTERN'
        experience (str): Find jobs with specific experience level, specified as a comma delimited list of the following values: under_3_years_experience, more_than_3_years_experience, no_experience, no_degree.
    
    Returns:
        list: A list of jobs
    """
    url = "https://jsearch.p.rapidapi.com/search"
    params = {
        "query": f"{job_title} jobs in {location}",
        "country": country,
        "employment_types": employment_type,
        "job_requirements": experience,
    }
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        return "get_list_of_jobs tool call failed"


@function_tool
def search_knowledge_base(query: str, filename:str) -> str:
    """
    Search the local knowledge base for information about a specific file.
    Use this tool when the user asks questions about the uploaded text file.
    """
    print("Filename : ", filename)
    # Query ChromaDB
    results = collection.query(
        query_texts=[query],
        where={"filename": {"$eq": filename}},
        n_results=5 # Return top 5 matches
    )
    # Combine the IDs and Documents into a readable string for the LLM
    print("Results : \n", results)
    # Format results as a single string for the Agent
    found_text = "\n\n".join(results['documents'][0])
    print("Found Text : \n", found_text)
    return found_text


def get_db_connection():
    return psycopg2.connect(dbname=TARGET_DB, **DB_CONFIG)

# --- Tool 1: SQL Lookup for IoCs ---
@function_tool
async def search_indicators_by_report(report_id: int):
    """Fetch all IoCs associated with a specific report ID."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT type, value FROM iocs WHERE report_id = %s", (report_id,))
        results = cur.fetchall()
        if not results:
            return "No indicators found for this report."
        return json.dumps([{"type": r[0], "value": r[1]} for r in results])
    finally:
        conn.close()


# --- Tool 2: SQL Filtering by Sector ---
@function_tool
async def search_by_victim(sector: str):
    """Find reports targeting a specific sector."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT report_id, summary, created_at FROM reports WHERE victim_sector ILIKE %s", (f"%{sector}%",))
        results = cur.fetchall()
        return str(results)
    finally:
        conn.close()

@function_tool
async def get_file_content(filename: str):
    """Fetch the content and summary of a specific file."""
    name = filename.split("\\")[-1]
    print("Filename : ", name)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT raw_content, summary FROM reports WHERE filename = %s", (name,))
        result = cur.fetchone()
        if not result:
            return "File not found."
        return result
    finally:
        conn.close()