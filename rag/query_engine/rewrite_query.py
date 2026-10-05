from rag.language_models.sml import load_slm

def rewrite_query(query: str, model: str) -> str:
    client = load_slm()
    prompt = f"""
    You are a query rewriting assistant. Your task is to rewrite the user's query to be more effective for retrieving relevant information from a database. The rewritten query should be clear, concise, and focused on the user's intent. Avoid adding any additional information or context that is not present in the original query.
    User's query: "{query}"
    Please provide the rewritten query in a single line, without any additional text or explanation.
    """
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        model=model,
        temperature=0.2,
        max_tokens=100,
        response_format={"type": "text"}
    )
    return response.output_text.strip()
