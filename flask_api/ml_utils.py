# flask_api/ml_utils.py
import pandas as pd
import numpy as np
import os
import time
from sklearn.preprocessing import OneHotEncoder
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.manifold import TSNE
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, Tuple, List

REQUIRED = ['movie_genre_top1', 'series_genre_top1', 'ott_top1', 'content_lang_top1']

def _normalize_name(name: str) -> str:
    if pd.isna(name):
        return ''
    s = str(name).strip().lower()
    s = s.replace('-', ' ').replace('_', ' ').replace('.', ' ')
    s = ' '.join(s.split())
    return s

def _find_best_column_match(col_candidates: List[str], target: str) -> Tuple[str, float]:
    """
    Very simple matching score:
      - exact normalized match -> score 1.0
      - contains all tokens -> 0.9
      - contains main keyword -> 0.7
      - else 0.0
    Returns (best_col, score)
    """
    tnorm = _normalize_name(target)
    t_tokens = tnorm.split()
    best = (None, 0.0)
    for c in col_candidates:
        cnorm = _normalize_name(c)
        if cnorm == tnorm:
            return c, 1.0
        # if target tokens all in candidate
        if all(tok in cnorm for tok in t_tokens if tok):
            if 0.9 > best[1]:
                best = (c, 0.9)
        # keyword heuristics
        keywords = []
        if 'movie' in tnorm or 'film' in tnorm:
            keywords = ['movie', 'film', 'movie genre', 'genre']
        elif 'series' in tnorm or 'tv' in tnorm:
            keywords = ['series', 'show', 'tv', 'series genre']
        elif 'ott' in tnorm or 'platform' in tnorm:
            keywords = ['ott', 'platform', 'stream', 'provider', 'service']
        elif 'lang' in tnorm or 'language' in tnorm:
            keywords = ['lang', 'language', 'content lang', 'language top']
        # if any keyword in candidate
        if any(k in cnorm for k in keywords):
            if 0.7 > best[1]:
                best = (c, 0.7)
        # also allow if candidate contains 'top' and a genre/platform/lang token
        if 'top' in cnorm and any(tok in cnorm for tok in ['movie', 'series', 'ott', 'lang', 'language', 'platform']):
            if 0.65 > best[1]:
                best = (c, 0.65)
    return best

def map_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Try to map required columns to available dataframe columns.
    Returns dict: required_name -> actual_column_name
    Raises ValueError with clear message if mapping cannot be done.
    """
    avail = list(df.columns)
    # quick lower-normalized dict
    matches = {}
    used = set()
    suggestions = {}
    for req in REQUIRED:
        best_col, score = _find_best_column_match(avail, req)
        if best_col and score >= 0.65:
            matches[req] = best_col
            used.add(best_col)
        else:
            # second pass: try substring based heuristics individually
            req_norm = _normalize_name(req)
            tokens = req_norm.split()
            found = None
            for c in avail:
                cnorm = _normalize_name(c)
                # allow if it contains 'movie' and 'genre' for movie_genre_top1 etc.
                if 'movie' in req_norm and 'movie' in cnorm:
                    if 'genre' in cnorm or 'gen' in cnorm or 'type' in cnorm:
                        found = c; break
                if 'series' in req_norm and ('series' in cnorm or 'show' in cnorm or 'tv' in cnorm):
                    found = c; break
                if 'ott' in req_norm and ('ott' in cnorm or 'platform' in cnorm or 'stream' in cnorm or 'service' in cnorm):
                    found = c; break
                if 'lang' in req_norm and ('lang' in cnorm or 'language' in cnorm or 'tongue' in cnorm):
                    found = c; break
            if found:
                matches[req] = found
                used.add(found)
            else:
                suggestions[req] = {
                    'required': req,
                    'candidates': avail
                }

    if suggestions:
        # create helpful message listing required vs available and suggestions
        msg_lines = []
        msg_lines.append("Missing required columns or ambiguous names. I tried to map automatically but failed for some fields.")
        msg_lines.append("Available columns in CSV: " + ", ".join(avail))
        msg_lines.append("Automatic mapping results so far:")
        for k, v in matches.items():
            msg_lines.append(f"  {k}  ->  {v}")
        msg_lines.append("Fields needing attention (not confidently mapped):")
        for k in suggestions.keys():
            msg_lines.append(f"  {k}")
        msg_lines.append("If your file uses different names, either rename CSV column(s) or add a header mapping.")
        raise ValueError("\n".join(msg_lines))

    return matches

def run_clustering(csv_path, k=4, out_dir='.', sample_limit=None):
    """
    Loads CSV, tries to map columns flexibly, one-hot encodes, runs KMeans,
    computes silhouette, produces t-SNE plot, and saves clusters CSV and plot.
    """
    df = pd.read_csv(csv_path)
    # Map columns - tolerant to column name differences
    mapping = map_columns(df)
    required_cols = [mapping[r] for r in REQUIRED]

    work = df[required_cols].fillna('Missing').astype(str)

    if sample_limit and len(work) > sample_limit:
        work = work.sample(sample_limit, random_state=42)

    if len(work) < max(2, k):
        raise ValueError(f"Not enough rows ({len(work)}) for k={k}. Reduce k or provide more data.")

    try:
        # Try older argument name first
        enc = OneHotEncoder(sparse=False, handle_unknown='ignore')
    except TypeError:
    # Fall back to newer argument name
        enc = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
    X = enc.fit_transform(work)

    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X)

    sil = -1.0
    if k > 1 and len(set(labels)) > 1:
        try:
            sil = float(silhouette_score(X, labels))
        except Exception:
            sil = -1.0

    tsne = TSNE(n_components=2, random_state=42, init='pca', learning_rate='auto')
    emb = tsne.fit_transform(X)

    plt.figure(figsize=(9,7))
    unique_labels = np.unique(labels)
    palette = plt.get_cmap('tab10')
    for i, lab in enumerate(unique_labels):
        sel = emb[labels == lab]
        plt.scatter(sel[:, 0], sel[:, 1], s=40, label=f'Cluster {lab}', alpha=0.85, color=palette(i % 10))
    plt.legend()
    plt.title(f't-SNE plot (k={k})')
    plot_path = os.path.join(out_dir, f'plot_tsne_{int(time.time())}.png')
    plt.savefig(plot_path, bbox_inches='tight', dpi=150)
    plt.close()

    out_df = df.copy()
    out_df['cluster'] = labels
    clusters_csv = os.path.join(out_dir, f'clusters_{int(time.time())}.csv')
    out_df.to_csv(clusters_csv, index=False)

    # summary per cluster
    summary_df = out_df.groupby('cluster').agg({
        mapping['movie_genre_top1']: lambda x: x.value_counts().index[0] if len(x)>0 else 'NA',
        mapping['series_genre_top1']: lambda x: x.value_counts().index[0] if len(x)>0 else 'NA',
        mapping['ott_top1']: lambda x: x.value_counts().index[0] if len(x)>0 else 'NA',
        mapping['content_lang_top1']: lambda x: x.value_counts().index[0] if len(x)>0 else 'NA',
        'cluster': 'count'
    }).rename(columns={'cluster':'count'})
    summary_df['pct'] = (summary_df['count'] / summary_df['count'].sum()).round(3)
    summary = summary_df.to_dict(orient='index')

    return {
        'silhouette': sil,
        'plot': plot_path,
        'clusters_csv': clusters_csv,
        'notes': 'Auto-mapped columns and applied one-hot encoding; KMeans clustering.',
        'summary': summary
    }
