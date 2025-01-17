import os
import sys
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

def execute_python_file(file_path):
    """
    Execute a Python file and return its output.
    Returns tuple of (success, output, execution_time)
    """
    try:
        start_time = datetime.now()
        
        # Create a new Python process to run the file
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = datetime.now()
        execution_duration = end_time - start_time
        
        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += "\n=== ERRORS ===\n" + result.stderr
            
        success = result.returncode == 0
        return success, output, execution_duration
    except subprocess.TimeoutExpired:
        return False, "Execution timed out after 5 minutes"
    except Exception as e:
        return False, f"Error executing file: {str(e)}"

def save_results(output_path, content, start_time, execution_duration):
    """Save execution results to a file with timing information."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Duration: {execution_duration.total_seconds():.2f} seconds\n\n")
        f.write("=== Output ===\n")
        f.write(content)

def process_implementation(impl_path):
    """Process a single implementation directory."""
    code_file = os.path.join(impl_path, 'app.py')
    results_path = os.path.join(impl_path, 'results.txt')
    
    if not os.path.exists(code_file):
        return f"Skipped {impl_path}: No app.py found"
    
    print(f"Executing {code_file}...")
    start_time = datetime.now()
    success, output, execution_duration = execute_python_file(code_file)
    save_results(results_path, output, start_time, execution_duration)
    
    status = "Successfully executed" if success else "Execution failed for"
    return f"{status} {code_file}"

def execute_samples(samples_path, max_workers=None):
    """
    Execute all app.py files found in the samples directory structure.
    Args:
        samples_path: Path to the samples directory
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
        future_to_path = {executor.submit(process_implementation, path): path 
                         for path in impl_paths}
        
        for future in as_completed(future_to_path):
            result = future.result()
            print(result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Execute sample Python files and save results')
    parser.add_argument('samples_path', help='Path to the samples directory')
    parser.add_argument('--workers', type=int, default=None, 
                       help='Maximum number of concurrent executions')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.samples_path):
        print(f"Error: Path {args.samples_path} does not exist")
        sys.exit(1)
    
    execute_samples(args.samples_path, args.workers)