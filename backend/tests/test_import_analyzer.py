from services.import_analyzer import find_imports


def test_find_relative_imports():
    code = '''
import React from "react";
import Button from "./Button";
import { helper } from "../utils/helper";
'''

    imports = find_imports(code)

    assert "react" in imports
    assert "./Button" in imports
    assert "../utils/helper" in imports


def test_find_imports_without_imports():
    assert find_imports("const value = 10;") == []
