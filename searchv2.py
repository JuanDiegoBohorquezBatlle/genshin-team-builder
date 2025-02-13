import google.generativeai as genai
import json

API_KEY = 'AIzaSyBtZYP4S2cSfpKIAG5XavaWC8Zsa1WUioY' 

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

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
            char_data = character_data.get(char_name.strip())

            if char_data:
                team_text += f" - {char_name} (Role: {char['Role']}, Element: {char['Element']}, Tier: {char['Tier']})\n"
                team_text += f"    - Elemental Skill: {char_data.get('elemental_skill', 'N/A')}\n"
                team_text += f"    - Elemental Burst: {char_data.get('elemental_burst', 'N/A')}\n"
                team_text += f"    - Artifact Set: {char_data.get('best_artifact_set', 'N/A')}\n"
            else:
                team_text += f" - {char_name} (Data not found!)\n"

    prompt = f'''
        You are an expert Genshin Impact team strategist. Based solely on the given team composition and character details, generate a structured explanation that covers elemental synergies, valid reactions, role distribution, resource management, and optimal artifact sets.

        Guidelines:
        1. Only mention elemental reactions that are directly supported by the teams elements.
        2. Do NOT mention any reactions if the team does not have the necessary elements. For example, if no team member provides Electro, do not mention Hyperbloom, Electro-Charged, or Overload.
        3. Allowed reactions (only mention these when applicable):
        - Vaporize = Hydro + Pyro
        - Freeze = Cryo + Hydro
        - Melt = Cryo + Pyro
        - Bloom = Dendro + Hydro
        - Quicken = Dendro + Electro
        - Hyperbloom = Electro + Dendro + Hydro. If this occurs, bloom and quicken should not be mentioned.
        - Electro-Charged = Hydro + Electro
        - Overload = Pyro + Electro
        - Swirl = triggered only with Pyro/Hydro/Electro/Cryo
        - Crystallize = triggered only with Pyro/Hydro/Electro/Cryo
        4. Do not hallucinate or introduce additional reactions. Prioritise information given in the text alongside teams whenever possible.
        5. Format output as Team X: character1 (Role), Character2 (Role), Character3(Role), Character4 (Role)

        Teams for Analysis:
        {team_text}
        '''


    response = model.generate_content(prompt) 

    print(response.text)
    return response.text

