# AI Ascent Backend

The API Backend for AI Ascent SAP Hackathon.

## API Documentation

### Endpoints

#### 1. Add Feedback
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

#### 2. Classify Feedback
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

## Agents

The backend uses AI agents powered by LangChain for processing feedback.

### Feedback Agent
- **Purpose**: Classifies user feedback into strengths and improvements.
- **How it works**:
  - Uses a structured output model to categorize feedback.
  - Filters out biased feedback (related to gender, race, ethnicity, age, religion, disability, nationality, or culture) and neutral feedback.
  - Returns concise, bulleted lists of strengths and areas for improvement.
  - Utilizes a language model specified by the `FEEDBACK_MODEL` environment variable.

### Coordinator Agent
- **Purpose**: A general-purpose agent for coordination tasks (currently not integrated into the API endpoints).
- **How it works**:
  - Initialized with a language model specified by the `CORDINATOR_MODEL` environment variable.
  - Uses a structured chat zero-shot react description agent type.
  - Designed for handling complex tasks with no predefined tools (tools list is empty).
  - Can be extended for future features requiring multi-step reasoning or coordination.

### Supabase Settings
(TO BE REMOVED IF MAKING THE REPO PUBLIC)

- Org and Project Name: AI Ascent Backend
- Password: AIAscent2025

### LangChain Model Setting

You can use "provider:model" as a shorthand instead of providing two seperate args to the chat model init. This way we can easily swap later too.

### Admin Username and Password

- Username (Email): admin@admin.com
- Password: Admin123