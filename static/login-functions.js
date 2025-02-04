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

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.classList.add('character-checkbox');
        checkbox.value = character; // Add this line to store the character name
        checkbox.addEventListener('change', () => toggleCharacterSelection(character, checkbox.checked));


        card.appendChild(img);
        card.appendChild(name);
        card.appendChild(checkbox);
        grid.appendChild(card);
    });

    characterIconsContainer.appendChild(grid);

    const confirmButton = document.createElement('button');
    confirmButton.id = 'confirmSelection';
    confirmButton.classList.add('btn', 'btn-primary', 'mt-3');
    confirmButton.textContent = 'Confirm Selection and Generate Teams';
    confirmButton.addEventListener('click', generateTeamsFromSelection);

    characterIconsContainer.appendChild(confirmButton);
}

// Function to toggle character selection with better visual feedback
const selectedCharacters = new Set();

function toggleCharacterSelection(character, isChecked) {
    const card = document.querySelector(`.character-card input[value="${character}"]`).closest('.character-card');
    if (!card) return;

    if (isChecked) {
        selectedCharacters.add(character);
        card.classList.add('selected');
    } else {
        selectedCharacters.delete(character);
        card.classList.remove('selected');
    }

    // Update confirm button text
    const confirmButton = document.getElementById('confirmSelection');
    if (confirmButton) {
        confirmButton.disabled = selectedCharacters.size < 4;
        confirmButton.textContent = `Generate Teams (${selectedCharacters.size} selected)`;
    }
}



// Function to generate teams based on selected characters
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
        console.log('Server response:', data);

        if (!data.teams || !Array.isArray(data.teams)) {
            throw new Error('Invalid teams data format: ' + JSON.stringify(data));
        }

        // Save teams and explanations to sessionStorage
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

        // Display teams and switch to teams tab
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



// Function to display generated teams and explanation
function displayTeams(teams, explanation) {
    const teamsList = document.getElementById("teamsList");

    if (teamsList) {
        console.log("Received explanation:", explanation); 

        let explanationSections = {};

        // Extract explanations properly
        if (explanation) {
            const explanationParts = explanation.split(/\*\*Team \d+: (.*?)\*\*/);
            console.log("📝 Extracted parts:", explanationParts);

            for (let i = 1; i < explanationParts.length; i += 2) {
                const teamKey = explanationParts[i].trim();
                const teamExplanation = explanationParts[i + 1]?.trim() || "No explanation available.";
                explanationSections[teamKey] = teamExplanation;
                console.log(`Matched Explanation for ${teamKey}:`, teamExplanation);
            }
        }

        teamsList.innerHTML = teams.map((team, index) => {
            const teamName = `<h3>${team["Team Name"]}</h3>`;

            // Generate character icons with roles
            const characterDisplay = team.Characters.map(char => `
                <div class="character-entry">
                    <img src="${LOCAL_ASSETS_PATH}/${char.Name.toLowerCase().replace(/ /g, "_")}/icon-big.png" 
                         alt="${char.Name}" 
                         class="character-icon">
                    <span class="character-name">${char.Name} (${char.Role})</span>
                </div>
            `).join("");

            // Construct team key based on character names
            const teamKey = team.Characters.map(c => c.Name).join(", ");
            console.log("🔹 Looking for explanation with key:", teamKey);

            // Match the explanation with the team
            const formattedExplanation = explanationSections[teamKey]
                ? `<p>${explanationSections[teamKey].replace(/\n/g, "<br>")}</p>`
                : "<p>No explanation available.</p>";

            return `
                <li class="team-card">
                    ${teamName}
                    <div class="character-icons">${characterDisplay}</div>
                    <div class="team-explanation">${formattedExplanation}</div>
                </li>
            `;
        }).join("");

        // Show the teams container
        toggleVisibility("teams-container", true);
    }
}





// Event listener for the generate teams button
document.getElementById('generateTeamsButton')?.addEventListener('click', generateTeamsFromSelection);

// Load character icons when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    loadCharacterIcons();
    toggleVisibility('characterSelection', true);
});

