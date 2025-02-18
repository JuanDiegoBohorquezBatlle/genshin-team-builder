// Define the API base URL
const BASE_URL = 'https://genshinteambuilder.xyz';  

// Utility function to toggle element visibility
function toggleVisibility(elementId, show) {
    const element = document.getElementById(elementId);
    console.log(`toggleVisibility called for ID: ${elementId}`);
    console.log('Found element:', element);

    if (!element) {
        console.warn(`Element with ID "${elementId}" not found.`);
        return;
    }

    try {
        element.style.display = show ? 'block' : 'none';
    } catch (error) {
        console.error('Error modifying element style:', error);
    }
}


// Login function
async function submitLogin() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (!username || !password) {
        alert('Please enter both username and password.');
        return;
    }

    try {
        toggleVisibility('loading', true);

        const response = await fetch(`${BASE_URL}/hoyolab_login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            throw new Error('Login failed. Please try again.');
        }

        const data = await response.json();
        console.log('Logged in successfully:', data);

        await getUserCharacters();
        
        toggleVisibility('characters', true);

    } catch (error) {
        alert('Login failed: ' + error.message);
        toggleVisibility('loading', false);
    }
}

// Fetch user characters
async function getUserCharacters() {
    try {
        const response = await fetch(`${BASE_URL}/get_characters`);
        console.log("response:", response);
        if (!response.ok) {
            throw new Error('Failed to fetch characters');
        }
        const characters = await response.json();
        console.log('Your characters are:', characters);
        
        if (!characters) {
            throw new Error('No character data received');
        }
        if (!Array.isArray(characters)) {
            throw new Error('Invalid character data received: ' + JSON.stringify(characters));
        }

        await generateTeams();
    } catch (error) {
        console.error('Character fetch error:', error);
        console.error('Response data:', characters);
        alert('Failed to fetch characters: ' + error.message);
        toggleVisibility('loading', false);
    }
}


async function generateTeams() {
    try {
        console.log("Fetching teams...");
        const response = await fetch(`${BASE_URL}/generate_teams`);
        if (!response.ok) {
            throw new Error(`Failed to fetch teams: ${response.status}`);
        }

        const data = await response.json();
        console.log('Server response:', data);

        if (!data.teams || !Array.isArray(data.teams)) {
            throw new Error('Invalid teams data format: ' + JSON.stringify(data));
        }

        const teamsList = document.getElementById('teamsList');
        if (!teamsList) {
            throw new Error('Teams list element not found in DOM');
        }
        const teamsHTML = data.teams.map(team => `
            <li>
                <h3>${team['Team Name']}</h3>
                <div class="characters">
                    ${team.Characters.map(char => `
                        <div class="character">
                            <strong>${char.Name}</strong>
                            <br>Role: ${char.Role}
                            <br>Element: ${char.Element}
                            <br>Tier: ${char.Tier}
                        </div>
                    `).join('')}
                </div>
            </li>
        `).join('');

        sessionStorage.setItem('teamsContent', teamsHTML);
        sessionStorage.setItem('explanationContent', data.explanation || '');
        toggleVisibility('characterSelectionContainer', false); 
        displayTeams(data.teams, data.explanation);

        toggleVisibility('loading', false);

        console.log('Teams generated successfully and saved');
    } catch (error) {
        console.error('Error generating teams:', error);
        alert('Failed to generate teams: ' + error.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            submitLogin();
        });
    }
});


const LOCAL_ASSETS_PATH = 'assets/images/characters';

async function fetchCharacters() {
    try {
        const response = await fetch(`${LOCAL_ASSETS_PATH}/characters.json`);
        if (!response.ok) {
            throw new Error('Failed to load local character data');
        }
        const characters = await response.json();
        return characters;
    } catch (error) {
        console.error('Error fetching characters:', error);
        alert('Failed to load characters from local assets.');
        return [];
    }
}

async function loadCharacterIcons() {
    const characterIconsContainer = document.getElementById('characterIcons');
    if (!characterIconsContainer) {
        console.error('Character icons container not found');
        return;
    }

    characterIconsContainer.innerHTML = '<div class="text-center">Loading characters...</div>';

    const characters = await fetchCharacters();
    if (characters.length === 0) return;

    characterIconsContainer.innerHTML = '';

    const grid = document.createElement('div');
    grid.classList.add('character-grid');

    characters.forEach(character => {
        const card = document.createElement('div');
        card.classList.add('character-card');

        const img = document.createElement('img');
        img.src = `${LOCAL_ASSETS_PATH}/${character.toLowerCase().replace(/ /g, "_")}/icon-big.png`; 
        img.alt = character;
        img.classList.add('character-icon');

        const name = document.createElement('div');
        name.classList.add('character-name');
        name.textContent = character;

        card.appendChild(img);
        card.appendChild(name);

        card.addEventListener('click', () => toggleCharacterSelection(character, !selectedCharacters.has(character)));

        grid.appendChild(card);
    });

    characterIconsContainer.appendChild(grid);
}


const selectedCharacters = new Set();

function toggleCharacterSelection(character, isSelected) {
    const card = [...document.querySelectorAll('.character-card')]
        .find(el => el.textContent.trim() === character);
    
    if (!card) return;

    if (isSelected) {
        selectedCharacters.add(character);
        card.classList.add('selected');
    } else {
        selectedCharacters.delete(character);
        card.classList.remove('selected');
    }
    const confirmButton = document.getElementById('confirmSelection');
    if (confirmButton) {
        confirmButton.disabled = selectedCharacters.size < 4;
        confirmButton.textContent = `Generate Teams (${selectedCharacters.size} selected)`;
    }
}


async function generateTeamsFromSelection() {
    if (selectedCharacters.size < 4) {
        alert('Please select at least four characters.');
        return;
    }

    try {
        toggleVisibility('loading', true);

        const formattedCharacters = Array.from(selectedCharacters);
        console.log('Sending characters to backend:', formattedCharacters);

        const response = await fetch(`${BASE_URL}/generate_teams_from_selection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ characters: formattedCharacters })
        });

        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }

        const data = await response.json();

        if (!data.teams || !Array.isArray(data.teams)) {
            throw new Error('Invalid teams data format: ' + JSON.stringify(data));
        }
        const teamsHTML = data.teams.map(team => `
            <li>
                <h3>${team['Team Name']}</h3>
                <div class="characters">
                    ${team.Characters.map(char => `
                        <div class="character">
                            <strong>${char.Name}</strong>
                            <br>Role: ${char.Role}
                            <br>Element: ${char.Element}
                            <br>Tier: ${char.Tier}
                        </div>
                    `).join('')}
                </div>
            </li>
        `).join('');
        console.log("TEAMS", teamsHTML);
        console.log("EXPLANATION:", data.explanation);

        localStorage.setItem('teamsContent', teamsHTML);
        localStorage.setItem('explanationContent', data.explanation || '');
        toggleVisibility('characterSelectionContainer', false);

        displayTeams(data.teams, data.explanation);
        const teamsTab = document.getElementById('pills-teams-tab');
        const bsTab = new bootstrap.Tab(teamsTab);
        bsTab.show();
        


    } catch (error) {
        console.error('Error generating teams:', error);
        alert('Failed to generate teams: ' + error.message);
    } finally {
        toggleVisibility('loading', false);
    }
}

