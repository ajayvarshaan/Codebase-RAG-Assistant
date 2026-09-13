from services.chunking import split_code_into_chunks


def test_code_is_split_into_20_line_chunks():
    content = "\n".join(f"line {number}" for number in range(1, 46))

    chunks = split_code_into_chunks(content)

    assert len(chunks) == 3
    assert chunks[0]["start_line"] == 1
    assert chunks[0]["end_line"] == 20
    assert chunks[1]["start_line"] == 21
    assert chunks[1]["end_line"] == 40
    assert chunks[2]["start_line"] == 41
    assert chunks[2]["end_line"] == 45


def test_empty_code_creates_no_chunks():
    assert split_code_into_chunks("") == []
