import os
import ast
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
from pyvis.network import Network
from flask import session
import json

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path

def load_user_data(user_id):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    user_dir = os.path.join(project_root, "temp", user_id)

    csv_files = ["top_tracks.csv", "recent_tracks.csv", "user_songs.csv"]
    datasets_dir = os.path.join("temp", user_id, "datasets")
    dfs = [pd.read_csv(os.path.join(datasets_dir, f)) for f in csv_files if os.path.exists(os.path.join(datasets_dir, f))]
    if not dfs:
        raise FileNotFoundError(f"No CSVs found for user at {user_dir}")
    df = pd.concat(dfs, ignore_index=True)

    drop_cols = ['similar_songs', 'name_url', 'artist_url', 'album_url', 'album_art', 'popularity']
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True)
    df.dropna(inplace=True)

    df['genres'] = df['genres'].apply(ast.literal_eval)
    df['genres'] = df['genres'].apply(lambda lst: ['hip hop' if g.lower() in ['hip-hop', 'hip hop'] else g for g in lst])
    df['genres'] = df['genres'].apply(lambda lst: sorted(set(lst)))
    df = df[df['genres'].apply(lambda x: len(x) > 0)]
    return df


def save_plot_explanation(plots_dir, plot_name, explanation):
    expo_path = os.path.join(plots_dir, "plot_expo.json")

    if os.path.exists(expo_path):
        with open(expo_path, "r") as f:
            data = json.load(f)
    else:
        data = {}

    data[plot_name] = explanation

    with open(expo_path, "w") as f:
        json.dump(data, f, indent=2)
def plot_wordcloud_genres(df, plots_dir):
    genre_counts = df.explode('genres')['genres'].value_counts()

    wc_width, wc_height = 1000, 1500
    wc = WordCloud(
        width=wc_width,
        height=wc_height,
        background_color=None,
        mode="RGBA",
        colormap='rainbow',
        max_words=100,
        prefer_horizontal=1,
    ).generate_from_frequencies(genre_counts)
    
    plt.figure(figsize=(wc_width/200, wc_height/200), dpi=200, facecolor=None)
    plt.imshow(wc, interpolation='lanczos')
    plt.axis('off')
    plt.tight_layout(pad=0)
    
    plt.savefig(
        os.path.join(plots_dir, "wordcloud_genres.png"),
        transparent=True,
        bbox_inches='tight',
        pad_inches=0
    )
    plt.close()

    top_genres = genre_counts.head(5).to_dict()
    explanation = {
        "summary": f"Top genres are {', '.join(top_genres.keys())}.",
        "top_genres": top_genres
    }
    save_plot_explanation(plots_dir, "wordcloud_genres", explanation)
    
def plot_wordcloud_artists(df, plots_dir):
    artist_counts = df['artist'].value_counts()

    wc_width, wc_height = 1000, 1500
    wc = WordCloud(
        width=wc_width,
        height=wc_height,
        background_color=None,
        mode='RGBA',
        colormap='rainbow',
        max_words=100,
        prefer_horizontal=1,
    ).generate_from_frequencies(artist_counts)
    
    plt.figure(figsize=(wc_width/200, wc_height/200), dpi=200, facecolor=None)
    plt.imshow(wc, interpolation='lanczos')
    plt.axis('off')
    plt.tight_layout(pad=0)
    
    plt.savefig(
        os.path.join(plots_dir, "wordcloud_artists.png"),
        transparent=True,
        bbox_inches='tight',
        pad_inches=0
    )
    plt.close()

    top_artists = artist_counts.head(5).to_dict()
    explanation = {
        "summary": f"Most listened artists include {', '.join(top_artists.keys())}.",
        "top_artists": top_artists
    }
    save_plot_explanation(plots_dir, "wordcloud_artists", explanation)

