# AI Agent Instructions for RAG System Development

## 🎯 Purpose

This repository implements a **production-grade Retrieval-Augmented Generation (RAG) system** for real users. This is not a demo, prototype, or proof-of-concept.

Any AI agent (Claude, ChatGPT, Cursor, Codex) working in this codebase **must behave like a senior AI engineer**, prioritizing:

1. **Correctness** — the system must provide accurate, reliable answers
2. **Retrieval Quality** — garbage in, garbage out
3. **Safety** — never hallucinate, never guess, never invent policy
4. **Explainability** — every decision must be defensible to humans
5. **Long-term Maintainability** — code will be debugged 6 months from now

**Speed and cleverness are explicitly secondary concerns.**

---

## 🚨 CRITICAL: Read Task Requirements Carefully

**Before you start ANY work:**

1. ✅ Read the ENTIRE task description (every word, every section)
2. ✅ Identify what you ARE building (explicit scope)
3. ✅ Identify what you ARE NOT building (out of scope)
4. ✅ List ALL explicit requirements (UI, file formats, features, APIs, etc.)
5. ✅ Create plan.md addressing ALL requirements
6. ✅ Wait for approval before writing any code

**Common failure mode**: Agents skip requirements or build the wrong thing because they don't read carefully or make assumptions.

**Example of reading carefully**:
```
Task: "Build a document loader with web UI that supports MD, PDF, DOCX"

✅ Correct understanding:
What I'm building:
- Document loader class
- Web UI (Flask/FastAPI)
- Support for: MD, PDF, DOCX (minimum)
- File loading and text extraction

What I'm NOT building:
- Chunking logic
- Vector embeddings
- Retrieval/search
- LLM integration

❌ Incorrect understanding (missing requirements):
- Built: Document loader only
- Missing: Web UI requirement  ← FAIL
- Missing: DOCX support        ← FAIL
```

**Checklist before planning**:
- [ ] I read every sentence of the task
- [ ] I listed all explicit "must have" features
- [ ] I identified what's explicitly out of scope
- [ ] I noted all file formats/technologies mentioned
- [ ] I understand what success looks like

---

## ⚖️ Core Principles (Non-Negotiable)

| Principle | Explanation |
|-----------|-------------|
| **Read requirements fully** | Missing a requirement = failed implementation |
| **Retrieval quality > Model intelligence** | No LLM can compensate for bad chunking or retrieval |
| **Deterministic behavior > Creative answers** | Prefer predictable, repeatable outputs |
| **Explicit control > Implicit magic** | Avoid "framework magic"; make behavior transparent |
| **Refuse when uncertain** | If the system doesn't know, it must say so |
| **Every choice must be explainable** | Document decisions for human review |

---

## 1️⃣ Coding Standards

### General Guidelines

```python
# ✅ Good: Clear, explicit, boring
def chunk_by_section_headers(document: str, metadata: dict) -> list[Chunk]:
    """Split document at H2 headers, preserving semantic boundaries."""
    sections = re.split(r'\n## ', document)
    return [Chunk(text=s, metadata=metadata) for s in sections if s.strip()]

# ❌ Bad: Clever, obscure, "framework magic"
def smart_chunk(doc, **kwargs):
    return ChunkerFactory.create(**kwargs).auto_chunk(doc)
```

**Rules:**
- Write **clear, boring, readable code**
- Prefer **explicit logic over abstraction**
- Avoid "framework magic" unless explicitly justified
- Functions should **do one thing** and do it well
- No premature optimization

### Python-Specific

- Use **modern Python** (3.10+)
- Add **type hints** where they improve clarity
- **No unused imports**
- **No hidden global state**
- Avoid **side effects at import time**

### Comments

Explain **why**, not **what**.

```python
# ✅ Good
# We chunk at headers because splitting mid-paragraph 
# destroys context for policy questions
chunks = split_at_headers(document)

# ❌ Bad
# Split the document into chunks
chunks = split_at_headers(document)
```

**Especially explain:**
- Chunking strategy rationale
- Retrieval filtering decisions
- Prompt constraints and refusal logic
- Why certain edge cases are handled a specific way

### Logging (IMPORTANT: Use Structured Format)

Log **decisions**, not noise. Use **structured key=value format** for parseability.

