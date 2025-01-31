// Define the API base URL
const BASE_URL = 'http://localhost:8000';  

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

        toggleVisibility('login', false);
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

        const charactersList = document.getElementById('charactersList');
        if (!charactersList) {
            throw new Error('Characters list element not found');
        }

        charactersList.innerHTML = '';
        characters.forEach(character => {
            const li = document.createElement('li');
            li.textContent = character;
            charactersList.appendChild(li);
        });

        await generateTeams();
    } catch (error) {
        console.error('Character fetch error:', error);
        console.error('Response data:', characters);
        alert('Failed to fetch characters: ' + error.message);
        toggleVisibility('loading', false);
    }
}


// Generate optimized teams
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

        // Save teams and explanations to sessionStorage
        sessionStorage.setItem('teamsContent', teamsHTML);
        sessionStorage.setItem('explanationContent', data.explanation || '');

        toggleVisibility('loading', false);

        toggleVisibility('done', true);
        console.log('Teams generated successfully and saved for new tab.');
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

document.getElementById('openTeamsTab').addEventListener('click', function () {
    const teamsTab = new bootstrap.Tab(document.getElementById('pills-teams-tab'));
    teamsTab.show();

    const teamsContent = sessionStorage.getItem('teamsContent');
    const explanationContent = sessionStorage.getItem('explanationContent');

    if (teamsContent) {
        document.getElementById('teamsList').innerHTML = teamsContent;
    }

    if (explanationContent) {
        document.getElementById('explanationText').innerHTML = explanationContent;
    }
});

// Define the base URL for the GenshinDev API
const GENSHIN_API_URL = 'https://genshin.dev/api';

// Function to fetch character data from the API
async function fetchCharacters() {
    try {
        const response = await fetch(`${GENSHIN_API_URL}/characters`);
        if (!response.ok) {
            throw new Error('Failed to fetch characters');
        }
        const characters = await response.json();
        return characters;
    } catch (error) {
        console.error('Error fetching characters:', error);
        alert('Failed to load characters. Please try again later.');
        return [];
    }
}

// Function to load character icons
async function loadCharacterIcons() {
    const characterIconsContainer = document.getElementById('characterIcons');
    if (!characterIconsContainer) {
        console.error('Character icons container not found');
        return;
    }

    // Fetch character data from the API
    const characters = await fetchCharacters();
    if (characters.length === 0) return;

    // Display character icons
    characters.forEach(character => {
        const img = document.createElement('img');
        img.src = `${GENSHIN_API_URL}/characters/${character}/icon`; // Use the API's icon endpoint
        img.alt = character;
        img.classList.add('character-icon');
        img.addEventListener('click', () => toggleCharacterSelection(character));
        characterIconsContainer.appendChild(img);
    });
}

// Function to toggle character selection
const selectedCharacters = new Set();

function toggleCharacterSelection(character) {
    const icon = document.querySelector(`img[alt="${character}"]`);
    if (!icon) return;

    if (selectedCharacters.has(character)) {
        selectedCharacters.delete(character);
        icon.classList.remove('selected');
    } else {
        selectedCharacters.add(character);
        icon.classList.add('selected');
    }
}

// Function to generate teams based on selected characters
async function generateTeamsFromSelection() {
    if (selectedCharacters.size === 0) {
        alert('Please select at least one character.');
        return;
    }

    try {
        toggleVisibility('loading', true);

        const response = await fetch(`${BASE_URL}/generate_teams`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ characters: Array.from(selectedCharacters) })
        });

        if (!response.ok) {
            throw new Error('Failed to generate teams');
        }

        const data = await response.json();
        console.log('Teams generated:', data);

        // Display the generated teams and explanation
        displayTeams(data.teams, data.explanation);
    } catch (error) {
        console.error('Error generating teams:', error);
        alert('Failed to generate teams: ' + error.message);
    } finally {
        toggleVisibility('loading', false);
    }
}

// Function to display generated teams and explanation
function displayTeams(teams, explanation) {
    const teamsList = document.getElementById('teamsList');
    const explanationText = document.getElementById('explanationText');

    if (teamsList && explanationText) {
        teamsList.innerHTML = teams.map(team => `
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

        explanationText.innerHTML = explanation || 'No explanation available.';

        toggleVisibility('teams-container', true);
        toggleVisibility('explanation', true);
    }
}

// Event listener for the generate teams button
document.getElementById('generateTeamsButton')?.addEventListener('click', generateTeamsFromSelection);

// Load character icons when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    loadCharacterIcons();
    toggleVisibility('characterSelection', true);
});