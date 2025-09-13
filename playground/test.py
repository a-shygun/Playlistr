

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import ast
from collections import Counter

#%%
df1 = pd.read_csv('../temp/31i3y3aur3k2mejzzfyuxvulxuoy/top_tracks.csv')
df2 = pd.read_csv('../temp/31i3y3aur3k2mejzzfyuxvulxuoy/recent_tracks.csv')
df3 = pd.read_csv('../temp/31i3y3aur3k2mejzzfyuxvulxuoy/user_songs.csv')
df = pd.concat([df1,df2,df3])
df.drop_duplicates(subset=['name', 'artist'], inplace=True)
df.drop(columns=['similar_songs', 'name_url', 'artist_url', 'album_url', 'album_art'], inplace=True)
df.info()
#%%
df['genres'] = df['genres'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
df = df[df['genres'].map(bool)]

#%%
df['genres'].value_counts()
#%%
from collections import Counter

# Suppose your column is called 'genres_list'
all_genres = [genre for sublist in df['genres'] for genre in sublist]
genre_counts = Counter(all_genres)

# Convert to a DataFrame for easier plotting
genre_counts_df = pd.DataFrame(genre_counts.items(), columns=['genre', 'count']).sort_values(by='count', ascending=False)
genre_counts_df


import streamlit as st
from wordcloud import WordCloud
import pandas as pd

# Assuming your dataframe is genre_counts_df with 'genre' and 'count' columns
freq_dict = dict([(row['genre'], row['count']) for _, row in genre_counts_df.iterrows()])

st.title("Genre WordCloud")

# Generate wordcloud
wc = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(freq_dict)

# Show in Streamlit
st.image(wc.to_array())