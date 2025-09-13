# AI Ascent Backend

The API Backend for AI Ascent SAP Hackathon.

## Table of Contents
- [Features](#features)
- [Agents](#agents)
- [API Documentation](#api-documentation)
- [Models](#models)
- [Setup](#setup)
- [Supabase Settings](#supabase-settings)
- [Admin Username and Password](#admin-username-and-password)

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

## Agents

The backend uses AI agents powered by LangChain for various processing tasks.

### Feedback Agent
- **Purpose**: Processes and analyzes user feedback to provide classification and actionable insights.
- **Features**:
  - **Classification**: Categorizes feedback into strengths and improvements using sentiment analysis, filtering out biased content.
  - **Insights Generation**: Creates actionable insights from classified feedback and provides growth tips.
  - **Bias Filtering**: Uses ML models to remove discriminatory or biased feedback.
- **How it works**:
  - Uses structured output models with Pydantic for consistent responses.
  - Employs a pipeline approach: first classifies feedback, then generates insights.
  - Filters feedback for bias using HuggingFace models.
  - Utilizes language models specified by the `FEEDBACK_MODEL` environment variable with temperature 0.0 for consistency.

### Onboard Agent
- **Purpose**: Provides personalized onboarding information using semantic search and AI reasoning.
- **Features**:
  - **Semantic Search**: Uses vector embeddings to find similar job titles, specializations, and tags.
  - **Intelligent Matching**: Combines multiple search strategies to find the most relevant onboarding content.
  - **Dynamic Content Generation**: Creates customized onboarding plans when exact matches aren't found.
- **How it works**:
  - Utilizes HuggingFace embeddings for vector similarity search on job titles, specializations, and tags.
  - Employs a tool-calling agent with specialized search tools.
  - Searches for similar jobs using cosine distance on vector fields.
  - Compiles information from multiple similar roles to generate comprehensive onboarding materials.
  - Returns structured JSON with checklists, resources, and explanations.
  - Uses the language model specified by the `ONBOARD_MODEL` environment variable.

### Skill Agent
- **Purpose**: Provides personalized skill development recommendations using semantic search and external resources.
- **Features**:
  - **Semantic Search**: Uses vector embeddings to find relevant skills and resources.
  - **Personalization**: Incorporates user feedback insights for tailored recommendations.
  - **External Integration**: Uses Tavily search for additional resources when catalog is insufficient.
  - **Structured Output**: Returns organized skill recommendations with resources and learning outcomes.
- **How it works**:
  - Utilizes vector fuzzy search on skill titles, types, and tags.
  - Employs a tool-calling agent with search and retrieval tools.
  - Considers user context (job title, specialization) and feedback insights.
  - Returns JSON with skills array containing titles, descriptions, learning outcomes, and resources.
  - Uses the language model specified by the `SKILL_MODEL` environment variable.

### Opportunity Agent
- **Purpose**: Matches users with mentors based on improvement areas and organizational talent retention.
- **Features**:
  - **Mentor Matching**: Finds users whose strengths match others' improvement areas using vector similarity.
  - **AI Selection**: Uses LLM to select the best mentor from candidates.
  - **Multiple Improvements**: Handles multiple improvement areas with individual mentor recommendations.
- **How it works**:
  - Computes vector embeddings for user improvement areas.
  - Finds similar user strengths using cosine distance.
  - Uses structured LLM output to select best mentor matches.
  - Returns detailed mentor information with reasoning.
  - Uses the language model specified by the `OPPORTUNITY_MODEL` environment variable.

### Safety Agent
- **Purpose**: Ensures safe and appropriate processing of all user inputs and content.
- **Features**:
  - **Bias Detection**: Filters hate speech and discriminatory content in feedback.
  - **Prompt Safety**: Detects and prevents prompt injection attacks.
  - **PII Redaction**: Removes personal information from prompts before processing.
- **How it works**:
  - Uses HuggingFace models for hate speech classification and prompt injection detection.
  - Applies regex-based PII redaction for emails and phone numbers.
  - Integrates safety checks throughout the application.

### Coordinator Agent
- **Purpose**: A general-purpose agent for coordination tasks (currently not integrated into the API endpoints).
- **How it works**:
  - Initialized with a language model specified by the `CORDINATOR_MODEL` environment variable.
  - Uses a structured chat zero-shot react description agent type.
  - Designed for handling complex tasks with no predefined tools (tools list is empty).
  - Can be extended for future features requiring multi-step reasoning or coordination.

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

### OpenRole - Not integrated yet tho
- **title**: Job title for open position
- **specialization**: Specialization for the role
- **skills**: Array of required skills
- **description**: Job description
- **level**: Experience level (e.g., Junior, Senior)
- **salary_min**: Minimum salary
- **salary_max**: Maximum salary
- **title_vector**: Vector embedding for title
- **specialization_vector**: Vector embedding for specialization
- **skills_vector**: Vector embedding for skills
- **description_vector**: Vector embedding for description
- **aggregate_vector**: Combined vector for overall matching

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL with pgvector extension
- Django 5.2+
- Required Python packages (see requirements.txt)

### Environment Variables
Create a `.env` file with the following variables:
```
FEEDBACK_MODEL=your-feedback-model
ONBOARD_MODEL=your-onboard-model
SKILL_MODEL=your-skill-model
OPPORTUNITY_MODEL=your-opportunity-model
CORDINATOR_MODEL=your-coordinator-model
TAVILY_API_KEY=your-tavily-api-key
HF_TOKEN=your-huggingface-token
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Create superuser: `python manage.py createsuperuser`
5. Start the server: `python manage.py runserver`

### Database Setup
The application uses PostgreSQL with the pgvector extension for vector similarity search. Ensure pgvector is installed and enabled in your database.

## Supabase Settings
(TO BE REMOVED IF MAKING THE REPO PUBLIC)

- Org and Project Name: AI Ascent Backend
- Password: AIAscent2025

## Admin Username and Password

- Username (Email): admin@admin.com
- Password: Admin123