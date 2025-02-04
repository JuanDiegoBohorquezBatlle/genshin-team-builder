import genshin
from fastapi import FastAPI, HTTPException, Request 
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import genshin
import pandas as pd
import json 
import time 
from search import explain_teams_with_gemini
from fastapi.staticfiles import StaticFiles

start= time.time()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# User data model for login
class HoYoLABLoginRequest(BaseModel):
    username: str
    password: str

cookies = {}

@app.post("/hoyolab_login")
async def hoyolab_login(request: HoYoLABLoginRequest):
    try:
        client = genshin.Client()
        login_cookies = await client.login_with_password(request.username, request.password)
        ltuid_v2 = login_cookies.ltuid_v2 if hasattr(login_cookies, 'ltuid_v2') else None
        ltoken_v2 = login_cookies.ltoken_v2 if hasattr(login_cookies, 'ltoken_v2') else None
        ltmid_v2 = login_cookies.ltmid_v2 if hasattr(login_cookies, 'ltmid_v2') else None
        cookies['ltuid_v2'] = ltuid_v2
        cookies['ltoken_v2'] = ltoken_v2
        cookies['ltmid_v2'] = ltmid_v2
        # Return cookies in the response to the frontend
        print(cookies)
        return cookies

    except genshin.errors.InvalidCookies:
        raise HTTPException(status_code=401, detail="Invalid login credentials.")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_characters")
