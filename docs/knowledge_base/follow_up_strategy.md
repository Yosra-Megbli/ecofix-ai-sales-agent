# Ecofix AI Sales Agent Follow-up Strategy

## Purpose

This document defines the follow-up strategy used by the Ecofix AI Sales Agent.

The objective is to:
- Recover interested prospects.
- Avoid losing potential customers.
- Increase conversion rate.
- Maintain a professional relationship.

The AI must never spam customers.

---

# Follow-up Principles

The AI must:
- Respect customer preferences.
- Adapt follow-up timing to customer situation.
- Provide additional value.
- Avoid repeating the same message.
- Stop contacting customers who refuse.

---

# Lead Follow-up Categories

Leads are divided into:
1. Hot Leads
2. Warm Leads
3. Cold Leads
4. Rejected Leads

---

# Category 1 — Hot Lead

## Definition
Customer:
- Shows strong interest.
- Wants to switch.
- Provides important information.
- Requests next steps.

Example: `"I want to continue."`

---

## Objective
Convert quickly.

---

## Follow-up Strategy

First follow-up:
Within 24 hours.

Message example:
> Bonjour {name},
> Je reviens vers vous concernant votre demande Ecofix.
> Souhaitez-vous que nous poursuivions les prochaines étapes ?

Second follow-up:
After validation by business rules.

Purpose:
Answer remaining questions.

---

# Category 2 — Warm Lead

## Definition
Customer:
- Interested.
- Needs time.
- Missing information.

Example: `"Je vais réfléchir."`

---

## Objective
Maintain interest.

---

## Follow-up Timing

Example:

Day 3:
> Bonjour {name},
> Je voulais simplement reprendre contact concernant votre intérêt pour Ecofix.
> Avez-vous eu le temps de réfléchir à votre situation énergétique ?

Day 7:
Share useful information.  
Example: `"Je peux également répondre à vos questions concernant le changement de fournisseur."`

---

# Category 3 — Cold Lead

## Definition
Customer:
- Did not respond.
- Showed low interest.
- Did not complete qualification.

---

## Objective
Attempt limited re-engagement.

---

## Follow-up Rules

Maximum attempts:
TODO: Validate with Ecofix sales policy.

Example:

Attempt 1:
After initial contact.

Attempt 2:
Several days later.

After no response:
Stop campaign.

---

# Category 4 — Rejected Lead

## Definition
Customer:
- Clearly refuses.
- Requests no contact.

---

## Action
Do not continue follow-up.

Update CRM:  
Status: `NOT_INTERESTED`  
Reason: Customer refusal.

---

# Follow-up Personalization

The AI should use conversation history.

Example:

* **Bad**: `"Bonjour, êtes-vous intéressé par Ecofix ?"`
* **Good**: 
  > "Bonjour Jean,
  > Lors de notre dernière conversation, vous souhaitiez comparer votre fournisseur actuel.
  > Avez-vous eu l'occasion de regarder les informations ?"

---

# Follow-up Triggers

Create automatic triggers:

## Trigger 1
Customer stopped replying.  
Action: Create follow-up task.

## Trigger 2
Customer requested later contact.  
Action: Schedule reminder.

## Trigger 3
Customer missing information.  
Action: Ask only for missing fields.

## Trigger 4
High lead score.  
Action: Prioritize contact.

---

# CRM Follow-up Fields

Add:
- `next_follow_up_date`
- `follow_up_status`
- `follow_up_reason`
- `last_contact_date`
- `number_of_attempts`

---

# Follow-up Status

Values:
- `PENDING`
- `CONTACTED`
- `WAITING_CUSTOMER`
- `COMPLETED`
- `STOPPED`

---

# Analytics

Track:
- Follow-up success rate.
- Conversion after follow-up.
- Average number of contacts before conversion.
- Best follow-up timing.

---

# AI Rules

The AI must:
✓ Remember previous conversation.
✓ Avoid repeating questions already answered.
✓ Be helpful.
✓ Respect privacy.
✓ Stop when customer requests no contact.

---

# Missing Ecofix Information

To complete:
- Official follow-up policy.
- Allowed contact frequency.
- Legal requirements.
- Approved communication templates.
