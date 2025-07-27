-- Migration script to extract clean author data from existing papers
-- and populate the new authors and paper_authors tables

-- Function to extract clean author name from nested Author objects
CREATE OR REPLACE FUNCTION extract_clean_author_name(author_json JSONB) 
RETURNS TEXT AS $$
DECLARE
    author_str TEXT;
    clean_name TEXT;
BEGIN
    -- Convert JSONB to string
    author_str := author_json::TEXT;
    
    -- Handle deeply nested Author objects by extracting the innermost name
    -- Pattern: Author(name='...', affiliation=None, email=None)
    -- We want to extract the actual name from the innermost level
    
    -- First, try to extract from the pattern Author(name='...', ...)
    IF author_str LIKE 'Author(name=%' THEN
        -- Extract the name part after 'name='
        clean_name := SUBSTRING(author_str FROM 'name=''([^'']*)''');
        
        -- If that didn't work, try with double quotes
        IF clean_name IS NULL THEN
            clean_name := SUBSTRING(author_str FROM 'name="([^"]*)"');
        END IF;
        
        -- If still no match, try without quotes
        IF clean_name IS NULL THEN
            clean_name := SUBSTRING(author_str FROM 'name=([^,)]*)');
        END IF;
        
        -- Clean up any remaining Author(...) wrapper
        IF clean_name LIKE 'Author(%' THEN
            clean_name := SUBSTRING(clean_name FROM 'Author\(name=''([^'']*)''');
            IF clean_name IS NULL THEN
                clean_name := SUBSTRING(clean_name FROM 'Author\(name="([^"]*)"');
            END IF;
        END IF;
    ELSE
        -- If it's not in Author format, try to extract as plain string
        clean_name := author_str;
    END IF;
    
    -- Clean up any remaining quotes or special characters
    IF clean_name IS NOT NULL THEN
        clean_name := TRIM(BOTH '''' FROM clean_name);
        clean_name := TRIM(BOTH '"' FROM clean_name);
        clean_name := TRIM(clean_name);
    END IF;
    
    RETURN clean_name;
END;
$$ LANGUAGE plpgsql;

-- Extract and insert authors from existing papers
INSERT INTO authors (name, affiliation, email, created_at, updated_at)
SELECT DISTINCT
    extract_clean_author_name(author_json) as name,
    NULL as affiliation,
    NULL as email,
    NOW() as created_at,
    NOW() as updated_at
FROM papers p,
     jsonb_array_elements(p.authors) as author_json
WHERE p.authors IS NOT NULL 
  AND jsonb_array_length(p.authors) > 0
  AND extract_clean_author_name(author_json) IS NOT NULL
  AND extract_clean_author_name(author_json) != ''
ON CONFLICT (name, email) DO NOTHING;

-- Create paper-author relationships
INSERT INTO paper_authors (paper_id, author_id, author_order, created_at)
SELECT 
    p.id as paper_id,
    a.id as author_id,
    author_json.ordinality as author_order,
    NOW() as created_at
FROM papers p,
     jsonb_array_elements(p.authors) WITH ORDINALITY AS author_json(author_data, ordinality),
     authors a
WHERE p.authors IS NOT NULL 
  AND jsonb_array_length(p.authors) > 0
  AND a.name = extract_clean_author_name(author_json.author_data)
  AND extract_clean_author_name(author_json.author_data) IS NOT NULL
  AND extract_clean_author_name(author_json.author_data) != '';

-- Clean up the function
DROP FUNCTION extract_clean_author_name(JSONB); 