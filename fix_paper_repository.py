#!/usr/bin/env python3
"""
Fix the paper repository to remove authors column references.
"""

import re

def fix_paper_repository():
    with open('src/database/paper_repository.py', 'r') as f:
        content = f.read()
    
    # Remove authors column from UPDATE query
    content = re.sub(
        r'authors = \$\d+::jsonb,\s*',
        '',
        content
    )
    
    # Fix the parameter positions in UPDATE query
    # This is tricky - we need to adjust all the parameter numbers after removing authors
    lines = content.split('\n')
    in_update_query = False
    
    for i, line in enumerate(lines):
        if 'UPDATE papers SET' in line:
            in_update_query = True
        elif in_update_query and 'WHERE id = $1' in line:
            in_update_query = False
        elif in_update_query and '$' in line:
            # Adjust parameter numbers by subtracting 1 for parameters after $4
            def adjust_param(match):
                param_num = int(match.group(1))
                if param_num > 4:  # After the removed authors parameter
                    return f'${param_num - 1}'
                return match.group(0)
            
            lines[i] = re.sub(r'\$(\d+)', adjust_param, line)
    
    content = '\n'.join(lines)
    
    # Remove the None value for authors in the values list
    content = re.sub(
        r'None,  # authors are now stored in separate table\s*',
        '',
        content
    )
    
    with open('src/database/paper_repository.py', 'w') as f:
        f.write(content)
    
    print("Fixed paper repository - removed authors column references")

if __name__ == "__main__":
    fix_paper_repository()