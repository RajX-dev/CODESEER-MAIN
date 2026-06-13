from tree_sitter import Language, Parser
import uuid
import os

# --- MULTI-LANGUAGE BINDINGS LOAD ---
LANGUAGES = {}

def load_lang(name, module_name, lang_func_name="language"):
    try:
        mod = __import__(module_name)
        func = getattr(mod, lang_func_name)
        LANGUAGES[name] = Language(func())
    except Exception:
        pass

# Load all 27 languages dynamically & safely
load_lang("python", "tree_sitter_python", "language")
load_lang("javascript", "tree_sitter_javascript", "language")
load_lang("typescript", "tree_sitter_typescript", "language_typescript")
load_lang("tsx", "tree_sitter_typescript", "language_tsx")
load_lang("go", "tree_sitter_go", "language")
load_lang("rust", "tree_sitter_rust", "language")
load_lang("java", "tree_sitter_java", "language")
load_lang("cpp", "tree_sitter_cpp", "language")
load_lang("c", "tree_sitter_c", "language")
load_lang("csharp", "tree_sitter_c_sharp", "language")
load_lang("cobol", "tree_sitter_cobol", "language")
load_lang("dart", "tree_sitter_dart", "language")
load_lang("delphi", "tree_sitter_delphi", "language")
load_lang("groovy", "tree_sitter_groovy", "language")
load_lang("haskell", "tree_sitter_haskell", "language")
load_lang("julia", "tree_sitter_julia", "language")
load_lang("kotlin", "tree_sitter_kotlin", "language")
load_lang("lua", "tree_sitter_lua", "language")
load_lang("matlab", "tree_sitter_matlab", "language")
load_lang("objc", "tree_sitter_objc", "language")
load_lang("perl", "tree_sitter_perl", "language")
load_lang("php", "tree_sitter_php", "language")
load_lang("powershell", "tree_sitter_powershell", "language")
load_lang("r", "tree_sitter_r", "language")
load_lang("ruby", "tree_sitter_ruby", "language")
load_lang("scala", "tree_sitter_scala", "language")
load_lang("swift", "tree_sitter_swift", "language")
load_lang("vba", "tree_sitter_vba", "language")

def get_parser(lang_name):
    if lang_name not in LANGUAGES:
        return None
    return Parser(LANGUAGES[lang_name])

# Main Python parser instance (preserved for legacy Python extractors)
PY_LANGUAGE = LANGUAGES.get("python")
parser = Parser(PY_LANGUAGE) if PY_LANGUAGE else None

# --- ADAPTER (Connects your logic to the runner) ---
def extract_symbols(file_path):
    """
    Reads the file and calls the appropriate parser based on the file extension.
    """
    try:
        if not os.path.exists(file_path):
            return [], [], []

        with open(file_path, "rb") as f:
            code_bytes = f.read()

        ext = os.path.splitext(file_path)[1].lower()

        # 1. Python (Original logic)
        if ext == ".py":
            return extract_symbols_imports_calls(code_bytes, file_path)

        # 2. JavaScript / JSX
        elif ext in (".js", ".jsx"):
            return extract_generic(code_bytes, file_path, "javascript")

        # 3. TypeScript / TSX
        elif ext == ".ts":
            return extract_generic(code_bytes, file_path, "typescript")
        elif ext == ".tsx":
            return extract_generic(code_bytes, file_path, "tsx")

        # 4. Go
        elif ext == ".go":
            return extract_generic(code_bytes, file_path, "go")

        # 5. Rust
        elif ext == ".rs":
            return extract_generic(code_bytes, file_path, "rust")

        # 6. Java
        elif ext == ".java":
            return extract_generic(code_bytes, file_path, "java")

        # 7. C++
        elif ext in (".cpp", ".cc", ".cxx", ".hpp", ".h"):
            return extract_generic(code_bytes, file_path, "cpp")

        # 8. C
        elif ext == ".c":
            return extract_generic(code_bytes, file_path, "c")

        # 9. C#
        elif ext == ".cs":
            return extract_generic(code_bytes, file_path, "csharp")

        # 10. Cobol
        elif ext in (".cob", ".cbl"):
            return extract_generic(code_bytes, file_path, "cobol")

        # 11. Dart
        elif ext == ".dart":
            return extract_generic(code_bytes, file_path, "dart")

        # 12. Delphi / Pascal
        elif ext in (".pas", ".dfm", ".dpr"):
            return extract_generic(code_bytes, file_path, "delphi")

        # 13. Groovy
        elif ext in (".groovy", ".gvy", ".gy", ".gsh"):
            return extract_generic(code_bytes, file_path, "groovy")

        # 14. Haskell
        elif ext in (".hs", ".lhs"):
            return extract_generic(code_bytes, file_path, "haskell")

        # 15. Julia
        elif ext == ".jl":
            return extract_generic(code_bytes, file_path, "julia")

        # 16. Kotlin
        elif ext in (".kt", ".kts"):
            return extract_generic(code_bytes, file_path, "kotlin")

        # 17. Lua
        elif ext == ".lua":
            return extract_generic(code_bytes, file_path, "lua")

        # 18. Matlab / Objective-C
        elif ext == ".m":
            res = extract_generic(code_bytes, file_path, "objc")
            if res[0] or res[1] or res[2]:
                return res
            return extract_generic(code_bytes, file_path, "matlab")
        elif ext == ".mm":
            return extract_generic(code_bytes, file_path, "objc")

        # 19. Perl
        elif ext in (".pl", ".pm", ".t"):
            return extract_generic(code_bytes, file_path, "perl")

        # 20. PHP
        elif ext == ".php":
            return extract_generic(code_bytes, file_path, "php")

        # 21. Powershell
        elif ext in (".ps1", ".psm1"):
            return extract_generic(code_bytes, file_path, "powershell")

        # 22. R
        elif ext in (".r", ".R"):
            return extract_generic(code_bytes, file_path, "r")

        # 23. Ruby
        elif ext in (".rb", ".rbw"):
            return extract_generic(code_bytes, file_path, "ruby")

        # 24. Scala
        elif ext in (".scala", ".sc"):
            return extract_generic(code_bytes, file_path, "scala")

        # 25. Swift
        elif ext == ".swift":
            return extract_generic(code_bytes, file_path, "swift")

        # 26. VBA / Visual Basic
        elif ext in (".vba", ".bas", ".cls", ".frm", ".vb"):
            return extract_generic(code_bytes, file_path, "vba")

        else:
            return [], [], []

    except Exception as e:
        print(f"⚠️ Error reading/extracting {file_path}: {e}")
        return [], [], []

