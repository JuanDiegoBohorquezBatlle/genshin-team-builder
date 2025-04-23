from fastapi import FastAPI, HTTPException, Request 
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import genshin 
import pandas as pd
import json 
import time
import os 
from itertools import combinations
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
load_dotenv()

from searchv2 import explain_teams
from fastapi.templating import Jinja2Templates


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HoYoLABLoginRequest(BaseModel):
    username: str
    password: str

@app.get("/")
def root(request : Request):
    return templates.TemplateResponse("login.html", {"request": request})
    

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    with open("static/login.html", "r") as file:
        return HTMLResponse(content=file.read())

@app.post("/hoyolab_login")
async def hoyolab_login(request: HoYoLABLoginRequest):
    try:
        client = genshin.Client()
        login_cookies = await client.login_with_password(request.username, request.password)
        return {
            "ltuid_v2": login_cookies.ltuid_v2 if hasattr(login_cookies, 'ltuid_v2') else None,
            "ltoken_v2": login_cookies.ltoken_v2 if hasattr(login_cookies, 'ltoken_v2') else None,
            "ltmid_v2": login_cookies.ltmid_v2 if hasattr(login_cookies, 'ltmid_v2') else None,
        }

    except genshin.errors.InvalidCookies:
        raise HTTPException(status_code=401, detail="Invalid login credentials.")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def normalise(name):
    # Normalize and convert to lowercase
    return name.replace(" ", "-").lower()

@app.post("/get_characters") # Changed to POST
async def get_characters(request: Request):
    try:
        # Expect cookies in the request body
        body = await request.json()
        hoyolab_cookies = {
            "ltuid_v2": body.get("ltuid_v2"),
            "ltoken_v2": body.get("ltoken_v2"),
            "ltmid_v2": body.get("ltmid_v2"),
        }

        # Validate required cookies
        if not hoyolab_cookies.get("ltuid_v2") or not hoyolab_cookies.get("ltoken_v2"):
             raise HTTPException(status_code=401, detail="Missing required HoYoLAB authentication cookies (ltuid_v2, ltoken_v2) in request body.")

        client = genshin.Client(hoyolab_cookies)
        # Fetch characters directly, removed file caching
        characters = await client.get_calculator_characters(sync=True)
        character_names = [char.name for char in characters]
        return character_names
    except genshin.errors.InvalidCookies:
        raise HTTPException(status_code=401, detail="Invalid HoYoLAB cookies provided.")
    except Exception as e:
        print(f"Error fetching characters: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch characters: {str(e)}")


def load_character_data():
    # Load character data from CSV, handling potential duplicates and processing roles
    try:
        df = pd.read_csv('actual.csv')
    except FileNotFoundError:
        print("Error: 'actual.csv' not found. Cannot load character data.")
        return {} # Return empty dict if file not found

    # Check for duplicates before setting index
    duplicates = df[df['Character'].duplicated()]['Character'].tolist()
    if duplicates:
        print(f"Warning: Duplicate characters found in actual.csv and will be dropped: {duplicates}")
        df = df.drop_duplicates(subset='Character', keep='first')

    if df['Character'].isnull().any():
        print("Warning: Found rows with missing 'Character' names in actual.csv. These rows will be skipped.")
        df = df.dropna(subset=['Character'])

    # Normalize character names in the DataFrame index *before* creating the dictionary
    df['Character'] = df['Character'].apply(normalise)
    df = df.set_index('Character')

    # Check for required columns
    required_columns = ['Best Role', 'Role Tier', 'Element', 'Nightsoul', 'Off-field']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: Missing required columns in actual.csv: {missing_columns}. Cannot process character data fully.")

    processed_data = {}
    for char_name, row in df.iterrows():
        try:
            roles = str(row.get('Best Role', '')).split('/') if pd.notna(row.get('Best Role')) else []
            tier = str(row.get('Role Tier', 'B'))
            element = str(row.get('Element', 'Unknown')) 
            nightsoul = bool(row.get('Nightsoul', False)) 
            off_field = str(row.get('Off-field', 'False')).strip().upper() == "TRUE" 

            processed_data[char_name] = {
                'roles': [role.strip() for role in roles if role.strip()], 
                'tier': tier.strip(),
                'element': element.strip(),
                'nightsoul': nightsoul,
                'off_field': off_field
            }
        except Exception as e:
            print(f"Error processing character '{char_name}': {e}. Skipping this character.")

    print(f"Loaded data for {len(processed_data)} characters.")
    return processed_data

