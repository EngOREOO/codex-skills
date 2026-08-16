# X Feed Intel (harvested 2026-08-04 from @xxx_toxic_off)

Distilled from 754 distinct security retweets to speed up finding-matching and
report-writing for active Bugcrowd programs (JET, myfitnesspal, iFood, Rapyd).

## Dominant themes (count of retweets)
- AI/ML security — 249
- CVE / 0-day disclosures — 114
- SSO / authentication logic — 76
- XSS — 56
- Recon / enumeration — 45
- SQL injection — 36
- Cloud / infra (AWS, S3, k8s) — 34
- IDOR / access control — 22
- Mobile (Android/iOS/APK) — 14
- Subdomain takeover (CNAME/CloudFront/Heroku) — 11
- SSRF — 10

## Researcher sources to mine
@tom_doerr, @viehgroup, @alghali, @7h3h4ckv157, @Abdullah4AI, @0x0SojalSec,
@cnemalek, @lostsec_, @suslu7616, @DarkWebInformer, @luckyhacker43,
@JulianGoldieSEO, @jameswt, @bbr_bug (Bug Bounty Insights).

## High-signal writeup techniques (reusable)
- AI system-prompt leak via a Burp config (tinopreter, $1,500).
- Missing-check API authorization flaw → full account control (Hun33er, €5,000).
- 30-min blind XSS to admin panel (zhenwarx, $6,500).
- SSO cookie set with `domain=.parent.com` → every subdomain an attack surface;
  enumerate unclaimed CNAMEs (CloudFront/Heroku/GH Pages/S3), claim, leak cookie
  (Uber #219205).
- Authorization bypass in a private program ($300, ameensec).
- Account takeover via insecure email-change flow (0xalr).
- Weak credentials after deep recon → admin panel (ro0od).

## Tooling feeds
DroidHunter (mobile), Burp-MCP-Unrestricted (RamanMG), Gemini-api-key-hunter &
Google-api-key-scanner (coffinxp), exfil-scan (vikasudasi), ADeleginator
(techspence), tlosint-vm (tracelabs), SOCKSRelayd, reverse-skill, PrivFu
(daem0nc0re), native: CVE RC PoCs for Langflow/DB/MariaDB/Rails ActiveStorage.

## Apply-to-program mapping
- **iFood** (focus: user info leakage, checkout, fraud): API authz missing-check
  w/u ($5,000) → high-value pattern for /v1|v2/developers|apps|teams IDOR;
  AI-search endpoints → system-prompt-leak pattern.
- **JET/JE-1**: SSO/session-cookie + subdomain ecosystem patterns vs the
  `lunarct.online` surface; unclaimed-CNAME angle if any.
- **MFP**: IDOR/access-control + account takeover (email-change) patterns.