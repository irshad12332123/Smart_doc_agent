from config.settings import GROQ_API_KEY
from groq import Groq
def load_slm() -> Groq:
    """
    Initializes and returns the Groq client.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in environment variables.")
    return Groq(api_key=GROQ_API_KEY)
