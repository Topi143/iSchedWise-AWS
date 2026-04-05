"""
Script to remove duplicate schedules from ischedwise.sql
Keeps the first occurrence (lowest ID) for each unique slot.
"""
import re

def main():
    # Read the file
    with open('ischedwise.sql', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the schedules INSERT statement
    pattern = r"(INSERT INTO `schedules` \([^)]+\) VALUES )(\([^;]+);"
    match = re.search(pattern, content)

    if not match:
        print('Could not find schedules INSERT statement')
        return

    prefix = match.group(1)
    values_str = match.group(2)
    
    # Parse individual records
    parts = re.findall(r'\([^)]+\)', values_str)
    
    seen_slots = set()
    kept_records = []
    duplicates_removed = 0
    
    for part in parts:
        vals = part.strip('()')
        
        # Use regex to extract values properly
        val_match = re.match(r"(\d+),(\d+),(\d+),([^,]+),([^,]+),'([^']+)','([^']+)','([^']+)','([^']+)','([^']+)','([^']+)',(\d+),", vals)
        if val_match:
            id_val = int(val_match.group(1))
            section_id = val_match.group(2)
            day_of_week = val_match.group(6)
            start_time = val_match.group(7)
            end_time = val_match.group(8)
            semester = val_match.group(9)
            academic_year = val_match.group(10)
            is_active = val_match.group(12)
            
            # Create unique key matching the constraint (WITHOUT is_active)
            # The uk_section_slot constraint is: (section_id, day_of_week, start_time, end_time, academic_year, semester)
            slot_key = (section_id, day_of_week, start_time, end_time, academic_year, semester)
            
            if slot_key not in seen_slots:
                seen_slots.add(slot_key)
                kept_records.append(part)
            else:
                duplicates_removed += 1
                print(f'Removed duplicate: id={id_val} ({section_id}, {day_of_week}, {start_time}-{end_time}, is_active={is_active})')
        else:
            kept_records.append(part)  # Keep if can't parse
    
    # Rebuild the INSERT statement
    new_values = ','.join(kept_records)
    new_insert = prefix + new_values + ';'
    
    # Replace in content
    new_content = content[:match.start()] + new_insert + content[match.end():]
    
    # Write back
    with open('ischedwise.sql', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f'\nTotal duplicates removed: {duplicates_removed}')
    print(f'Records kept: {len(kept_records)}')

if __name__ == '__main__':
    main()
