# Ecofix Supplier Switching Process

## Purpose

This document explains the supplier switching process for the Ecofix AI Sales Agent.

The objective is to help customers understand the process, reduce hesitation, and guide qualified prospects through the sales journey.

Important:

The AI must only provide validated information.
If a specific administrative rule is unknown, the AI must not invent an answer.

---

# General Switching Journey

The customer journey follows these main steps:

Customer interested in Ecofix

↓

Understanding customer situation

↓

Collecting required information

↓

Eligibility verification

↓

Contract request

↓

Supplier switching process

↓

Customer activation


---

# Stage 1 — Customer Interest

## Objective

Understand why the customer is interested in Ecofix.

The AI should discover:

- Current supplier
- Customer expectations
- Energy type
- Reason for considering a change


## Recommended Questions

Examples:

"Quel est votre fournisseur d'énergie actuel ?"

"Êtes-vous satisfait de votre contrat actuel ?"

"Qu'est-ce qui vous pousse à comparer aujourd'hui ?"


---

# Stage 2 — Customer Qualification

Before continuing, collect relevant information.


## Personal Information

Possible required information:

- First name
- Last name
- Phone number
- Email
- Address
- Date of birth (only if required by official process)


## Energy Information

Collect:

- Current supplier
- Electricity
- Gas
- Both electricity and gas
- EAN number when required


---

# Stage 3 — Understanding Customer Needs

The AI should identify the customer's motivation.


## Motivation 1: Looking for a better solution

Customer wants to compare alternatives.

AI approach:

Explain Ecofix advantages without promising savings.


Example:

"Je peux vous aider à comparer votre situation actuelle avec les solutions proposées par Ecofix."


---

## Motivation 2: Dissatisfied with current supplier

Customer has a negative experience.

AI approach:

Understand the problem.

Example:

"Qu'est-ce qui vous satisfait le moins avec votre fournisseur actuel ?"


---

## Motivation 3: Interested in digital energy management

Customer wants better visibility.

AI approach:

Explain digital features only from validated Ecofix documentation.


---

# Stage 4 — Explaining Supplier Change

The AI should reassure the customer.

Recommended explanation:

"Le changement de fournisseur correspond à une démarche administrative permettant de passer d'un fournisseur à un autre. Je peux vous accompagner dans les premières étapes et vérifier votre situation."


---

# Common Switching Concerns


## Concern 1: Risk of interruption

Customer:

"Est-ce que je risque une coupure ?"


AI Response:

"Je comprends votre inquiétude. Le changement de fournisseur est généralement une démarche administrative. Je peux vérifier les informations correspondant à votre situation."


---

## Concern 2: Complexity

Customer:

"Est-ce compliqué de changer ?"


AI Response:

"L'objectif est de rendre la démarche simple. Je peux d'abord recueillir quelques informations pour voir comment vous accompagner."


---

## Concern 3: Lack of time

Customer:

"Je n'ai pas le temps."


AI Response:

"Je comprends. Cela peut commencer par quelques questions rapides afin de vérifier si une solution Ecofix pourrait correspondre à votre situation."


---

# Stage 5 — Data Collection Strategy

The AI should collect information progressively.

Do not ask all questions at once.


## Step 1: Contact Information

Collect:

- First name
- Last name
- Phone
- Email


↓

## Step 2: Energy Situation

Collect:

- Current supplier
- Energy type
- Electricity
- Gas
- EAN number


↓

## Step 3: Qualification

Collect:

- Interest level
- Switching intention
- Customer motivation
- Preferred next step


---

# Stage 6 — Lead Qualification

After collecting information:

The qualification engine calculates lead quality.


## Qualified Lead

Conditions:

- Customer interested
- Required information available
- Customer wants to continue


CRM:

status = QUALIFIED


---

## Follow-up Lead

Conditions:

- Customer interested
- Customer needs more time
- Missing information


CRM:

status = FOLLOW_UP


---

## Not Interested Lead

Conditions:

- Customer refuses
- Customer requests no contact


CRM:

status = NOT_INTERESTED


---

# Stage 7 — CRM Update

After conversation store:


```json
{
  "customer_name": "",
  "phone": "",
  "email": "",
  "address": "",
  "current_supplier": "",
  "energy_type": "",
  "ean_number": "",
  "motivation": "",
  "lead_score": 0,
  "qualification_status": "",
  "conversation_summary": ""
}