# --- Character Data Loading ---
# Load character data once at startup
character_data = load_character_data()
# --- End Character Data Loading ---

# --- Team Rules Loading ---
def load_team_rules(filepath="team_rules.json"):
    try:
        with open(filepath, 'r') as f:
            rules = json.load(f)
            # Basic validation (check if keys exist)
            if "incompatible_supports" not in rules or "synergy_rules" not in rules:
                print(f"Warning: '{filepath}' is missing expected keys ('incompatible_supports', 'synergy_rules'). Using empty rules.")
                return {"incompatible_supports": {}, "synergy_rules": {}}
            print(f"Loaded team rules from '{filepath}'.")
            return rules
    except FileNotFoundError:
        print(f"Warning: Team rules file '{filepath}' not found. Using empty rules.")
        return {"incompatible_supports": {}, "synergy_rules": {}}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in team rules file '{filepath}'. Using empty rules.")
        return {"incompatible_supports": {}, "synergy_rules": {}}

team_rules = load_team_rules()
INCOMPATIBLE_SUPPORTS = team_rules.get("incompatible_supports", {})
SYNERGY_RULES = team_rules.get("synergy_rules", {})
# --- End Team Rules Loading ---


# Corrected expand_traveler_variants function definition
def expand_traveler_variants(user_characters, char_data): # Renamed param for clarity
    # Use lowercase consistent names from normalization
    traveler_variants = [
        'traveler-anemo',
        'traveler-geo',
        'traveler-electro',
        'traveler-dendro',
        'traveler-hydro',
        'traveler-pyro'
    ]
    # Normalize input characters first (assuming they might not be normalized yet)
    normalized_user_chars = [normalise(name) for name in user_characters]

    new_characters = set() # Use a set to avoid duplicates
    for char in normalized_user_chars:
        if char == 'traveler':
            # Add only traveler variants that actually exist in the loaded data
            valid_travelers = [tv for tv in traveler_variants if tv in char_data]
            new_characters.update(valid_travelers)
        elif char in char_data: # Only add characters present in the data
             new_characters.add(char)
        # else:
        #     print(f"Warning: Character '{char}' from user list not found in character data. Skipping.")

    return list(new_characters) # Return as list



def tier_sort(character_list, char_data): # Use char_data consistently
    tier_order = {"SS": 100, "S": 80, "A": 50, "B": 20, "C": 10}
    # Ensure character exists in data before sorting and handle missing tiers gracefully
    valid_chars = [char for char in character_list if char in char_data]
    return sorted(valid_chars, key=lambda char: tier_order.get(char_data[char].get('tier', 'C'), 0), reverse=True)

