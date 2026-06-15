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
import stat
import logging

logger = logging.getLogger("n3mo")

HOOK_CONTENT = """#!/bin/sh
# N3MO Automated Incremental Indexer Hook
echo ""
echo "🌊 N3MO: Running automated post-commit incremental indexing..."
n3mo index
echo "🌊 N3MO: Indexing complete."
echo ""
"""

def install_git_hook(target_dir):
    """
    Installs a post-commit Git hook in the target directory's .git repository.
    """
    target_dir = os.path.abspath(target_dir)
    git_dir = os.path.join(target_dir, ".git")
    
    if not os.path.exists(git_dir):
        logger.error(f"❌ Error: '{target_dir}' is not a Git repository (no .git folder found).")
        return False
        
    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    
    hook_path = os.path.join(hooks_dir, "post-commit")
    
    try:
        # Write the hook content
        with open(hook_path, "w", newline="\n", encoding="utf-8") as f:
            f.write(HOOK_CONTENT)
            
        # Make it executable (cross-platform permission handling)
        if os.name != 'nt':
            st = os.stat(hook_path)
            os.chmod(hook_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            
        logger.info(f"✅ N3MO: Installed Git post-commit hook successfully at {hook_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to install Git hook: {e}")
        return False
