import tree_sitter_python as tspython
from tree_sitter import Language, Parser
import uuid

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

def extract_symbols_imports_calls(code_bytes, file_path="unknown"):
    """
    Returns: (symbols, imports, calls)
    """
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
            "start_line": node.start_point[0],
            "end_line": node.end_point[0],
            "signature": f"{kind.lower()} {name}..."
        }
        symbols.append(symbol_data)
        new_scope_id = symbol_id

    # --- B. DETECT CALLS (FIXED NODE NAME) ---
    elif node_type == "call": 
        # The field name for the function being called is still "function"
        func_node = node.child_by_field_name("function")
        if func_node:
            call_text = func_node.text.decode("utf8")
            
            # We only record calls if we are inside a function/class
            if current_scope_id:
                calls.append({
                    "id": str(uuid.uuid4()),
                    "source_symbol_id": current_scope_id,
                    "call_name": call_text,
                    "line_number": node.start_point[0]
                })

    # Recurse
    for child in node.children:
        _visit_definitions_and_calls(child, new_scope_id, symbols, calls, file_path)

def _visit_imports(node, imports_list, file_path):
    # (Same standard logic as before)
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