```python
# ✅ Good: Structured, parseable, decision-focused
logger.info(
    "event=retrieval_complete query='%s' chunks=%d scores=%s",
    query,
    len(chunks),
    [round(c.score, 3) for c in chunks]
)

logger.warning(
    "event=file_skipped path='%s' reason='%s'",
    file_path,
    "corrupted PDF structure"
)

logger.error(
    "event=extraction_failed path='%s' format=%s error='%s'",
    file_path,
    "pdf",
    str(error)
)

# ❌ Bad: Unstructured, noisy, unparseable
logger.debug("Entering retrieval function")
logger.debug("Query received")
logger.info("Retrieved some chunks")
logger.error("Something failed")
```

**Event-driven logging template**:
```python
logger.{level}("event={event_name} {key1}='{value1}' {key2}={value2} ...")
```

**Always log** (with structured format):
- Start/completion of major operations (`event=operation_start`, `event=operation_complete`)
- Retrieved chunks and scores (`event=retrieval_complete`)
- Files processed/skipped (`event=file_loaded`, `event=file_skipped`)
- Refusal/escalation reasons (`event=refusal`)
- Metadata filters applied (`event=filter_applied`)
- Performance metrics (`duration_ms=123`, `file_count=45`)
- Errors with context (`event=error`, `path=...`, `reason=...`)

**Never log** (noise):
- Function entry/exit without decisions
- Variable assignments
- Loop iterations
- Successful operations without useful metrics

---

## 2️⃣ RAG-Specific Engineering Rules

### Knowledge Definition

**Not all text is knowledge.**

Knowledge must be:
- ✅ Factual and authoritative
- ✅ Intended to answer user questions
- ✅ Currently accurate and maintained

**Do NOT ingest:**
- ❌ Navigation menus ("Home | About | Contact")
- ❌ Boilerplate ("© 2024 All Rights Reserved")
- ❌ Duplicated legal disclaimers
- ❌ Empty or structural-only content
- ❌ Marketing copy that doesn't answer questions

**Example:**
```python
# ✅ Good knowledge
"Employees are eligible for 15 days of paid vacation per year after 90 days of employment."

# ❌ Not knowledge (navigation)
"Benefits > Time Off > Vacation Policy"

# ❌ Not knowledge (boilerplate)
"This policy is subject to change. For questions, contact HR."
```

### Chunking Strategy

**Chunk by semantic structure, NOT raw token count.**

```python
# ✅ Good: Semantic boundaries
chunks = split_at_headers(document)

# ❌ Bad: Arbitrary token limits
chunks = split_every_n_tokens(document, n=512)
```

**Rules:**
- Use **headers as natural boundaries** (H2, H3)
- **Never split mid-sentence**
- Each chunk must be **meaningful in isolation**
- Preserve **context** (e.g., parent section title)

**Warning:**
> Bad chunking = bad system.  
> No prompt or model can fix bad chunking.

**Example of good chunking:**
```
Chunk 1:
Section: "Vacation Policy"
Text: "Full-time employees receive 15 days of paid vacation annually..."

Chunk 2:
Section: "Sick Leave Policy"
Text: "Employees receive 10 days of paid sick leave per year..."
```

### Metadata (Mandatory)

**Every chunk MUST carry:**

```python
@dataclass
class Chunk:
    text: str
    metadata: ChunkMetadata

@dataclass
class ChunkMetadata:
    source_document: str      # "employee_handbook.pdf"
    section_path: str          # "Benefits > Time Off > Vacation"
    chunk_index: int           # Position in document
    document_type: str         # "policy" | "faq" | "guide"
    created_at: datetime       # When chunk was created
    last_updated: datetime     # When source was last modified
```

**If metadata is missing, the implementation is incomplete.**

### Retrieval

```python
# ✅ Good: Inspectable, filterable retrieval with logging
results = vector_store.search(
    query=query_embedding,
    top_k=5,
    filters={"document_type": "policy", "last_updated": "> 2024-01-01"}
)
logger.info(
    "event=retrieval_complete query='%s' chunks=%d scores=%s filters=%s",
    query,
    len(results),
    [round(r.score, 3) for r in results],
    str(filters)
)

# ❌ Bad: Black-box retrieval, no logging
results = magic_retrieval_function(query)
```

**Requirements:**
- Similarity search must be **inspectable**
- Must support **metadata filtering**
- **Always log** what was retrieved and why
- Store retrieval results for debugging

### Prompts as Contracts

**Prompts are contracts, not suggestions.**

```python
# ✅ Good prompt
SYSTEM_PROMPT = """
You are a customer support assistant. You MUST:

1. ONLY answer using the provided context
2. If the context doesn't contain the answer, respond: "I don't have enough information to answer that. Please contact support@company.com"
3. NEVER make up policy details
4. NEVER speculate or guess

Context:
{context}

Question: {question}
"""

# ❌ Bad prompt
SYSTEM_PROMPT = """
You're a helpful assistant. Answer the user's question based on this context:
{context}
"""
```

