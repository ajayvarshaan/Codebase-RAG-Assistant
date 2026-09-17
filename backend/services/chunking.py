def split_code_into_chunks(
    content: str,
    lines_per_chunk: int = 20
):
    lines = content.splitlines()
    chunks = []

    for start in range(0, len(lines), lines_per_chunk):
        end = min(
            start + lines_per_chunk,
            len(lines)
        )

        chunk_content = "\n".join(
            lines[start:end]
        )

        # Skip empty or whitespace-only chunks
        if not chunk_content.strip():
            continue

        chunks.append(
            {
                "content": chunk_content,
                "chunk_index": len(chunks),
                "start_line": start + 1,
                "end_line": end
            }
        )

    return chunks