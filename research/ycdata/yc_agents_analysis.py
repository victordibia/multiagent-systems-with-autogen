import json
import pandas as pd
from collections import Counter, defaultdict
import os

def load_agent_data(json_path='yc_agents.json'):
    with open(json_path, 'r') as f:
        data = json.load(f)
    # Support both list and dict format
    if isinstance(data, dict) and 'agents' in data:
        agents = data['agents']
    else:
        agents = data
    return pd.DataFrame(agents)

def get_top_counts(df, column, n=5):
    counts = df[column].value_counts().head(n)
    return counts

# New: Get number of companies in raw YC dataset
def get_raw_company_count(json_path='yc_data.json'):
    if not os.path.exists(json_path):
        return None
    with open(json_path, 'r') as f:
        data = json.load(f)
    if isinstance(data, list):
        return len(data)
    elif isinstance(data, dict) and 'companies' in data:
        return len(data['companies'])
    return None

# New: Get number of companies after AI/agent keyword filter
def get_ai_filtered_count(json_path='yc_agents.json'):
    if not os.path.exists(json_path):
        return None
    with open(json_path, 'r') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'agents' in data:
        agents = data['agents']
    else:
        agents = data
    # Only count companies that actually mention AI/agents
    ai_filtered = [company for company in agents if company.get('mentions_ai', False)]
    return len(ai_filtered)

def get_value_prop_patterns(df, n=5):
    # Use the 'reason' field for value prop patterns
    reasons = df['reason'].dropna().tolist()
    # Simple keyword extraction: most common words (excluding stopwords)
    import re
    stopwords = set(['the', 'and', 'to', 'of', 'for', 'in', 'on', 'with', 'a', 'is', 'as', 'by', 'an', 'at', 'from', 'that', 'this', 'it', 'be', 'or', 'are', 'their', 'user', 'users', 'using', 'can', 'will', 'which', 'into', 'has', 'have', 'but', 'not', 'about', 'more', 'than', 'also', 'such', 'these', 'they', 'who', 'when', 'where', 'how', 'what', 'all', 'other', 'its', 'through', 'based', 'help', 'make', 'provide', 'allows', 'enables', 'via', 'used', 'being', 'each', 'may', 'new', 'one', 'our', 'your', 'we', 'you'])
    words = []
    for reason in reasons:
        words += [w.lower() for w in re.findall(r'\b\w+\b', reason) if w.lower() not in stopwords and len(w) > 2]
    return Counter(words).most_common(n)

def get_example_companies(df, group_col, n=1):
    # Return a dict: {group: [examples]}
    examples = defaultdict(list)
    for group, group_df in df.groupby(group_col):
        for _, row in group_df.head(n).iterrows():
            examples[group].append({
                'name': row.get('name'),
                'desc': row.get('desc'),
                'reason': row.get('reason'),
                'website': row.get('website')
            })
    return examples

def get_yoy_agentic_stats(agentic_df, raw_df, year_col='launched_at'):
    # Parse year from date string
    agentic_df = agentic_df.copy()
    raw_df = raw_df.copy()
    agentic_df['year'] = pd.to_datetime(agentic_df[year_col], errors='coerce').dt.year
    raw_df['year'] = pd.to_datetime(raw_df[year_col], errors='coerce').dt.year
    # Only consider years 2020-2025
    years = list(range(2020, 2026))
    yoy_stats = []
    for year in years:
        # Cumulative counts up to and including this year
        total_raw = raw_df[raw_df['year'] <= year].shape[0]
        total_agentic = agentic_df[agentic_df['year'] <= year].shape[0]
        # Companies added that year (yearly counts)
        raw_that_year = raw_df[raw_df['year'] == year].shape[0]
        agentic_that_year = agentic_df[agentic_df['year'] == year].shape[0]
        # Calculate yearly percentage (agentic companies that year / total companies that year)
        pct_agentic = (agentic_that_year / raw_that_year * 100) if raw_that_year > 0 else 0
        # Cumulative % growth in agentic companies (relative to base year 2020)
        if year == 2020:
            cum_growth_agentic = 0
        else:
            # Get the base year (2020) agentic count for growth calculation
            base_agentic = yoy_stats[0]['total_agentic'] if yoy_stats else 0
            cum_growth_agentic = ((total_agentic - base_agentic) / base_agentic * 100) if base_agentic > 0 else 0
        yoy_stats.append({
            'year': year,
            'total_yc': total_raw,
            'raw_that_year': raw_that_year,
            'total_agentic': total_agentic,
            'agentic_that_year': agentic_that_year,
            'pct_agentic': pct_agentic,
            'cum_growth_agentic': cum_growth_agentic
        })
    return yoy_stats

