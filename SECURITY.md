# Security

Treat packages and plan files as untrusted. The resolver never executes product code.
Do not run it elevated. Keep sources and destinations idle while installing.
It rejects traversal, linked paths, encrypted ZIPs, oversized packages and known binary
installers. Static validation cannot sandbox concurrent hostile filesystem mutations.

For vulnerabilities, use GitHub's private vulnerability reporting if available, or contact
the owner through their GitHub profile without posting exploit details or private content.
Do not attach purchased assets, account data or real library inventories to public issues.
