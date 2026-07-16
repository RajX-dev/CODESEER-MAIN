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
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import os
import logging
import subprocess
import urllib.request
import urllib.error
import json
from fastapi import HTTPException

from n3mo.core.crawler import crawl_directory
from n3mo.core.database import get_connection, release_connection
from n3mo.core.run_indexer import run_indexer_for_path

logger = logging.getLogger("n3mo.core_engine")

'''

for func in core_functions:
    core_engine_content += func + '\n'

with open('n3mo/core_engine.py', 'w', encoding='utf-8') as f:
    f.write(core_engine_content)
