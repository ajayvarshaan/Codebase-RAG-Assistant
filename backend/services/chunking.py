def split_code_into_chunks(
    content: str,
    lines_per_chunk: int = 20
):
    lines = content.splitlines()
    chunks = []

    for start in range(0, len(lines), lines_per_chunk):
        end = min(start + lines_per_chunk, len(lines))

        chunks.append(
            {
                "content": "\n".join(lines[start:end]),
                "chunk_index": len(chunks),
                "start_line": start + 1,
                "end_line": end,
            }
        )

    return chunks