#!/usr/bin/env python3
"""
Setup notes schema in the database.
This script creates the notes tables, indexes, and functions.
"""

import sys
import os
import asyncio
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.connection import db_manager

def split_sql_statements(sql_content: str) -> list:
    """Split SQL content into individual statements, handling dollar-quoted strings."""
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

async def setup_notes_schema():
    try:
        await db_manager.initialize()
        async with db_manager.get_connection() as conn:
            print("Setting up notes schema...")
            schema_file = Path(__file__).parent.parent.parent / "database" / "schema" / "08_notes.sql"
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            statements = split_sql_statements(schema_sql)
            print(f"Found {len(statements)} SQL statements to execute")
            
            for i, statement in enumerate(statements, 1):
                if statement.strip():
                    try:
                        await conn.execute(statement)
                        print(f"Executed statement {i}/{len(statements)}")
                    except Exception as e:
                        # Skip errors for objects that already exist
                        if "already exists" in str(e).lower():
                            print(f"Skipped statement {i} (already exists): {str(e)[:100]}...")
                            continue
                        print(f"Error executing statement {i}: {e}")
                        print(f"Statement: {statement[:200]}...")
                        return False
            print("✅ Notes schema setup completed successfully!")
            return True
    except Exception as e:
        print(f"Error setting up notes schema: {e}")
        return False
    finally:
        await db_manager.close()

async def verify_notes_schema():
    """Verify that the notes schema was created correctly."""
    try:
        await db_manager.initialize()
        async with db_manager.get_connection() as conn:
            print("Verifying notes schema...")
            
            # Check if tables exist
            tables = ['notes', 'note_tags', 'note_relationships', 'note_collections', 
                     'note_collection_members', 'note_templates']
            for table in tables:
                result = await conn.fetchval(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, table)
                if not result:
                    print(f"❌ Table {table} not found")
                    return False
                print(f"✅ Table {table} exists")
            
            # Check if enums exist
            enums = ['note_type_enum', 'note_priority_enum']
            for enum in enums:
                result = await conn.fetchval(f"""
                    SELECT EXISTS (
                        SELECT FROM pg_type 
                        WHERE typname = $1
                    )
                """, enum)
                if not result:
                    print(f"❌ Enum {enum} not found")
                    return False
                print(f"✅ Enum {enum} exists")
            
            # Check if functions exist
            functions = ['update_note_search_vector', 'update_tag_usage_count', 'get_note_statistics']
            for func in functions:
                result = await conn.fetchval(f"""
                    SELECT EXISTS (
                        SELECT FROM pg_proc 
                        WHERE proname = $1
                    )
                """, func)
                if not result:
                    print(f"❌ Function {func} not found")
                    return False
                print(f"✅ Function {func} exists")
            
            # Check if view exists
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.views 
                    WHERE table_schema = 'public' 
                    AND table_name = 'note_summaries'
                )
            """)
            if not result:
                print("❌ View note_summaries not found")
                return False
            print("✅ View note_summaries exists")
            
            # Check if default templates were inserted
            template_count = await conn.fetchval("SELECT COUNT(*) FROM note_templates")
            if template_count == 0:
                print("❌ No default templates found")
                return False
            print(f"✅ {template_count} default templates found")
            
            print("✅ Notes schema verification completed successfully!")
            return True
    except Exception as e:
        print(f"Error verifying notes schema: {e}")
        return False
    finally:
        await db_manager.close()

async def main():
    print("🚀 Setting up Notes Schema for Research Dashboard")
    print("=" * 50)
    if not await setup_notes_schema():
        print("❌ Failed to set up notes schema")
        sys.exit(1)
    if not await verify_notes_schema():
        print("❌ Notes schema verification failed")
        sys.exit(1)
    print("\n🎉 Notes schema setup completed successfully!")
    print("\nNext steps:")
    print("1. Run the web dashboard to test note functionality")
    print("2. Create some test notes to verify the system")
    print("3. Integrate notes with the PDF viewer (Phase 2)")

if __name__ == "__main__":
    asyncio.run(main()) 