**Prompts must:**
- **Forbid hallucinations** explicitly
- **Allow explicit "I don't know"** responses
- **Enforce refusal** when context is insufficient
- Include **examples** of good/bad responses

---

## 3️⃣ Model Usage Rules

### Configuration

```python
# ✅ Default configuration
model_config = {
    "temperature": 0.0,      # No creativity
    "model": "gpt-4",        # Prefer OpenAI for safety
    "max_tokens": 500,       # Concise answers
}
```

**Rules:**
- **Temperature defaults to 0** (deterministic)
- **No creative writing, speculation, or policy invention**
- Prefer **OpenAI models** for instruction-following and safety
- Use **structured outputs** where possible

**Remember:**
> The model is a reasoning engine, not a source of truth.

### Model Selection Guide

| Use Case | Recommended Model | Rationale |
|----------|------------------|-----------|
| Production answers | GPT-4 | Best instruction-following, safety |
| Development/testing | GPT-3.5-Turbo | Faster, cheaper iteration |
| Embeddings | text-embedding-3-small | Cost-effective, good quality |

---

## 4️⃣ Planning-First Workflow (MANDATORY)

### 🔴 This is absolutely required

**The agent must NEVER implement code immediately.**

### Critical Planning Rules

**BEFORE creating plan.md:**
1. ✅ Read the FULL task description (every word)
2. ✅ List ALL explicit requirements from the task
3. ✅ Identify what's in scope vs out of scope
4. ✅ Note all technologies, file formats, features mentioned

**IN plan.md:**
1. ✅ Include "Requirements Checklist" section listing every requirement
2. ✅ Include "What This IS" and "What This IS NOT" sections
3. ✅ Answer all questions posed in the task
4. ✅ Address every requirement explicitly

### Two-Step Process

#### Step 1: Planning Phase (Required)

Before writing or modifying **any** code, create **`plan.md`**.

**Mandatory Template:**

```markdown
# Implementation Plan

## Objective
[What is being implemented - be specific and complete]

## Requirements Checklist
[Read the task and extract EVERY requirement]
- [ ] Requirement 1: [e.g., "Web UI using Flask"]
- [ ] Requirement 2: [e.g., "Support PDF, DOCX, XLSX formats"]
- [ ] Requirement 3: [e.g., "Recursive directory traversal"]
- [ ] Requirement 4: [e.g., "Real-time progress tracking"]
- [ ] ...

## Scope Definition

### What This IS (In Scope)
- [Specific component/feature being built]
- [Technology choice 1]
- [Technology choice 2]
- ...

### What This IS NOT (Out of Scope)
- [Things explicitly not being built now]
- [Future work]
- [Related but separate concerns]

## Assumptions
- [Technical assumptions]
- [Environment assumptions]
- [Dependency assumptions]

## Design Decisions

### Technology Choices
For each major technology choice, explain:

**Choice 1: [Library/Framework X for Y]**
- **Rationale**: Why this choice?
- **Alternatives considered**: What else was considered?
- **Trade-offs**: What are we giving up?

Example:
**PDF Extraction: pypdf**
- **Rationale**: Pure Python, no system dependencies, good for text extraction
- **Alternatives**: pdfplumber (heavier), pymupdf (C dependency)
- **Trade-offs**: May struggle with complex PDFs, but sufficient for text documents

### Architecture Overview
[High-level design, data flow, component interaction]

### File Structure
```
project/
├── component1/
│   ├── __init__.py
│   └── module1.py
├── component2/
│   └── ...
```

### Error Handling Strategy
[How errors will be handled]
- **Error category 1**: [Behavior]
- **Error category 2**: [Behavior]

### Logging Strategy
[What events will be logged]
- `event=X`: [When this is logged]
- `event=Y`: [When this is logged]

## Implementation Steps
1. **Step 1**: [Concrete action with file names]
2. **Step 2**: [Concrete action with file names]
3. ...

## Testing Strategy
- [ ] **Test 1**: [What is being tested and how]
- [ ] **Test 2**: [What is being tested and how]
- [ ] **Edge case 1**: [Specific edge case]
- [ ] ...

## Risks & Mitigation
- **Risk 1**: [What could go wrong]
  - **Mitigation**: [How to handle it]
  - **Fallback**: [Plan B]

## Questions Answered
[If task posed specific questions, answer them]
1. **Question from task**: [Answer with rationale]
2. **Question from task**: [Answer with rationale]

## Open Questions
[Things needing human clarification]
- [Question 1]
- [Question 2]
```

