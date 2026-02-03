import tree_sitter_python as tspython
from tree_sitter import Language, Parser
import uuid

# Initialize Parser ONCE (Global optimization)
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

def extract_symbols(code_bytes, file_path="unknown"):
    """
    Parses code and returns a flat list of symbol dictionaries
    ready for database insertion.
    """
    tree = parser.parse(code_bytes)
    root_node = tree.root_node
    
    symbols = []
    
    # Start the recursive journey
    # We pass 'None' as parent_id because the file itself is the root context
    _visit_node(root_node, None, symbols, file_path)
    
    return symbols

def _visit_node(node, parent_id, symbols_list, file_path):
    """
    Recursive function to walk the tree.
    """
    # 1. IDENTIFY: Is this node interesting?
    node_type = node.type
    kind = None
    
    if node_type == "function_definition":
        kind = "FUNCTION"
    elif node_type == "class_definition":
        kind = "CLASS"
    
    # 2. EXTRACT: If it is interesting, get its details
    current_id = parent_id # Default: pass the current parent down if we don't create a new one
    
    if kind:
        # Get the name (The function/class name is usually a child node of type 'identifier')
        name_node = node.child_by_field_name("name")
        name = name_node.text.decode("utf8") if name_node else "anonymous"
        
        # Get location
        start_line = node.start_point[0]
        end_line = node.end_point[0]
        
        # Generate a temporary UUID for this session 
        # (The DB logic will handle persistence later)
        symbol_id = str(uuid.uuid4())
        
        # Create the Dictionary (The "Row")
        symbol_data = {
            "id": symbol_id,
            "parent_id": parent_id,
            "name": name,
            "kind": kind,
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "signature": f"{kind.lower()} {name}..." # Simplified for now
        }
        
        symbols_list.append(symbol_data)
        
        # IMPORTANT: This symbol becomes the PARENT for everything inside it
        current_id = symbol_id

    # 3. RECURSE: Check all children (Go deeper)
    # We keep walking down the tree looking for more symbols
    for child in node.children:
        _visit_node(child, current_id, symbols_list, file_path)