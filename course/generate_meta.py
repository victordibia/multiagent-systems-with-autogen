import os
import json
from pathlib import Path

def count_lines_of_code(file_path):
    """Count non-empty lines in a file."""
    if not os.path.exists(file_path):
        return 0
    with open(file_path, 'r', encoding='utf-8') as f:
        return sum(1 for line in f if line.strip())

def generate_usecases_json(samples_path):
    # Repository info
    repo_info = {
        "owner": "victordibia",
        "name": "multiagent-systems-with-autogen",
        "branch": "main",
        "base_url": "https://raw.githubusercontent.com/victordibia/multiagent-systems-with-autogen/refs/heads/main/course/"
    }
    
    # Construct GitHub repository URL - now includes /course prefix
    github_base_url = f"https://github.com/{repo_info['owner']}/{repo_info['name']}/blob/{repo_info['branch']}/course"
    
    usecases = {}
    domains = set()
    frameworks = set()
    
    # Walk through the samples directory
    for usecase_dir in os.listdir(samples_path):
        usecase_path = os.path.join(samples_path, usecase_dir)
        
        # Skip if not a directory or starts with .
        if not os.path.isdir(usecase_path) or usecase_dir.startswith('.'):
            continue
        
        # Get metadata from metadata.json if it exists, otherwise use defaults
        metadata_path = os.path.join(usecase_path, 'metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                "title": usecase_dir.replace('_', ' ').title(),
                "description": f"Implementation of {usecase_dir}",
                "domains": ["basics"],
                "tags": []
            }
        
        # Add domains to global set
        domains.update(metadata.get("domains", []))
        
        # Find implementations (subdirectories)
        implementations = []
        for impl_dir in os.listdir(usecase_path):
            impl_path = os.path.join(usecase_path, impl_dir)
            
            if not os.path.isdir(impl_path) or impl_dir.startswith('.'):
                continue
            
            # Look for app.py and results.json
            code_file = os.path.join(impl_path, 'app.py')
            results_path = os.path.join(impl_dir, 'results.json')
            metadata_path = os.path.join(impl_path, 'metadata.json')

            # read metadata if it exists
            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            
            frameworks.add(impl_dir)  # Add to global frameworks set
            
            # Count lines of code if file exists
            loc = count_lines_of_code(code_file) if os.path.exists(code_file) else 0
            
            # Construct relative path for GitHub URL
            relative_code_path = f"samples/{usecase_dir}/{impl_dir}/app.py"
            github_url = f"{github_base_url}/{relative_code_path}"
            
            implementation = {
                "framework": impl_dir,
                "title": f"{impl_dir.replace('_', ' ').title()} Implementation",
                "description": f"Implementation using {impl_dir}",
                "code": {
                    "path": f"/samples/{usecase_dir}/{impl_dir}/app.py",
                    "language": "python",
                    "loc": loc,
                    "githubUrl": github_url,
                    "metadata": metadata
                },
                "results": {
                    "path": f"/samples/{usecase_dir}/{results_path}"
                }
            }
            
            implementations.append(implementation)
        
        # sort implementations by framework
        implementations = sorted(implementations, key=lambda x: x["framework"])

        # Add usecase to usecases dict
        usecases[usecase_dir] = {
            "title": metadata.get("title", usecase_dir.replace('_', ' ').title()),
            "description": metadata.get("description", f"Implementation of {usecase_dir}"),
            "domains": metadata.get("domains", ["basics"]),
            "tags": metadata.get("tags", []),
            "implementations": implementations
        }
    
    # Construct final JSON structure
    final_json = {
        "repository": repo_info,
        "usecases": usecases,
        "metadata": {
            "domains": sorted(list(domains)),
            "frameworks": sorted(list(frameworks))
        }
    }
    
    # Save to file
    output_path = os.path.join(samples_path, 'usecases.json')
    with open(output_path, 'w') as f:
        json.dump(final_json, f, indent=2)
    
    print(f"Generated usecases.json at {output_path}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python generate_usecases.py <samples_directory_path>")
        sys.exit(1)
    
    samples_path = sys.argv[1]
    if not os.path.exists(samples_path):
        print(f"Error: Path {samples_path} does not exist")
        sys.exit(1)
    
    generate_usecases_json(samples_path)