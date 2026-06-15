import json
import os
import subprocess
import sys
import uuid

import litellm
import psycopg2
from dotenv import load_dotenv
from fastembed import TextEmbedding
from pgvector.psycopg2 import register_vector

load_dotenv()

VALID_TYPES = {"decision", "constraint", "open_question", "finding", "file_reference", "dependency"}

EXTRACTION_PROMPT = """You are extracting knowledge from an AI coding session transcript.
Return a JSON array of facts. Each fact is an object with these keys:
- type: one of [decision, constraint, open_question, finding, file_reference, dependency]
- text: the fact in present tense, max 30 words
- files: array of file paths this fact relates to (may be empty)
- confidence: float 0.0-1.0

Rules:
- Return only the JSON array, no other text, no markdown code fences
- One atomic fact per object
- Do not extract tool call outputs, intermediate steps, or rejected proposals
- open_question is for unresolved questions only; stale_question is NOT a valid type
- confidence reflects certainty this is a real fact from the transcript (clearly stated = 0.9+, implied = 0.5-0.7)
- Keep each fact text to max 30 words — trim rather than exceed

Transcript:
{transcript}"""


# --- Block E: read transcript, handle .json (Claude Exporter) or plain text ---

def load_transcript(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if path.endswith(".json"):
        data = json.loads(content)
        messages = data.get("messages", [])
        lines = []
        for msg in messages:
            role = "Human" if msg.get("role") == "human" else "Assistant"
            lines.append(f"{role}: {msg.get('say', '')}")
        return "\n\n".join(lines)

    return content


# --- Block C: developer identity from git ---

def get_developer_id() -> str:
    result = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True)
    email = result.stdout.strip()
    if not email:
        print("ERROR: git config user.email is empty — set it with: git config --global user.email you@example.com", file=sys.stderr)
        sys.exit(1)
    return email


# --- Block H: validate a single fact dict ---

def validate_fact(fact: dict, index: int) -> tuple[bool, str]:
    fact_type = fact.get("type", "")
    if fact_type not in VALID_TYPES:
        return False, f"invalid type '{fact_type}'"

    text = fact.get("text", "")
    if not text or not isinstance(text, str):
        return False, "text is empty"
    word_count = len(text.split())
    if word_count > 30:
        return False, f"text exceeds 30 words ({word_count} words)"

    confidence = fact.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
        return False, f"confidence '{confidence}' is not a float in [0.0, 1.0]"

    return True, ""


def main():
    # --- Block A: argument parsing ---
    if len(sys.argv) != 2:
        print("Usage: python scripts/extract.py <transcript_file>", file=sys.stderr)
        sys.exit(1)

    transcript_path = sys.argv[1]
    if not os.path.exists(transcript_path):
        print(f"ERROR: file not found: {transcript_path}", file=sys.stderr)
        sys.exit(1)

    # --- Block B: load environment variables ---
    database_url = os.environ.get("DATABASE_URL")
    model = os.environ.get("LogTora_MODEL")
    api_key = os.environ.get("LogTora_API_KEY")
    project = os.environ.get("LogTora_PROJECT") or os.path.basename(os.getcwd())

    for name, val in [("DATABASE_URL", database_url), ("LogTora_MODEL", model), ("LogTora_API_KEY", api_key)]:
        if not val:
            print(f"ERROR: {name} is not set in environment", file=sys.stderr)
            sys.exit(1)

    # --- Block C: developer identity ---
    developer_id = get_developer_id()

    # --- Block D: session UUID ---
    session_id = str(uuid.uuid4())

    # --- Block E: read transcript ---
    try:
        transcript = load_transcript(transcript_path)
    except Exception as e:
        print(f"ERROR: could not read transcript: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Block F: load embedding model ---
    print("Loading embedding model...")
    embedding_model = TextEmbedding("nomic-ai/nomic-embed-text-v1.5")

    # --- Block G: call LLM ---
    print(f"Calling {model} to extract facts...")
    try:
        response = litellm.completion(
            model=model,
            api_key=api_key,
            messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(transcript=transcript)}],
        )
        raw = response.choices[0].message.content.strip()
        cost = litellm.completion_cost(completion_response=response)
    except Exception as e:
        print(f"ERROR: LLM call failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Strip markdown code fences if LLM wrapped the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0].strip()

    # --- Block H: parse and validate ---
    try:
        facts = json.loads(raw)
        if not isinstance(facts, list):
            raise ValueError("LLM response is not a JSON array")
    except Exception as e:
        print(f"ERROR: could not parse LLM response as JSON: {e}", file=sys.stderr)
        print(f"Raw response:\n{raw}", file=sys.stderr)
        sys.exit(1)

    extracted_count = len(facts)
    valid_facts = []
    skip_reasons = []

    for i, fact in enumerate(facts):
        ok, reason = validate_fact(fact, i)
        if ok:
            valid_facts.append(fact)
        else:
            text_preview = str(fact.get("text", ""))[:60]
            print(f"WARNING: skipped fact {i + 1} ({reason}): {text_preview}")
            skip_reasons.append(reason)

    # --- Block I: embed valid facts in one batch ---
    embeddings = []
    if valid_facts:
        print(f"Embedding {len(valid_facts)} facts...")
        texts = [f["text"] for f in valid_facts]
        embeddings = list(embedding_model.embed(texts))

    # --- Block J: insert into PostgreSQL ---
    try:
        conn = psycopg2.connect(database_url)
        register_vector(conn)
        cur = conn.cursor()

        for fact, embedding in zip(valid_facts, embeddings):
            cur.execute(
                """
                INSERT INTO facts
                    (project, developer_id, session_id, type, text, files, embedding, confidence, status)
                VALUES
                    (%s, %s, %s::uuid, %s, %s, %s, %s, %s, 'pending_review')
                """,
                (
                    project,
                    developer_id,
                    session_id,
                    fact["type"],
                    fact["text"],
                    fact.get("files") or [],
                    embedding,
                    float(fact["confidence"]),
                ),
            )

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: database error: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Block K: summary ---
    skipped_count = extracted_count - len(valid_facts)
    print()
    print(f"Session ID:  {session_id}")
    print(f"Extracted:   {extracted_count} facts from LLM")
    print(f"Valid:       {len(valid_facts)}")
    if skipped_count:
        print(f"Skipped:     {skipped_count} ({', '.join(set(skip_reasons))})")
    else:
        print(f"Skipped:     0")
    print(f"Stored:      {len(valid_facts)} facts")
    print(f"LLM cost:    ${cost:.4f} ({response.usage.prompt_tokens} in / {response.usage.completion_tokens} out)")


if __name__ == "__main__":
    main()