def calculate_resonance_score(team_elements, team, char_cache): # char_cache comes from generate_teams_optimized
        element_counts = {}
        score = 0 
        for element in team_elements:
            element_counts[element] = element_counts.get(element, 0) + 1
        for char in team: #character specific support
            if char == 'Fischl': #fischl not the best in hyperbloom
                    hydro = element_counts.get('Hydro',0)
                    dendro = element_counts.get('Dendro',0)
                    if hydro + dendro >= 2:
                        score-=20 
            if 'Support' in char_cache[char]['roles']:
                # Chev needs Pyro/Electro teammates
                if char == 'Chevreuse':
                    pyro = element_counts.get('Pyro', 0)
                    electro = element_counts.get('Electro', 0)
                    if pyro + electro < 3:
                        score -= 50  
                        
                # Sara needs Electro DPS
                elif char == 'Kujou Sara':
                    if element_counts.get('Electro', 0) < 2:
                        score -= 100
                
                # Shenhe is a cryo support 
                elif char == 'Shenhe':
                    if element_counts.get('Cryo', 0) < 2:
                        score -= 100
                
                elif char == 'Faruzan':
                    if element_counts.get('Anemo', 0) < 2:
                        score -= 100
                
                elif char == 'Gorou':
                    if element_counts.get('Geo', 0) < 2:
                        score -= 100

                elif char == 'Kuki Shinobu': #prioritize kuki over other electro supports like fischl in hyperbloom teams
                    hydro = element_counts.get('Hydro',0)
                    dendro = element_counts.get('Dendro',0)
                    if hydro + dendro >= 2:
                        score+=100
                
        
        pyro_count = element_counts.get("Pyro", 0)
        hydro_count = element_counts.get("Hydro", 0)
        cryo_count = element_counts.get("Cryo", 0)
        electro_count = element_counts.get("Electro", 0)
        geo_count = element_counts.get("Geo", 0)
        anemo_count = element_counts.get("Anemo", 0)
        dendro_count = element_counts.get("Dendro", 0)
        
        #Resonances 
        if pyro_count >= 2: score += 20
        if hydro_count >= 2: score += 15
        if cryo_count >= 2: score += 20
        if electro_count >= 2: score += 15
        if geo_count >= 2: score += 15
        if anemo_count >= 2: score += 10
        if dendro_count >= 2: score += 15



        #Reactions
        if hydro_count and pyro_count: score += 25  # Vaporize
        if cryo_count and pyro_count: score += 30   # Melt
        if cryo_count and hydro_count: score += 8  # Freeze
        if electro_count and pyro_count: score += 15  # Overload
        dendro_off_field = any(
            char_cache[char]['element'] == 'Dendro' and char_cache[char].get('off_field', True)
            for char in team
    )
        if electro_count and hydro_count and dendro_off_field and pyro_count==0: score += 50  #hyperbloom
        if hydro_count and dendro_count and pyro_count: score += 20 #burgeon 
        if hydro_count and dendro_count: score +=15 #bloom 
        if electro_count and dendro_count: score+=8 #quicken

        if geo_count and (hydro_count or pyro_count or electro_count): #crystallise 
            score +=5
        
        if anemo_count and (hydro_count or pyro_count or electro_count): #swirl
            score += 25
        if anemo_count and (geo_count or dendro_count):
            score -= 50
            
        return score



