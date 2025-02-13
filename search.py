import google.generativeai as genai
API_KEY='AIzaSyBtZYP4S2cSfpKIAG5XavaWC8Zsa1WUioY'

genai.configure(api_key=API_KEY)


import base64

model = genai.GenerativeModel("gemini-1.5-flash")
async def explain_teams_with_gemini(teams):
    doc_path = "/Users/rgsstudent/Documents/genshin/test.pdf"

    # Read and encode the PDF file
    with open(doc_path, "rb") as doc_file:
        doc_data = base64.standard_b64encode(doc_file.read()).decode("utf-8")

    team_text = "\n\n".join(
        f"{team['Team Name']}:\n" + "\n".join(
            [f" - {char['Name']} (Role: {char['Role']}, Element: {char['Element']}, Tier: {char['Tier']})"
             for char in team['Characters']]
        ) for team in teams
    )

    prompt = f'''You are to create explanations for a given party from the game Genshin Impact.\
    First, get the characters abilities from the PDF and then generate a analysis, covering how their abilities compliment each other.\
    **Use ONLY the abilities described in the attached PDF. Do not infer abilities not mentioned.**
    Secondly, consider their elements and how that enables the team to trigger reactions.\
    Example team: Mavuika, Citlali, Xilonen, Bennett\
    Example response: Teaming Mavuika with Citlali and Xilonen is especially useful for Mavuika's Fighting Spirit regeneration, as she doesn't rely on traditional elemental energy requirements. Both units gain and lose Nightsoul points quickly, 
    allowing Mavuika to continuously cast her Elemental Burst, which is her main source of damage. Additionally, Citlali can trigger Melt and reduce enemies' Pyro RES through her passive. 
    Xilonen can also act as a RES shredder. Bennett's burst can heal and buff the team's attack. Him being in the team also provides elemental resonance: Fervent Flames which triggers with 2 Pyro characters in the team.
    Teams for Analysis:
    {team_text}
    Requirements:
    - Explain elemental synergies and reactions.
    - Resource management
    - Role distribution for each team. 
    '''

    response = model.generate_content([
        {'mime_type': 'application/pdf', 'data': doc_data},
        prompt
    ])
    
    print(response.text)
    return response.text



