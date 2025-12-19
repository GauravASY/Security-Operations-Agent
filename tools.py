from agents import function_tool
from vectorstore import collection
import requests

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
        n_results=3 # Return top 3 matches
    )
    print("Results : \n", results)
    # Format results as a single string for the Agent
    found_text = "\n\n".join(results['documents'][0])
    print("Found Text : \n", found_text)
    return found_text