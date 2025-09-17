# Playlistr

**Analyze and enhance your Spotify playlists with data-driven insights.**

Playlistr is a Flask web application designed to fetch, analyze, and visualize Spotify playlists for individual users. It integrates Spotify API data with Python data analysis tools to provide meaningful insights about your listening habits, playlist patterns, and music preferences.

---

## Key Features

- **Spotify OAuth Login**: Secure login using Spotify credentials.  
- **Playlist Analysis**: Score playlists based on multiple metrics like variety, mood, and popularity.  
- **Visualizations**: Charts, WordClouds, and popularity graphs for quick insights.  
- **Dynamic Dashboard**: User-specific insights on tracks, playlists, top artists, and genres.  
- **Email Notifications**: Sends registration requests or alerts to the admin.

---

## Overview

- Users log in using their Spotify account.  
- The app fetches all playlists, tracks, and associated metadata (artist, album, genre, audio features).  
- Data is processed for analysis: scoring playlists, generating plots, and creating recommendations.  
- Users receive insights in the form of visualizations, recommendations, and summary stats.

---

## Technologies Used

- **Backend:** Python 3.11+, Flask framework  
- **Frontend:** HTML, CSS, JavaScript  
- **Data Analysis / ML:** pandas, NumPy, matplotlib, seaborn, WordCloud, pyvis, chart.js
- **APIs:** Spotify Web API, Last.fm API  
- **Email Notifications:** smtplib / sendmail  
- **Deployment:** cPanel with Phusion Passenger for Python apps  

---

## Architecture & Modules

1. **app.py**  
   - The main Flask application entry point.  
   - Creates the Flask app object, registers blueprints, and sets the secret key.  
   - Handles app configuration, including environment variables for API keys and ports.  

2. **passenger_wsgi.py**  
   - Entry point for Passenger (cPanel hosting).  
   - Loads the Flask app so it can be served in a production environment.  