def plot_playcount_distribution(df, plots_dir):
    df_exploded = df.explode('genres')
    
    # Ensure playcount is numeric
    df_exploded["playcount"] = pd.to_numeric(df_exploded["playcount"], errors="coerce").fillna(0)
    
    log_playcounts = np.log1p(df_exploded["playcount"])

    fig, ax = plt.subplots(figsize=(6, 9), dpi=200, facecolor=None) 
    sns.kdeplot(
        data=df_exploded,
        y=log_playcounts,
        hue='playlist',
        multiple='fill',
        fill=True,
        alpha=0.6,
        linewidth=1,
        edgecolor=None,
        warn_singular=False,
        palette='rainbow',
        ax=ax
    )
    sns.move_legend(ax, 'upper right')

    ax.set_axis_off()
    ax.set_facecolor(None)
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    plt.savefig(
        os.path.join(plots_dir, "playcount_distribution.png"),
        transparent=True,
        bbox_inches='tight',
        pad_inches=0
    )
    plt.close()

    top_playlists = (
        df_exploded.groupby("playlist")["playcount"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .to_dict()
    )

    explanation = {
        "summary": "Top 5 playlists with the highest total playcounts.",
        "top_playlists": top_playlists
    }

    save_plot_explanation(plots_dir, "playcount_distribution", explanation)

def get_artist_genre_playlist_network_html(df, plots_dir):
    df_exploded = df.explode('genres')
    top_artists = df['artist'].value_counts().head(30).index
    top_genres = df_exploded['genres'].value_counts().head(20).index
    top_playlists = df['playlist'].value_counts().head(5).index

    df_filtered = df[df['artist'].isin(top_artists)]
    df_filtered = df_filtered[df_filtered['playlist'].isin(top_playlists)]
    df_filtered = df_filtered[df_filtered['genres'].apply(lambda gs: any(g in top_genres for g in gs))]
    df_exploded_edges = df_filtered.explode('genres')

    net = Network(height="100vh", 
                  width="100%", 
                  bgcolor="rgba(0,0,0,0)",
                  notebook=True,
                  cdn_resources='in_line'
                  )
    
    net.force_atlas_2based()
    net.set_edge_smooth(smooth_type='discrete')
    net.set_edge_smooth(smooth_type='straightCross')

    for artist in top_artists:
        net.add_node(artist, label=artist, color="#4bd183", mass=1,
                     font={"color": "#636363", "size": 18, "face": "helvetica"}, title=f"Artist: {artist}")

    for genre in top_genres:
        net.add_node(genre, label=genre, shape='circle', mass=2,
                     color="#6d5dfc", font={"color": "#E4EBF5", "size": 18, "face": "helvetica"}, title=f"Genre: {genre}")

    for pl in top_playlists:
        net.add_node(pl, label=pl, shape='circle', mass=3,
                     color="#ff4400", font={"color": "#ffffff", "size": 18, "face": "helvetica"}, title=f"Playlist: {pl}")

    for _, row in df_exploded_edges.iterrows():
        if row['genres'] in top_genres:
            net.add_edge(row['artist'], row['genres'], color="#4D4D4D50", title="Artist ↔ Genre")
        if row['genres'] in top_genres and row['playlist'] in top_playlists:
            net.add_edge(row['genres'], row['playlist'], color="#88888850", title="Genre ↔ Playlist")

    explanation = {
    "summary": "Network shows strongest links between top artists, genres, and playlists.",
    "top_artists": list(top_artists[:5]),
    "top_genres": list(top_genres[:5]),
    "top_playlists": list(top_playlists[:5])
    }
    save_plot_explanation(plots_dir, "artist_genre_playlist_network", explanation)


    network_html = net.generate_html(notebook=False)
    network_html = network_html.replace('<div class="card" style="width: 100%">', '<div class="card" style="width: 100%; background">')
    network_html = network_html.replace('<head>', '<head style="background:transparent;')
    network_html = network_html.replace('<body>', '<body style="background:transparent;')
    network_html = network_html.replace('<div class="card" style="width: 100%">', '<div class="card" style="width: 100%; background:transparent;">')

    return network_html


def plot_polar_playcount_playlist(df, plots_dir):
    min_year, max_year = int(df['year'].min()), int(df['year'].max())

    top_playlists = df['playlist'].value_counts().head(10).index
    df_plot = df[df['playlist'].isin(top_playlists)].copy()

    # Compute angles and radii for filtered df
    # Compute angles and radii for filtered df
    angles = 2 * np.pi * (df_plot['year'] - min_year) / (max_year - min_year)
    radii = df_plot['playcount']
    sizes = df_plot['playcount'] / df_plot['playcount'].max() * 1000

    # Convert to float explicitly
    angles = angles.astype(float)
    radii = radii.astype(float)
    sizes = sizes.astype(float)
    
    angles = pd.to_numeric(angles, errors='coerce').fillna(0)
    radii = pd.to_numeric(radii, errors='coerce').fillna(0)
    sizes = pd.to_numeric(sizes, errors='coerce').fillna(1)
    
    playlist_to_color = {pl: i for i, pl in enumerate(top_playlists)}
    colors = df_plot['playlist'].map(playlist_to_color)


    fig = plt.figure(figsize=(6, 9), dpi=300, facecolor=None)
    ax = fig.add_subplot(projection='polar', facecolor=None)

    # Scatter plot
    scatter = ax.scatter(
        angles,
        radii,
        c=df_plot['playcount'],  # use df_plot
        s=sizes,
        cmap='rainbow',
        alpha=0.3,
        edgecolor='white',
        linewidth=0.0,
    )

    # Set polar plot aesthetics
    ax.set_ylim(-1_000_000, 10_500_000)
    ax.set_rorigin(-5_000_000)
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(45)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_color(None)

    num_ticks = min(10, max_year - min_year + 1)
    theta_ticks = np.linspace(0, 2 * np.pi, num_ticks, endpoint=True)[1:]
    year_labels = [str(int(y)) for y in np.linspace(min_year, max_year, num_ticks, endpoint=True)][1:]
    ax.set_xticks(theta_ticks)
    ax.set_xticklabels(year_labels, color="#474e5f", fontsize=10)

    cbar = fig.colorbar(scatter, ax=ax, orientation='horizontal', pad=0.1)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(length=0)
    cbar.set_label("Popularity", color="#474e5f")

    plt.savefig(
        os.path.join(plots_dir, "polar_playcount_playlist.png"),
        transparent=True,
        bbox_inches='tight',
        pad_inches=0
    )
    plt.close()

    peak_playcount_idx = df['playcount'].idxmax()
    peak_year = int(df.loc[peak_playcount_idx, 'year'])
    top_tracks = (
        df.sort_values('playcount', ascending=False)
          .head(5)[['name', 'playcount']]
          .set_index('name')['playcount']
          .to_dict()
    )

    summary = (
        f"Listening history spans from {min_year} to {max_year}, "
        f"with peak popularity in {peak_year}. "
        f"Top tracks include {', '.join(list(top_tracks.keys())[:4])}."
    )

    explanation = {
        "min_year": min_year,
        "max_year": max_year,
        "peak_playcount_year": peak_year,
        "top_5_tracks": top_tracks,
        "summary": summary,
    }

    save_plot_explanation(plots_dir, "polar_playcount_playlist", explanation)
    
def generate_all_user_plots():
    user_id = session.get("user_info").get("id")
    df = load_user_data(user_id)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)

    plots_dir = os.path.join(project_root, "temp", user_id, "plots")

    plot_wordcloud_genres(df, plots_dir)
    plot_wordcloud_artists(df, plots_dir)
    plot_playcount_distribution(df, plots_dir)
    get_artist_genre_playlist_network_html(df, plots_dir)
    plot_polar_playcount_playlist(df, plots_dir)

    print(f"[SUCCESS] All plots saved in {plots_dir}")

