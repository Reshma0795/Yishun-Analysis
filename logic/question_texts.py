# logic/question_texts.py

HEALTHCARE_UTILIZATION_QUESTIONS = {
    "Q78": {
        "title": "Private General Practitioner (GP)",
        "question": (
            "In the past 12 months, how many times did you visit a General Practitioner (GP) "
            "in a private clinic / see a doctor at home?"
        ),
        "response_codes": {
            "0": "0 visits",
            "1+": "Number of times (exclude 0)",
            "666": "Unable to recall",
            "777": "Refused",
        },
    },

    "Q85": {
        "title": "Polyclinic doctor visits",
        "question": (
            "In the past 12 months, how many times did you visit a doctor in a polyclinic?"
        ),
        "response_codes": {
            "0": "0 visits",
            "1+": "Number of times (exclude 0)",
            "666": "Unable to recall",
            "777": "Refused",
        },
    },

    "Q91": {
        "title": "Specialist Outpatient Clinic (SOC) visits",
        "question": (
            "In the past 12 months, how many times did you visit a doctor "
            "in a specialist outpatient clinic (SOC)?"
        ),
        "response_codes": {
            "0": "0 visits",
            "1+": "Number of times (exclude 0)",
            "666": "Unable to recall",
            "777": "Refused",
        },
    },

    "Q93": {
        "title": "Emergency Department (ED) visits",
        "question": (
            "In the past 12 months, how many times have you had Emergency Department (ED) visits?"
        ),
        "response_codes": {
            "0": "0 visits",
            "1+": "Number of times (exclude 0)",
            "666": "Unable to recall",
            "777": "Refused",
        },
    },

    "Q96": {
        "title": "Public hospital admissions",
        "question": (
            "In the past 12 months, how many times have you had public hospital admissions, "
            "including public community hospital admissions?"
        ),
        "response_codes": {
            "0": "0 admissions",
            "1+": "Number of times (exclude 0)",
            "666": "Unable to recall",
            "777": "Refused",
        },
    },

    "Q103": {
        "title": "Private hospital admissions",
        "question": (
            "In the past 12 months, how many times have you had private hospital admissions?"
        ),
        "response_codes": {
            "0": "0 admissions",
            "1+": "Number of times (exclude 0)",
            "666": "Unable to recall",
            "777": "Refused",
        },
    },
}
