#!/usr/bin/env python3
"""
Simple, clean YC clustering pipeline with auto-detection.
Just 4 main functions: load_data, get_clusters, annotate_df, save_data
"""

import pandas as pd
import numpy as np
import json
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
from typing import Dict, Tuple, Optional
from openai import OpenAI
from pydantic import BaseModel
import time
from sklearn.manifold import TSNE
import datetime

# ============================================================================
# 1. DATA LOADING
# ============================================================================

def load_data(data_path: str = 'yc_agents.json', 
              embeddings_path: str = 'yc_embeddings.json') -> Tuple[pd.DataFrame, Dict]:
    """Load YC data and embeddings, focusing on the 'agents' section and filtering for is_agent == True."""
    print("📂 Loading data...")
    
    with open(data_path, 'r') as f:
        data = json.load(f)
    agents = data.get('agents', [])
    df = pd.DataFrame(agents)
    # Filter for is_agent == True
    df = df[df['is_agent'] == True].reset_index(drop=True)
    with open(embeddings_path, 'r') as f:
        embeddings_dict = json.load(f)
    
    print(f"Loaded {len(df)} agents (is_agent=True) and {len(embeddings_dict)} embeddings")
    return df, embeddings_dict

# ============================================================================
# 2. CLUSTERING
# ============================================================================

