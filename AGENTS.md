# Agent instructions

Before every push or publication, inspect the outgoing files and commit metadata
for secrets and private or identifying information. Real hostnames, deployment
addresses, personal emails, usernames, machine names, home paths, and other
personal environment details belong in ignored configuration, never in examples
or documentation. Use reserved example domains and configurable image addresses.

Check author and committer metadata; do not publish identities inferred from a
local machine. Use a deliberate public/noreply or neutral project identity.
Registry and repository owner variables may identify an explicitly selected
publication destination. Recheck the complete outgoing diff before pushing.
