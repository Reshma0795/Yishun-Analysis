GI_CONTENT = {
    1: {
        "gi_no": "I",
        "sst_v3": "Healthy",
        "definition": "No more than minimal symptomatic conditions and no asymptomatic conditions that increase risk.",
        "example": "Acute URTI",
        "eligibility": "No self-reported chronic condition\n\nAND\n\nNo indication of long course of decline (see GI IV)",
    },
    2: {
        "gi_no": "II",
        "sst_v3": "Chronic conditions, asymptomatic",
        "definition": "Chronic conditions (not curable once acquired or has persisted >3 months despite treatment) that are asymptomatic, but notable for increasing preventable risk. (If chronic condition-related symptoms that interfere with/restrict normal function are present (at time of assessment), or if unclear whether acute symptoms are chronic condition-related, assign to Category III).",
        "example": "Asymptomatic diabetes",
        "eligibility": "[At least 1 self-reported non-life-threatening chronic condition or elevated blood pressure]\n\nAND\n\n[Did not report any hospital admission for this chronic condition in the last 6 months]\n\nOR\n\nIs not limited by a health problem in activities people usually do",
    },
    3: {
        "gi_no": "III",
        "sst_v3": "Chronic conditions, stable but moderately/ seriously symptomatic or silently severe",
        "definition": "Chronic conditions that are relatively stable but are associated with symptoms that interfere with/restrict usual function or would generally be sufficient to trigger care seeking (e.g., pain, fatigue). Also, include conditions that are silent (relatively asymptomatic) but severe (e.g., chronic kidney disease, malignancy).",
        "example": "Symptomatic Parkinson’s disease",
        "eligibility": "[At least 1 self-reported diagnosed non-life-threatening chronic condition or elevated blood pressure]\n\nAND\n\n[Reported at least one non-life-threatening hospital admission in the last six months]\n\nOR\n\nIs limited by a health problem in activities people usually do\n\nOR\n\n[At least one potentially life-threatening chronic condition\n\nAND\n\n[reported 0-1 potentially life-threatening hospital admission in the last six months\n\nOR\n\nIs not limited by a health problem in activities people usually do]]",
    },
    4: {
        "gi_no": "IV",
        "sst_v3": "Long course of decline",
        "definition": "Long (months to years) dwindling course of loss of reserve in multiple organ systems; typically, elderly. Decline may be characterized by geriatric syndromes (e.g., recurrent falls/gait instability, urinary/bowel incontinence, sleep disorders, poor feeding/malnutrition/inanition, fainting/syncope, dizziness, iatrogenic disorders, pressure ulcers, elder mistreatment, constipation, cognitive impairment [includes dementia, depression, delirium (ever)], frailty [includes decline in functional reserves]) or recurrent exacerbations for multiple co-dominant medical (non-social) conditions.",
        "example": "Frail elderly with dementia",
        "eligibility": "At least 2 of the following conditions:\n\n1) Presence of three or more indicators of frailty (weight loss , indicators of exhaustion on Fried’s scale, low physical activity , slowness  and weakness)\n\n2) Has dementia (reported by proxy)\n\n3) Self-reported 2 or more hospitalization admissions in the last 6 six months for more than one condition (acute or chronic)\n\n4) Is limited by a health problem in activities people usually do\n\n5) AMT score <5 (indicative of cognitive impairment)",
    
    },
    5: {
        "gi_no": "V",
        "sst_v3": "Limited reserve & serious exacerbations",
        "definition": "Single dominant medical (non-social) condition associated with recurrent exacerbations. (Recurrent exacerbations are defined as 3 or more healthcare episodes (e.g., emergency department visits, unplanned hospital admissions, urgent primary care attention) in prior 6 months for the condition, may include episode at time of assessment).",
        "example": "Frequent flares of COPD",
        "eligibility": "Self-reported 2 or more hospital admissions in the last 6 six months for the same potentially life-threatening chronic condition",
    },
}
