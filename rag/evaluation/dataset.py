"""
Benchmark Test Dataset for College Student Document Retrieval Evaluation.

Categories:
1. Notices & Circulars (Attendance, Exam reschedule, Fees, Placements, Library)
2. Time Tables (Semester schedule, Lab slots, Room allocations)
3. Subject Notes (Operating Systems, Data Structures, DBMS, Computer Networks)
4. Assignments & Lab Guides (AI Search, ML Project, OS IPC Lab)
"""

from typing import Any

COLLEGE_STUDENT_DOCUMENTS: list[dict[str, Any]] = [
    {
        "doc_id": "notice-001",
        "title": "Mandatory_75_Percent_Attendance_Rule_Notice.pdf",
        "category": "notice",
        "chunks": [
            {
                "chunk_id": "chunk-notice-001-1",
                "content": (
                    "UNIVERSITY ACADEMIC REGULATION NOTICE: Minimum Attendance Requirement.\n"
                    "All undergraduate (BCA, B.Tech) and postgraduate students are hereby notified "
                    "that a minimum of 75% attendance in lectures, tutorials, and practical lab sessions "
                    "is mandatory to be eligible for appearing in the End-Semester Final Examinations."
                ),
                "page_number": 1,
                "chunk_index": 0,
            },
            {
                "chunk_id": "chunk-notice-001-2",
                "content": (
                    "ATTENDANCE SHORTAGE CONDONATION RULES:\n"
                    "Students with attendance between 65% and 74.9% may apply for medical condonation by submitting "
                    "a valid medical certificate from a registered civil hospital within 3 working days of absence.\n"
                    "Students with attendance below 65% will be strictly detained and awarded an 'F' grade in the course."
                ),
                "page_number": 1,
                "chunk_index": 1,
            },
        ],
    },
    {
        "doc_id": "notice-002",
        "title": "End_Semester_Exam_Registration_And_Fee_Deadline.pdf",
        "category": "notice",
        "chunks": [
            {
                "chunk_id": "chunk-notice-002-1",
                "content": (
                    "OFFICE OF THE CONTROLLER OF EXAMINATIONS: Examination Form & Fee Notice.\n"
                    "The examination portal for the Spring 2026 End-Semester Examinations will open on October 1, 2026.\n"
                    "The last date for standard online examination fee submission is October 20, 2026 without late fee."
                ),
                "page_number": 1,
                "chunk_index": 0,
            },
            {
                "chunk_id": "chunk-notice-002-2",
                "content": (
                    "LATE FEE SCHEDULE:\n"
                    "- October 21 to October 25: Late fine of Rs. 500.\n"
                    "- October 26 to October 31: Late fine of Rs. 1500.\n"
                    "No exam forms will be accepted under any circumstances after October 31, 2026."
                ),
                "page_number": 1,
                "chunk_index": 1,
            },
        ],
    },
    {
        "doc_id": "notice-003",
        "title": "Campus_Placement_Drive_Eligibility_Criteria.pdf",
        "category": "notice",
        "chunks": [
            {
                "chunk_id": "chunk-notice-003-1",
                "content": (
                    "TRAINING & PLACEMENT CELL: Mega Campus Recruitment Drive 2026.\n"
                    "Top tier product and services firms including Google, Microsoft, Infosys, and TCS will visit "
                    "campus starting November 10, 2026 for Software Engineer and Data Analyst roles."
                ),
                "page_number": 1,
                "chunk_index": 0,
            },
            {
                "chunk_id": "chunk-notice-003-2",
                "content": (
                    "PLACEMENT ELIGIBILITY CRITERIA:\n"
                    "1. Minimum CGPA of 7.0 with no active backlogs / back papers.\n"
                    "2. 10th and 12th minimum score of 65% aggregate.\n"
                    "3. Formal dress code and university ID card mandatory during all interview rounds.\n"
                    "4. Students with offers above 12 LPA are ineligible for subsequent standard drives (Dream Offer Policy)."
                ),
                "page_number": 1,
                "chunk_index": 1,
            },
        ],
    },

    # ------------------ 2. TIME TABLES ------------------
    {
        "doc_id": "timetable-001",
        "title": "BCA_4th_Semester_Weekly_Class_Timetable.pdf",
        "category": "time_table",
        "chunks": [
            {
                "chunk_id": "chunk-tt-001-1",
                "content": (
                    "DEPARTMENT OF COMPUTER APPLICATIONS: BCA 4th Semester Timetable (Room 304, Block B).\n"
                    "- Monday: 09:00 - 10:30 AM: Operating Systems (Prof. Verma)\n"
                    "- Monday: 11:00 - 12:30 PM: Database Management Systems (Dr. Sharma)\n"
                    "- Monday: 01:30 - 04:30 PM: Operating Systems Practical Lab (Computer Lab 3, 2nd Floor)"
                ),
                "page_number": 1,
                "chunk_index": 0,
            },
            {
                "chunk_id": "chunk-tt-001-2",
                "content": (
                    "- Tuesday: 09:00 - 10:30 AM: Artificial Intelligence & Intelligent Agents (Dr. Rajesh Kumar)\n"
                    "- Tuesday: 11:00 - 12:30 PM: Computer Networks (Prof. Ananya Sen)\n"
                    "- Wednesday: 10:00 - 01:00 PM: DBMS Project Lab (Computer Lab 2)\n"
                    "- Thursday: 09:00 - 11:00 AM: Design and Analysis of Algorithms (Room 304)"
                ),
                "page_number": 1,
                "chunk_index": 1,
            },
            {
                "chunk_id": "chunk-tt-001-3",
                "content": (
                    "- Friday: 09:00 - 10:30 AM: Cloud Computing & Virtualization (Room 304)\n"
                    "- Friday: 11:00 - 01:00 PM: Soft Skills & Aptitude Training (Seminar Hall 1)\n"
                    "- Friday: 02:00 - 04:00 PM: Remedial and Doubt Clearing Sessions for DAA and OS."
                ),
                "page_number": 1,
                "chunk_index": 2,
            },
        ],
    },

    # ------------------ 3. SUBJECT NOTES ------------------
    {
        "doc_id": "notes-001",
        "title": "Operating_Systems_Deadlocks_And_Scheduling_Notes.pdf",
        "category": "notes",
        "chunks": [
            {
                "chunk_id": "chunk-os-001-1",
                "content": (
                    "OPERATING SYSTEMS: Deadlock Characterization (Coffman Conditions).\n"
                    "A deadlock occurs if and only if all four conditions hold simultaneously:\n"
                    "1. Mutual Exclusion: At least one resource must be held in a non-shareable mode.\n"
                    "2. Hold and Wait: A process must be holding at least one resource and waiting to acquire additional resources.\n"
                    "3. No Preemption: Resources cannot be preempted; a resource can only be released voluntarily by the process.\n"
                    "4. Circular Wait: A set of waiting processes {P0, P1, ..., Pn} exists such that P0 waits for a resource held by P1, and Pn waits for P0."
                ),
                "page_number": 1,
                "chunk_index": 0,
            },
            {
                "chunk_id": "chunk-os-001-2",
                "content": (
                    "DEADLOCK AVOIDANCE: Banker's Algorithm by Edsger Dijkstra.\n"
                    "The Banker's algorithm tests for safety by simulating the allocation of predetermined maximum possible "
                    "amounts of all resources, and then makes an 's-state' check to test for possible deadlock conditions "
                    "for all other pending activities before deciding whether allocation should be allowed to proceed.\n"
                    "Data structures used: Available[m], Max[n][m], Allocation[n][m], Need[n][m] where Need = Max - Allocation."
                ),
                "page_number": 2,
                "chunk_index": 1,
            },
            {
                "chunk_id": "chunk-os-001-3",
                "content": (
                    "CPU SCHEDULING ALGORITHMS:\n"
                    "- First-Come, First-Served (FCFS): Non-preemptive, suffers from Convoy Effect where short processes wait behind long ones.\n"
                    "- Shortest Job First (SJF): Optimal average waiting time. Preemptive version is Shortest Remaining Time First (SRTF).\n"
                    "- Round Robin (RR): Preemptive, uses a fixed Time Quantum (q). If q is very large, RR degenerates to FCFS. If q is very small, context switch overhead increases."
                ),
                "page_number": 3,
                "chunk_index": 2,
            },
        ],
    },
    {
        "doc_id": "notes-002",
        "title": "DBMS_Normalization_And_ACID_Properties_Notes.pdf",
        "category": "notes",
        "chunks": [
            {
                "chunk_id": "chunk-dbms-001-1",
                "content": (
                    "DATABASE MANAGEMENT SYSTEMS: Normalization Forms.\n"
                    "- 1NF (First Normal Form): All attributes contain atomic (indivisible) values, no repeating groups.\n"
                    "- 2NF (Second Normal Form): Table is in 1NF and contains no Partial Dependency (every non-prime attribute is fully functionally dependent on primary key).\n"
                    "- 3NF (Third Normal Form): Table is in 2NF and contains no Transitive Dependency (X -> Y where Y is non-prime and X is not a super key).\n"
                    "- BCNF (Boyce-Codd Normal Form): A stricter version of 3NF where for every functional dependency X -> Y, X must be a super key."
                ),
                "page_number": 1,
                "chunk_index": 0,
            },
            {
                "chunk_id": "chunk-dbms-001-2",
                "content": (
                    "TRANSACTION MANAGEMENT: ACID Properties in DBMS.\n"
                    "- Atomicity: All operations in a transaction succeed, or the entire transaction is rolled back (All or Nothing).\n"
                    "- Consistency: Transaction brings the database from one valid state to another, preserving all integrity constraints.\n"
                    "- Isolation: Concurrent execution of transactions yields the same system state as if transactions were executed serially.\n"
                    "- Durability: Once a transaction commits, its changes survive even across system crashes or power failures (Write-Ahead Logging)."
                ),
                "page_number": 2,
                "chunk_index": 1,
            },
        ],
    },
    {
        "doc_id": "notes-003",
        "title": "Computer_Networks_TCP_IP_And_Subnetting_Notes.pdf",
        "category": "notes",
        "chunks": [
            {
                "chunk_id": "chunk-cn-001-1",
                "content": (
                    "COMPUTER NETWORKS: TCP 3-Way Handshake Connection Establishment.\n"
                    "Step 1 (SYN): The client sends a TCP segment with SYN flag set and an initial sequence number (ISN_client) to server.\n"
                    "Step 2 (SYN-ACK): The server replies with SYN flag and ACK flag set, acknowledging ISN_client + 1 and providing ISN_server.\n"
                    "Step 3 (ACK): The client sends an ACK packet acknowledging ISN_server + 1. Connection state changes to ESTABLISHED."
                ),
                "page_number": 1,
                "chunk_index": 0,
            },
            {
                "chunk_id": "chunk-cn-001-2",
                "content": (
                    "IP ADDRESSING AND CIDR SUBNETTING:\n"
                    "Classless Inter-Domain Routing (CIDR) uses slash notation e.g., 192.168.1.0/24.\n"
                    "Number of host bits = 32 - prefix_length. Total available hosts = 2^(32 - prefix_length) - 2 (subtracting network and broadcast addresses).\n"
                    "Example: A /26 subnet has 32 - 26 = 6 host bits, yielding 2^6 - 2 = 62 usable host IP addresses."
                ),
                "page_number": 2,
                "chunk_index": 1,
            },
        ],
    },

    # ------------------ 4. ASSIGNMENTS ------------------
    {
        "doc_id": "assign-001",
        "title": "AI_Search_Algorithms_Assignment_1_Instructions.pdf",
        "category": "assignment",
        "chunks": [
            {
                "chunk_id": "chunk-ai-assign-001-1",
                "content": (
                    "ARTIFICIAL INTELLIGENCE: Assignment 1 - Informed Search and Adversarial Search.\n"
                    "Due Date: October 15, 2026 at 11:59 PM.\n"
                    "Submission Format: GitHub Repository link containing Python code and PDF report submitted via LMS.\n"
                    "Tasks:\n"
                    "Task 1: Implement A* Search algorithm for solving the 8-Puzzle Problem using Manhattan Distance and Misplaced Tiles heuristics."
                ),
                "page_number": 1,
                "chunk_index": 0,
            },
            {
                "chunk_id": "chunk-ai-assign-001-2",
                "content": (
                    "Task 2: Implement Minimax algorithm with Alpha-Beta Pruning for a 4x4 Tic-Tac-Toe agent.\n"
                    "Evaluation Rubric (Total 20 Marks):\n"
                    "- Code Correctness & Heuristic Admissibility: 8 Marks\n"
                    "- Benchmark Node Expansion Analysis Report: 6 Marks\n"
                    "- Code Style, Unit Tests, and PEP8 Compliance: 6 Marks\n"
                    "Late submissions will incur a 10% penalty per 24 hours."
                ),
                "page_number": 2,
                "chunk_index": 1,
            },
        ],
    },
    {
        "doc_id": "assign-002",
        "title": "Operating_Systems_Lab_IPC_Assignment_2.pdf",
        "category": "assignment",
        "chunks": [
            {
                "chunk_id": "chunk-os-assign-002-1",
                "content": (
                    "OPERATING SYSTEMS LAB: Practical Assignment 2 - Inter-Process Communication (IPC).\n"
                    "Submission Deadline: October 18, 2026.\n"
                    "Objective: Implement a Producer-Consumer problem in C using POSIX Shared Memory (shm_open, mmap) and POSIX Semaphores (sem_open, sem_wait, sem_post).\n"
                    "Requirement: Ensure race conditions are completely eliminated with proper mutual exclusion."
                ),
                "page_number": 1,
                "chunk_index": 0,
            },
        ],
    },
]


