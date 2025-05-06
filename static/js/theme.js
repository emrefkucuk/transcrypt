// theme.js - Handles theme switching and related functionality
export function initializeTheme() {
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    
    // If no saved preference, check system preference
    if (!savedTheme) {
        const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.body.setAttribute('data-bs-theme', prefersDarkMode ? 'dark' : 'light');
        updateThemeUI(prefersDarkMode ? 'dark' : 'light');
    } else {
        // Use saved preference
        document.body.setAttribute('data-bs-theme', savedTheme);
        updateThemeUI(savedTheme);
    }
}

// Update UI elements when theme changes
export function updateThemeUI(theme) {
    // Update theme toggle button
    const toggleButton = document.getElementById('themeToggle');
    if (toggleButton) {
        toggleButton.querySelector('i').className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    }
    
    // Update logo
    const themeLogo = document.getElementById('themeLogo');
    if (themeLogo) {
        if (theme === 'dark') {
            themeLogo.src = '/static/media/Transcrypt_Logo_Dark.png';
            themeLogo.setAttribute('data-theme', 'dark');
        } else {
            themeLogo.src = '/static/media/Transcrypt_Logo_Light.png';
            themeLogo.setAttribute('data-theme', 'light');
        }
        // Force the browser to reload the image
        themeLogo.setAttribute('src', themeLogo.src + '?t=' + new Date().getTime());
    }
}

// Toggle between light and dark theme
export function toggleTheme() {
    // Get the current theme
    const currentTheme = document.body.getAttribute('data-bs-theme');
    // Set the new theme
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    // Update document theme
    document.body.setAttribute('data-bs-theme', newTheme);
    
    // Update UI elements
    updateThemeUI(newTheme);
    
    // Save theme preference
    localStorage.setItem('theme', newTheme);
}