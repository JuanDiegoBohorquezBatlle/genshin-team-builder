import re

def parse_character_data(file_content):
    # Split the content by "Character:" to separate each character's data
    character_blocks = file_content.split("Character: ")[1:]  # Skip the first empty element
    
    characters_dict = {}
    
    for block in character_blocks:
        lines = block.strip().split('\n')
        character_name = lines[0].strip()
        characters_dict[character_name] = {}
        
        current_section = None
        section_content = []
        
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
                
            # Check for known sections
            if line.startswith("Talent priority:") or line.startswith("Talent Priority:"):
                current_section = None  # Reset current section as this is directly processed
                talents = line.split(':', 1)[1].strip().split(',')
                characters_dict[character_name]["talent_priority"] = [t.strip() for t in talents]
            elif line.startswith("Best artifact set:"):
                current_section = None  # Reset current section as this is directly processed
                artifact_info = line.split(':', 1)[1].strip()
                parts = artifact_info.split(' - ', 1)
                name_part = parts[0].strip()
                desc_part = parts[1].strip() if len(parts) > 1 else ""
                
                # Safely handle the (4pc) part if it exists
                if ' (' in name_part:
                    name_parts = name_part.split(' (')
                    name_clean = name_parts[0].strip()
                    piece_info = name_parts[1].rstrip(')') if len(name_parts) > 1 else ""
                else:
                    name_clean = name_part
                    piece_info = ""
                
                characters_dict[character_name]["best_artifact_set"] = {
                    "name": name_clean,
                    "piece_bonus": piece_info,
                    "description": desc_part
                }
            elif line.startswith("Elemental skill:"):
                current_section = "elemental_skill"
                characters_dict[character_name][current_section] = line.split(':', 1)[1].strip()
            elif line.startswith("Elemental Burst:"):
                current_section = "elemental_burst"
                characters_dict[character_name][current_section] = line.split(':', 1)[1].strip()
            elif line.startswith("Passive talent 1:"):
                current_section = "passive_talent_1"
                characters_dict[character_name][current_section] = line.split(':', 1)[1].strip()
            elif line.startswith("Passive talent 2:"):
                current_section = "passive_talent_2"
                characters_dict[character_name][current_section] = line.split(':', 1)[1].strip()
            elif current_section and current_section in characters_dict[character_name]:
                # Append content to the current section if it's a string-based section
                characters_dict[character_name][current_section] += " " + line
    
    return characters_dict

# Example usage:
if __name__ == "__main__":
    # Read the file
    with open('test.txt', 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Parse the content
    result = parse_character_data(content)
    
    # Optional: Pretty print the result
    import json
    print(json.dumps(result, indent=2))
    
    # Optional: Save to file
    with open('characters.json', 'w', encoding='utf-8') as f:
        json.dump(result, indent=2, fp=f)