# Curated benchmark test queries with ground-truth relevance judgements
COLLEGE_EVALUATION_QUERIES: list[dict[str, Any]] = [
    # 1. Keyword / Exact Queries (Favors BM25)
    {
        "query_id": "q-001",
        "query": "Coffman conditions for deadlock",
        "query_type": "keyword",
        "ground_truth_chunks": ["chunk-os-001-1"],
        "ground_truth_docs": ["notes-001"],
        "description": "Exact keyword match for Operating Systems Coffman conditions",
    },
    {
        "query_id": "q-002",
        "query": "BCA Room 304 Monday Operating Systems lab timing",
        "query_type": "keyword",
        "ground_truth_chunks": ["chunk-tt-001-1"],
        "ground_truth_docs": ["timetable-001"],
        "description": "Specific schedule details for Monday timetable",
    },
    {
        "query_id": "q-003",
        "query": "CIDR /26 usable hosts formula",
        "query_type": "keyword",
        "ground_truth_chunks": ["chunk-cn-001-2"],
        "ground_truth_docs": ["notes-003"],
        "description": "Exact networking subnetting formula query",
    },
    {
        "query_id": "q-004",
        "query": "Banker's algorithm Available Max Allocation Need formula",
        "query_type": "keyword",
        "ground_truth_chunks": ["chunk-os-001-2"],
        "ground_truth_docs": ["notes-001"],
        "description": "Banker's algorithm formula and data structures",
    },

    # 2. Semantic / Paraphrased Queries (Favors Dense Embeddings)
    {
        "query_id": "q-005",
        "query": "What happens if my attendance is less than the required minimum threshold for exams?",
        "query_type": "semantic",
        "ground_truth_chunks": ["chunk-notice-001-1", "chunk-notice-001-2"],
        "ground_truth_docs": ["notice-001"],
        "description": "Paraphrased query regarding low attendance penalty and rules",
    },
    {
        "query_id": "q-006",
        "query": "How to ensure database changes remain permanently stored even after power outage or hardware failure?",
        "query_type": "semantic",
        "ground_truth_chunks": ["chunk-dbms-001-2"],
        "ground_truth_docs": ["notes-002"],
        "description": "Semantic query describing Durability in ACID properties without saying 'Durability'",
    },
    {
        "query_id": "q-007",
        "query": "Why does a CPU scheduler with a very small time slice slow down the operating system?",
        "query_type": "semantic",
        "ground_truth_chunks": ["chunk-os-001-3"],
        "ground_truth_docs": ["notes-001"],
        "description": "Semantic query describing Round Robin context switch overhead",
    },
    {
        "query_id": "q-008",
        "query": "What are the rules for submitting a doctor's certificate if I get sick and miss lectures?",
        "query_type": "semantic",
        "ground_truth_chunks": ["chunk-notice-001-2"],
        "ground_truth_docs": ["notice-001"],
        "description": "Medical certificate submission rules for condonation",
    },

    # 3. Hybrid / Compound Queries (Requires both lexical precision and semantic understanding)
    {
        "query_id": "q-009",
        "query": "When is the last date to submit AI Assignment 1 on 8-puzzle and what are the rubric marks for heuristic report?",
        "query_type": "hybrid",
        "ground_truth_chunks": ["chunk-ai-assign-001-1", "chunk-ai-assign-001-2"],
        "ground_truth_docs": ["assign-001"],
        "description": "Compound query with specific entity names and deadline questions",
    },
    {
        "query_id": "q-010",
        "query": "What is the penalty if I register for end semester examinations after October 20 2026?",
        "query_type": "hybrid",
        "ground_truth_chunks": ["chunk-notice-002-1", "chunk-notice-002-2"],
        "ground_truth_docs": ["notice-002"],
        "description": "Late fine query combining specific dates and policy details",
    },
    {
        "query_id": "q-011",
        "query": "How does client and server establish connection using SYN and ACK flags sequence numbers?",
        "query_type": "hybrid",
        "ground_truth_chunks": ["chunk-cn-001-1"],
        "ground_truth_docs": ["notes-003"],
        "description": "TCP 3-way handshake process query",
    },
    {
        "query_id": "q-012",
        "query": "Difference between 3NF and BCNF dependencies with super key constraints",
        "query_type": "hybrid",
        "ground_truth_chunks": ["chunk-dbms-001-1"],
        "ground_truth_docs": ["notes-002"],
        "description": "Database normalization comparison query",
    },
    {
        "query_id": "q-013",
        "query": "Placement drive minimum CGPA cutoff and dream offer policy rules",
        "query_type": "hybrid",
        "ground_truth_chunks": ["chunk-notice-003-2"],
        "ground_truth_docs": ["notice-003"],
        "description": "Campus recruitment eligibility and Dream Offer criteria",
    },
    {
        "query_id": "q-014",
        "query": "Where and when is the practical laboratory for Producer-Consumer Operating Systems assignment?",
        "query_type": "hybrid",
        "ground_truth_chunks": ["chunk-tt-001-1", "chunk-os-assign-002-1"],
        "ground_truth_docs": ["timetable-001", "assign-002"],
        "description": "Cross-document query linking timetable lab slot with assignment requirements",
    },
]


def get_flattened_chunks() -> list[dict[str, Any]]:
    """Return all chunks in flattened format ready for BM25 and Dense indexing."""
    flattened: list[dict[str, Any]] = []
    for doc in COLLEGE_STUDENT_DOCUMENTS:
        for chunk in doc["chunks"]:
            flattened.append({
                "id": chunk["chunk_id"],
                "chunk_id": chunk["chunk_id"],
                "document_id": doc["doc_id"],
                "doc_id": doc["doc_id"],
                "content": chunk["content"],
                "text": chunk["content"],
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "title": doc["title"],
                "category": doc["category"],
            })
    return flattened