async def get_characters():
    # Check if cached data exists
    try:
        with open('cached_characters.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Fetch if no cache
        client = genshin.Client(cookies)
        characters = await client.get_calculator_characters(sync=True)
        character_names = [char.name for char in characters]
        with open('cached_characters.json', 'w') as f:
            json.dump(character_names, f)
        return character_names


def load_character_data():
    df = pd.read_csv('actual.csv')
    if df['Character'].duplicated().any():
        raise ValueError("Duplicate characters found")

    
    df['Best Role'] = df['Best Role'].str.split('/')  # Split roles directly
    character_data = df.set_index('Character')[['Best Role', 'Role Tier', 'Element', 'Nightsoul']].to_dict(orient='index')
    
    for char in character_data:
        character_data[char]['roles'] = character_data[char]['Best Role']
        character_data[char]['tier'] = character_data[char]['Role Tier']
        character_data[char]['element'] = character_data[char]['Element']
        character_data[char]['nightsoul'] = character_data[char]['Nightsoul']
        del character_data[char]['Best Role']
        del character_data[char]['Role Tier']
        del character_data[char]['Element']
        del character_data[char]['Nightsoul']

    return character_data



def tier_sort(character_list, character_data):
    tier_order = {"SS": 150, "S": 100, "A": 50, "B": 20, "C": 10}
    return sorted(character_list, key=lambda char: tier_order[character_data[char]['tier']], reverse=True)

def calculate_resonance_score(team_elements):
    """Calculate team resonance score based on element combinations."""
    element_counts = {}
    for element in team_elements:
        element_counts[element] = element_counts.get(element, 0) + 1
    
    score = 0
    
    # Score different resonances
    for element, count in element_counts.items():
        if count >= 2:
            if element == "Pyro":  # ATK +25%
                score += 20
            elif element == "Hydro":  # HP +25%
                score += 15
            elif element == "Cryo":  # CRIT Rate +15%
                score += 20
            elif element == "Electro":  # Energy Recharge
                score += 15
            elif element == "Geo":  # Shield Strength + DMG
                score += 15
            elif element == "Anemo":  # Stamina & Movement
                score += 10
            elif element == "Dendro":  # EM +50
                score += 15
    
    # Core reaction combinations
    if "Hydro" in element_counts and "Pyro" in element_counts:  # Vaporize
        score += 25
    if "Cryo" in element_counts and "Pyro" in element_counts:  # Melt
        score += 25
    if "Cryo" in element_counts and "Hydro" in element_counts:  # Freeze
        score += 10
    if "Electro" in element_counts and "Pyro" in element_counts:  # overload 
        score += 5  
    if "Electro" in element_counts and "Hydro" in element_counts:  # Electrocharged
        score += 5
    
    if "Anemo" in element_counts and "Hydro" or "Pyro" or "Electro" in element_counts: #swirl 
        score+=15 
    
    if "Anemo" in element_counts and "Geo" or "Dendro" in element_counts:
        score-=5 

    if "Dendro" in element_counts:
        # Hyperbloom (Dendro + Hydro + Electro)
        if "Hydro" in element_counts and "Electro" in element_counts:
            score += 35  
        
        # Aggravate (Dendro + Electro)
        elif "Electro" in element_counts:
            score += 15 
            
        # Bloom base reaction
        elif "Hydro" in element_counts:
            score += 5
            
        # Burning
        elif "Pyro" in element_counts:
            score += 5 
            
        # Spread (Dendro + Electro application)
        if "Electro" in element_counts:
            score += 10  

    return score


# generate teams 
def generate_teams_optimized(user_characters, character_data, num_teams, max_teams_per_dps):
    roles = {
        "Main DPS": {},
        "Sub-DPS": {},
        "Support": {}
    }
    
    char_elements = {}
    char_nightsoul = {} 
    main_dps_usage = {}
    
    for char in user_characters:
        if char in character_data:
            char_roles = character_data[char]['roles']
            char_tier = character_data[char]['tier']
            char_element = character_data[char]['element']
            char_nightsoul_status = character_data[char]['nightsoul']
            tier_value = {"SS": 150, "S": 120, "A": 90, "B": 50, "C": 20}[char_tier]
            
            char_elements[char] = char_element
            char_nightsoul[char] = char_nightsoul_status
            for role in char_roles:
                roles[role][char] = tier_value
                if role == 'Main DPS':
                    main_dps_usage[char] = 0 

    teams = []
    team_scores = []

    def calculate_nightsoul_score(team):
        """Calculate bonus score based on number of Nightsoul characters"""
        nightsoul_count = sum(1 for char in team if char_nightsoul[char])
        if nightsoul_count == 4:
            return 20
        elif nightsoul_count == 3:
            return 15
        elif nightsoul_count >= 2:
            return 10
        return 0

    def verify_roles(team):
        """Verify that team has all required roles filled"""
        has_main_dps = False
        has_sub_dps = False
        support_count = 0
        
        for char in team:
            if any(char in roles[role] for role in character_data[char]['roles']):
                if 'Main DPS' in character_data[char]['roles']:
                    has_main_dps = True
                if 'Sub-DPS' in character_data[char]['roles']:
                    has_sub_dps = True
                if 'Support' in character_data[char]['roles']:
                    support_count += 1
        
        return has_main_dps and has_sub_dps and support_count >= 1

    def get_main_dps(team):
        """Return the Main DPS character from the team"""
        for char in team:
            if 'Main DPS' in character_data[char]['roles']:
                return char
        return None

    def is_unique_team(new_team, existing_teams):
        """Check if the team composition is unique (regardless of order)"""
        new_team_set = set(new_team)
        for team in existing_teams:
            if set(team) == new_team_set:
                return False
        return True

    def try_build_team(base_chars=None, current_score=0):
        if base_chars is None:
            base_chars = []
            
        team = base_chars.copy()
        needed_roles = ["Main DPS", "Sub-DPS", "Support", "Support"]
        needed_roles = needed_roles[len(base_chars):]
        if len(team) == 4:
            main_dps_char = get_main_dps(team)
            if main_dps_char and main_dps_usage[main_dps_char] >= max_teams_per_dps:
                return None, -1
        
        team_elements = [char_elements[char] for char in team]
        
        # Calculate score only once per character
        for role, char in zip(needed_roles, team[len(base_chars):]):
            if char in roles[role]:
                current_score += roles[role][char] 
                
        if len(team) == 4:
            current_score += calculate_resonance_score(team_elements)
            current_score += calculate_nightsoul_score(team)
        
        if len(team) == 4:
            # Only return team if it meets role requirements and is unique
            if verify_roles(team) and is_unique_team(team, teams):
                return team, current_score
            return None, -1

        best_team = None
        best_score = -1
        
        if len(team) >= 2:
            has_main_dps = any('Main DPS' in character_data[char]['roles'] for char in team)
            if not has_main_dps and 'Main DPS' not in needed_roles:
                return None, -1
        
        for role in needed_roles:
            for char in roles[role]:
                # Check that character is available and not already in the team
                if char in user_characters and char not in team:
                    new_team = team + [char]
                    new_score = current_score + roles[role][char] 
                    
                    complete_team, final_score = try_build_team(new_team, new_score)
                    if complete_team and final_score > best_score:
                        best_team = complete_team
                        best_score = final_score
        return best_team, best_score

    # Generate specified number of teams
    attempts = 0
    max_attempts = num_teams * 5  # Prevent infinite loops if we can't find enough unique teams
    while len(teams) < num_teams and attempts < max_attempts:
        team, score = try_build_team()
        if team:
            main_dps_char = get_main_dps(team)
            if main_dps_char:
                main_dps_usage[main_dps_char] += 1
            teams.append(team)
            team_scores.append(score)
        attempts += 1
    
    sorted_teams = [x for _, x in sorted(zip(team_scores, teams), reverse=True)]
    return sorted_teams

@app.post("/explain_teams_with_gemini")
async def explain_teams_endpoint(teams: dict):
    try:
        explanation = await explain_teams_with_gemini(teams['teams'])
        return explanation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generate_teams")
async def generate_teams():     
    user_characters = await get_characters()
    print(user_characters)
    character_data = load_character_data()

    # Generate teams
    recommended_teams = generate_teams_optimized(user_characters, character_data,6,2)
    print(recommended_teams)
    teams_for_explanation = []

    for i, team in enumerate(recommended_teams):
        formatted_team = {
            "Team Name": f"Team {i + 1}",
            "Characters": [
                {
                    "Name": char,
                    "Role": ', '.join(character_data[char]['roles']),
                    "Element": character_data[char]['element'],
                    "Tier": character_data[char]['tier']
                }
                for char in team
            ]
        }
        teams_for_explanation.append(formatted_team)

    # Call the explain function with Gemini
    explanation = await explain_teams_with_gemini(teams_for_explanation)

    t1 = time.time() - start
    print(f"Execution Time: {t1:.2f} seconds")
    return {
        "teams": teams_for_explanation,
        "explanation": explanation,
        "status": "success"
    }


@app.post("/generate_teams_from_selection")
async def generate_teams_from_selection(request:Request):
    data = await request.json()
    user_characters = data.get('characters', [])
    print(f"test {user_characters}")     
    character_data = load_character_data()

    recommended_teams = generate_teams_optimized(user_characters, character_data,6,2)
    print(f"Recommended teams:{recommended_teams}")
    teams_for_explanation = []

    for i, team in enumerate(recommended_teams):
        formatted_team = {
            "Team Name": f"Team {i + 1}",
            "Characters": [
                {
                    "Name": char,
                    "Role": ', '.join(character_data[char]['roles']),
                    "Element": character_data[char]['element'],
                    "Tier": character_data[char]['tier']
                }
                for char in team
            ]
        }
        teams_for_explanation.append(formatted_team)

    # Call the explain function with Gemini
    explanation = await explain_teams_with_gemini(teams_for_explanation)

    t1 = time.time() - start
    print(f"Execution Time: {t1:.2f} seconds")
    return {
        "teams": teams_for_explanation,
        "explanation": explanation,
        "status": "success"
    }