3. **auth/** Blueprint  
   - Handles user authentication, Spotify OAuth, and initial user data setup.  
   - Uses `fetch.py` to fetch, save, and enrich Spotify data for each user.  
   - Routes include:  
     - `/login` → Redirects user to Spotify login with PKCE.  
     - `/callback` → Receives authorization code, fetches access token, and retrieves basic user info.  
     - `/setup` →  
       - Creates user-specific folders (`datasets/` and `plots/`) in `temp/`.  
       - Fetches playlists, tracks, top tracks, and recently played tracks.  
       - Enriches data with Last.fm API (genres, playcounts, similar songs).  
       - Generates plots and caches data for quick retrieval.  
     - `/logout` → Clears session and deletes temporary user data.  
   - **fetch.py functions used:**  
     - `fetch_user_info()` → Fetches user profile info from Spotify.  
     - `save_user_info()` → Saves user info to JSON.  
     - `fetch_save_user_tracks()` → Retrieves all playlist tracks.  
     - `fetch_save_top_tracks()` → Retrieves user’s top tracks.  
     - `fetch_save_recent_tracks()` → Retrieves recently played tracks.  
     - `enrich_songs_with_lastfm()` → Adds genres and playcounts from Last.fm.  
     - `enrich_top_recent_with_similar_songs()` → Adds similar song recommendations via Last.fm.
    
       
4. **views/** Blueprint  
   - Handles all core application routes for displaying user data, plots, and dashboards.  
   - Fetches processed data from `temp/<user_id>/datasets/` and `plots/` for rendering.  
   - Routes include:  
     - `/` → Main dashboard (renders `home.html` content).  
     - `/home` → Home page for logged-in users.  
     - `/profile` → Displays user profile information.  
     - `/tracks` → Shows top tracks and recently played tracks with genres and similar songs.  
     - `/data` → Displays user plots, visualizations, and JSON plot data.  
     - `/user_plot_data` → Returns JSON data of all user plots (used for dynamic charts).  
     - `/network` → Generates interactive network visualization of artist-genre-playlist relationships.  
     - `/user_plots/<filename>` → Serves individual plot images or JSON files.  
     - `/register` → Handles user registration requests, sending approval emails via `sendmail`.  
   - **Data Handling:**  
     - Reads CSVs and JSONs from `datasets/` and `plots/` directories.  
     - Loads enriched track data including genres, similar songs, and user stats.  
     - Renders dynamic dashboards and visualizations for the frontend.
    
      
5. **utils/** Module  
   - Provides helper functions for loading, processing, and visualizing Spotify user data.  
   - Handles CSV/JSON I/O, data cleaning, and plot generation for dashboards.  
   - Key functionalities:  
     
     1. **File & Directory Handling**  
        - `ensure_dir(path)` → Ensures a directory exists, creates it if missing.  
        - `load_user_data(user_id)` → Loads and merges all user CSVs (`top_tracks.csv`, `recent_tracks.csv`, `user_songs.csv`). Cleans data, processes genres, and filters invalid rows.  
        - `save_plot_explanation(plots_dir, plot_name, explanation)` → Stores metadata and explanations for generated plots in `plot_expo.json`.  

     2. **Plot Generation**  
        - `plot_wordcloud_genres(df, plots_dir)` → Generates a word cloud of top genres with summary explanations.  
        - `plot_wordcloud_artists(df, plots_dir)` → Generates a word cloud of top artists with summary explanations.  
        - `plot_playcount_distribution(df, plots_dir)` → KDE plot of playcount distributions across playlists, highlights top playlists.  
        - `plot_polar_playcount_playlist(df, plots_dir)` → Polar scatter plot showing yearly playcount by playlist, includes top tracks and peak popularity year.  
        - `get_artist_genre_playlist_network_html(df, plots_dir)` → Creates an interactive network of top artists, genres, and playlists using PyVis, saves explanation metadata.  

     3. **Combined Plot Generation**  
        - `generate_all_user_plots()` → Loads user data and generates all plots at once, saving results and explanations to the user’s `plots/` directory.  

   - **Notes:**  
     - Uses `matplotlib` in Agg mode for headless servers.  
     - Explodes and normalizes genre lists for accurate visualizations.  
     - All plots are saved with transparent backgrounds for seamless integration in web dashboards.
    
       
6. **main.js** – Frontend Interactivity & AJAX  
   - Handles DOM events, dynamic content loading, and plot rendering for the dashboard.  
   - Key functionalities:

     1. **DOM Initialization**  
        - Waits for `DOMContentLoaded` to bind event listeners.  
        - Central container: `#main-content`.

     2. **Segmented Controls**  
        - `bindSegmentedControl()` → Toggles between top songs and recent songs views.  
        - Switch input updates `.music-cols.top-songs` and `.music-cols.recent-songs` visibility.

     3. **Track Expansion**  
        - `bindTrackToggles()` → Enables "See More / See Less" toggle for track details.  
        - Expands `.expandable` sections within `.record` elements.

     4. **User Registration Form**  
        - `bindRegistrationForm()` → Shows/hides registration form.  
        - Submits JSON POST request to `/register`.  
        - Displays status message upon submission.

     5. **Dynamic Plot Rendering**  
        - `renderBarChart(canvasId, dataKey, datasetKey, color, horizontal)` → Fetches JSON from `/user_plot_data` and renders bar charts using Chart.js.  
        - Handles horizontal and vertical bars.  
        - Used for `genresBarChart`, `artistsBarChart`, and `playcountBarChart`.

     6. **AJAX Page Navigation**  
        - `bindAjaxButtons()` → Handles header button clicks for AJAX page loading.  
        - Loads HTML content into `#main-content` without full page reload.  
        - Rebinds track toggles, segmented controls, registration forms, and charts after load.  
        - Updates header slider position and button icon styles.

     7. **Hamburger Menu Dropdown**  
        - Toggles `.dropdown-content` visibility for mobile menu.  
        - Closes dropdown when clicking outside the menu.

     8. **Theme Toggle**  
        - `toggleThemeColors()` → Switches between light/dark mode and updates button text.

   - **Notes:**  
     - Heavy use of optional chaining (`?.`) for safe DOM operations.  
     - Ensures charts and toggles reinitialize after AJAX content load.  
     - Works in conjunction with Flask routes to dynamically fetch user data and plots.
    
       
7. **static/**  
   - Frontend assets:  
     - CSS stylesheets (including theme toggle light/dark)  
     - JavaScript scripts (dynamic charts, toggle buttons)  
     - Images (album art, logos, etc.)
    
---
## Data Flow

1. **User Login**
   - User visits the app and clicks **“Login with Spotify”**.
   - Flask backend handles OAuth flow: requests authorization → user approves → Spotify returns an access token.
   - User info (ID, name, email) is stored in the session for subsequent requests.

2. **Fetching & Storing Playlists**
   - Backend uses Spotify API to fetch:
     - User playlists, tracks, albums, artists, and genres.
     - Audio features and related metadata for each track.
   - Data is stored locally under `temp/{user_id}/datasets/` as CSV files:
     - `top_tracks.csv` → most played tracks
     - `recent_tracks.csv` → recently played tracks
     - `user_songs.csv` → all user tracks with full metadata

3. **Data Processing & Analysis (`utils.py`)**
   - `load_user_data()` consolidates CSVs, cleans columns, parses genres, and filters out invalid entries.
   - Analysis functions generate plots and insights:
     - **WordClouds** → `plot_wordcloud_genres()`, `plot_wordcloud_artists()`
     - **Playlist Distribution** → `plot_playcount_distribution()`
     - **Polar Playcount Plot** → `plot_polar_playcount_playlist()`
     - **Network Graph** → `get_artist_genre_playlist_network_html()` showing relationships between top artists, genres, and playlists
   - Explanations for plots are saved in `plot_expo.json` for frontend consumption.

4. **Frontend Rendering (`main.js` + templates)**
   - Templates (`base.html`, `pages/tracks.html`, `pages/home.html`, `pages/profile.html`) receive processed data from Flask.
   - **Dynamic Interactivity:**
     - AJAX header buttons load pages into `#main-content` without full reload.
     - Segmented controls toggle top vs recent tracks.
     - Expandable track details with “See More / See Less”.
   - **Charts & Visualizations:**
     - `renderBarChart()` fetches `plot_expo.json` and renders Chart.js bar charts for top genres, artists, and playlists.
     - Network visualizations and polar plots are embedded directly into the dashboard.

5. **Optional Notifications & Registration**
   - `/register` route accepts user registration requests.
   - Sends email via `sendmail` or subprocess to notify the admin of new registration requests.

6. **Data Refresh**
   - Whenever the user revisits `/tracks`, `/data`, or `/network`, the backend reloads CSVs and regenerates plots as needed.
   - Frontend ensures charts and toggles are rebound after AJAX page loads to maintain interactivity.
---
## Contributing
Contributions, bug reports, and feature requests are welcome!  
Please open an issue or submit a pull request.

## License
This project is licensed under the MIT License.  
See the [LICENSE](LICENSE) file for details.

--
This project is built as a learning + showcase tool.  
If you're interested in extending it or collaborating, feel free to reach out!
