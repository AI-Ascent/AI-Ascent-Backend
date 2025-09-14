# AI Ascent Backend

The API Backend for AI Ascent SAP Hackathon.

## Table of Contents
- [Agents](#agents)
- [AI Models](#ai-models)
- [Features](#features)
- [API Documentation](#api-documentation)
- [Models](#models)
- [Setup](#setup)
- [Run with Docker](#run-with-docker)
- [Caching Configuration](#caching-configuration)

## Agents

The backend uses AI agents powered by LangChain for various processing tasks.

### Feedback Agent
- Collect and store user feedback
- AI-powered classification of feedback into strengths and improvements using sentiment analysis
- Generation of actionable insights and growth tips from classified feedback
- Bias filtering to ensure fair and inclusive feedback analysis
- Vector-based storage of user strengths for mentor matching

### Onboarding Management
- Create and manage onboarding catalogs for different job roles
- Associate specializations, tags, checklists, and resources with each role
- AI-powered semantic search using vector embeddings to find relevant onboarding information
- Personalized onboarding plans based on employee job titles and specializations
- Support for structured onboarding processes with customizable checklists and learning resources

### Skill Development
- Create and manage skill catalogs with learning resources
- AI-powered semantic search for skill recommendations
- Personalized skill suggestions based on user context and feedback insights
- Integration with external search (Tavily) for additional resources when needed
- Support for various resource types (tutorials, courses, documentation, etc.)

### Mentorship Matching
- Find mentors within the organization based on improvement areas
- Vector similarity matching between user improvements and other users' strengths
- AI-powered selection of best mentor matches
- Support for multiple improvement areas with individual mentor recommendations

### Safety and Security
- Bias and hate speech filtering in feedback using ML models
- Prompt injection detection for user inputs
- PII (Personal Identifiable Information) redaction from prompts
- Safe processing of all AI agent interactions

## AI Models

This project uses various AI models for different purposes. Defaults live in `agents/agents/model_config.py` and can be overridden via env vars.

### Large Language Models (LLMs)
The app uses Groq-hosted models:

- Coordinator Agent (default): `groq:openai/gpt-oss-120b`
- Feedback Agent (default): `groq:llama-3.1-8b-instant`
- Opportunity Agent (default): `groq:llama-3.1-8b-instant`
- Onboard Agent (default): `groq:qwen/qwen3-32b`
- Skill Agent (default): `groq:openai/gpt-oss-20b`

Override with env vars: `CORDINATOR_MODEL`, `FEEDBACK_MODEL`, `OPPORTUNITY_MODEL`, `ONBOARD_MODEL`, `SKILL_MODEL`.

### HuggingFace Models
The application uses several HuggingFace models for specialized tasks:

- **Embeddings Model**: `all-MiniLM-L6-v2`
  - Purpose: Text embeddings for semantic search and similarity matching
  - Used in: Vector similarity search across job titles, skills, and user data

- **Sentiment Analysis**: `cardiffnlp/twitter-roberta-base-sentiment-latest`
  - Purpose: Sentiment classification of user feedback
  - Used in: Feedback processing and classification

- **Hate Speech Detection**: `facebook/roberta-hate-speech-dynabench-r4-target`
  - Purpose: Filtering biased and discriminatory content
  - Used in: Safety checks on user feedback

- **Prompt Injection Detection**: `protectai/deberta-v3-base-prompt-injection-v2`
  - Purpose: Preventing malicious prompt injection attacks
  - Used in: Input validation and security checks

## Features

### User Authentication
- Secure user login with email and password
- User management with custom APIUser model
- Password hashing and validation

### Feedback Processing
- Collect and store user feedback
- AI-powered classification of feedback into strengths and improvements using sentiment analysis
- Generation of actionable insights and growth tips from classified feedback
- Bias filtering to ensure fair and inclusive feedback analysis
- Vector-based storage of user strengths for mentor matching

### Onboarding Management
- Create and manage onboarding catalogs for different job roles
- Associate specializations, tags, checklists, and resources with each role
- AI-powered semantic search using vector embeddings to find relevant onboarding information
- Personalized onboarding plans based on employee job titles and specializations
- Support for structured onboarding processes with customizable checklists and learning resources

### Skill Development
- Create and manage skill catalogs with learning resources
- AI-powered semantic search for skill recommendations
- Personalized skill suggestions based on user context and feedback insights
- Integration with external search (Tavily) for additional resources when needed
- Support for various resource types (tutorials, courses, documentation, etc.)

Notes on agent behavior:
- Skill agent returns a JSON string (not a Python dict/object). It prefers the internal catalog and will only search the web sparingly.
- Coordinator agent also formats its final answer as a JSON string and can call a lightweight internal "json" tool as a guardrail.
- Opportunity agent surfaces mentor emails when available—API responses include them when the tool finds a match.

### Mentorship Matching
- Find mentors within the organization based on improvement areas
- Vector similarity matching between user improvements and other users' strengths
- AI-powered selection of best mentor matches
- Support for multiple improvement areas with individual mentor recommendations

### Safety and Security
- Bias and hate speech filtering in feedback using ML models
- Prompt injection detection for user inputs
- PII (Personal Identifiable Information) redaction from prompts
- Safe processing of all AI agent interactions

### Performance & Caching
- Comprehensive caching system for improved response times
- Database-backed cache storage for persistence across deployments
- Smart cache invalidation to maintain data consistency
- Optimized timeouts based on data volatility (1 hour to 2 days)
- Reduced API costs through intelligent response caching

## API Documentation

### Endpoints

#### 1. User Authentication
- **URL**: `/api/login/`
- **Method**: `POST`
- **Description**: Authenticates a user with email and password.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "userpassword"
  }
  ```
- **Response**:
  - Success (200): `{"message": "Authentication successful."}`
  - Error (400): `{"error": "Email and password are required."}`
  - Error (401): `{"error": "Invalid password."}`
  - Error (404): `{"error": "User not found."}`

#### 2. Add Feedback
- **URL**: `/api/add-feedback/`
- **Method**: `POST`
- **Description**: Adds a new feedback item to a user's feedback list.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "feedback": "Your feedback text here"
  }
  ```
- **Response**:
  - Success (200): `{"message": "Feedback added successfully"}`
  - Error (400): `{"error": "email and feedback are required"}`
  - Error (404): `{"error": "User not found"}`

#### 3. Classify Feedback
- **URL**: `/api/classify-feedback/`
- **Method**: `POST`
- **Description**: Classifies all feedback items for a user into strengths and improvements using AI.
- **Request Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response**:
  - Success (200):
    ```json
    {
      "classified_feedback": {
        "strengths": ["List of strengths"],
        "improvements": ["List of improvements"]
      }
    }
    ```
  - Error (400): `{"error": "email is required"}`
  - Error (404): `{"error": "User not found"}` or `{"error": "No feedbacks found for this user"}`

#### 4. Summarise Feedback
- **URL**: `/api/summarise-feedback/`
- **Method**: `POST`
- **Description**: Provides a comprehensive summary of user feedback including classification and actionable insights.
- **Request Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response**:
  - Success (200):
    ```json
    {
      "summary": {
        "strengths": ["List of strengths"],
        "improvements": ["List of improvements"],
        "strengths_insights": ["Actionable insights based on strengths"],
        "improvements_insights": ["Actionable insights based on improvements"],
        "growth_tips": ["Helpful growth tips derived from the feedback"]
      }
    }
    ```
  - Error (400): `{"error": "email is required"}`
  - Error (404): `{"error": "User not found"}` or `{"error": "No feedbacks found for this user"}`

#### 5. Create Onboarding Item
- **URL**: `/api/onboard/create/`
- **Method**: `POST`
- **Description**: Creates a new onboarding catalog item for job roles with associated checklists and resources.
- **Request Body**:
  ```json
  {
    "title": "Software Engineer",
    "specialization": "Backend",
    "tags": ["python", "django", "api"],
    "checklist": ["Collect laptop from IT", "Complete coding assessment", "Review company policies", "Setup development environment"],
    "resources": ["https://docs.djangoproject.com/", "https://www.python.org/", "Backend service map"]
  }
  ```
- **Response**:
  - Success (201): `{"message": "Onboarding item created successfully", "id": 1}`
  - Error (400): `{"error": "title and specialization are required"}` or `{"error": "tags, checklist, and resources must be arrays"}`
  - Error (500): `{"error": "Failed to create onboarding item: [error details]"}`

#### 6. Get Onboarding Information
- **URL**: `/api/onboard/get/`
- **Method**: `POST`
- **Description**: Retrieves personalized onboarding information for an employee based on their job title and specialization using AI-powered semantic search.
- **Request Body**:
  ```json
  {
    "email": "employee@example.com",
    "additional_prompt": "focus on the analytics part" // Optional
  }
  ```
- **Response**:
  - Success (200):
    ```json
    {
      "checklist": ["Complete coding assessment", "Setup development environment", "Review project documentation"],
      "resources": ["https://docs.djangoproject.com/", "Internal wiki", "Team onboarding guide"],
      "explanation": "Customized onboarding plan based on your role as Backend Developer"
    }
    ```
  - Error (400): `{"error": "Email is required"}`
  - Error (404): `{"error": "Employee not found"}`
  - Error (500): `{"error": "Failed to run onboard agent: [error details]"}`

#### 7. Create Skill Item
- **URL**: `/api/create-skill/`
- **Method**: `POST`
- **Description**: Creates a new skill catalog item with learning resources.
- **Request Body**:
  ```json
  {
    "title": "Python Programming",
    "tags": ["python", "programming", "beginner"],
    "type": "tutorial",
    "url": "https://example.com/python-tutorial"
  }
  ```
- **Response**:
  - Success (201): `{"message": "Skill item created successfully", "id": 1}`
  - Error (400): `{"error": "title, type, and url are required"}` or `{"error": "tags must be an array"}`
  - Error (500): `{"error": "Failed to create skill item: [error details]"}`

#### 8. Get Skill Recommendations
- **URL**: `/api/get-skill-recommendations/`
- **Method**: `POST`
- **Description**: Provides personalized skill development recommendations based on user context and query using AI-powered semantic search.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "skill_query": "improve my data analysis skills"
  }
  ```
- **Response**:
  - Success (200):
    ```json
    {
      "skills": [
        {
          "title": "Data Analysis with Python",
          "description": "Learn data analysis techniques using Python",
          "learning_outcomes": ["Understand pandas", "Create visualizations"],
          "resources": [
            {
              "title": "Python Data Science Handbook",
              "url": "https://example.com/handbook",
              "type": "book"
            }
          ]
        }
      ],
      "explanation": "Recommendations based on your role and improvement areas"
    }
    ```
  - Error (400): `{"error": "skill_query is required"}`
  - Error (500): `{"error": "Failed to get skill recommendations: [error details]"}`

#### 9. Find Mentors
- **URL**: `/api/find-mentors/`
- **Method**: `POST`
- **Description**: Finds potential mentors within the organization whose strengths match the user's improvement areas.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "top_k": 3
  }
  ```
- **Response**:
  - Success (200) - Mentors found:
    ```json
    {
      "mentors": [
        {
          "email": "mentor@example.com",
          "job_title": "Senior Developer",
          "specialization": "Backend",
          "strengths": ["Leadership", "Technical expertise"],
          "can_help_with": "communication skills",
          "llm_reason": "Strong match for improvement area"
        },
        {
          "can_help_with": "communication skills",
          "no_good_mentor": true,
          "llm_reason": "No strong mentor found for this improvement"
        }
      ]
    }
    ```
  - Error (400): `{"error": "Email is required."}` or `{"error": "top_k must be a positive integer."}`
  - Error (404): `{"error": "User not found."}`
  - Error (500): `{"error": "Failed to find mentors: [error details]"}`

#### 10. Coordinator Ask
- **URL**: `/api/coordinator-ask/`
- **Method**: `POST`
- **Description**: Processes a user query using the coordinator agent to provide coordinated responses with action items and resources.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "query": "What skills should I develop for my role?"
  }
  ```
- **Response**:
  - Success (200):
    ```json
    {
      "message": "Based on your role as a Backend Developer, you should focus on improving your API design skills and learning about microservices architecture.",
      "action_items": ["Complete the API Design course", "Review microservices documentation"],
      "resources": ["API Design Best Practices Guide", "Microservices Architecture Tutorial"]
    }
    ```
  - Error (400): `{"error": "Email and query are required."}`
  - Error (404): `{"error": "User not found."}`
  - Error (500): `{"error": "Failed to process query: [error details]"}`

## Models

### APIUser
- **email**: Unique email field (used as username)
- **job_title**: Job title of the employee
- **specialization**: Specialization within the job title
- **feedbacks**: Array of feedback strings
- **strengths**: Array of strength strings (derived from feedback)
- **improvements**: Array of improvement strings (derived from feedback)
- **strengths_vector**: Vector embedding for strengths (used for mentor matching)

### OnboardCatalog
- **title**: Job title
- **specialization**: Specialization within the job title
- **tags**: Array of relevant tags
- **checklist**: Array of onboarding checklist items
- **resources**: Array of resource URLs or descriptions
- **title_vector**: Vector embedding for title
- **specialization_vector**: Vector embedding for specialization
- **tags_vector**: Vector embedding for tags

### SkillCatalog
- **title**: Skill title
- **tags**: Array of relevant tags
- **type**: Resource type (e.g., tutorial, course)
- **url**: Resource URL
- **title_vector**: Vector embedding for title
- **tags_vector**: Vector embedding for tags
- **type_vector**: Vector embedding for type

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL with pgvector extension
- Django 5.2+
- Required Python packages (see requirements.txt)

### Environment Variables
Create a `.env` file. At minimum, point Django at your Postgres instance and set a secret key. Model names are optional overrides.

```
# Django
DEBUG=False
SECRET_KEY=change-me

# Database
DB_ENGINE=django.db.backends.postgresql
DB_HOST=your-postgres-host
DB_PORT=6543
DB_NAME=postgres
DB_USER=your-db-user
DB_PASSWORD=your-db-password

# Optional model overrides
CORDINATOR_MODEL=groq:openai/gpt-oss-120b
FEEDBACK_MODEL=groq:llama-3.1-8b-instant
OPPORTUNITY_MODEL=groq:llama-3.1-8b-instant
ONBOARD_MODEL=groq:qwen/qwen3-32b
SKILL_MODEL=groq:openai/gpt-oss-20b

# Optional external services
TAVILY_API_KEY=...
HF_TOKEN=...
```

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Create cache table (first time only): `python manage.py createcachetable`
4. Create superuser: `python manage.py createsuperuser`
5. Start the server: `python manage.py runserver`

### Database Setup
The application uses PostgreSQL with the pgvector extension for vector similarity search. Ensure pgvector is installed and enabled in your database.

If you're using Django's database cache (default here), create the cache table once:

- Locally: `python manage.py createcachetable`
- In Docker: see the Docker section below for a one-liner.

## Run with Docker

Docker is the fastest way to try this backend. The image downloads HF models at build time, so the first build can take a few minutes.

1) Put your `.env` next to `docker-compose.yml` (see the Environment Variables section).

2) Build and start:

```powershell
docker compose up --build
```

This will run database migrations and start Gunicorn on port 8000. Visit http://localhost:8000.

3) First-time cache table (one-time):

```powershell
docker compose exec web python manage.py createcachetable
```

4) Create an admin user (optional):

```powershell
docker compose exec web python manage.py createsuperuser
```

Notes
- The container uses Gunicorn with 3 workers, 2 threads each, preload on. Adjust in `docker-compose.yml` if needed.
- This setup expects an external Postgres instance; the compose file does not start a database.

### Caching Configuration
The application implements comprehensive caching to improve performance and reduce redundant API calls:

#### Django Cache Setup
- Backend: Database cache using PostgreSQL table `django_cache`
- Purpose: Stores cached responses and agent results
- Setup: Run `python manage.py createcachetable` once (or the Docker equivalent)

#### Agent-Level Caching
Most agent/tool results are cached for ~2 days (172,800 seconds) to keep things snappy:

- Coordinator: final responses
- Feedback: classifications and generated insights
- Onboarding: plans and semantic search results
- Skill: recommendations and external search results
- Opportunity: mentor matching and selection details

#### API-Level Caching
Read-heavy endpoints use view-level caching:

- **Coordinator Ask**: 2 days
- **Get Onboarding Information**: 2 days
- **Get Skill Recommendations**: 2 days
- **Find Mentors**: 2 days
- **Classify Feedback**: 2 days
- **Summarize Feedback**: 2 days

#### Cache Invalidation
Hints:

- Adding feedback will invalidate related feedback caches.
- Expired entries are removed automatically by Django.
- Cache keys are structured to allow targeted invalidation if needed.

#### Performance Benefits
- **Faster Response Times**: Duplicate queries served from cache in milliseconds
- **Reduced API Costs**: Fewer calls to external AI services (Groq, HuggingFace)
- **Improved User Experience**: Consistent response times for repeated queries
- **Scalability**: Reduced server load during peak usage

Cache timeouts are optimized based on data volatility - frequently changing data (like feedback) uses shorter timeouts, while stable data (like skill recommendations) uses longer timeouts.

## Admin & Access

There are no default credentials. Create an admin locally or in Docker:

```powershell
# Local
python manage.py createsuperuser

# Docker
docker compose exec web python manage.py createsuperuser
```