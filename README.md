# Playlistr  

[![Live Demo](https://img.shields.io/badge/demo-online-brightgreen)](https://playlistr.shygun.com)  

Full-stack Spotify playlist app with Flask backend and JavaScript frontend.  

---

![Playlistr App](./playlistr%20app.png)

## Overview  

**Analyze and visualize your Spotify listening habits with data-driven insights.**

Playlistr is a Flask web application that connects to your Spotify account, fetches your playlists and tracks, and generates interactive visualizations. It combines Spotify API data with Python’s data analysis stack to reveal patterns in your music taste.


---

## Key Features

- **Spotify OAuth Login** – Secure sign-in with your Spotify account  
- **Playlist & Track Insights** – Analyze top 50 tracks, recent 50 tracks, and playlists  
- **Visualizations** – Word clouds, popularity graphs, distributions, and network graphs  
- **Dynamic Dashboard** – Interactive UI for profile, tracks, artists, and genres  
- **Email Notifications** – Handles waitlist/registration requests  

---

## Overview

1. User logs in with Spotify.  
2. The app fetches playlists, tracks, and metadata (artists, albums, genres, audio features).  
3. Data is processed into CSVs, cleaned, and analyzed.  
4. Plots and insights are generated (matplotlib, PyVis, Chart.js).  
5. Results are displayed on a personalized dashboard.  

---

## Technologies Used

- **Backend:** Python (Flask)  
- **Frontend:** HTML, CSS, JavaScript  
- **Data Analysis & Visualization:** pandas, NumPy, matplotlib, seaborn, WordCloud, PyVis, Chart.js  
- **APIs:** Spotify Web API, Last.fm API  
- **Email Notifications:** smtplib / sendmail  
- **Deployment:** cPanel + Phusion Passenger  

---

## Architecture & Modules

1. **app.py** – Main Flask entry, config, and blueprint registration  
2. **passenger_wsgi.py** – Production entry for cPanel/Passenger hosting  
3. **auth/** – Handles Spotify login, authentication, and data fetching  
4. **views/** – Routes for dashboard, tracks, profile, plots, registration  
5. **utils/** – Helpers for file handling, data cleaning, and visualizations  
6. **main.js** – Frontend interactivity (AJAX, charts, toggles)  
7. **static/** – CSS, JS, and image assets  

---

## Data Flow

1. **User Login** – OAuth flow with Spotify → session stores token + profile info  
2. **Data Fetching** – Spotify API gets playlists, top 50, recent 50 → saved as CSVs  
3. **Processing & Analysis** – CSVs cleaned/merged → plots generated + explanations saved  
4. **Frontend Rendering** – Flask templates + `main.js` render profile, tracks, and plots  
5. **Registration (Optional)** – `/register` handles new user requests → notifies admin  
6. **Data Refresh** – On each request, datasets are reloaded and visualizations updated  

---

## Next Steps
- Improve caching and preloading for faster performance  
- Add a dynamic loading screen with real-time logs  
- Implement an export button to download CSV stats  
- Explore building a mobile app version  
- Automate and streamline the user waitlist process (currently manual)  

