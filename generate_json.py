import os
import json

# Path to the character images directory
CHARACTER_DIR = "/Users/rgsstudent/Documents/genshin/static/assets/images/characters"
OUTPUT_FILE = os.path.join(CHARACTER_DIR, "characters.json")

def generate_character_list():
    # List all folders in CHARACTER_DIR (assuming each folder is a character)
    characters = sorted([
        folder.replace("_", " ").title() for folder in os.listdir(CHARACTER_DIR) 
        if os.path.isdir(os.path.join(CHARACTER_DIR, folder))
    ])

    # Save to characters.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(characters, f, indent=4)

    print(f"Generated {OUTPUT_FILE} with {len(characters)} characters.")

if __name__ == "__main__":
    generate_character_list()

