import os
import json
import glob
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# API endpoint (FastAPI backend)
API_URL = os.getenv("API_URL", "http://localhost:5001")

# Contract address (Arbitrum Sepolia)
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x6218f4b695c4b54f7eb02060d80a7ee3649024e9")

# Custom Jinja2 filters
@app.template_filter('slice')
def slice_filter(iterable, start, end=None):
    if iterable is None:
        return []
    if end is None:
        end = len(iterable)
    try:
        return iterable[start:end]
    except (TypeError, KeyError):
        # If iterable doesn't support slicing, convert to list first
        try:
            return list(iterable)[start:end]
        except:
            return []

@app.context_processor
def inject_user():
    return dict(user=None)  # Replace with actual user data when you implement authentication

@app.context_processor
def inject_globals():
    """Make global variables available to all templates"""
    return {
        'contract_address': CONTRACT_ADDRESS,
        'explorer_url': 'https://sepolia.arbiscan.io'
    }

@app.route('/')
def index():
    """Home page with overview of the application"""
    api_info = {}
    tasks = []
    property_types = []
    analysis_types = []
    ai_results = []
    agent_outputs = []
    
    try:
        # Get API info
        try:
            response = requests.get(f"{API_URL}/", timeout=15)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            api_info = response.json()
            
            # Add contract address
            api_info['contract_address'] = CONTRACT_ADDRESS
        except requests.exceptions.RequestException as e:
            flash(f"Error connecting to API root endpoint: {str(e)}", "warning")
        
        # Get recent tasks
        try:
            tasks_response = requests.get(f"{API_URL}/recent_tasks", timeout=5)
            tasks_response.raise_for_status()
            tasks = tasks_response.json()
        except requests.exceptions.RequestException as e:
            flash(f"Error fetching recent tasks: {str(e)}", "warning")
        
        # Get property types and analysis types
        try:
            property_types_response = requests.get(f"{API_URL}/property_types", timeout=5)
            property_types_response.raise_for_status()
            property_types = property_types_response.json().get("property_types", [])
        except requests.exceptions.RequestException as e:
            flash(f"Error fetching property types: {str(e)}", "warning")
        
        try:
            analysis_types_response = requests.get(f"{API_URL}/analysis_types", timeout=5)
            analysis_types_response.raise_for_status()
            analysis_types = analysis_types_response.json().get("analysis_types", [])
        except requests.exceptions.RequestException as e:
            flash(f"Error fetching analysis types: {str(e)}", "warning")
        
        # Get recent AI agent results (this doesn't require API connection)
        ai_results = get_recent_ai_results(3)
        
        # Get recent agent outputs (this doesn't require API connection)
        agent_outputs = get_recent_agent_outputs(3)
        
    except Exception as e:
        flash(f"Error in application: {type(e).__name__}: {str(e)}", "error")
    
    return render_template('index_tailwind.html', 
                          api_info=api_info, 
                          tasks=tasks,
                          property_types=property_types,
                          analysis_types=analysis_types,
                          ai_results=ai_results,
                          agent_outputs=agent_outputs)

