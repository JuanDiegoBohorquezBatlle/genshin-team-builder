from google import genai
import json
import os
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY environment variable not set.")
client = genai.Client(api_key=API_KEY)

async def explain_teams(teams): 
    character_data_path='characters.json'
    try:
        with open(character_data_path, 'r', encoding='utf-8') as f:
            character_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Character data file '{character_data_path}' not found.")
        return None  
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{character_data_path}'.")
        return None

    team_text = ""
    for team in teams:
        formatted_team_key = ", ".join(
            f"{char['Name']} ({char['Role']})" for char in team['Characters']
        )
        
        team_text += f"**Team Explanation Start**\nTEAM: {formatted_team_key}\nExplanation:\n"
        for char in team['Characters']:
            char_name = char['Name']
            # Ensure the lookup key is capitalized correctly, handling hyphens (e.g., "Kaedehara-Kazuha")
            lookup_key = '-'.join(part.capitalize() for part in char_name.strip().split('-'))
            char_data = character_data.get(lookup_key)

            if char_data:
                # Use the original char_name for display purposes if needed, or lookup_key if consistent capitalization is preferred
                team_text += f" - {lookup_key} (Role: {char['Role']}, Element: {char['Element']}, Tier: {char['Tier']})\n" 
                team_text += f"    - Elemental Skill: {char_data.get('elemental_skill', 'N/A')}\n"
                team_text += f"    - Elemental Burst: {char_data.get('elemental_burst', 'N/A')}\n"
                team_text += f"    - Passive talent 1: {char_data.get('passive_talent_1','N/A')}\n"
                team_text += f"    - Passive talent 2: {char_data.get('passive_talent_2', 'N/A')}\n"
                team_text += f"    - Artifact Set: {char_data.get('best_artifact_set', 'N/A')}\n"
            else:
                 # Use the original char_name or lookup_key here as well
                team_text += f" - {lookup_key} (Data not found!)\n"
    print(team_text)
    prompt = f'''
        You are an expert Genshin Impact team strategist. Based solely on the given team composition and character details, generate a structured explanation that covers elemental synergies, valid playstyles, role distribution, resource management (based on characters' energy requirements), a funny overall judgement on the team and optimal artifact sets.

        1. Allowed reactions (DO NOT mix up these reactions, DO NOT MENTION UNRELATED REACTIONS.):
        - Vaporize = Hydro + Pyro
        - Freeze = Cryo + Hydro
        - Superconduct = Cryo + Electro
        - Melt = Cryo + Pyro
        - Burning = Dendro + Pyro 
        - Bloom = Dendro + Hydro
        - Quicken = Dendro + Electro
        - Hyperbloom = Electro + Dendro + Hydro. If this occurs, bloom or quicken should not be mentioned.
        - Burgeon = Pyro + Dendro + Hydro 
        - Electro-Charged = Hydro + Electro
        - Overload = Pyro + Electro
        - Swirl = triggered only with Pyro/Hydro/Electro/Cryo
        - Crystallize = triggered only with Pyro/Hydro/Electro/Cryo
        2. IMPORTANT: Capitalize the first letter of all character names in the explanation, but KEEP the hyphens, e.g Kamisato-Ayato instead of kamisato-ayato.
        3. The following is an example explanation generation:
        (GENERATE ALL TEAMS LIKE THIS, and always start with Team 1)**Team 1: Mavuika (Main DPS), Citlali (Sub-DPS), Xilonen (Support), Bennett (Support)** 
        Both Citlali and Xilonen gain and lose Nightsoul points quickly, allowing Mavuika to continuously cast her Elemental Burst with ease. Bennett provides healing and ATK buff through his Burst.

        Role distribution: Citlali is a notable off-field Cryo driver who can help Mavuika continuously trigger Melt on most of her attacks. On top of that, Citlali reduces enemies’ resistance to Pyro by 20% through her Ascension passive. Let Xilonen take the field for a few seconds and shred enemies' RES, allowing your attacks to deal more manage.

        Resource management: Fighting Spirit generation is crucial for Mavuika, but that is not an issue with both Citlali and Xilonen, who both have Nightsoul, in the team.
        
        Overall, this is an extremely good team which should serve you well in both the abyss and the overworld. With 3 five-stars in the same team, are you sure you aren't a whale?
        
        Recommended artifact set: Mavuika (Obsidian Codex), Citlali (Scroll of the Hero of Cinder City), Xilonen (Archaic Petra), Bennett (Noblesse Oblige)

        Teams for Analysis:
        {team_text}
        '''


    response = client.models.generate_content(model="gemini-2.5-flash",
                                       contents=prompt, 
                                       config=types.GenerateContentConfig(temperature=0.5)
                                       ) 

    print(response.text)
    return response.text
