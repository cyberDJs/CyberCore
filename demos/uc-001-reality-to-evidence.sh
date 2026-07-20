#!/usr/bin/env bash
set -euo pipefail

pause() {
  sleep "${1:-1}"
}

run() {
  printf '\n\033[1;36m$ %s\033[0m\n' "$1"
  pause 0.8
}

clear
printf '\033[1;33mCYBERCORE — UC-001: REALITY TO EVIDENCE\033[0m\n'
printf 'Synthetic demonstration. No production systems are contacted.\n'
pause 1.5

run 'cybercore doctor'
printf 'CyberCore runtime: \033[32mready\033[0m\n'
printf 'Repository: \033[32mclean\033[0m\n'
printf 'Mutation policy: \033[33mhuman approval required\033[0m\n'
pause 1.6

run 'cybercore observe demo/fixtures/web-stack'
printf 'Observed entities:       4\n'
printf 'Observed relationships:  5\n'
printf 'Evidence records:        9\n'
printf 'Observation ID:          OBS-0001\n'
pause 1.8

run 'cybercore explain service:web'
printf 'State:       \033[31mdegraded\033[0m\n'
printf 'Reason:      reverse proxy depends on an unhealthy upstream\n'
printf 'Confidence:  0.94\n'
printf 'Evidence:    EV-0001, EV-0004, EV-0007\n'
pause 2

run 'cybercore plan service:web'
printf 'Decision candidate: restart upstream application\n'
printf 'Risk:               low\n'
printf 'Automatic execution: \033[31mblocked\033[0m\n'
printf 'Approval required:    \033[33myes\033[0m\n'
pause 2

printf '\n\033[1;32mReality -> Evidence -> Knowledge -> Governed decision\033[0m\n'
printf 'No mutation was executed.\n'
pause 2
