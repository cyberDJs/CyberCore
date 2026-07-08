# Initial Architecture Context

Updated: 2026-07-08

## Known services

- Provider: InterServer
- Domain: eimyherrer.com
- Shared hosting: yes
- VPS: one
- DirectAdmin: expected for shared hosting and VPS
- DNS: InterServer
- Mail: primary use case
- Applications:
  - WordPress
  - Nextcloud
  - Softaculous apps on subdomains

## Current pain points

- Production and development are not separated.
- Deployment has been FTP-first.
- Inventory is not yet machine-readable.
- Secrets management needs formal policy.
- Monitoring and backup status need verification.
