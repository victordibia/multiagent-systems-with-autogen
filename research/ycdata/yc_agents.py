import pandas as pd
import json
import time
from openai import OpenAI
from pydantic import BaseModel
import os
import concurrent.futures
import random

# 1. Pydantic model for LLM response
class AgentAnalysis(BaseModel):
    domain: str
    subdomain: str
    is_agent: bool
    reason: str

# 2. Load DataFrame
def load_df(data_path='yc_data.json'):
    df = pd.read_json(data_path)
    return df

# 3. Filter for AI-related companies
def filter_mentions_ai(df):
    return df[df['mentions_ai'] == True].copy()

# 4. Load already processed results
def load_existing_results(json_path='yc_ai_agents_analysis.json'):
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                results = json.load(f)
            done_ids = set(row.get('long_slug') for row in results if row.get('long_slug'))
            return results, done_ids
        except Exception:
            return [], set()
    return [], set()

# 5. LLM prediction function using Pydantic and .parse
def analyze_agent_usecase(desc, model="gpt-4.1-mini"):
    client = OpenAI()
    # Normalized top-level domains with descriptions
    allowed_domains = {
        "health": "Healthcare, medical services, and life sciences",
        "finance": "Banking, investing, insurance, and financial services",
        "legal": "Law, legal services, and compliance",
        "government": "Public sector, civic tech, and government services",
        "education": "Learning, training, and educational technology",
        "productivity": "Workflow, automation, and tools to improve efficiency",
        "software": "Developer tools, platforms, and infrastructure",
        "e_commerce": "Online retail, marketplaces, and commerce platforms",
        "media": "Content creation, publishing, and entertainment",
        "real_estate": "Property, housing, and real estate services",
        "transportation": "Mobility, logistics, and transportation services",
        "other": "Does not fit in the above categories"
    }
    allowed_domain_keys = list(allowed_domains.keys())
    system_message = (
        "You are an expert in AI company analysis. "
        "Given a company description, predict if it is about generative AI agents (where a gen AI model is delegated to address tasks on the user's behalf). "
        f"Return a JSON with: domain (choose one of: {allowed_domain_keys}), subdomain (fine-grained), is_agent (true/false), and reason (justification). "
        "Be concise and accurate. "
        "IMPORTANT: If the company is about AI or ML in general, or about human agents, but is NOT about generative AI agents with some ability to act on the user's behalf or autonomously, then is_agent should be false. Do NOT mark as agent unless it is clearly about generative AI agents. "
        "For reference, here are the domain descriptions: " + ", ".join([f"{k}: {v}" for k, v in allowed_domains.items()])
    )
    user_message = f"Description: {desc}\nRespond in structured JSON."
    try:
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            response_format=AgentAnalysis,
            temperature=0.1
        )
        parsed = completion.choices[0].message.parsed
        return parsed.model_dump() if parsed else {}
    except Exception as e:
        print(f"Error: {e}")
        return {"domain": "", "subdomain": "", "is_agent": False, "reason": str(e)}

def process_batch(rows, model="gpt-4.1-mini", max_retries=3):
    batch_results = []
    for row in rows:
        desc = row.get('desc', '')
        retries = 0
        while retries < max_retries:
            try:
                analysis = analyze_agent_usecase(desc, model=model)
                # Save all fields from the row, plus analysis
                result_row = dict(row)
                result_row.update(analysis)
                batch_results.append(result_row)
                print(f"Analyzed: {row.get('name')} | is_agent: {analysis.get('is_agent')}")
                break
            except Exception as e:
                wait = 2 ** retries + random.uniform(0, 1)
                print(f"Error for {row.get('name')}: {e}. Backing off {wait:.1f}s.")
                time.sleep(wait)
                retries += 1
        else:
            print(f"Failed to process {row.get('name')} after {max_retries} retries.")
    return batch_results

def ensure_json_serializable(obj):
    """Recursively convert datetime, pd.Timestamp, and similar objects to strings for JSON serialization."""
    import datetime
    import pandas as pd
    if isinstance(obj, dict):
        return {k: ensure_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [ensure_json_serializable(v) for v in obj]
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    else:
        return obj

# 6. Main pipeline with batching and checkpointing
def main(batch_size=10, output_path='yc_agents.json', max_workers=3):
    df = load_df()
    ai_df = filter_mentions_ai(df)
    results, done_ids = load_existing_results(output_path)
    print(f"Loaded {len(done_ids)} already processed companies.")
    to_process = ai_df[~ai_df['long_slug'].isin(done_ids)]
    print(f"Need to process {len(to_process)} companies.")
    rows = [row for _, row in to_process.iterrows()]
    batches = [rows[i:i+batch_size] for i in range(0, len(rows), batch_size)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_batch = {executor.submit(process_batch, batch): batch for batch in batches}
        for future in concurrent.futures.as_completed(future_to_batch):
            batch_results = future.result()
            results.extend(batch_results)
            # Ensure all results are JSON serializable before dumping
            serializable_results = ensure_json_serializable(results)
            with open(output_path, 'w') as f:
                json.dump(serializable_results, f, indent=2)
            print(f"Checkpoint: saved {len(results)} results.")
    print("Done! Results saved to yc_agents.json")

if __name__ == "__main__":
    main()
