from langchain_core.prompts import ChatPromptTemplate

EXPLAIN_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a senior software engineer who specialises in reading and "
            "explaining legacy code. You write clear, jargon-free English that a "
            "junior developer or a non-technical stakeholder can understand.",
        ),
        (
            "human",
            "Below is a Java 8 source file together with a structural summary "
            "produced by an AST parser.\n\n"
            "## Structural Summary\n{structure_summary}\n\n"
            "## Source Code\n```java\n{source_code}\n```\n\n"
            "Explain what this code does. Cover:\n"
            "1. Overall purpose of the file / class.\n"
            "2. What each public method does, including edge cases.\n"
            "3. Any business rules or invariants encoded in the logic.\n"
            "4. Known patterns or anti-patterns you spot.\n\n"
            "Write in plain English with numbered sections.",
        ),
    ]
)

EXPLAIN_COBOL_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a senior software engineer who specialises in reading and "
            "explaining legacy COBOL code. You write clear, jargon-free English that a "
            "junior developer or a non-technical stakeholder can understand.",
        ),
        (
            "human",
            "Below is a COBOL source program together with a structural summary.\n\n"
            "## Structural Summary\n{structure_summary}\n\n"
            "## Source Code\n```cobol\n{source_code}\n```\n\n"
            "Explain what this program does. Cover:\n"
            "1. Overall purpose (PROGRAM-ID, main business logic).\n"
            "2. What each paragraph/section does, including data flow and key logic.\n"
            "3. Any business rules or calculations encoded in the logic.\n"
            "4. Known patterns or anti-patterns you spot.\n\n"
            "Write in plain English with numbered sections.",
        ),
    ]
)
