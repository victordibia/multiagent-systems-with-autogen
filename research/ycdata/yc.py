import pandas as pd
import json
import re
import os
from typing import Dict, List, Tuple
from openai import OpenAI
import time

def clean_key_component(text: str) -> str:
    """Clean text component for use in keys by removing special characters."""
    if pd.isna(text) or text is None:
        return ""
    # Convert to string, lowercase, and keep only alphanumeric
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', str(text).strip().lower())
    return cleaned

def generate_long_slug(row: pd.Series) -> str:
    """Generate a long_slug key in format: id_name_slug_website"""
    id_part = clean_key_component(row.get('id', ''))
    name_part = clean_key_component(row.get('name', ''))
    slug_part = clean_key_component(row.get('slug', ''))
    website_part = clean_key_component(row.get('website', ''))
    
    # Combine parts with underscores, filter out empty parts
    parts = [part for part in [id_part, name_part, slug_part, website_part] if part]
    long_slug = '_'.join(parts)
    return long_slug

def load_existing_embeddings(json_path: str) -> Dict:
    """Load existing embeddings from JSON file."""
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print(f"Warning: Could not load existing embeddings from {json_path}")
            return {}
    return {}

def save_embeddings(embeddings_dict: Dict, json_path: str):
    """Save embeddings dictionary to JSON file."""
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(embeddings_dict, f, indent=2, ensure_ascii=False)

def load_and_process_df() -> pd.DataFrame:
    """Load and process the YC companies dataframe."""
    # Load data
    df = pd.read_json('https://raw.githubusercontent.com/akshaybhalotia/yc_company_scraper/refs/heads/main/data/combined_companies_data.json') 
    
    # Deduplicate and process
    df = df.drop_duplicates(subset=['id', 'slug', 'name', 'website'], keep='first')
    df["one_liner"] = df.one_liner.fillna("").astype(str)
    df["long_description"] = df.long_description.fillna("").astype(str)
    df["desc"] = df.one_liner + " " + df.long_description 
    df["short"] = df.name + " \n " + df.one_liner
    
    # Filter out rows with insufficient description
    original_length = len(df) 
    df = df[df['desc'].notna() & (df['desc'].str.len() >= 5)] 
    rows_dropped = original_length - len(df)
    
    print(f"Dropped {rows_dropped} rows where 'desc' was NaN or had length less than 5.")
    print(f"New DataFrame length: {len(df)}")
    
    # Add regex analysis
    AI_REGEX = re.compile(r'\bai\b|artificial intelligence|machine learning|llm|nlp|ai-power')
    AGENT_REGEX = re.compile(r'\bagents?\b')
    HEALTH_REGEX = re.compile(r'''
        \b(health(care)?|medical|medicine|med(i)?tech|pharma(ceuticals?)?|biotech|
        wellness|fitness|nutrition|therapy|mental[\s-]health|telemedicine|
        diagnosis|treatment|patient|doctor|hospital|clinic|drug|vaccine|
        health[\s-]tech|life[\s-]sciences?|genomics?|bioinformatics)\b
    ''', re.VERBOSE | re.IGNORECASE)

    def mentions_ai(text):
        if not isinstance(text, str):
            return False
        return bool(AI_REGEX.search(text.lower()))

    def mentions_ai_agents(text):
        if not isinstance(text, str):
            return False
        text = text.lower()
        return bool(AI_REGEX.search(text) and AGENT_REGEX.search(text))

    df["mentions_ai_agents"] = df.desc.apply(mentions_ai_agents)
    df["mentions_ai"] = df.desc.apply(mentions_ai)
    df["mentions_health"] = df.desc.apply(lambda x: bool(HEALTH_REGEX.search(x.lower())))
    
    # Generate long_slug
    df['long_slug'] = df.apply(generate_long_slug, axis=1)
    
    return df

