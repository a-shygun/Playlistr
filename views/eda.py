# data/eda.py
from collections import Counter
import pandas as pd

def combine_tracks(top_tracks, recent_tracks):
    """
    Combine top and recent tracks into a single dataframe.
    """
    all_tracks = top_tracks + recent_tracks
    df = pd.DataFrame(all_tracks)
    return df

def genre_distribution(df):
    """
    Returns a Counter of genres.
    """
    genres = []
    for g_list in df['genres']:
        if g_list:  # skip empty lists
            genres.extend(g_list)
    return Counter(genres)

def artist_distribution(df, top_n=10):
    """
    Returns the most frequent artists.
    """
    return Counter(df['artist']).most_common(top_n)

def album_distribution(df, top_n=10):
    """
    Returns the most frequent albums.
    """
    return Counter(df['album']).most_common(top_n)

def year_distribution(df):
    """
    Returns a Counter of release years.
    """
    return Counter(df['year'])

def popularity_stats(df):
    """
    Returns basic statistics of popularity.
    """
    return {
        "mean": df['popularity'].mean(),
        "max": df['popularity'].max(),
        "min": df['popularity'].min()
    }