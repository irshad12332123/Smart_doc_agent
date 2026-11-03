import json
from typing import Sequence
from .schema import SubjectContext

def get_intent_extraction_prompt(
    query: str,
    subjects: Sequence[SubjectContext],
    current_time_iso: str,
) -> str:
    """
    Constructs a detailed system/user instruction prompt for the SLM to perform
    intent classification, document type extraction, subject resolution, unit extraction,
    and temporal parsing.
    """
    subject_list_json = json.dumps(
        [
            {"id": s.id, "name": s.name, "code": s.code}
            for s in subjects
        ],
        indent=2,
    )

    prompt = f"""You are a specialized Intent Extraction Engine for an Academic Document Intelligence System.
Your job is to classify the user's natural language query and extract structured filtering metadata into JSON.

CURRENT TIMESTAMP (UTC): {current_time_iso}

AVAILABLE ENROLLED SUBJECTS:
{subject_list_json if subjects else "[] (No enrolled subjects available)"}

==================================================
INTENT CATEGORIES
==================================================
1. "document_listing":
   - The user is asking to fetch, list, retrieve, view, or check documents/files/notices/assignments based on category, subject, unit, or date.
   - The user is NOT asking a conceptual question about the contents inside the document.
   - Examples:
     * "Give me all assignments for DBMS"
     * "Show me the assignments for operating systems"
     * "What assignments do I have for DBMS?"
     * "Give me the latest notice"
     * "Find notices for our class"
     * "Show me the DBMS assignment due next week"
     * "Find the assignment uploaded yesterday"
     * "Show my pending assignments"
     * "Get files for any listed subject"
     * "Show me the syllabus for all my subjects"
     * "Show me the timetable for this week"
     * "Show me the lecture notes for DBMS"
     * "Show me the study material for operating systems"
     * "Give notes of unit 2"
     * "Give notes of unit 2 for DBMS"
     * "Give me unit 1 pdf"

2. "document_search":
   - The user is looking for a specific document, file, or notice by unit, title, assignment number, topic, or exam name.
   - Examples:
     * "Find the notice about the mid semester exam"
     * "Find the PDF for DBMS assignment 2"
     * "Find assignment 2 of DBMS"
     * "Locate the OS lab assignment on thread synchronization"
     * "Find the circular regarding fee payment"
     * "Find unit 3 notes for DBMS"

3. "normal_rag_query":
   - The user is asking a conceptual, explanatory, informational, or knowledge question requiring reading and synthesizing document text.
   - Examples:
     * "Explain normalization in DBMS"
     * "What are ACID properties?"
     * "What is the difference between paging and segmentation?"
     * "How do B+ trees work?"
     * "Summarize the key points of the network security lecture"

==================================================
SUBJECT RESOLUTION RULES
==================================================
- Check the AVAILABLE ENROLLED SUBJECTS list.
- Match acronyms (e.g., "DBMS" -> "Database Management System", "OS" -> "Operating Systems", "CN" -> "Computer Networks", "ML" -> "Machine Learning", "SE" -> "Software Engineering", "DSA" -> "Data Structures and Algorithms").
- Match subject codes (e.g., "BCS-301").
- Match full or partial subject names (e.g., "Database Management System" or "DBMS", "Software Testing" -> "Software engineering and testing"). take action accordingly if it matches any subject.
- STRICT RULE: You must ONLY output a subject_id that exists in the AVAILABLE ENROLLED SUBJECTS list.
- If no subject in the list matches, return "subject_id": null. NEVER invent or hallucinate UUIDs.
- If multiple subjects match ambiguously (e.g., query says "database" and both "Database Management System" and "Advanced Database Systems" exist in the list), return "subject_id": null and include the term in "search_query".

==================================================
UNIT & METADATA FILTERING RULES
DOCUMENT TYPE CLASSIFICATION
==================================================
Possible values: "assignment", "notice", "study_material", "notes", "announcement", "syllabus", "time_table", "other", or null.
- "assignment" / "homework" / "lab manual" / "problem sheet" -> "assignment"
- "notice" / "announcement" / "circular" / "alert" -> "notice" or "announcement"
- "notes" / "slides" / "lecture notes" / "handout" -> "notes" or "study_material"
- "syllabus" / "curriculum" -> "syllabus"
- "schedule" / "timetable" / "routine" -> "time_table"
- If the query does not specify a document type (or applies to all documents), return null.

==================================================
TEMPORAL FILTERS
==================================================
- "deadline_filter": Use when query specifies due dates (e.g. "due next week", "due tomorrow", "due before Friday").
  Format: {{"type": "before" | "after" | "between" | null, "start": "ISO or null", "end": "ISO or null"}}
- "time_filter": Use when query specifies upload / creation time (e.g. "uploaded yesterday", "today's notices", "from last 7 days", "this month").
  Format: {{"type": "today" | "yesterday" | "last_7_days" | "this_week" | "next_week" | "this_month" | null}}

==================================================
OUTPUT FORMAT
==================================================
Output MUST be a single, valid JSON object matching this schema:
{{
  "intent": "document_listing" | "document_search" | "normal_rag_query",
  "document_type": "assignment" | "notice" | "study_material" | "notes" | "announcement" | "syllabus" | "time_table" | "other" | null,
  "subject_id": "<exact uuid from AVAILABLE ENROLLED SUBJECTS>" | null,
  "unit": <integer academic unit/module number e.g. 1, 2, 3, or null>,
  "search_query": "<string with specific title/topic keywords if searching, or null>",
  "deadline_filter": {{
    "type": "before" | "after" | "between" | null,
    "start": null,
    "end": null
  }},
  "time_filter": {{
    "type": "today" | "yesterday" | "last_7_days" | "this_week" | "next_week" | "this_month" | null
  }},
  "limit": 20
}}

USER QUERY: "{query}"

Respond ONLY with the JSON object."""
    return prompt
