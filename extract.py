import ast
import astunparse

with open('saas_webhook_handler.py', 'r', encoding='utf-16le') as f:
    content = f.read()
    if content.startswith('\ufeff'):
        content = content[1:]
    tree = ast.parse(content)

functions_to_extract = [
    'get_workspace_dir',
    'calculate_repo_loc',
    'checkout_repo',
    'get_changed_files',
    'get_project_id',
    'get_impact_for_changed_files',
    'merge_impacts',
    'format_impact_markdown',
    'post_github_comment',
    'get_github_app_installation_token'
]

core_functions = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in functions_to_extract:
        core_functions.append(astunparse.unparse(node))

core_engine_content = '''# Copyright (C) 2026 Raj shekhar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import os
import logging
import subprocess
import urllib.request
import urllib.error
import json
from fastapi import HTTPException

from n3mo.crawler import crawl_directory
from n3mo.database import get_connection, release_connection
from n3mo.run_indexer import run_indexer_for_path

logger = logging.getLogger("n3mo.core_engine")

'''

for func in core_functions:
    core_engine_content += func + '\n'

with open('n3mo/core_engine.py', 'w', encoding='utf-8') as f:
    f.write(core_engine_content)
