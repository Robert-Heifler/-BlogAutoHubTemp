# YouTube to Blogger Automation

This project automates:

- Fetching YouTube videos (with OAuth)
- Using Claude AI for content spinning and summarizing
- Posting spun blog posts to multiple Blogger blogs
- Sending email announcements via Gmail API

---

## Setup

1. Install Python 3.8 or higher.

2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

pip install -r requirements.txt