@app.route('/task/<int:task_id>')
def view_task(task_id):
    """View details of a specific task"""
    try:
        # Get task details
        response = requests.get(f"{API_URL}/get_task/{task_id}")
        task = response.json()
        
        # Get task result (if available)
        result_response = requests.get(f"{API_URL}/task_result/{task_id}")
        result = result_response.json()
        
        # Merge transaction information if available in the result
        if isinstance(result, dict):
            # Copy transaction-related fields from result to task
            for field in ['transaction_hash', 'transaction_status', 'error']:
                if field in result:
                    task[field] = result[field]
        
        return render_template('task_detail.html', task=task, result=result)
    except Exception as e:
        flash(f"Error retrieving task {task_id}: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/create_task', methods=['GET', 'POST'])
def create_task():
    """Create a new real estate analysis task"""
    if request.method == 'GET':
        # Get property types and analysis types for the form
        property_types_response = requests.get(f"{API_URL}/property_types")
        property_types = property_types_response.json()["property_types"]
        
        analysis_types_response = requests.get(f"{API_URL}/analysis_types")
        analysis_types = analysis_types_response.json()["analysis_types"]
        
        return render_template('create_task.html', 
                              property_types=property_types,
                              analysis_types=analysis_types)
    
    elif request.method == 'POST':
        try:
            # Get form data
            task_id = int(request.form.get('task_id'))
            property_address = request.form.get('property_address')
            task_type = request.form.get('task_type')
            
            # Build additional details
            additional_details = {
                "property_details": {
                    "property_type": request.form.get('property_type'),
                    "bedrooms": int(request.form.get('bedrooms')) if request.form.get('bedrooms') else None,
                    "bathrooms": float(request.form.get('bathrooms')) if request.form.get('bathrooms') else None,
                    "square_footage": int(request.form.get('square_footage')) if request.form.get('square_footage') else None,
                    "year_built": int(request.form.get('year_built')) if request.form.get('year_built') else None,
                    "price": float(request.form.get('price')) if request.form.get('price') else None
                }
            }
            
            # Remove None values
            additional_details["property_details"] = {k: v for k, v in additional_details["property_details"].items() if v is not None}
            
            # Create task request payload
            payload = {
                "task_id": task_id,
                "property_address": property_address,
                "task_type": task_type,
                "additional_details": additional_details
            }
            
            # Send request to API
            response = requests.post(f"{API_URL}/process_task", json=payload)
            result = response.json()
            
            if response.status_code == 200:
                # Check if there was an error in the blockchain transaction
                if 'error' in result:
                    # Task was created but blockchain transaction failed
                    flash_message = f"Task {task_id} created with local analysis, but blockchain storage failed: {result.get('error')}"
                    flash_category = "warning"
                else:
                    # Task created successfully
                    flash_message = f"Task {task_id} created successfully!"
                    flash_category = "success"
                
                # Always show transaction hash if available
                if 'transaction_hash' in result:
                    flash_message += f" Transaction hash: {result['transaction_hash'][:10]}..."
                
                flash(flash_message, flash_category)
                return redirect(url_for('view_task', task_id=task_id))
            else:
                flash(f"Error creating task: {result.get('error', 'Unknown error')}", "error")
                return redirect(url_for('create_task'))
                
        except Exception as e:
            flash(f"Error creating task: {str(e)}", "error")
            return redirect(url_for('create_task'))

@app.route('/recent_tasks')
def recent_tasks():
    """View recent tasks"""
    try:
        count = request.args.get('count', 10, type=int)
        response = requests.get(f"{API_URL}/recent_tasks?count={count}")
        tasks = response.json()
        return render_template('recent_tasks.html', tasks=tasks)
    except Exception as e:
        flash(f"Error retrieving recent tasks: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/blockchain_info')
def blockchain_info():
    """View blockchain information"""
    try:
        # Get recent tasks which includes blockchain info
        response = requests.get(f"{API_URL}/recent_tasks")
        blockchain_data = response.json()
        
        return render_template('blockchain_info.html', blockchain_data=blockchain_data)
    except Exception as e:
        flash(f"Error retrieving blockchain information: {str(e)}", "error")
        return redirect(url_for('index'))

# API proxy routes to handle CORS issues
@app.route('/api/recent_tasks')
def api_recent_tasks():
    count = request.args.get('count', 10, type=int)
    response = requests.get(f"{API_URL}/recent_tasks?count={count}")
    return jsonify(response.json())

@app.route('/api/task/<int:task_id>')
def api_task(task_id):
    response = requests.get(f"{API_URL}/get_task/{task_id}")
    return jsonify(response.json())

@app.route('/api/task_result/<int:task_id>')
def api_task_result(task_id):
    response = requests.get(f"{API_URL}/task_result/{task_id}")

def get_recent_ai_results(count=5):
    """Get the most recent AI agent results using the local_tasks API endpoint"""
    try:
        results = []
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
        
        # Check if directory exists
        if not os.path.exists(results_dir):
            return results
        
        # Try to use the API endpoint first
        try:
            response = requests.get(f"{API_URL}/local_tasks", timeout=5)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            tasks = response.json()
            
            # Sort tasks by ID (assuming higher ID = more recent)
            sorted_tasks = sorted(tasks, key=lambda x: x.get('task_id', 0), reverse=True)
            
            # Get the most recent tasks
            recent_tasks = sorted_tasks[:count]
            
            for task in recent_tasks:
                task_id = task.get('task_id')
                if task_id:
                    try:
                        # Get detailed task information
                        task_response = requests.get(f"{API_URL}/local_task/{task_id}", timeout=5)
                        task_response.raise_for_status()
                        task_detail = task_response.json()
                        
                        # Add to results
                        results.append({
                            'task_id': task_id,
                            'property_address': task_detail.get('property_address', 'Unknown Address'),
                            'task_type': task_detail.get('task_type', 'Unknown Type'),
                            'timestamp': task_detail.get('timestamp', ''),
                            'file_hash': task_detail.get('file_hash', ''),
                            'summary': task_detail.get('summary', '')
                        })
                    except requests.exceptions.RequestException as e:
                        # Log the error but continue with other tasks
                        print(f"Error fetching task {task_id}: {str(e)}")
                        continue
            
            return results[:count]
        except requests.exceptions.RequestException as e:
            # Log the error and fall back to file-based approach
            print(f"Error fetching local tasks from API: {str(e)}")
            # Fall back to file-based approach
            pass
        
        # Fallback: Get results directory path
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
        
        # Check for task_index.json first
        index_file = os.path.join(results_dir, "task_index.json")
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r') as f:
                    task_index = json.load(f)
                    
                # Sort by timestamp (newest first)
                task_index.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                
                # Get the details for each task
                results = []
                for task_info in task_index[:count]:  # Limit to requested count
                    result_file = task_info.get('result_file')
                    if result_file:
                        file_path = os.path.join(results_dir, result_file)
                        if os.path.exists(file_path):
                            try:
                                with open(file_path, 'r') as f:
                                    result_data = json.load(f)
                                    # Add filename to result data
                                    result_data['filename'] = result_file
                                    results.append(result_data)
                            except Exception as file_error:
                                print(f"Error loading result file {result_file}: {str(file_error)}")
                
                return results
            except Exception as index_error:
                print(f"Error reading task index: {str(index_error)}")
                # Fall back to direct file search
        
        # Fallback: Find all JSON files in the results directory (excluding task_index.json)
        result_files = [f for f in glob.glob(os.path.join(results_dir, '*.json')) 
                       if os.path.basename(f) != "task_index.json"]
        
        # Load and parse each result file
        results = []
        for file_path in result_files:
            try:
                with open(file_path, 'r') as f:
                    result_data = json.load(f)
                    # Add filename to result data
                    result_data['filename'] = os.path.basename(file_path)
                    results.append(result_data)
            except Exception as e:
                print(f"Error loading result file {os.path.basename(file_path)}: {str(e)}")
        
        # Sort results by timestamp (if available) or fallback to modification time
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Return only the requested number of results
        return results[:count]
    except Exception as e:
        print(f"Error retrieving AI results: {str(e)}")
        return []


def get_recent_agent_outputs(count=5):
    """Get the most recent CrewAI agent outputs from the results/agents directory"""
    try:
        # Get agents directory path
        agents_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'agents')
        
        # Check if directory exists
        if not os.path.exists(agents_dir):
            return []
        
        # Find all JSON files in the agents directory
        result_files = glob.glob(os.path.join(agents_dir, '*.json'))
        
        # Load and parse each result file
        results = []
        for file_path in result_files:
            try:
                with open(file_path, 'r') as f:
                    result_data = json.load(f)
                    # Add filename to result data
                    result_data['filename'] = os.path.basename(file_path)
                    results.append(result_data)
            except Exception as e:
                print(f"Error loading agent output file {os.path.basename(file_path)}: {str(e)}")
        
        # Sort results by timestamp (if available) or fallback to modification time
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Return only the requested number of results
        return results[:count]
    except Exception as e:
        print(f"Error retrieving agent outputs: {str(e)}")
        return []

@app.route('/ai_results')
def ai_results():
    """View all AI agent results saved in the results directory"""
    try:
        # First try to use the new API endpoint
        try:
            response = requests.get(f"{API_URL}/local_tasks")
            if response.status_code == 200:
                # Get all tasks from the index
                all_tasks = response.json()
                
                # Get the details for each task
                results = []
                for task_info in all_tasks:
                    task_id = task_info.get('task_id')
                    if task_id:
                        try:
                            # Get the full task details
                            task_response = requests.get(f"{API_URL}/local_task/{task_id}")
                            if task_response.status_code == 200:
                                task_data = task_response.json()
                                # Add filename to result data for compatibility
                                task_data['filename'] = task_info.get('result_file', f"task_{task_id}.json")
                                results.append(task_data)
                            else:
                                # If we can't get details, just use the index info
                                task_info['filename'] = task_info.get('result_file', f"task_{task_id}.json")
                                results.append(task_info)
                        except Exception as task_error:
                            flash(f"Error fetching details for task {task_id}: {str(task_error)}", "warning")
                
                # Sort results by task_id and timestamp (if available)
                results.sort(key=lambda x: (x.get('task_id', 0), x.get('timestamp', '')), reverse=True)
                return render_template('ai_results.html', results=results)
                
        except Exception as api_error:
            flash(f"Error using API endpoint: {str(api_error)}", "warning")
            # Fall back to direct file access if API fails
        
        # Fallback: Get results directory path
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
        
        # Check for task_index.json first
        index_file = os.path.join(results_dir, "task_index.json")
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r') as f:
                    task_index = json.load(f)
                    
                # Get the details for each task
                results = []
                for task_info in task_index:
                    result_file = task_info.get('result_file')
                    if result_file:
                        file_path = os.path.join(results_dir, result_file)
                        if os.path.exists(file_path):
                            try:
                                with open(file_path, 'r') as f:
                                    result_data = json.load(f)
                                    # Add filename to result data
                                    result_data['filename'] = result_file
                                    results.append(result_data)
                            except Exception as file_error:
                                flash(f"Error loading result file {result_file}: {str(file_error)}", "warning")
                
                # Sort results by task_id and timestamp
                results.sort(key=lambda x: (x.get('task_id', 0), x.get('timestamp', '')), reverse=True)
                return render_template('ai_results.html', results=results)
                
            except Exception as index_error:
                flash(f"Error reading task index: {str(index_error)}", "warning")
                # Fall back to direct file search
        
        # Fallback: Find all JSON files in the results directory (excluding task_index.json)
        result_files = [f for f in glob.glob(os.path.join(results_dir, '*.json')) 
                       if os.path.basename(f) != "task_index.json"]
        
        # Load and parse each result file
        results = []
        for file_path in result_files:
            try:
                with open(file_path, 'r') as f:
                    result_data = json.load(f)
                    # Add filename to result data
                    result_data['filename'] = os.path.basename(file_path)
                    results.append(result_data)
            except Exception as e:
                flash(f"Error loading result file {os.path.basename(file_path)}: {str(e)}", "warning")
        
        # Sort results by task_id and timestamp (if available)
        results.sort(key=lambda x: (x.get('task_id', 0), x.get('timestamp', '')), reverse=True)
        
        return render_template('ai_results.html', results=results)
    except Exception as e:
        flash(f"Error retrieving AI results: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/ai_result/<int:task_id>', defaults={'file_hash': None})
@app.route('/ai_result/<int:task_id>/<string:file_hash>')
def ai_result_detail(task_id, file_hash):
    """View details of a specific AI agent result"""
    try:
        # First try to use the new API endpoint
        try:
            # Try to get the result using the local_task endpoint
            response = requests.get(f"{API_URL}/local_task/{task_id}")
            if response.status_code == 200:
                result_data = response.json()
                # If file_hash wasn't provided but is available in the result, use that
                if file_hash is None and 'file_hash' in result_data:
                    file_hash = result_data['file_hash']
                return render_template('ai_result_detail.html', result=result_data, task_id=task_id, file_hash=file_hash)
            
            # If that fails and we have a file_hash, try using it as a transaction hash
            if file_hash and len(file_hash) > 10:  # If it's a full hash
                response = requests.get(f"{API_URL}/local_result/{file_hash}")
                if response.status_code == 200:
                    result_data = response.json()
                    return render_template('ai_result_detail.html', result=result_data, task_id=task_id, file_hash=file_hash)
        except Exception as api_error:
            flash(f"Error using API endpoint: {str(api_error)}", "warning")
            # Fall back to direct file access if API fails
        
        # Fallback: Get results directory path
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
        
        # First check the task_index.json to find the correct file
        index_file = os.path.join(results_dir, "task_index.json")
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r') as f:
                    task_index = json.load(f)
                
                # Look for the task in the index
                for task_info in task_index:
                    if task_info.get('task_id') == task_id:
                        result_file = task_info.get('result_file')
                        if result_file:
                            file_path = os.path.join(results_dir, result_file)
                            if os.path.exists(file_path):
                                with open(file_path, 'r') as f:
                                    result_data = json.load(f)
                                return render_template('ai_result_detail.html', result=result_data, task_id=task_id, file_hash=file_hash)
            except Exception as index_error:
                flash(f"Error reading task index: {str(index_error)}", "warning")
        
        # If we couldn't find it in the index, try direct file lookup
        file_pattern = f"task_{task_id}_{file_hash}.json"
        file_path = os.path.join(results_dir, file_pattern)
        
        if not os.path.exists(file_path):
            # Try looking for any file with this task_id
            matching_files = glob.glob(os.path.join(results_dir, f"task_{task_id}_*.json"))
            if matching_files:
                file_path = matching_files[0]  # Use the first match
            else:
                flash(f"Result file for task {task_id} not found", "error")
                return redirect(url_for('ai_results'))
        
        # Load result data
        with open(file_path, 'r') as f:
            result_data = json.load(f)
        
        return render_template('ai_result_detail.html', result=result_data, task_id=task_id, file_hash=file_hash)
    except Exception as e:
        flash(f"Error retrieving AI result details: {str(e)}", "error")
        return redirect(url_for('ai_results'))

@app.route('/agent_outputs')
def agent_outputs():
    """View all CrewAI agent outputs saved in the results/agents directory"""
    try:
        # Get agents directory path
        agents_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'agents')
        
        # Check if directory exists
        if not os.path.exists(agents_dir):
            os.makedirs(agents_dir, exist_ok=True)  # Create directory if it doesn't exist
            flash("No agent outputs found. Directory created.", "warning")
            return render_template('agent_outputs_tailwind.html', results=[])
        
        # Find all JSON files in the agents directory
        result_files = glob.glob(os.path.join(agents_dir, '*.json'))
        
        if not result_files:
            flash("No agent output files found in the directory", "info")
            return render_template('agent_outputs_tailwind.html', results=[])
        
        # Load and parse each result file
        results = []
        for file_path in result_files:
            try:
                with open(file_path, 'r') as f:
                    result_data = json.load(f)
                    # Add filename to result data
                    result_data['filename'] = os.path.basename(file_path)
                    results.append(result_data)
            except json.JSONDecodeError as e:
                flash(f"Error parsing JSON in file {os.path.basename(file_path)}: {str(e)}", "warning")
            except Exception as e:
                flash(f"Error loading agent output file {os.path.basename(file_path)}: {type(e).__name__}: {str(e)}", "warning")
        
        # Sort results by timestamp (if available) or fallback to modification time
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return render_template('agent_outputs_tailwind.html', results=results)
    except Exception as e:
        flash(f"Error retrieving agent outputs: {type(e).__name__}: {str(e)}", "error")
        return render_template('agent_outputs_tailwind.html', results=[])

@app.route('/agent_output/<string:filename>')
def agent_output_detail(filename):
    """View details of a specific agent output"""
    try:
        # Get agents directory path
        agents_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'agents')
        
        # Sanitize filename to prevent directory traversal attacks
        safe_filename = os.path.basename(filename)
        
        # Find matching result file
        file_path = os.path.join(agents_dir, safe_filename)
        
        if not os.path.exists(file_path):
            flash(f"Agent output file {safe_filename} not found", "error")
            return redirect(url_for('agent_outputs'))
        
        # Load result data
        try:
            with open(file_path, 'r') as f:
                result_data = json.load(f)
        except json.JSONDecodeError as e:
            flash(f"Error parsing JSON in file {safe_filename}: {str(e)}", "error")
            return redirect(url_for('agent_outputs'))
        
        # Extract structured data for display if available
        structured_data = {}
        if 'crew_output' in result_data and 'json_dict' in result_data['crew_output']:
            structured_data = result_data['crew_output']['json_dict']
        
        # Format raw JSON for display
        raw_json = json.dumps(result_data, indent=2)
        
        return render_template('agent_output_detail_tailwind.html', 
                              result=result_data, 
                              filename=safe_filename,
                              structured_data=structured_data,
                              raw_json=raw_json)
    except Exception as e:
        flash(f"Error retrieving agent output details: {type(e).__name__}: {str(e)}", "error")
        return redirect(url_for('agent_outputs'))