**No code is allowed in this phase.**

#### Step 2: Execution Phase (Explicit Approval Required)

**Only after the human explicitly approves:**
- "Proceed with the plan"
- "Execute plan.md"
- "Approved — implement"
- "LGTM, go ahead"
- "Yes, implement this"
- "Go ahead"

**Then and only then** may the agent:
- Modify files
- Add new code
- Refactor existing code

**If approval is not given or is ambiguous, do nothing and ask for clarification.**

### Example Workflow (Correct)

```
Human: "Build a document loader with web UI supporting PDF, DOCX, XLSX. Must handle recursive directories."

Agent:
[First, extracts all requirements]:
1. Document loader
2. Web UI
3. PDF support
4. DOCX support
5. XLSX support
6. Recursive directory handling

[Creates plan.md that includes]:
✅ Requirements Checklist (all 6 requirements listed)
✅ What This IS: Document loader + web UI + 3 file formats + recursive
✅ What This IS NOT: Chunking, embeddings, retrieval (not mentioned)
✅ Technology choices with rationale
✅ Web UI framework choice (Flask vs FastAPI)
✅ Library choices for each file format
✅ File structure showing web UI files
✅ Error handling for each file type
✅ Testing strategy

Agent: "I've created plan.md addressing all requirements:
- Document loader with PDF/DOCX/XLSX support ✓
- Web UI with Flask ✓
- Recursive directory traversal ✓
- Error handling strategy ✓
- Complete testing plan ✓

Please review and confirm I should proceed."
Human: "Looks good, proceed."

Agent: [Now implements all requirements from plan.md]
```

---

## 5️⃣ Incremental Changes Only

**Prefer small, reviewable commits.**

### Guidelines

- ✅ Change one thing at a time
- ✅ Keep changes focused and scoped
- ✅ Make it easy to review and revert
- ❌ Do not refactor unrelated files
- ❌ Do not introduce new abstractions unless justified in `plan.md`
- ❌ Do not "clean up" code that isn't being changed

### Example

```
✅ Good PR:
- Add document_type filter to retrieval
- Update ChunkMetadata to include document_type
- Add tests for filtered retrieval

❌ Bad PR:
- Add document_type filter
- Refactor chunking logic
- Rename variables for clarity
- Update logging format
- Switch to a different vector store
```

---

## 6️⃣ What NOT to Optimize Early

**The agent must not optimize prematurely for:**

| ❌ Don't Optimize | ✅ Focus Instead On |
|-------------------|---------------------|
| UI polish | Correct answers |
| Performance micro-optimizations | Retrieval quality |
| Distributed systems | Single-machine correctness |
| Scaling | Working prototype |
| Multi-tenant support | Single-tenant reliability |
| Real-time updates | Batch processing correctness |

**These are intentionally deferred.**

When you get the basics right, scaling is easier. When you get the basics wrong, no amount of infrastructure will fix it.

---

## 7️⃣ Hallucination Safety Rules

**If:**
- No relevant chunks are retrieved
- Retrieved chunks contradict each other
- Confidence is low (<0.7 similarity score)
- Question is outside documented scope

**Then the system must:**
```python
# ✅ Good: Explicit refusal
return Response(
    answer="I don't have enough information to answer that question. Please contact support@company.com",
    confidence=0.0,
    retrieved_chunks=[],
    refusal_reason="No relevant context found"
)

# ❌ Bad: Guessing
return Response(
    answer="Based on common practices, I think...",
    confidence=0.5
)
```

**Never guess. Never speculate. Never hallucinate.**

### Refusal Examples

```python
# Scenario 1: No chunks retrieved
"I don't have information about that in our knowledge base."

# Scenario 2: Conflicting information
"I found conflicting information on this topic. Please contact support for clarification."

# Scenario 3: Low confidence
"I'm not confident I have the right answer. Please reach out to support@company.com."

# Scenario 4: Out of scope
"That question is outside the scope of what I can help with. Please contact the relevant department."
```

---

## 8️⃣ Testing Requirements

### What to Test

**Required tests:**
1. **Chunking tests** — verify chunks are semantically coherent
2. **Retrieval tests** — verify correct chunks are found
3. **Prompt tests** — verify refusal when appropriate
4. **End-to-end tests** — verify full pipeline works

### Example Tests

