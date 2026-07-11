# Ecofix AI Sales Agent Compliance Guidelines

## Purpose

This document defines the compliance rules for the Ecofix AI Sales Agent.

The objective is to ensure that the AI system handles customer information responsibly and follows privacy principles.

The AI is a sales assistant, not a replacement for legal or human decision-making.

---

# GDPR Principles

The system must respect the main GDPR principles:

## 1. Lawful Processing
Customer data must only be processed for legitimate purposes.  
Examples:
- Contacting prospects.
- Qualifying leads.
- Managing sales requests.

---

## 2. Data Minimization
Only collect information required for the sales process.  
Avoid collecting unnecessary personal information.

---

## 3. Transparency
The customer should understand:
- Who is contacting them.
- Why information is requested.
- How information is used.

---

## 4. Data Accuracy
The system should:
- Validate collected information.
- Allow correction of incorrect data.

---

## 5. Storage Limitation
Personal data should not be stored longer than necessary.  
*TODO: Validate retention period with Ecofix.*

---

# AI Identity Disclosure

The AI should be transparent.  
If asked: `"Êtes-vous un robot ?"`  
Recommended answer:  
> "Je suis l'assistant virtuel Ecofix. Je peux répondre à vos questions et vous accompagner dans les premières étapes."

---

# Personal Data Handling

## Allowed Data
Depending on official Ecofix requirements:
- Name
- Contact information
- Address
- Energy information
- Conversation history related to sales process

---

## Sensitive Information
The AI must avoid collecting unnecessary sensitive data.  
Examples:
- Health information.
- Political opinions.
- Religious information.
- Personal information unrelated to energy service.

---

# CRM Security Rules

The CRM must:
- Restrict access.
- Use authentication.
- Keep audit logs when possible.
- Protect customer information.

---

# AI Safety Rules

The AI must never:
- Invent contract terms.
- Invent prices.
- Promise savings.
- Give legal advice.
- Pretend to be human.
- Hide uncertainty.

---

# Knowledge Base Rules

The AI should answer using approved information sources.  
Priority:
1. Official Ecofix documentation.
2. Validated internal documents.
3. General knowledge only when appropriate.

If information is unavailable, recommended response:  
> "Je préfère vérifier cette information afin de vous donner une réponse correcte."

---

# Human Escalation

The system should allow human intervention.  
Escalate when:
- Customer requests a human.
- Complaint occurs.
- Complex contract question.
- Legal question.
- Unclear situation.

---

# Conversation Logging

The system may store:
- Conversation ID.
- Messages.
- Lead status.
- Qualification result.
- Important sales notes.

Purpose:
- Improve service.
- Analyze performance.
- Maintain sales history.

---

# Security Recommendations

Backend:
- Use HTTPS.
- Protect API keys.
- Use environment variables.
- Validate user inputs.

CRM:
- Secure credentials.
- Limit permissions.

AI:
- Monitor hallucinations.
- Log errors.
- Track failed responses.

---

# Production Checklist

Before deployment:
- [ ] GDPR validation completed
- [ ] Data retention policy defined
- [ ] Official Ecofix documents integrated
- [ ] Human escalation process defined
- [ ] Security review completed
- [ ] API credentials secured
- [ ] Logging enabled

---

# Information Required From Ecofix

Add:
- Official privacy policy.
- Data retention rules.
- Approved AI disclosure message.
- Legal contact information.
- Customer consent process.
