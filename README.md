# Soulful Journey

Soulful Journey is a travel web application that shows popular places in India,
allows users to read and write blogs, and chat with an AI travel guide.

## Features
- User login and registration
- Travel blogs with likes
- Places data from database
- AI chat using Gemini API

## Tech Used
- Python (Flask)
- MySQL
- HTML, CSS, JavaScript
- Google Gemini API

### Live Website
https://soulful-journey-backend.onrender.com

## How to Run Locally

1. Clone the repo
```bash
git clone https://github.com/Vedanshu1428/soulful-journey-.git
```

2. Go inside the project folder
   ```bash
   cd soulful-journey-
   ```

3. Create a .env file
   ```bash
   DB_URI=your_database_uri
   GEMINI_API_KEY=your_api_key
   ```
   
4. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

5. Run the server
   ```bash
   python server.py
   ```
