import os
import sys
import json
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from dotenv import load_dotenv


load_dotenv()

def execute_python_file(file_path):
    """
    Execute a Python file and return structured results.
    Returns dict with execution info and output.
    """
    start_time = datetime.now()
    
    try:
        # Create a new Python process to run the file
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = datetime.now()
        execution_duration = (end_time - start_time).total_seconds()
        
        return {
            "execution": {
                "start_time": start_time.isoformat(),
                "duration_seconds": execution_duration,
                "success": result.returncode == 0,
                "timed_out": False,
                "error": None
            },
            "output": {
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        }
        
    except subprocess.TimeoutExpired:
        end_time = datetime.now()
        execution_duration = (end_time - start_time).total_seconds()
        return {
            "execution": {
                "start_time": start_time.isoformat(),
                "duration_seconds": execution_duration,
                "success": False,
                "timed_out": True,
                "error": "Execution timed out after 5 minutes"
            },
            "output": {
                "stdout": "",
                "stderr": "Process timed out after 5 minutes"
            }
        }
    except Exception as e:
        end_time = datetime.now()
        execution_duration = (end_time - start_time).total_seconds()
        return {
            "execution": {
                "start_time": start_time.isoformat(),
                "duration_seconds": execution_duration,
                "success": False,
                "timed_out": False,
                "error": str(e)
            },
            "output": {
                "stdout": "",
                "stderr": f"Error executing file: {str(e)}"
            }
        }

def save_results(output_path, results):
    """Save execution results as JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Convert to results.json instead of results.txt
    output_path = os.path.splitext(output_path)[0] + '.json'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

def process_implementation(impl_path, regenerate=False):
    """Process a single implementation directory."""
    code_file = os.path.join(impl_path, 'app.py')
    results_path = os.path.join(impl_path, 'results.json')
    
    if not os.path.exists(code_file):
        return f"Skipped {impl_path}: No app.py found"

    # Check if results already exist and regenerate flag is false
    if os.path.exists(results_path) and not regenerate:
        return f"Skipped {code_file}: Results already exist"
    
    print(f"Executing {code_file}...")
    results = execute_python_file(code_file)
    save_results(results_path, results)
    
    status = "Successfully executed" if results["execution"]["success"] else "Execution failed for"
    return f"{status} {code_file}"

def execute_samples(samples_path, regenerate=False, max_workers=None):
    """
    Execute all app.py files found in the samples directory structure.
    Args:
        samples_path: Path to the samples directory
        regenerate: If True, always regenerate results even if they exist
        max_workers: Maximum number of concurrent executions (None for default)
    """
    print(f"Starting sample execution in {samples_path}")
    
    # Collect all implementation directories
    impl_paths = []
    for usecase_dir in os.listdir(samples_path):
        usecase_path = os.path.join(samples_path, usecase_dir)
        
        if not os.path.isdir(usecase_path) or usecase_dir.startswith('.'):
            continue
            
        for impl_dir in os.listdir(usecase_path):
            impl_path = os.path.join(usecase_path, impl_dir)
            if os.path.isdir(impl_path) and not impl_dir.startswith('.'):
                impl_paths.append(impl_path)
    
    # Execute implementations in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(process_implementation, path, regenerate): path 
            for path in impl_paths
        }
        
        for future in as_completed(future_to_path):
            result = future.result()
            print(result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Execute sample Python files and save results')
    parser.add_argument('samples_path', help='Path to the samples directory', default='course/samples')
    parser.add_argument('--workers', type=int, default=None, 
                       help='Maximum number of concurrent executions')
    parser.add_argument('--regenerate', action='store_true', default=False,
                       help='Regenerate results even if they already exist')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.samples_path):
        print(f"Error: Path {args.samples_path} does not exist")
        sys.exit(1)
    
    execute_samples(args.samples_path, args.regenerate, args.workers)