def find_optimal_k(embeddings_array: np.ndarray, max_k: int = 15) -> int:
    """Find optimal number of clusters using elbow method."""
    print(f"🔍 Finding optimal k (testing 2-{max_k})...")
    
    k_range = range(2, min(max_k + 1, len(embeddings_array) // 2))
    inertias = []
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(embeddings_array)
        inertias.append(kmeans.inertia_)
        print(f"k={k}: inertia={kmeans.inertia_:.0f}")
    
    # Simple elbow detection: find max second derivative
    if len(inertias) >= 3:
        second_derivs = [inertias[i-1] - 2*inertias[i] + inertias[i+1] 
                        for i in range(1, len(inertias)-1)]
        optimal_k = k_range[np.argmax(second_derivs) + 1]
    else:
        optimal_k = k_range[0]
    
    print(f"✅ Optimal k: {optimal_k}")
    return optimal_k

def get_clusters(df: pd.DataFrame, embeddings_dict: Dict, 
                n_clusters: Optional[int] = None, key_col: str = 'long_slug') -> Dict:
    """
    Get cluster assignments for companies.
    
    Returns:
        Dictionary with cluster info: {cluster_labels, n_clusters, embeddings_array}
    """
    print("🎯 Running clustering...")
    
    # Prepare data
    df_with_emb = df[df[key_col].isin(embeddings_dict.keys())].copy()
    embeddings_list = [embeddings_dict[key] for key in df_with_emb[key_col]]
    embeddings_array = np.array(embeddings_list)
    
    print(f"Clustering {len(df_with_emb)} companies")
    
    # Auto-detect or use specified k
    if n_clusters is None:
        n_clusters = find_optimal_k(embeddings_array)
    
    # Cluster
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings_array)
    
    # Quality metric
    sil_score = silhouette_score(embeddings_array, cluster_labels)
    print(f"✅ Created {n_clusters} clusters (silhouette: {sil_score:.3f})")
    print(f"Cluster sizes: {np.bincount(cluster_labels).tolist()}")
    
    return {
        'cluster_labels': cluster_labels,
        'n_clusters': n_clusters, 
        'embeddings_array': embeddings_array,
        'df_subset': df_with_emb,
        'kmeans_model': kmeans
    }

# ============================================================================
# 3. ANNOTATION & METADATA
# ============================================================================

def annotate_df(cluster_info: Dict, df: pd.DataFrame, 
                key_col: str = 'long_slug') -> pd.DataFrame:
    """
    Add cluster information to the full DataFrame.
    This adds cluster_id, x, y coordinates to all companies.
    """
    print("📝 Annotating DataFrame with cluster info...")
    df_annotated = df.copy()
    df_subset = cluster_info['df_subset']
    cluster_labels = cluster_info['cluster_labels']
    # Map cluster assignments back to full df
    cluster_mapping = dict(zip(df_subset[key_col], cluster_labels))
    df_annotated['cluster_id'] = df_annotated[key_col].map(cluster_mapping)
    # Add 2D coordinates using t-SNE (default)
    embeddings_array = cluster_info['embeddings_array']
    tsne = TSNE(n_components=2, random_state=42, perplexity=40)
    coords_2d = tsne.fit_transform(embeddings_array)
    coord_mapping_x = dict(zip(df_subset[key_col], coords_2d[:, 0]))
    coord_mapping_y = dict(zip(df_subset[key_col], coords_2d[:, 1]))
    df_annotated['x'] = df_annotated[key_col].map(coord_mapping_x)
    df_annotated['y'] = df_annotated[key_col].map(coord_mapping_y)
    clustered_count = df_annotated['cluster_id'].notna().sum()
    print(f"✅ Annotated {len(df_annotated)} companies ({clustered_count} clustered)")
    return df_annotated

class ClusterMetadata(BaseModel):
    domain: str
    description: str
    agent_usecases: str
    value_prop: str

def generate_cluster_metadata(cluster_info: Dict, df: pd.DataFrame, key_col: str = 'long_slug', n_samples: int = 10, save_path: str = 'cluster_metadata.json') -> Dict:
    """
    Generate cluster metadata using LLM and save to file.
    Returns a dictionary mapping cluster_id to metadata.
    Each sample company now includes id, slug, long_slug, and name.
    Adds a 'last_updated' field to the metadata file.
    For each cluster, select the top 30 closest to centroid, then pick the 10 most recent by launched_at.
    """
    print("🤖 Generating cluster metadata using LLM...")
    client = OpenAI()
    df_subset = cluster_info['df_subset']
    cluster_labels = cluster_info['cluster_labels']
    kmeans_model = cluster_info['kmeans_model']
    embeddings_array = cluster_info['embeddings_array']
    cluster_metadata = {}
    for cluster_id in range(cluster_info['n_clusters']):
        mask = cluster_labels == cluster_id
        cluster_df = df_subset[mask].copy()
        if len(cluster_df) == 0:
            continue
        # Get top 30 closest to centroid
        centroid = kmeans_model.cluster_centers_[cluster_id]
        cluster_embeddings = embeddings_array[mask]
        distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
        n_to_sample = min(30, len(cluster_df))
        closest_indices = np.argsort(distances)[:n_to_sample]
        closest_df = cluster_df.iloc[closest_indices]
        # Now sort by launched_at descending and take top 10
        if 'launched_at' in closest_df.columns:
            closest_df = closest_df.sort_values('launched_at', ascending=False)
        samples = closest_df.head(n_samples)
        # Prepare prompt
        companies_text = "\n".join([f"- {row['name']}: {row['desc']}" for _, row in samples.iterrows()])
        system_message = (
            "You are an expert in analyzing AI agent startups. "
            "All companies in this cluster build or use AI agents. "
            "Your task is to analyze the cluster and provide structured labels.\n\n"
            "INSTRUCTIONS:\n"
            "- For 'domain': Use a single descriptive word for the main problem area or industry (e.g., 'fintech', 'healthcare', 'logistics').\n"
            "- For 'description': Give a clear, concise summary of the types of problems or use cases these AI agents address.\n"
            "- For 'agent_usecases': Summarize the main use cases or tasks the AI agents are applied to in this cluster.\n"
            "- For 'value_prop': Identify the main value proposition arguments these companies use (e.g., efficiency, automation, cost savings, new capabilities).\n\n"
            "Focus on the diversity of use cases and value props. Do not repeat that these are AI agents—focus on what the agents do and why it matters."
        )
        user_message = f"""Analyze these {len(samples)} companies from cluster {cluster_id}:\n\n{companies_text}\n\nProvide a structured analysis of this cluster."""
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4.1-2025-04-14",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                response_format=ClusterMetadata,
                temperature=0.1
            )
            cluster_analysis = completion.choices[0].message.parsed
            meta = cluster_analysis.model_dump() if cluster_analysis else {}
            meta['cluster_id'] = cluster_id
            meta['sample_count'] = len(samples)
            meta['sample_companies'] = [
                {
                    'id': row.get('id', None),
                    'slug': row.get('slug', None),
                    'long_slug': row.get('long_slug', None),
                    'name': row.get('name', None),
                    'desc': row.get('desc', None),
                    'website': row.get('website', None),
                }
                for _, row in samples.iterrows()
            ]
            print(f"✅ Cluster {cluster_id} analyzed: {meta.get('domain', 'unknown')}")
        except Exception as e:
            print(f"❌ Error generating label for cluster {cluster_id}: {e}")
            meta = {
                'cluster_id': cluster_id,
                'domain': 'unknown',
                'description': 'Error in analysis',
                'agent_usecases': '',
                'value_prop': 'Unable to determine',
                'sample_count': len(samples),
                'sample_companies': [
                    {
                        'id': row.get('id', None),
                        'slug': row.get('slug', None),
                        'long_slug': row.get('long_slug', None),
                        'name': row.get('name', None)
                    }
                    for _, row in samples.iterrows()
                ]
            }
        cluster_metadata[cluster_id] = meta
        time.sleep(1)
    output = {
        'last_updated': datetime.datetime.now().isoformat(),
        'clusters': cluster_metadata
    }
    with open(save_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Cluster metadata saved to: {save_path}")
    return output

def add_metadata_to_df(df_annotated: pd.DataFrame, cluster_metadata: Dict) -> pd.DataFrame:
    """Add LLM-generated cluster metadata to the DataFrame."""
    meta_map = {cid: meta for cid, meta in cluster_metadata.items()}
    df_annotated['cluster_domain'] = df_annotated['cluster_id'].map(lambda cid: meta_map.get(cid, {}).get('domain', ''))
    df_annotated['cluster_description'] = df_annotated['cluster_id'].map(lambda cid: meta_map.get(cid, {}).get('description', ''))
    df_annotated['cluster_agent_usecases'] = df_annotated['cluster_id'].map(lambda cid: meta_map.get(cid, {}).get('agent_usecases', ''))
    df_annotated['cluster_value_prop'] = df_annotated['cluster_id'].map(lambda cid: meta_map.get(cid, {}).get('value_prop', ''))
    return df_annotated

# ============================================================================
# 4. SAVING & VISUALIZATION
# ============================================================================

def save_data(df_annotated: pd.DataFrame, output_path: str = 'yc_clustered_simple.json', cluster_metadata: Optional[Dict] = None):
    """Save the annotated DataFrame, optionally adding domain from cluster_metadata."""
    print(f"💾 Saving results to {output_path}...")
    df_to_save = df_annotated.copy()
    if cluster_metadata is not None:
        # Map domain to each row based on cluster_id
        def get_domain(cid):
            if pd.isna(cid):
                return ''
            # Try both int and str keys for robustness
            return (
                cluster_metadata.get(str(int(cid)), {}).get('domain') or
                cluster_metadata.get(int(cid), {}).get('domain') or
                ''
            )
        df_to_save['domain'] = df_to_save['cluster_id'].map(get_domain)
    df_to_save.to_json(output_path, orient='records', indent=2)
    # Summary stats
    total_companies = len(df_to_save)
    clustered_companies = df_to_save['cluster_id'].notna().sum()
    n_clusters = df_to_save['cluster_id'].nunique()
    print(f"✅ Saved {total_companies} companies")
    print(f"   📊 {clustered_companies} clustered into {n_clusters} groups")
    print(f"   📁 File: {output_path}")

def quick_plot(df_annotated: pd.DataFrame, save_path: str = 'clusters_simple.png', cluster_metadata: Optional[Dict] = None):
    """Create a simple cluster visualization. Optionally use cluster metadata for legend labels."""
    print("📊 Creating visualization...")
    
    # Only plot companies with coordinates
    df_plot = df_annotated.dropna(subset=['x', 'y', 'cluster_id'])
    
    if len(df_plot) == 0:
        print("⚠️  No data to plot")
        return
    
    plt.figure(figsize=(10, 8))
    
    # Plot each cluster
    for cluster_id in sorted(df_plot['cluster_id'].unique()):
        cluster_data = df_plot[df_plot['cluster_id'] == cluster_id]
        # Use domain from metadata if available
        if cluster_metadata and str(int(cluster_id)) in cluster_metadata:
            meta = cluster_metadata[str(int(cluster_id))]
            label = meta.get('domain') or f'Cluster {int(cluster_id)}'
        elif cluster_metadata and int(cluster_id) in cluster_metadata:
            meta = cluster_metadata[int(cluster_id)]
            label = meta.get('domain') or f'Cluster {int(cluster_id)}'
        else:
            label = f'Cluster {int(cluster_id)}'
        plt.scatter(cluster_data['x'], cluster_data['y'], 
                   label=label, alpha=0.7, s=50)
    
    plt.xlabel('PC1')
    plt.ylabel('PC2') 
    plt.title('YC Companies Clusters')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plt.savefig(save_path, dpi=100, bbox_inches='tight')
    # plt.show()
    
    print(f"✅ Plot saved: {save_path}")

# ============================================================================
# 5. MAIN PIPELINE
# ============================================================================

def main():
    """Simple main pipeline - just 4 steps!"""
    print("🚀 YC Clustering Pipeline (Simple)")
    print("=" * 50)
    
    # Step 1: Load data
    df, embeddings_dict = load_data(data_path='yc_agents.json')

    # Step 2: Get clusters
    cluster_info = get_clusters(df, embeddings_dict)
    
    # # Step 3: Annotate dataframe
    df_annotated = annotate_df(cluster_info, df)
    
    # # Step 4: Save results
    cluster_metadata = generate_cluster_metadata(cluster_info, df)
    clusters = cluster_metadata['clusters']
    save_data(df_annotated, output_path='yc_clustered.json', cluster_metadata=clusters)
    
    # # Bonus: Quick visualization
    quick_plot(df_annotated, cluster_metadata=clusters, save_path='clusters.png')
    
    print("\n✅ Pipeline complete!")
    # return df_annotated

if __name__ == "__main__":
    df_result = main()
