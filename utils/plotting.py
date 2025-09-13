import os
import ast
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
from pyvis.network import Network
import re

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path

def load_user_data(user_id):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    user_dir = os.path.join(project_root, "temp", user_id)

    csv_files = ["top_tracks.csv", "recent_tracks.csv", "user_songs.csv"]
    dfs = [pd.read_csv(os.path.join(user_dir, f)) for f in csv_files if os.path.exists(os.path.join(user_dir, f))]
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

def plot_wordcloud_genres(df, plots_dir):
    genre_counts = df.explode('genres')['genres'].value_counts()
    
    wc = WordCloud(
        width=1000,
        height=1500,
        background_color='#E4EBF5',
        colormap='rainbow',
        max_words=200,
        prefer_horizontal=1,
    ).generate_from_frequencies(genre_counts)
    
    plt.figure(figsize=(6,9), facecolor='#E4EBF5', dpi=500)
    plt.imshow(wc, interpolation='lanczos')
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.savefig(os.path.join(plots_dir, "wordcloud_genres.png"))
    plt.close()

def plot_wordcloud_artists(df, plots_dir):
    artist_counts = df['artist'].value_counts()
    wc = WordCloud(
        width=1000,
        height=1500,
        background_color='#E4EBF5',
        colormap='rainbow',
        max_words=200,
        prefer_horizontal=1,
    ).generate_from_frequencies(artist_counts)
    
    plt.figure(figsize=(6,9), facecolor='#E4EBF5', dpi=500)
    plt.imshow(wc, interpolation='lanczos')
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.savefig(os.path.join(plots_dir, "wordcloud_artists.png"))
    plt.close()

# def plot_playcount_distribution(df, plots_dir):
    # df_exploded = df.explode('genres')
    
    # font_color = "#474e5f"  # desired font color
    
    # plt.figure(figsize=(6,9), facecolor='#E4EBF5', dpi=500)

    # log_playcounts = np.log1p(df_exploded["playcount"])
    # sns.kdeplot(
    #     data=df_exploded, 
    #     y=log_playcounts,
    #     hue='playlist',
    #     multiple='fill',
    #     fill=True,
    #     alpha=0.6,
    #     linewidth=1,
    #     edgecolor='#E4EBF5',
    #     warn_singular=False,
    #     palette='rainbow',
    #     legend=True
    # )
    # y_min = np.floor(log_playcounts.min())
    # y_max = np.ceil(log_playcounts.max())
    # plt.ylim(y_min, y_max)
    # plt.yticks(
    #     [y_min, y_max], 
    #     [int(np.expm1(y_min)), int(np.expm1(y_max))],
    #     color=font_color, rotation=90
    # )
    
    # plt.xlim(0, 1)
    # plt.xticks([0, 1], color=font_color)

    # for spine in plt.gca().spines.values():
    #     spine.set_color("#E4EBF5")
    #     spine.set_linewidth(1)
    # plt.title("Playcount Distribution by Playlist", color=font_color)
    # plt.xlabel("Proportion", color=font_color)
    # plt.ylabel("Playcount", color=font_color)
    
    # plt.grid(False)
    # plt.tight_layout(pad=0)
    # plt.savefig(os.path.join(plots_dir, "playcount_distribution.png"))
    # plt.close()
def plot_playcount_distribution(df, plots_dir):
    
    df_exploded = df.explode('genres')
    fig, ax = plt.subplots(figsize=(6,9), dpi=500, facecolor='#E4EBF5')
    log_playcounts = np.log1p(df_exploded["playcount"])
    sns.kdeplot(
        data=df_exploded,
        y=log_playcounts,
        hue='playlist',
        multiple='fill',
        fill=True,
        alpha=0.6,
        linewidth=1,
        edgecolor='#E4EBF5',
        warn_singular=False,
        palette='rainbow',
        ax=ax
    )
    sns.move_legend(ax, 'upper right')
    ax.set_axis_off()
    ax.set_facecolor('#E4EBF5')

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.savefig(os.path.join(plots_dir, "playcount_distribution.png"))
    plt.close()


def get_artist_genre_playlist_network_html(df):
    df_exploded = df.explode('genres')
    top_artists = df['artist'].value_counts().head(30).index
    top_genres = df_exploded['genres'].value_counts().head(20).index
    top_playlists = df['playlist'].value_counts().head(5).index

    df_filtered = df[df['artist'].isin(top_artists)]
    df_filtered = df_filtered[df_filtered['playlist'].isin(top_playlists)]
    df_filtered = df_filtered[df_filtered['genres'].apply(lambda gs: any(g in top_genres for g in gs))]
    df_exploded_edges = df_filtered.explode('genres')

    # net = Network(height="100vh", width="100%", bgcolor="#E4EBF5", notebook=True,
    #               cdn_resources='in_line', filter_menu=True, select_menu=True)
    net = Network(height="100vh", 
                  width="100%", 
                  bgcolor="#E4EBF5", 
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

    network_html = net.generate_html(notebook=False)
    return network_html


def plot_polar_playcount_playlist(df, plots_dir):
    min_year, max_year = df['year'].min(), df['year'].max()
    angles = 2 * np.pi * (df['year'] - min_year) / (max_year - min_year)

    radii = df['playcount']
    sizes = df['playcount'] / df['playcount'].max() * 1000

    # switch to c = colors for accurate genre based coloiring
    top_playlists = df['playlist'].value_counts().head(10).index
    df_plot = df[df['playlist'].isin(top_playlists)]
    playlist_to_color = {pl: i for i, pl in enumerate(top_playlists)}
    colors = df_plot['playlist'].map(playlist_to_color)

    fig = plt.figure(figsize=(6,9), dpi=167, facecolor='#E4EBF5')
    ax = fig.add_subplot(projection='polar', facecolor='#E4EBF5')
    scatter = ax.scatter(
        angles, 
        radii, 
        c=df['playcount'],
        s=sizes, 
        cmap='rainbow', 
        alpha=0.3,
        edgecolor='white',
        linewidth=0.0,
    )

    ax.set_ylim(-1_000_000, 10_500_000)
    ax.set_rorigin(-5_000_000)
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(45)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_color('#E4EBF5')

    
    num_ticks = min(10, max_year - min_year + 1)
    theta_ticks = np.linspace(0, 2*np.pi, num_ticks, endpoint=True)[1:]
    year_labels = [str(int(y)) for y in np.linspace(min_year, max_year, num_ticks, endpoint=True)][1:]
    ax.set_xticks(theta_ticks)
    ax.set_xticklabels(year_labels, color="#474e5f", fontsize=10)
    
    cbar = fig.colorbar(scatter, ax=ax, orientation='horizontal', pad=0.1)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(length=0)
    cbar.set_label("Popularity", color="#474e5f")

    plt.savefig(os.path.join(plots_dir, "polar_playcount_playlist.png"))
    plt.close()


def generate_all_user_plots(user_id):
    df = load_user_data(user_id)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    plots_dir = ensure_dir(os.path.join(project_root, "temp", user_id, "plots"))

    plot_wordcloud_genres(df, plots_dir)
    plot_wordcloud_artists(df, plots_dir)
    plot_playcount_distribution(df, plots_dir)
    get_artist_genre_playlist_network_html(df)
    plot_polar_playcount_playlist(df, plots_dir)

    print(f"[SUCCESS] All plots saved in {plots_dir}")

# if __name__ == "__main__":
#     generate_all_user_plots("31i3y3aur3k2mejzzfyuxvulxuoy")