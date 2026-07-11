# Ecofix AI Lead Scoring System

## Purpose

This document defines the lead scoring methodology used by the Ecofix AI Sales Agent.
The objective is to transform conversation data into a measurable qualification score.
The score helps determine:
- Qualified leads
- Follow-up leads
- Low-interest leads

Important:
The AI model must NOT decide the score alone.
The score must be calculated using deterministic business rules.

---

# Lead Score Range

Total score:
0 - 100 points

---

# Qualification Levels

## Qualified Lead
Score: 80 - 100
Definition: The customer shows strong interest and provides enough information to continue the sales process.
Recommended CRM status: QUALIFIED

---

## Follow-up Lead
Score: 50 - 79
Definition: The customer shows interest but some information or decision is missing.
Recommended CRM status: FOLLOW_UP

---

## Low Interest Lead
Score: 0 - 49
Definition: The customer is not ready, refuses, or provides insufficient information.
Recommended CRM status: NOT_QUALIFIED

---

# Scoring Criteria

## Customer Contact Information

### First Name
Points: +5
Reason: Identifies the prospect.

### Last Name
Points: +5
Reason: Improves lead quality.

### Phone Number
Points: +15
Reason: Allows sales follow-up.

### Email
Points: +10
Reason: Allows communication and confirmation.

### Complete Address
Points: +15
Reason: Required for customer identification and energy context.

---

# Energy Information

## Current Supplier Provided
Points: +10
Reason: Helps understand switching opportunity.

## Energy Type Provided
Examples:
- Electricity
- Gas
- Both
Points: +5

## EAN Number Provided
Points: +20
Reason: Strong indicator of real customer intent.

---

# Purchase Intent

## Customer Wants To Compare
Points: +10

## Customer Wants To Switch Supplier
Points: +20

## Customer Requests Next Step
Examples:
- Wants more information
- Wants contract process
- Wants callback
Points: +10

---

# Negative Signals

## Customer Refuses Contact
Points: -30

## Customer Says Not Interested
Points: -20

## Customer Already Signed New Contract
Points: -30

## Fake or Invalid Information
Points: -50

---

# Example Calculation

Customer:
- Name: Provided
- Phone: Provided
- Email: Provided
- Address: Provided
- EAN: Provided
- Wants switching: Yes

Calculation:
- Name: +5
- Phone: +15
- Email: +10
- Address: +15
- EAN: +20
- Switch intention: +20

Total: 85/100
Result: QUALIFIED

---

# CRM Fields Generated

After scoring:
```json
{
  "lead_score": 85,
  "qualification_status": "QUALIFIED",
  "qualification_reason": "Customer interested in switching and provided required information"
}
```

---

# AI Behavior According To Score

## Score >= 80
The AI should:
- Confirm interest.
- Complete missing information.
- Create qualified CRM lead.

## Score 50-79
The AI should:
- Ask remaining questions.
- Schedule follow-up if possible.
- Keep relationship.

## Score < 50
The AI should:
- Remain polite.
- Store conversation if needed.
- Avoid aggressive selling.

---

# Analytics Metrics

The system should track:
- Average lead score
- Number of qualified leads
- Qualification rate
- Score distribution
- Conversion rate by score range

---

# Future Improvements

Possible ML improvements:
- Predict conversion probability.
- Learn from successful sales.
- Identify best conversation patterns.
- Optimize sales script.
