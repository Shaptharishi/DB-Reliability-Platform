import os
import re
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

model = SentenceTransformer("all-MiniLM-L6-v2")

RUNBOOKS_DIR = os.path.join(os.path.dirname(__file__), "..", "runbooks")

PG_CONFIG = {
    "host": os.environ.get("PG_HOST"),
    "port": int(os.environ.get("PG_PORT")),
    "dbname": os.environ.get("PG_DB"),
    "user": os.environ.get("PG_USER"),
    "password": os.environ.get("PG_PASSWORD"),
}


def chunk_by_section(text):
    """
    Splits a runbook by its markdown headers (## Symptoms,
    ## Resolution, etc.) -- chunking by SECTION, exactly as
    reasoned through earlier: aligned with the natural structure
    of the document, not an arbitrary character count.
    """
    sections = re.split(r'\n(?=## )', text)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        lines = section.split("\n", 1)
        title = lines[0].replace("#", "").strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if body:
            chunks.append({"section": title, "content": body})
    return chunks


def main():
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    cur.execute("DELETE FROM runbook_chunks;")  # clean slate each run

    for filename in os.listdir(RUNBOOKS_DIR):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(RUNBOOKS_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_by_section(text)
        print(f"{filename}: {len(chunks)} chunks")

        for chunk in chunks:
            embedding = model.encode(chunk["content"]).tolist()
            cur.execute(
                "INSERT INTO runbook_chunks (source_file, section, content, embedding) VALUES (%s, %s, %s, %s)",
                (filename, chunk["section"], chunk["content"], embedding)
            )

    conn.commit()
    cur.close()
    conn.close()
    print("Done embedding all runbooks.")


if __name__ == "__main__":
    main()