function canonicalizeTeamKey(key) {
    return key         
      .replace(/\//g, ', ')       
      .replace(/\s*,\s*/g, ', ')                 
      .trim();
  }

function displayTeams(teams, explanation) {
    console.log("DisplayTeams called with:", { teams, explanation });
    const teamsList = document.getElementById("teamsList");
    const teamsContainer = document.getElementById('teams-container');

    if (!teamsList) {
        console.error("teamsList element not found in DOM");
        return;
    }

    if (!teamsContainer) {
        console.error("teams-container element not found in DOM");
        return;
    }

    console.log("Received teams:", teams);
    console.log("Received explanation:", explanation);

    if (!teams || teams.length === 0) {
        teamsList.innerHTML = "<p>No teams generated.</p>";
        return;
    }

    let explanationSections = {};

    if (explanation) {
        const explanationParts = explanation.split(/\*\*Team \d+:\s?(.*?)\*\*/is);

        for (let i = 1; i < explanationParts.length; i += 2) {
            const teamKey = canonicalizeTeamKey(explanationParts[i].trim());
            const teamExplanation = explanationParts[i + 1]?.trim() || "No explanation available.";
            explanationSections[teamKey] = teamExplanation;
        }
    }
    console.log(explanationSections);
    teamsList.innerHTML = teams.map((team) => {
        const teamName = `<h3>${team["Team Name"]}</h3>`;

        const characterDisplay = team.Characters.map(char => `
            <div class="character-entry">
                <img src="${LOCAL_ASSETS_PATH}/${char.Name.toLowerCase().replace(/ /g, "_")}/icon-big.png" 
                     alt="${char.Name}" 
                     class="character-icon">
                <span class="character-name">${char.Name} (${char.Role})</span>
            </div>
        `).join("");

        const teamKey = canonicalizeTeamKey(team.Characters.map(c => `${c.Name} (${c.Role})`).join(", "));
        console.log("Looking for explanation with key:", teamKey);

        const formattedExplanation = explanationSections[teamKey]
            ? `<p>${explanationSections[teamKey].replace(/\n/g, "<br>")}</p>`
            : "<p>No explanation available.</p>";
        console.log(formattedExplanation);
        return `
            <li class="team-card">
                ${teamName}
                <div class="character-icons">${characterDisplay}</div>
                <div class="team-explanation">${formattedExplanation}</div>
            </li>
        `;
    }).join("");

    if (teamsContainer) {
        teamsContainer.style.display = 'block';
    }
    
    const trigger = document.getElementById('pills-teams-tab');
    if (trigger) {
        new bootstrap.Tab(trigger).show();
    }

    toggleVisibility("teams-container", true);
}





document.getElementById('confirmSelection')?.addEventListener('click', generateTeamsFromSelection);

document.addEventListener('DOMContentLoaded', () => {
    loadCharacterIcons();
    toggleVisibility('characterSelectionContainer', true);
});