@app.route('/agent_output_structured/<string:filename>')
def agent_output_structured(filename):
    """View structured details of a specific agent output"""
    try:
        # Get agents directory path
        agents_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'agents')
        
        # Sanitize filename to prevent directory traversal attacks
        safe_filename = os.path.basename(filename)
        
        # Find matching result file
        file_path = os.path.join(agents_dir, safe_filename)
        
        if not os.path.exists(file_path):
            flash(f"Agent output file {safe_filename} not found", "error")
            return redirect(url_for('agent_outputs'))
        
        # Load result data
        try:
            with open(file_path, 'r') as f:
                result_data = json.load(f)
        except json.JSONDecodeError as e:
            flash(f"Error parsing JSON in file {safe_filename}: {str(e)}", "error")
            return redirect(url_for('agent_outputs'))
        
        # Extract structured data for display if available
        structured_data = {}
        if 'crew_output' in result_data and 'json_dict' in result_data['crew_output']:
            structured_data = result_data['crew_output']['json_dict']
        
        return render_template('agent_output_structured.html', 
                              result=result_data, 
                              filename=safe_filename,
                              structured_data=structured_data)
    except Exception as e:
        flash(f"Error retrieving agent output details: {type(e).__name__}: {str(e)}", "error")
        return redirect(url_for('agent_outputs'))

if __name__ == '__main__':
    port = int(os.getenv("FLASK_PORT", 5070))
    app.run(host='0.0.0.0', port=port, debug=True)
