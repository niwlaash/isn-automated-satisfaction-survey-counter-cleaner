# ISN Automated Satisfaction Survey Response Counter

This tool automates the process of counting and categorizing responses from the **2026 Athletes and Coaches Satisfaction Survey**. It maps raw survey data into a clean, flat table ready for review and analysis.

## Features
- **Professional Organization**: Clean folder structure for data and results.
- **Explicit Sport List Matching**: Uses `instruction2.md.resolve` as the source of truth.
- **"Others Review" Sheet**: Captures unmatched responses for manual review.
- **Virtual Environment Integration**: Ready to run in an isolated environment.

## Prerequisites
- Python 3.10+

## Folders
- **`/raw_data`**: Place your input survey respondent file and original template file here.
- **`/output`**: The generated `Processed_Survey_Update_2026.xlsx` will appear here.
- **`/scripts_and_docs`**: Historical instructions and maintenance scripts.

## Setup & Running
1.  **Initialize Environment** (only first time):
    ```powershell
    python -m venv venv
    .\venv\Scripts\python -m pip install pandas openpyxl
    ```
2.  **Run Automation**:
    ```powershell
    .\venv\Scripts\python survey_counter.py
    ```

## Maintenance Guide
- **Updating Sports**: Edit the list in `instruction2.md.resolve`. The script will automatically update the summary to match.
- **"Others" Check**: Always review the `Others_Review` sheet in the output file to ensure no valid sports were missed due to typos in the survey.
