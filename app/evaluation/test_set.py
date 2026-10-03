OS_GOLD_SET = [
    {
        "question": "Explain paging and define a page fault.",
        "in_scope": True,
        "gold_contexts": [
            "Paging: logical address space divided into fixed-size pages mapped to physical frames via a page table.",
            "Page Fault: interrupt raised by MMU when a page is not resident in physical memory and must be loaded from disk.",
        ],
        "gold_answer": "Paging divides memory into pages and frames managed by a page table. A page fault occurs when the requested page is not in physical memory.",
        "gold_keywords": ["paging", "page", "page fault", "frame", "page table", "memory"],
    },
    {
        "question": "What are the four necessary conditions for a deadlock?",
        "in_scope": True,
        "gold_contexts": [
            "Deadlock 4 conditions: Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait.",
        ],
        "gold_answer": "Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait are all required for a deadlock.",
        "gold_keywords": ["mutual exclusion", "hold", "wait", "preemption", "circular", "deadlock"],
    },
    {
        "question": "Compare a process and a thread.",
        "in_scope": True,
        "gold_contexts": [
            "Process: independent program instance with own address space and PCB.",
            "Thread: lightweight unit sharing parent's address space but with own stack and registers.",
        ],
        "gold_answer": "A process has its own address space while threads of the same process share address space but have private stacks.",
        "gold_keywords": ["process", "thread", "address", "space", "stack", "pcb"],
    },
    {
        "question": "Describe Banker's Algorithm and the meaning of a safe state.",
        "in_scope": True,
        "gold_contexts": [
            "Banker's Algorithm: deadlock avoidance that checks whether granting a resource request keeps the system in a safe state.",
            "Safe State: there exists an ordering (P1..Pn) such that every process can finish using currently available + resources freed by earlier processes.",
        ],
        "gold_answer": "Banker's Algorithm avoids deadlock by only granting requests that leave the system in a safe ordering of finishing processes.",
        "gold_keywords": ["banker", "safe", "state", "deadlock", "avoidance", "resource", "request"],
    },
    {
        "question": "What is thrashing and how does the working-set model mitigate it?",
        "in_scope": True,
        "gold_contexts": [
            "Thrashing: high page-fault rate causing CPU utilization to collapse because processes spend more time paging than executing.",
            "Working Set: the set of pages actively used during a locality window; allocate enough frames for each process's working set to stop thrashing.",
        ],
        "gold_answer": "Thrashing is excessive paging; working set ensures each process has enough frames to hold its locality pages.",
        "gold_keywords": ["thrashing", "page fault", "working", "set", "locality", "frame"],
    },
    {
        "question": "Explain semaphores and the difference between a mutex and a counting semaphore.",
        "in_scope": True,
        "gold_contexts": [
            "Semaphore: integer variable with atomic wait/signal operations controlling access to shared resources.",
            "Mutex (binary semaphore) = 0 or 1 for mutual exclusion; Counting semaphore = 0..N for N identical resources.",
        ],
        "gold_answer": "Semaphores protect critical sections. Mutex is binary; counting semaphore covers N identical units.",
        "gold_keywords": ["semaphore", "mutex", "lock", "counting", "critical", "atomic"],
    },
    {
        "question": "Contrast Round Robin scheduling and SJF scheduling.",
        "in_scope": True,
        "gold_contexts": [
            "Round Robin: preemptive FCFS with a time quantum, designed for interactive fairness.",
            "SJF: pick the process with smallest next CPU burst; optimal for minimum average waiting time but can starve long jobs.",
        ],
        "gold_answer": "RR gives every process a quantum for fairness; SJF minimizes average wait but can starve long jobs.",
        "gold_keywords": ["round", "robin", "quantum", "sjf", "scheduling", "preemptive", "fairness"],
    },
    {
        "question": "Who won the FIFA World Cup in 2022?",
        "in_scope": False,
        "gold_contexts": [],
        "gold_answer": "This is out of scope for the Operating Systems course material.",
        "gold_keywords": [],
    },
    {
        "question": "Give me a recipe for Masala Dosa.",
        "in_scope": False,
        "gold_contexts": [],
        "gold_answer": "This is out of scope for the Operating Systems course material.",
        "gold_keywords": [],
    },
]
