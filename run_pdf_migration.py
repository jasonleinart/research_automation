#!/usr/bin/env python3
import asyncio
from src.database.connection import db_manager

async def run_migration():
    await db_manager.initialize()
    async with db_manager.get_connection() as conn:
        with open('database/migrations/002_add_pdf_storage.sql', 'r') as f:
            migration_sql = f.read()
        
        # Use the same SQL parsing function as setup_notes_schema.py
        def split_sql_statements(sql_content: str) -> list:
            """Split SQL content into individual statements, handling dollar-quoted strings."""
            import re
            statements = []
            current_statement = ""
            in_dollar_quote = False
            dollar_tag = ""
            paren_depth = 0
            
            lines = sql_content.split('\n')
            
            for line in lines:
                # Check for dollar-quoted string start/end
                if not in_dollar_quote:
                    # Look for start of dollar-quoted string
                    dollar_match = re.search(r'\$([^$]*)\$', line)
                    if dollar_match:
                        in_dollar_quote = True
                        dollar_tag = dollar_match.group(1)
                        current_statement += line + "\n"
                        continue
                
                if in_dollar_quote:
                    current_statement += line + "\n"
                    # Check for end of dollar-quoted string
                    if f"${dollar_tag}$" in line:
                        in_dollar_quote = False
                        dollar_tag = ""
                    continue
                
                # Track parentheses depth for function definitions
                paren_depth += line.count('(') - line.count(')')
                
                current_statement += line + "\n"
                
                # Check if statement ends (semicolon outside of parentheses and not in dollar quote)
                if line.strip().endswith(';') and paren_depth == 0 and not in_dollar_quote:
                    statement = current_statement.strip()
                    if statement:
                        statements.append(statement)
                    current_statement = ""
                    paren_depth = 0
            
            # Add any remaining statement
            if current_statement.strip():
                statements.append(current_statement.strip())
            
            return statements
        
        statements = split_sql_statements(migration_sql)
        
        for i, statement in enumerate(statements, 1):
            try:
                await conn.execute(statement)
                print(f"Executed statement {i}/{len(statements)}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"Skipped statement {i} (already exists): {str(e)[:100]}...")
                else:
                    print(f"Error executing statement {i}: {e}")
                    raise
    
    await db_manager.close()
    print("PDF storage migration completed!")

if __name__ == "__main__":
    asyncio.run(run_migration()) 