def extract_generic(code_bytes, file_path, lang_name):
    parser_instance = get_parser(lang_name)
    if not parser_instance:
        return [], [], []

    tree = parser_instance.parse(code_bytes)
    root_node = tree.root_node

    symbols = []
    imports = []
    calls = []

    _visit_generic(root_node, None, symbols, calls, imports, file_path, lang_name)

    return symbols, imports, calls

# --- HELPERS FOR C/C++ DECLARATOR PARSING ---
def _find_function_declarator(node):
    if node.type == "function_declarator":
        return node
    for child in node.children:
        res = _find_function_declarator(child)
        if res:
            return res
    return None

def _get_cpp_declarator_name(node):
    if node.type == "identifier":
        return node.text.decode("utf-8", errors="ignore")
    nested = node.child_by_field_name("declarator")
    if nested:
        return _get_cpp_declarator_name(nested)
    for child in node.children:
        res = _get_cpp_declarator_name(child)
        if res:
            return res
    return None

# --- GENERIC MULTI-LANGUAGE AST VISITOR ---
def _visit_generic(node, current_scope_id, symbols, calls, imports, file_path, lang):
    node_type = node.type
    new_scope_id = current_scope_id

    kind = None
    name = None

    # 1. ES6, JVM, and Modern Languages Group (JS, TS, TSX, C#, Go, Kotlin, Scala, Swift, Groovy)
    if lang in ("javascript", "typescript", "tsx", "csharp", "go", "kotlin", "scala", "swift", "groovy"):
        if node_type in (
            "class_declaration", "interface_declaration", "struct_declaration", 
            "object_declaration", "trait_definition", "class_definition", 
            "object_definition", "enum_declaration", "record_declaration"
        ):
            kind = "CLASS"
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="ignore")
        elif node_type in (
            "function_declaration", "generator_function_declaration", 
            "method_definition", "method_declaration", "function_definition", 
            "local_function_statement"
        ):
            kind = "FUNCTION"
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="ignore")
        elif node_type == "arrow_function":
            parent = node.parent
            if parent and parent.type == "variable_declarator":
                name_node = parent.child_by_field_name("name")
                if name_node:
                    kind = "FUNCTION"
                    name = name_node.text.decode("utf-8", errors="ignore")
        elif node_type in ("call_expression", "method_call", "invocation_expression"):
            func_node = node.child_by_field_name("function") or node.child_by_field_name("expression") or node.child_by_field_name("name")
            if func_node and current_scope_id:
                call_text = func_node.text.decode("utf-8", errors="ignore")
                calls.append({
                    "id": str(uuid.uuid4()),
                    "source_symbol_id": current_scope_id,
                    "call_name": call_text,
                    "line_number": node.start_point[0] + 1
                })
        elif node_type in ("import_statement", "using_directive", "import_declaration", "import_header", "import_spec"):
            source_node = node.child_by_field_name("source") or node.child_by_field_name("name") or node.child_by_field_name("path")
            if source_node:
                module_name = source_node.text.decode("utf-8", errors="ignore").strip("'\"")
                imports.append({
                    "id": str(uuid.uuid4()),
                    "file_path": file_path,
                    "module": module_name,
                    "name": None,
                    "alias": None
                })

    # 2. Rust Group
    elif lang == "rust":
        if node_type == "function_item":
            kind = "FUNCTION"
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="ignore")
        elif node_type in ("struct_item", "enum_item", "trait_item"):
            kind = "CLASS"
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="ignore")
        elif node_type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node and current_scope_id:
                call_text = func_node.text.decode("utf-8", errors="ignore")
                calls.append({
                    "id": str(uuid.uuid4()),
                    "source_symbol_id": current_scope_id,
                    "call_name": call_text,
                    "line_number": node.start_point[0] + 1
                })
        elif node_type == "use_declaration":
            argument = node.child_by_field_name("argument")
            if argument:
                use_path = argument.text.decode("utf-8", errors="ignore")
                imports.append({
                    "id": str(uuid.uuid4()),
                    "file_path": file_path,
                    "module": use_path,
                    "name": None,
                    "alias": None
                })

    # 3. Java Group
    elif lang == "java":
        if node_type == "method_declaration":
            kind = "FUNCTION"
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="ignore")
        elif node_type in ("class_declaration", "interface_declaration"):
            kind = "CLASS"
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="ignore")
        elif node_type == "method_invocation":
            name_node = node.child_by_field_name("name")
            if name_node and current_scope_id:
                call_text = name_node.text.decode("utf-8", errors="ignore")
                calls.append({
                    "id": str(uuid.uuid4()),
                    "source_symbol_id": current_scope_id,
                    "call_name": call_text,
                    "line_number": node.start_point[0] + 1
                })
        elif node_type == "import_declaration":
            for child in node.children:
                if child.type in ("scoped_identifier", "identifier"):
                    module_name = child.text.decode("utf-8", errors="ignore")
                    imports.append({
                        "id": str(uuid.uuid4()),
                        "file_path": file_path,
                        "module": module_name,
                        "name": None,
                        "alias": None
                    })

    # 4. C/C++/Objective-C Group
    elif lang in ("cpp", "c", "objc"):
        if node_type in ("function_definition", "declaration", "method_definition"):
            declarator = node.child_by_field_name("declarator")
            if declarator:
                func_dec = _find_function_declarator(declarator)
                if func_dec:
                    kind = "FUNCTION"
                    name = _get_cpp_declarator_name(func_dec)
        elif node_type in ("class_specifier", "class_interface", "class_implementation"):
            kind = "CLASS"
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="ignore")
        elif node_type in ("call_expression", "message_expression"):
            func_node = node.child_by_field_name("function") or node.child_by_field_name("selector")
            if func_node and current_scope_id:
                call_text = func_node.text.decode("utf-8", errors="ignore")
                calls.append({
                    "id": str(uuid.uuid4()),
                    "source_symbol_id": current_scope_id,
                    "call_name": call_text,
                    "line_number": node.start_point[0] + 1
                })
        elif node_type == "preproc_include":
            path_node = node.child_by_field_name("path")
            if path_node:
                include_path = path_node.text.decode("utf-8", errors="ignore").strip("<>\"")
                imports.append({
                    "id": str(uuid.uuid4()),
                    "file_path": file_path,
                    "module": include_path,
                    "name": None,
                    "alias": None
                })

    # 5. Dynamic & Scripting Group (Ruby, PHP, Perl, Lua, Julia, Powershell, Groovy, Matlab, Delphi, Haskell)
    else:
        if node_type in (
            "method_declaration", "function_declaration", "function_definition", 
            "subroutine_declaration", "procedure_declaration", "function_statement"
        ):
            kind = "FUNCTION"
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="ignore")
        elif node_type in (
            "class_declaration", "module_declaration", "struct_definition", 
            "class_specifier", "class_type"
        ):
            kind = "CLASS"
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="ignore")
        elif node_type in (
            "call_expression", "function_call", "method_call", 
            "function_call_expression", "command_invocation", "call"
        ):
            func_node = node.child_by_field_name("function") or node.child_by_field_name("name") or node.child_by_field_name("expression")
            if func_node and current_scope_id:
                call_text = func_node.text.decode("utf-8", errors="ignore")
                calls.append({
                    "id": str(uuid.uuid4()),
                    "source_symbol_id": current_scope_id,
                    "call_name": call_text,
                    "line_number": node.start_point[0] + 1
                })
        elif node_type in (
            "use_statement", "require_statement", "import_declaration", 
            "import_statement", "using_statement", "preproc_include"
        ):
            for child in node.children:
                if child.type in ("identifier", "scoped_identifier", "string", "path"):
                    module_name = child.text.decode("utf-8", errors="ignore").strip("'\"")
                    imports.append({
                        "id": str(uuid.uuid4()),
                        "file_path": file_path,
                        "module": module_name,
                        "name": None,
                        "alias": None
                    })
                    break

    if kind and name:
        symbol_id = str(uuid.uuid4())
        symbols.append({
            "id": symbol_id,
            "parent_id": current_scope_id,
            "name": name,
            "kind": kind,
            "file_path": file_path,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "signature": f"{kind.lower()} {name}..."
        })
        new_scope_id = symbol_id

    for child in node.children:
        _visit_generic(child, new_scope_id, symbols, calls, imports, file_path, lang)


