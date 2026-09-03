import json
from src import config
from src.memory.session_store import SessionStore

# ─── Tool Implementations ──────────────────────────────────────────────

def search_problems(topic: str) -> str:
    """Search the JSON document for coding problems related to a topic."""
    try:
        with open(config.PROBLEMS_PATH, "r", encoding="utf-8") as f:
            problems_db = json.load(f)
            
        topic = topic.lower()
        results = []
        
        for category, problems in problems_db.items():
            if topic in category.lower():
                results.extend(problems)
                continue
                
            for prob in problems:
                # Search title and description for keywords
                if topic in prob["title"].lower() or topic in prob.get("description", "").lower():
                    results.append(prob)
                    
        if not results:
            return f"No practice problems found for topic '{topic}'."
            
        # Return first 3 to save context window
        formatted = json.dumps(results[:3], indent=2)
        return f"Found {len(results)} problems. Top results:\n{formatted}"
        
    except Exception as e:
        return f"Error searching problems database: {str(e)}"


def get_past_session(company: str) -> str:
    """Retrieve past session history (gap analysis) from the SQLite database."""
    try:
        store = SessionStore()
        # Find session matching company
        session = store.find_prior_session(company)
        
        if not session:
            return f"No past session history found for company '{company}'."
            
        return json.dumps(session, indent=2)
        
    except Exception as e:
        return f"Error accessing relational database: {str(e)}"


# ─── Tool Mappings and Schema ──────────────────────────────────────────

TOOLS_MAP = {
    "search_problems": search_problems,
    "get_past_session": get_past_session
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_problems",
            "description": "Searches the JSON document database for coding problems related to a specific topic or keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic, algorithm, or data structure to search for (e.g. 'arrays', 'dynamic programming', 'sql')"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_past_session",
            "description": "Queries the relational SQLite database for past session history and gap analysis for a specific company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "The name of the company to search history for."
                    }
                },
                "required": ["company"]
            }
        }
    }
]
