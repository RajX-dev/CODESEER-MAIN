# Copyright (C) 2026 Raj shekhar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os

# Folders we never want to scan (case-insensitive)
IGNORED_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__", 
    ".venv", "venv", "env", ".idea", ".vscode",
    "tests", "test", "__tests__", "spec", "specs", "mock", "mocks",
    "benchmark", "benchmarks", "example", "examples", "sample", "samples",
    "fixtures", "fixture", "testing", "tmp", "temp"
}

def is_test_or_mock_file(filename: str) -> bool:
    name_lower = filename.lower()
    
    # Handle Perl test file extension .t
    if name_lower.endswith(".t"):
        return True
        
    name_without_ext, ext = os.path.splitext(filename)
    name_without_ext_lower = name_without_ext.lower()
    
    # 1. Direct match checks (case-insensitive)
    test_terms = {
        "test", "tests", "spec", "specs", "unittest", "unittests", 
        "mock", "mocks", "fixture", "fixtures"
    }
    if name_without_ext_lower in test_terms:
        return True
        
    # 2. Check prefix: starts with "test" or "mock" followed by a separator or uppercase letter
    for prefix in ("test", "mock"):
        if name_without_ext_lower.startswith(prefix):
            rest = name_without_ext[len(prefix):]
            if not rest:
                return True
            # If next char is a separator or uppercase letter
            if rest[0] in ("_", "-", ".") or rest[0].isupper():
                return True
                
    # 3. Check suffix: ends with one of the test terms preceded by a separator or uppercase boundary
    for suffix in test_terms:
        if name_without_ext_lower.endswith(suffix):
            prefix_len = len(name_without_ext) - len(suffix)
            if prefix_len <= 0:
                return True
            before_char = name_without_ext[prefix_len - 1]
            if before_char in ("_", "-", ".") or name_without_ext[prefix_len].isupper():
                return True
                
    return False

def detect_language(filename: str) -> str | None:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".py":
        return "python"
    elif ext in (".js", ".jsx"):
        return "javascript"
    elif ext in (".ts", ".tsx"):
        return "typescript"
    elif ext == ".go":
        return "go"
    elif ext == ".rs":
        return "rust"
    elif ext == ".java":
        return "java"
    elif ext in (".cpp", ".cc", ".cxx", ".hpp", ".h"):
        return "cpp"
    elif ext == ".c":
        return "c"
    elif ext == ".cs":
        return "csharp"
    elif ext in (".cob", ".cbl"):
        return "cobol"
    elif ext == ".dart":
        return "dart"
    elif ext in (".pas", ".dfm", ".dpr"):
        return "delphi"
    elif ext in (".groovy", ".gvy", ".gy", ".gsh"):
        return "groovy"
    elif ext in (".hs", ".lhs"):
        return "haskell"
    elif ext == ".jl":
        return "julia"
    elif ext in (".kt", ".kts"):
        return "kotlin"
    elif ext == ".lua":
        return "lua"
    elif ext in (".m", ".mm"):
        # Default to Objective-C; fallback to Matlab if parser matches
        return "objc"
    elif ext in (".pl", ".pm"):
        return "perl"
    elif ext == ".php":
        return "php"
    elif ext in (".ps1", ".psm1"):
        return "powershell"
    elif ext in (".r", ".R"):
        return "r"
    elif ext in (".rb", ".rbw"):
        return "ruby"
    elif ext in (".scala", ".sc"):
        return "scala"
    elif ext == ".swift":
        return "swift"
    elif ext in (".vba", ".bas", ".cls", ".frm", ".vb"):
        return "vba"
    return None

def crawl_repo(repo_path: str):
    """
    Scans the repo and returns a list of file paths.
    """
    files = []

    for root, dirs, filenames in os.walk(repo_path):
        # Modify dirs in-place so os.walk skips them (case-insensitive)
        dirs[:] = [d for d in dirs if d.lower() not in IGNORED_DIRS]

        for filename in filenames:
            # Skip test or mock files
            if is_test_or_mock_file(filename):
                continue

            language = detect_language(filename)
            if not language:
                continue

            full_path = os.path.join(root, filename)
            files.append(full_path) 

    return files

# Wrapper function to match what run_indexer.py expects
def crawl_directory(repo_path):
    return crawl_repo(repo_path)

if __name__ == "__main__":
    # Test it locally
    repo_path = os.getcwd()
    result = crawl_repo(repo_path)
    print(f"Found {len(result)} code files")
    for f in result[:5]:
        print(f)