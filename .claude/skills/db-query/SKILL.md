---
name: db-query
description: Use when the user wants to run a read-only SELECT query against the project database. Refuses writes.
---

Execute a safe READ-ONLY query against the project database.

The query to run:
<PASTE QUERY HERE>

Rules:
- Always use READ-ONLY queries (SELECT only)
- If the query looks like it would modify data (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE), STOP and ask for confirmation first
- Never print passwords in output
- Format output nicely
