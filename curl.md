To test the API endpoints you've created with `curl`, you can use the following commands for different endpoints:

### 1. **Process Task** (`POST /process_task`)
To process a real estate task:

```bash
curl -X 'POST' \
  'http://localhost:5001/process_task' \
  -H 'Content-Type: application/json' \
  -d '{
  "task_id": 1,
  "property_address": "123 Main St, Springfield, IL",
  "task_type": "investment_analysis",
  "additional_details": {
    "extra_info": "Research on real estate trends"
  }
}'
```

### 2. **Get Task by ID** (`GET /get_task/{task_id}`)
To retrieve a specific task by its `task_id`:

```bash
curl -X 'GET' \
  'http://localhost:5001/get_task/1'
```

### 3. **Recent Tasks** (`GET /recent_tasks`)
To fetch the most recent tasks (default is 10 tasks):

```bash
curl -X 'GET' \
  'http://localhost:5001/recent_tasks?count=5'
```

### 4. **Get Task Result** (`GET /task_result/{task_id}`)
To fetch the final result for a task:

```bash
curl -X 'GET' \
  'http://localhost:5001/task_result/1'
```

### 5. **Property Types** (`GET /property_types`)
To get the list of supported property types:

```bash
curl -X 'GET' \
  'http://localhost:5001/property_types'
```

### 6. **Analysis Types** (`GET /analysis_types`)
To get the list of supported analysis types:

```bash
curl -X 'GET' \
  'http://localhost:5001/analysis_types'
```

### Example of Testing a Failed Task with a Non-existent `task_id`:
To test the failure scenario (e.g., a task not found):

```bash
curl -X 'GET' \
  'http://localhost:5001/get_task/9999'
```

Replace `localhost:5001` with the actual URL if the server is hosted elsewhere.