# generate teams
def generate_teams_optimized(user_characters, char_data, num_teams, max_teams_per_dps): 
    expanded_characters = expand_traveler_variants(user_characters, char_data)
    print(f"Generating teams for: {expanded_characters}")

    char_cache = {}
    char_elements = {} 
    char_nightsoul = {} 
    main_dps_usage = {}

    tier_value_map = {"SS": 100, "S": 80, "A": 50, "B": 20, "C": 10}

    for char in expanded_characters: 
        info = char_data[char]
        roles = set(info.get('roles', [])) 
        tier = info.get('tier', 'B') 
        element = info.get('element', 'Unknown') 
        nightsoul = info.get('nightsoul', False) 
        off_field = info.get('off_field', False) 
        tier_value = tier_value_map.get(tier, 0)

        is_main_dps = 'Main DPS' in roles
        is_sub_dps = 'Sub-DPS' in roles
        is_support = 'Support' in roles

        char_cache[char] = {
            'roles': roles,
            'element': element,
            'nightsoul': nightsoul,
            'tier_value': tier_value,
            'off_field': off_field,
            'is_main_dps': is_main_dps,
            'is_sub_dps': is_sub_dps,
            'is_support': is_support
        }

        # Populate char_elements and char_nightsoul directly from info
        char_elements[char] = element
        char_nightsoul[char] = nightsoul

        if is_main_dps:
            main_dps_usage[char] = 0

    # Filter role_chars based on the actual roles found in char_cache
    role_chars = {
        'Main DPS': [char for char, cache_data in char_cache.items() if cache_data['is_main_dps']],
        'Sub-DPS': [char for char, cache_data in char_cache.items() if cache_data['is_sub_dps']],
        'Support': [char for char, cache_data in char_cache.items() if cache_data['is_support']]
    }

    # Sort roles based on tier_value from char_cache
    for role in role_chars:
        role_chars[role].sort(key=lambda x: char_cache[x]['tier_value'], reverse=True)

    def calculate_off_field_bonus(team):
        # Access off_field safely from char_cache
        off_field_count = sum(1 for char in team if char_cache.get(char, {}).get('off_field', False))
        bonus = 0
        if off_field_count == 2:
            bonus = 10  
        elif off_field_count == 3:
            bonus = 15
        return bonus
    
    def calculate_nightsoul_score(team):
        # Access nightsoul safely from char_cache
        nightsoul_count = sum(1 for char in team if char_cache.get(char, {}).get('nightsoul', False))
        # Simplified scoring logic
        if nightsoul_count >= 4: return 30 # Should not exceed 4, but safe check
        elif nightsoul_count == 3:
            return 25
        elif nightsoul_count >= 2:
            return 20
        return 0

    def calculate_team_score(team):
        # Safely get elements and tier values from char_cache
        elements = [char_cache.get(char, {}).get('element', 'Unknown') for char in team]
        # print(f"Calculating score for team: {team}, Elements: {elements}") # Debug print
        base_score = sum(char_cache.get(char, {}).get('tier_value', 0) for char in team)

        resonance_score = calculate_resonance_score(elements, team, char_cache) # Pass char_cache
        nightsoul_score = calculate_nightsoul_score(team)
        off_field_bonus = calculate_off_field_bonus(team)

        synergy_score = 0
        for char in team:
            if char in SYNERGY_RULES:
                rules = SYNERGY_RULES[char]
                team_elements_set = set(elements) 

                if 'preferred_elements' in rules:
                    count = sum(1 for element in rules['preferred_elements'] if element in team_elements_set)
                    synergy_score += 25 * count

                if 'preferred' in rules:
                    normalized_preferred = [normalise(p) for p in rules['preferred']]
                    count = sum(1 for preferred_char in normalized_preferred if preferred_char in team)
                    synergy_score += 50 * count

                # Excluded elements check
                if 'excluded_elements' in rules:
                    count = sum(1 for element in rules['excluded_elements'] if element in team_elements_set)
                    synergy_score -= 100 * count

            for main_dps, incompatible_list in INCOMPATIBLE_SUPPORTS.items():
                 if main_dps in team and char in [normalise(inc) for inc in incompatible_list] and char != main_dps:
                     synergy_score -= 100

        total_score = base_score + resonance_score + nightsoul_score + off_field_bonus + synergy_score
        # print(f" Team: {team}, Base: {base_score}, Res: {resonance_score}, NS: {nightsoul_score}, Off: {off_field_bonus}, Syn: {synergy_score}, Total: {total_score}") 
        return total_score

    seen_teams = set()
    def is_unique_team(team):
        # Normalize traveler names for consistent checking
        team_key = tuple(sorted(char.replace('traveler-', 'traveler') for char in team))
        if team_key in seen_teams:
            return False
        seen_teams.add(team_key)
        return True
    
    collected_teams = []
    
    # --- Team Generation Logic ---
    collected_teams = []
    # Use the filtered and sorted role_chars lists
    main_dps_list = role_chars.get('Main DPS', [])
    sub_dps_list = role_chars.get('Sub-DPS', [])
    support_list = role_chars.get('Support', [])

    if not main_dps_list:
        print("Warning: No Main DPS characters found in the provided list or data. Cannot generate standard teams.")

    for main in main_dps_list:
        teams_for_main = []
        current_sub_candidates = [s for s in sub_dps_list if s != main]
        current_support_candidates = [sup for sup in support_list if sup != main]

        # --- Format A: 1 Main DPS + 2 Sub-DPS + 1 Support ---
        if len(current_sub_candidates) >= 2 and len(current_support_candidates) >= 1:
            for subs in combinations(current_sub_candidates, 2):
                remaining_supports = [sup for sup in current_support_candidates if sup not in subs]
                for support in remaining_supports:
                    team = [main] + list(subs) + [support]
                    if is_unique_team(team):
                        score = calculate_team_score(team)
                        teams_for_main.append((team, score))

        # --- Format B: 1 Main DPS + 1 Sub-DPS + 2 Supports ---
        if len(current_sub_candidates) >= 1 and len(current_support_candidates) >= 2:
            for sub in current_sub_candidates:
                eligible_supports = [sup for sup in current_support_candidates if sup != sub]
                if len(eligible_supports) >= 2:
                    for supports in combinations(eligible_supports, 2):
                        team = [main, sub] + list(supports)
                        if is_unique_team(team):
                            score = calculate_team_score(team)
                            teams_for_main.append((team, score))

        # --- Format C: 1 Main DPS + 3 Supports (Hypercarry) ---
        # Ensure enough supports exist and are different from main
        if len(current_support_candidates) >= 3:
            for supports in combinations(current_support_candidates, 3):
                team = [main] + list(supports)
                if is_unique_team(team):
                    score = calculate_team_score(team)
                    teams_for_main.append((team, score))

        # Sort and limit teams for this specific main DPS
        teams_for_main.sort(key=lambda x: x[1], reverse=True)
        limited_teams = teams_for_main[:max_teams_per_dps]
        if main in main_dps_usage: # Check if main_dps was added to usage dict
             main_dps_usage[main] += len(limited_teams)
        collected_teams.extend(limited_teams)
    # --- End Team Generation Logic ---

    collected_teams.sort(key=lambda x: x[1], reverse=True)
    # Limit total number of teams
    final_teams = [team for team, score in collected_teams][:num_teams]

    # Fallback if no teams generated but enough characters exist
    if not final_teams and len(expanded_characters) >= 4:
        print("No suitable teams generated based on roles/synergy. Creating fallback team based on tier.")
        # Use the already filtered expanded_characters list
        fallback_team = tier_sort(expanded_characters, char_data)[:4] # Use char_data
        if len(fallback_team) == 4: 
             final_teams = [fallback_team]
        else:
             print("Could not generate a valid fallback team.")

    return final_teams 