def get_embedding_batch(texts: List[str], model: str = "text-embedding-3-large") -> List[List[float]]:
    """Get embeddings for a batch of texts."""
    client = OpenAI()
    
    # Clean texts - replace newlines with spaces
    cleaned_texts = [text.replace("\n", " ").strip() for text in texts]
    
    try:
        response = client.embeddings.create(
            input=cleaned_texts,
            model=model
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        print(f"Error getting embeddings: {e}")
        return []

def generate_embeddings_for_df(
    df: pd.DataFrame, 
    embeddings_json_path: str, 
    desc_column: str = 'desc',
    key_column: str = 'long_slug',
    batch_size: int = 10,
    model: str = "text-embedding-3-small"
) -> Dict:
    """
    Generate embeddings for companies in dataframe, with caching to avoid re-processing.
    
    Args:
        df: DataFrame containing company data
        embeddings_json_path: Path to JSON file for storing embeddings
        desc_column: Column name containing text to embed
        key_column: Column name containing the unique key for each company
        batch_size: Number of texts to process in each batch
        model: OpenAI embedding model to use
    
    Returns:
        Dictionary mapping company keys to their embeddings
    """
    
    # Load existing embeddings
    embeddings_dict = load_existing_embeddings(embeddings_json_path)
    initial_count = len(embeddings_dict)
    
    print(f"Loaded {initial_count} existing embeddings from {embeddings_json_path}")
    
    # Filter to companies that need embeddings
    missing_mask = ~df[key_column].isin(embeddings_dict.keys())
    missing_df = df[missing_mask].copy()
    
    if len(missing_df) == 0:
        print("All companies already have embeddings!")
        return embeddings_dict
    
    print(f"Need to generate embeddings for {len(missing_df)} companies")
    
    # Process in batches
    total_processed = 0
    
    for i in range(0, len(missing_df), batch_size):
        batch_df = missing_df.iloc[i:i+batch_size]
        batch_texts = batch_df[desc_column].tolist()
        batch_keys = batch_df[key_column].tolist()
        
        print(f"Processing batch {i//batch_size + 1}/{(len(missing_df)-1)//batch_size + 1} ({len(batch_texts)} companies)...")
        
        # Get embeddings for this batch
        embeddings = get_embedding_batch(batch_texts, model=model)
        
        if len(embeddings) == len(batch_texts):
            # Store embeddings with their keys
            for key, embedding in zip(batch_keys, embeddings):
                embeddings_dict[key] = embedding
            
            total_processed += len(batch_texts)
            
            # Save incrementally to avoid losing progress
            save_embeddings(embeddings_dict, embeddings_json_path)
            print(f"Saved embeddings for batch. Total processed: {total_processed}")
            
            # Small delay to be respectful to API
            time.sleep(0.5)
        else:
            print(f"Warning: Expected {len(batch_texts)} embeddings but got {len(embeddings)}")
    
    print(f"Completed! Generated {total_processed} new embeddings.")
    print(f"Total embeddings in cache: {len(embeddings_dict)}")
    
    return embeddings_dict

def get_embeddings_for_companies(df: pd.DataFrame, embeddings_dict: Dict, key_column: str = 'long_slug') -> pd.DataFrame:
    """
    Add embeddings to dataframe based on cached embeddings.
    
    Args:
        df: DataFrame with company data
        embeddings_dict: Dictionary mapping company keys to embeddings
        key_column: Column name containing the unique key for each company
    
    Returns:
        DataFrame with embeddings column added
    """
    # Map embeddings to dataframe
    df['embedding'] = df[key_column].map(embeddings_dict)
    
    # Report on missing embeddings
    missing_count = df['embedding'].isna().sum()
    if missing_count > 0:
        print(f"Warning: {missing_count} companies don't have embeddings")
    
    return df

# Example usage:
if __name__ == "__main__":
    # Load and process the dataframe
    df = load_and_process_df()
    
    # Generate embeddings (saves to JSON, doesn't add to df)
    embeddings_dict = generate_embeddings_for_df(
        df, 
        embeddings_json_path='yc_embeddings.json',
        desc_column='desc',
        key_column='long_slug',
        batch_size=10
    )
    
    # Save the dataframe with long_slug for reference
    fields_to_save = ['id', 'name', 'slug', 'desc', 'small_logo_thumb_url', 'website', 
                      'short', 'launched_at', 'tags', 'mentions_ai_agents', 'mentions_ai',
                      'industries', 'status', 'batch', 'mentions_health', 'long_slug']
    
    df[fields_to_save].to_json('yc_data.json', orient='records')
    
    print("Process completed!")
    print(f"Embeddings saved to 'yc_embeddings.json' with {len(embeddings_dict)} entries")
    print("DataFrame with long_slug saved to 'yc_data.json'")
    print(f"Example long_slug: {df['long_slug'].iloc[0]}")
     