import re


def find_imports(content: str):
    """
    Find imported file/module paths from JavaScript/TypeScript code.
    """

    imports = []

    # Handles:
    # import x from "./file"
    # import x from "../file"
    # import "./file"
    pattern = r'import(?:.*?from\s*)?[\'"](.+?)[\'"]'

    matches = re.findall(pattern, content)

    for match in matches:
        imports.append(match)

    return imports