@app.post("/explain_teams_with_gemini")
async def explain_teams_endpoint(teams: dict):
    try:
        explanation = await explain_teams(teams['teams'])
        return explanation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_teams_from_selection")
async def generate_teams_from_selection(request: Request):
    try:
        data = await request.json()
        user_characters = data.get('characters', [])
        if not user_characters:
            raise HTTPException(status_code=400, detail="No characters provided in request body.")

        print(f"Generating teams from selection: {user_characters}")
        recommended_teams = generate_teams_optimized(user_characters, character_data, 6, 2)
        print(f"Recommended teams: {recommended_teams}")

        if not recommended_teams:
             return {"teams": [], "explanation": "Could not generate teams from selection. Ensure you provided at least 4 valid characters.", "status": "failure"}

        teams_for_explanation = []
        for i, team in enumerate(recommended_teams):
            formatted_team = {
                "Team Name": f"Team {i + 1}",
                "Characters": [
                     {
                        "Name": char, # Already normalized
                        "Role": ', '.join(character_data.get(char, {}).get('roles', ['N/A'])),
                        "Element": character_data.get(char, {}).get('element', 'N/A'),
                        "Tier": character_data.get(char, {}).get('tier', 'N/A')
                    }
                    for char in team # team contains normalized names
                ]
            }
            teams_for_explanation.append(formatted_team)

        explanation = await explain_teams(teams_for_explanation)

        return {
            "teams": teams_for_explanation,
            "explanation": explanation,
            "status": "success"
        }
    except Exception as e:
        print(f"Error in /generate_teams_from_selection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate teams from selection: {str(e)}")