# --- ORIGINAL PYTHON EXTRACTION LOGIC (PRESERVED) ---
def extract_symbols_imports_calls(code_bytes, file_path="unknown"):
    """
    Returns: (symbols, imports, calls)
    """
    if not parser:
        return [], [], []
    tree = parser.parse(code_bytes)
    root_node = tree.root_node

    symbols = []
    imports = []
    calls = []

    # 1. Definitions AND Calls
    _visit_definitions_and_calls(root_node, None, symbols, calls, file_path)

    # 2. Imports
    _visit_imports(root_node, imports, file_path)

    return symbols, imports, calls

def _visit_definitions_and_calls(node, current_scope_id, symbols, calls, file_path):
    node_type = node.type
    new_scope_id = current_scope_id

    # --- A. DETECT DEFINITIONS ---
    kind = None
    if node_type == "function_definition":
        kind = "FUNCTION"
    elif node_type == "class_definition":
        kind = "CLASS"

    if kind:
        name_node = node.child_by_field_name("name")
        name = name_node.text.decode("utf8") if name_node else "anon"
        symbol_id = str(uuid.uuid4())

        symbol_data = {
            "id": symbol_id,
            "parent_id": current_scope_id,
            "name": name,
            "kind": kind,
            "file_path": file_path,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "signature": f"{kind.lower()} {name}..."
        }
        symbols.append(symbol_data)
        new_scope_id = symbol_id

    # --- B. DETECT CALLS ---
    elif node_type == "call":
        func_node = node.child_by_field_name("function")
        if func_node:
            call_text = func_node.text.decode("utf8")

            if current_scope_id:
                calls.append({
                    "id": str(uuid.uuid4()),
                    "source_symbol_id": current_scope_id,
                    "call_name": call_text,
                    "line_number": node.start_point[0] + 1
                })

    for child in node.children:
        _visit_definitions_and_calls(child, new_scope_id, symbols, calls, file_path)

