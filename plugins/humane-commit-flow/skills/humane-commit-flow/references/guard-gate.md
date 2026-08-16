# Guard gate

Select guards from the files changed; run every applicable available skill before push.

| Changed work | Guard skill |
| --- | --- |
| Production code | `clean-code-guard` |
| Tests | `test-guard` |
| Documentation, docstrings, API docs | `docs-guard` |
| WordPress | `wp-guard` |
| WooCommerce | `woo-guard` |

Apply repository-specific guards in addition to this table. Invoke guards against the complete outgoing commit range, not only the last commit. Treat high-confidence actionable findings as blocking: fix them, run focused verification again, and repeat the relevant guard. Record unavailable or inapplicable guards explicitly.

After guards pass, run the project's relevant formatter/linter, type checker, tests, and build. Prefer documented project commands. Do not silently weaken the gate because a check is slow; report blockers and ask before excluding a required check.
