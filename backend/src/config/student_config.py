"""
Student Configuration
This file contains the list of schools, grades, and sections available for student login.
Edit this file to add/remove schools or sections as needed.
"""

# List of schools (easily editable)
SCHOOLS = [
    "JNV Palghar",
    "School A",
    "School B",
]

# Grades (3 to 10)
GRADES = list(range(3, 13))  # [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

# Sections (optional - students can choose or leave blank)
SECTIONS = ["A", "B", "C", "D", "E", "F"]

# Validation constraints
MIN_ROLL_NUMBER = 1
MAX_ROLL_NUMBER = 1000000000000