def _visit_imports(node, imports_list, file_path):
    if node.type == "import_statement":
        for child in node.children:
            if child.type == "dotted_name":
                _add_import(imports_list, file_path, module=child.text.decode("utf8"))
            elif child.type == "aliased_import":
                name_node = child.child_by_field_name("name")
                alias_node = child.child_by_field_name("alias")
                mod = name_node.text.decode("utf8") if name_node else ""
                alias = alias_node.text.decode("utf8") if alias_node else None
                _add_import(imports_list, file_path, module=mod, alias=alias)

    elif node.type == "import_from_statement":
        module_node = node.child_by_field_name("module_name")
        module_name = module_node.text.decode("utf8") if module_node else "."
        for child in node.children:
             if child.type == "dotted_name" and child != module_node:
                 _add_import(imports_list, file_path, module=module_name, name=child.text.decode("utf8"))
             elif child.type == "aliased_import":
                 name_node = child.child_by_field_name("name")
                 alias_node = child.child_by_field_name("alias")
                 imported = name_node.text.decode("utf8")
                 alias = alias_node.text.decode("utf8")
                 _add_import(imports_list, file_path, module=module_name, name=imported, alias=alias)

    for child in node.children:
        _visit_imports(child, imports_list, file_path)

def _add_import(imports_list, file_path, module, name=None, alias=None):
    imports_list.append({
        "id": str(uuid.uuid4()),
        "file_path": file_path,
        "module": module,
        "name": name,
        "alias": alias
    })