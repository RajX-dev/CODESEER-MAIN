import sys
sys.path.insert(0, r"c:\Users\Raj shekhar\Documents\raj\project\main\n3mo")

import tree_sitter_python
from tree_sitter import Language, Parser
from n3mo.core.symbol_extractor import _visit_imports

code = b"""
INSTALLED_APPS = [
    'django.contrib.admin',
    "myapp.apps.MyAppConfig",
]

class MyModel(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
"""

lang = Language(tree_sitter_python.language())
parser = Parser(lang)
tree = parser.parse(code)

imports_list = []
_visit_imports(tree.root_node, imports_list, "test.py")

for imp in imports_list:
    print(f"Extracted Import: {imp['module']}")