def main():
    json_path = 'yc_agents.json'
    raw_json_path = 'yc_data.json'
    if not os.path.exists(json_path):
        print(f"File {json_path} not found.")
        return
    # New: Get raw and filtered counts
    raw_count = get_raw_company_count(raw_json_path)
    ai_filtered_count = get_ai_filtered_count(json_path)
    df = load_agent_data(json_path)
    # Only keep rows where is_agent is True
    agentic_df = df[df['is_agent'] == True]
    total_agents = len(agentic_df)
    
    if total_agents == 0:
        print("Warning: No agentic companies found in the dataset.")
        return
    # Load raw YC data for YoY stats
    if not os.path.exists(raw_json_path):
        print(f"Raw data file {raw_json_path} not found. Cannot calculate YoY stats.")
        return
    raw_df = pd.read_json(raw_json_path)
    # Calculate YoY stats
    yoy_stats = get_yoy_agentic_stats(agentic_df, raw_df, year_col='launched_at')
    # Calculate percentages safely
    pct_ai_filtered = (ai_filtered_count / raw_count * 100) if (raw_count is not None and ai_filtered_count is not None and raw_count > 0) else 0
    pct_agentic = (total_agents / raw_count * 100) if (raw_count is not None and raw_count > 0) else 0
    pct_agentic_of_ai = (total_agents / ai_filtered_count * 100) if (ai_filtered_count is not None and ai_filtered_count > 0) else 0
    
    # Validation: agentic companies should not exceed AI-filtered companies
    if ai_filtered_count is not None and total_agents > ai_filtered_count:
        print(f"Warning: More agentic companies ({total_agents}) than AI-filtered companies ({ai_filtered_count}). This suggests a data inconsistency.")
    top_domains = get_top_counts(agentic_df, 'domain', n=5)
    top_subdomains = get_top_counts(agentic_df, 'subdomain', n=5)
    value_prop_patterns = get_value_prop_patterns(agentic_df, n=10)
    example_companies = get_example_companies(agentic_df, 'domain', n=2)
    # Save summary as markdown
    summary_md = f"""
## Key Findings: YC Agentic Companies (Auto-generated)

- **Total companies in raw YC dataset:** {raw_count}
- **Companies after AI/agent keyword filter:** {ai_filtered_count} ({pct_ai_filtered:.1f}% of raw)
- **Total agentic companies identified:** {total_agents} ({pct_agentic:.1f}% of raw, {pct_agentic_of_ai:.1f}% of AI/agent filtered)

### Year-over-Year Growth of Agentic Companies (2020-2025)

| Year | Cumulative YC Startups | YC Startups That Year | Cumulative Agentic Companies | Agentic Companies That Year | % Agentic That Year | Cumulative % Growth Agentic |
|------|-----------------------|-----------------------|------------------------------|----------------------------|---------------------|----------------------------|
"""
    for i, row in enumerate(yoy_stats):
        summary_md += f"| {row['year']} | {row['total_yc']} | {row['raw_that_year']} | {row['total_agentic']} | {row['agentic_that_year']} | {row['pct_agentic']:.1f}% | {row['cum_growth_agentic']:.1f}% |\n"
    summary_md += f"""
- **Top domains:**\n{top_domains.to_string()}
- **Top use cases (subdomains):**\n{top_subdomains.to_string()}
- **Most common value proposition keywords:** {', '.join([w for w, _ in value_prop_patterns])}
"""
    for domain, examples in example_companies.items():
        summary_md += f"\n**{domain.title()}**\n"
        for ex in examples:
            summary_md += f"- {ex['name']}: {ex['desc']}\n  - Value prop: {ex['reason']}\n  - Website: {ex['website']}\n"
    with open('yc_agents_summary.md', 'w') as f:
        f.write(summary_md)
    print("Analysis complete. Summary written to yc_agents_summary.md.")
    print(f"Raw YC companies: {raw_count}")
    print(f"After AI/agent keyword filter: {ai_filtered_count} ({pct_ai_filtered:.1f}% of raw)")
    print(f"After LLM agentic filter: {total_agents} ({pct_agentic:.1f}% of raw, {pct_agentic_of_ai:.1f}% of AI/agent filtered)")
    print("\nYear-over-Year Agentic Company Growth:")
    for row in yoy_stats:
        print(f"{row['year']}: {row['total_agentic']} agentic / {row['total_yc']} total ({row['pct_agentic']:.1f}%)")

if __name__ == "__main__":
    main()