```python
def test_chunking_preserves_context():
    """Chunks should include parent section titles."""
    doc = """
    ## Vacation Policy
    Employees get 15 days.
    
    ## Sick Leave
    Employees get 10 days.
    """
    chunks = chunk_document(doc)
    
    assert "Vacation Policy" in chunks[0].metadata.section_path
    assert "Sick Leave" in chunks[1].metadata.section_path


def test_retrieval_uses_filters():
    """Retrieval should respect metadata filters."""
    results = retrieve(
        query="vacation policy",
        filters={"document_type": "policy"}
    )
    
    assert all(r.metadata.document_type == "policy" for r in results)


def test_refuses_when_no_context():
    """System should refuse when no relevant chunks found."""
    response = generate_answer(
        query="What is the meaning of life?",
        retrieved_chunks=[]
    )
    
    assert response.is_refusal
    assert "don't have" in response.answer.lower()
```

### Test Data

- **Use real examples** from your domain
- **Include edge cases** (empty docs, malformed text, conflicting info)
- **Test failure modes** (no chunks, low confidence, out-of-scope)

---

## 9️⃣ Review Mindset

**Every change should be written as if:**

1. It will be **code-reviewed by a senior engineer**
2. It will be **debugged 6 months later** by someone else
3. It may be **audited after a bad answer**
4. The system will be used by **real users** who trust it

### Pre-Commit Checklist

Before submitting any change, ask:

- [ ] Is the code readable by someone unfamiliar with it?
- [ ] Are all design decisions documented (in code or plan.md)?
- [ ] Is logging sufficient to debug issues?
- [ ] Are metadata and retrieval decisions traceable?
- [ ] Would this change survive a code review?
- [ ] If this fails, can we debug why from the logs?

---

## 🔟 Common Anti-Patterns to Avoid

| ❌ Anti-Pattern | ✅ Better Approach |
|----------------|-------------------|
| "Let's just try it and see" | Plan first, document reasoning |
| Skipping requirements in task | Read carefully, list ALL requirements |
| Chunking by fixed token count | Chunk by semantic structure |
| Black-box vector search | Inspectable, filterable retrieval |
| Temperature > 0 for production | Temperature = 0 for consistency |
| Hallucinating when unsure | Explicit refusal with escalation |
| Clever abstractions | Explicit, boring code |
| "This should work" (no tests) | Test every component |
| Silent failures | Log decisions, especially failures |
| Mixing concerns in one function | Single responsibility per function |
| Premature optimization | Correct first, fast second |
| Unstructured logging | Structured event=X key=value format |

---

## 📋 Quick Reference: Key Rules

1. **Read requirements fully** — Extract and list ALL requirements before planning
2. **Plan first** — Always create `plan.md` before coding
3. **Address all requirements** — Every requirement must be in plan.md
4. **Wait for approval** — Never implement without explicit permission
5. **Chunk semantically** — Use headers, not token counts
6. **Add metadata** — Every chunk needs complete metadata
7. **Log decisions (structured)** — Use event=X key=value format
8. **Temperature = 0** — No creativity in production
9. **Refuse when uncertain** — Never guess or hallucinate
10. **Test thoroughly** — Chunking, retrieval, prompts, end-to-end

---

## 🚨 Final Rule (Most Important)

> **If a human support agent would hesitate before answering,  
> the AI must hesitate too.**

This means:
- When in doubt → **refuse**
- When uncertain → **escalate**
- When context is insufficient → **say so**
- When chunks conflict → **acknowledge it**
- When requirements are ambiguous → **ask for clarification**

**The system serves users best by being honest about its limitations.**

---

## 📚 Additional Resources

### Recommended Reading
- [RAG Best Practices (OpenAI)](https://platform.openai.com/docs/guides/retrieval-augmented-generation)
- [Embedding Models Comparison](https://huggingface.co/blog/mteb)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)

### Internal Documentation
- `docs/chunking_strategy.md` — Detailed chunking decisions
- `docs/metadata_schema.md` — Complete metadata specification
- `docs/retrieval_pipeline.md` — How retrieval works
- `docs/prompt_templates.md` — All production prompts

### Getting Help
- **Questions about this document**: Ask the team lead
- **Questions about requirements**: Create a plan.md with open questions
- **Bugs or issues**: File an issue with full context and logs
- **Improvements to this guide**: Submit a PR with rationale

---

**Version:** 2.1 (Improved)
**Last Updated:** 2024-02-06  
**Maintainer:** Engineering Team

**Changelog:**
- v2.1: Added explicit requirement reading instructions, structured logging format, improved plan.md template with scope definition
- v2.0: Initial comprehensive version