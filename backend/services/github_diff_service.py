def detect_changed_files(old_files, new_files):
    old_map = {file["path"]: file["content"] for file in old_files}
    new_map = {file["path"]: file["content"] for file in new_files}

    added = []
    deleted = []
    modified = []

    for path in new_map:
        if path not in old_map:
            added.append(path)
        elif new_map[path] != old_map[path]:
            modified.append(path)

    for path in old_map:
        if path not in new_map:
            deleted.append(path)

    return {
        "added": added,
        "modified": modified,
        "deleted": deleted,
    }