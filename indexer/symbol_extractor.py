import tree_sitter_python as tspython
from tree_sitter import Language, Parser
import uuid

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

def extract_symbols_and_imports(code_bytes, file_path="unknown"):
    """
    Returns a tuple: (list_of_symbols, list_of_imports)
    """
    tree = parser.parse(code_bytes)
    root_node = tree.root_node
    
    symbols = []
    imports = []
    
    # 1. Walk the tree for DEFINITIONS (Classes/Functions)
    _visit_definition(root_node, None, symbols, file_path)
    
    # 2. Walk the tree for IMPORTS
    # (Imports are usually top-level, but can be inside functions too)
    _visit_imports(root_node, imports, file_path)
    
    return symbols, imports

def _visit_definition(node, parent_id, symbols_list, file_path):
    """Recursive walk for definitions (What we wrote in Day 17)"""
    node_type = node.type
    kind = None
    
    if node_type == "function_definition":
        kind = "FUNCTION"
    elif node_type == "class_definition":
        kind = "CLASS"
    
    current_id = parent_id 
    
    if kind:
        name_node = node.child_by_field_name("name")
        name = name_node.text.decode("utf8") if name_node else "anonymous"
        
        symbol_id = str(uuid.uuid4())
        
        symbol_data = {
            "id": symbol_id,
            "parent_id": parent_id,
            "name": name,
            "kind": kind,
            "file_path": file_path,
            "start_line": node.start_point[0],
            "end_line": node.end_point[0],
            "signature": f"{kind.lower()} {name}..."
        }
        symbols_list.append(symbol_data)
        current_id = symbol_id

    for child in node.children:
        _visit_definition(child, current_id, symbols_list, file_path)

def _visit_imports(node, imports_list, file_path):
    """Recursive walk for imports"""
    if node.type == "import_statement":
        # Format: import os, sys
        for child in node.children:
            if child.type == "dotted_name":
                _add_import(imports_list, file_path, module=child.text.decode("utf8"))
            elif child.type == "aliased_import":
                # import numpy as np
                name_node = child.child_by_field_name("name")
                alias_node = child.child_by_field_name("alias")
                mod_name = name_node.text.decode("utf8") if name_node else ""
                alias = alias_node.text.decode("utf8") if alias_node else None
                _add_import(imports_list, file_path, module=mod_name, alias=alias)

    elif node.type == "import_from_statement":
        # Format: from utils import helper
        module_node = node.child_by_field_name("module_name")
        module_name = module_node.text.decode("utf8") if module_node else "."
        
        # Iterate over the 'import X, Y' part
        for child in node.children:
            if child.type == "dotted_name":
                # This catches the 'import os' part if mixed, but usually 'import_from' has specific structure
                pass
            
            # Tree-sitter structure for 'import x, y' is a bit complex.
            # We look for "aliased_import" or "dotted_name" inside the children 
            # BUT usually they are wrapped. For simplicity, we scan specific children.
            pass

        # Simplified Logic for 'from X import Y, Z'
        # In tree-sitter python, the imported names are siblings or children depending on version.
        # Let's trust a simple traversal of children to find what is imported.
        for i, child in enumerate(node.children):
             # Skip the 'from' and 'module' parts, look for names after 'import'
             if child.type == "dotted_name" and child != module_node:
                 _add_import(imports_list, file_path, module=module_name, name=child.text.decode("utf8"))
             elif child.type == "aliased_import":
                 name_node = child.child_by_field_name("name")
                 alias_node = child.child_by_field_name("alias")
                 imported_obj = name_node.text.decode("utf8")
                 alias = alias_node.text.decode("utf8")
                 _add_import(imports_list, file_path, module=module_name, name=imported_obj, alias=alias)

    # Recurse
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