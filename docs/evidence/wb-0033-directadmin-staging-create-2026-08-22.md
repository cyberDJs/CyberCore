# WB-0033 DirectAdmin staging-create evidence

Date: 2026-08-22
Work block: `WB-0033`
Target: `staging.eimyherrer.com`
Provider: InterServer shared hosting / DirectAdmin

## Result

`VERIFIED_CREATED`

Observed runtime facts from the operator-executed guarded apply:

- DirectAdmin server: `vda7600.is.cc:2222`
- DirectAdmin user: `eimyherr`
- API login: HTTP 200
- temporary cookie session established: yes
- temporary login key created: no
- create endpoint: `/CMD_SUBDOMAIN`
- create response: HTTP 200
- target existed before: no
- target present on readback: yes
- requested document root: `/domains/staging.eimyherrer.com/public_html`
- observed target document root: `/domains/staging.eimyherrer.com/public_html`
- production document root inspected: no
- production content mutated: no
- application deployed: no
- DirectAdmin session logout: HTTP 200

## Correction to earlier auth observations

Earlier DirectAdmin password-auth probes returned 401 because the operator had entered the InterServer API key at a prompt requesting the DirectAdmin password. Those 401 observations therefore do not establish `api_with_password=no` or an invalid DirectAdmin password.

The separate `/CMD_LOGIN` HTTP 410 observation remains evidence that the legacy login route used by the v2 helper was not valid for this server. The corrected v3 helper used the server-advertised `/api/login` flow and authenticated successfully with the existing DirectAdmin password.

## Remaining gate

The DirectAdmin target is created and isolated, but the immediate public DNS post-check did not resolve `staging.eimyherrer.com` (`dns_after.exists=false`). Public DNS record creation / verification remains pending before the staging URL can be treated as externally reachable.

## Safety assertions

- plaintext credentials recorded: false
- session cookie values recorded: false
- login URL value recorded: false
- production document root inspected: false
- production content mutated: false
- application deployed: false
