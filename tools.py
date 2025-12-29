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
def search_knowledge_base(query: str) -> str:
    """
    Search the local knowledge base for information.
    Use this tool when the user asks questions about the uploaded text files.
    """
    
    # Query ChromaDB
    results = collection.query(
        query_texts=[query],
        n_results=8 # Return top 8 matches
    )
    found = []
    # Combine the IDs and Documents into a readable string for the LLM
    if results['ids']:
        for i, doc in enumerate(results['documents'][0]):
            rid = results['ids'][0][i]
            print("RID : ", rid)
            found.append(f"[Report ID: {rid}] Content Snippet: {doc[:300]}...")
            
    return "\n".join(found) if found else "No related reports found."


def get_db_connection():
    return psycopg2.connect(dbname=TARGET_DB, **DB_CONFIG)

# --- Tool 1: SQL Lookup for IoCs ---
@function_tool
def search_indicators_by_report(report_id: int):
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


# --- Tool 3: SQL Filtering by Sector ---
@function_tool
def search_by_victim(sector: str):
    """Find reports targeting a specific sector."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT report_id, summary, created_at FROM reports WHERE victim_sector ILIKE %s", (f"%{sector}%",))
        results = cur.fetchall()
        return str(results)
    finally:
        conn.close()