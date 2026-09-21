# Product Requirements Document

## Overview

The Distributed API Health & Incident Monitoring Dashboard helps API owners, deployment-experienced developers, incident responders, and team leads know when an API is unhealthy. It is based on the requirement documents, especially `FR1`–`FR18`, `NFR1`–`NFR18`, `DR1`–`DR7`, and `US-01`–`US-25`.

## Goals and non-goals

Goals: let users register endpoints, run responsible background checks, store results, confirm incidents, send useful alerts, show dashboard/history information, and support secure team work. The platform must be reliable, secure, and maintainable.

Non-goals for the bootstrap: a finished authentication system, all notification providers, multi-region probes, hosted production deployment, and full AI/RAG features.

## Main workflow

Users add endpoint configuration (`FR1`). Background checks evaluate status, timeout, connection/SSL, and later assertions (`FR2`, `FR3`, `FR16`). Results are stored (`FR9`). A threshold prevents a temporary failure from becoming an incident (`FR5`, `DR5`). State changes cause one alert (`FR6`–`FR8`) and recovery updates the incident. Dashboard, history, uptime, and later reports use deterministic stored data (`FR4`, `FR10`, `FR14`, `DR3`).

## Security, access, and AI

Protect stored data and communications (`NFR5`, `NFR6`, `DR2`), maintain audit traces (`NFR15`), and later enforce RBAC (`FR17`). AI can summarize and suggest investigation paths from computed incident facts. It cannot decide health, incidents, or uptime. Any unclear business question remains an open item for the normal requirement process.

## Quality targets

The requirements set targets including failure detection within two minutes for 95% of incidents (`NFR1`), recent data under five seconds (`NFR2`), 99% notification delivery with five-second acknowledgement (`NFR3`), responsible rate limits (`NFR11`), and growth toward 200 active users (`NFR10`). These are targets to measure during feature work, not claims that the bootstrap already meets them.
