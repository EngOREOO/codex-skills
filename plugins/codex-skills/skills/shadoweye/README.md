# ShadowEye — OSINT Intelligence Skill for opencode

**See the unseen. Find the unfound. Know the unknown.**

ShadowEye is an elite OSINT intelligence engine that automatically gathers intelligence on targets using photos, names, emails, usernames, and domains. It runs as an auto-loaded skill in opencode — just provide input and it executes the full intelligence pipeline.

---

## What ShadowEye Does

### Photo Analysis
- **Face feature extraction** — Gender, age, hair, facial hair, glasses, skin tone, distinguishing features
- **EXIF data extraction** — GPS coordinates, camera info, timestamps
- **Social media discovery** — Searches Facebook, Instagram, Twitter, LinkedIn, GitHub via websearch
- **Reverse image search guidance** — Provides manual upload links for Google Lens, TinEye, FaceCheck, Yandex, PimEyes

### People Search
- **Name to profiles** — Finds social media accounts by name
- **Username enumeration** — Checks 400+ platforms for username availability
- **Email discovery** — Generates and verifies email patterns
- **Breach check** — Checks if email appears in known data breaches

### Domain Recon
- **DNS enumeration** — A, MX, TXT, NS records
- **Subdomain discovery** — Uses subfinder/amass for enumeration
- **Technology detection** — Fingerprints server stack

---

## How It Works

ShadowEye uses a **practical approach** that works within tool limitations:

### ✅ What Works
| Tool | Usage |
|------|-------|
| `websearch` | Finding search results, social profiles, news articles |
| `webfetch` | GitHub repos, Shodan, individual non-blocked pages |
| `bash` | EXIF extraction, DNS enumeration, username tools |

### ❌ What's Blocked
| Target | Issue |
|--------|-------|
| Google via webfetch | Returns CAPTCHA/error page |
| Facebook via webfetch | Returns 400 error |
| Instagram/Twitter via webfetch | Returns 403/redirect |

### 🔄 Manual Workflow (Reverse Image Search)
Reverse image search cannot be done programmatically. ShadowEye provides **direct upload links** for:
- **Google Lens** — Best for faces
- **TinEye** — Best for exact matches
- **FaceCheck.id** — Best for face recognition
- **Yandex Images** — Best for non-Western faces
- **PimEyes** — Premium face search

---

## Installation

ShadowEye is auto-loaded by opencode. No manual installation needed.

### Manual Setup (if needed)
```bash
# Clone the skill
git clone https://github.com/EngOREOO/ShadowEye---OSINT-Skill.git ~/.agents/skills/shadoweye

# Or create symlink
ln -s /path/to/ShadowEye---OSINT-Skill ~/.agents/skills/shadoweye
```

---

## Usage

### Automatic (Recommended)
Just provide a photo, name, email, or username — ShadowEye auto-executes:

```
# Photo analysis
[attach photo] → ShadowEye runs full pipeline automatically

# Name search
"Find info about Ahmed Al-Saud" → ShadowEye searches all platforms

# Email lookup
"Check ahmed@gmail.com" → ShadowEye does breach check + social profiles

# Username search
"@ahmed_s" → ShadowEye enumerates across platforms
```

### Via Command
```bash
/osint analyze this person [name or photo]
```

---

## Example Output

```markdown
# ShadowEye Intelligence Report

## Target: Young man with short dark hair, beard, brown skin
**Generated:** 2026-07-16
**Confidence:** MEDIUM

---

## APPEARANCE ANALYSIS
| Feature | Value |
|---------|-------|
| Gender | Male |
| Age Range | Young (18-25) |
| Hair Color | Dark/Black |
| Hair Style | Short |
| Facial Hair | Beard |
| Glasses | No |
| Skin Tone | Brown |

## SEARCH RESULTS
| Platform | Query | Key Findings |
|----------|-------|--------------|
| Facebook | site:facebook.com "short dark hair" "beard" | 5 profiles matched |
| Instagram | site:instagram.com "short dark hair" | 12 profiles found |
| LinkedIn | site:linkedin.com "Ahmed" | 3 profiles found |

## REVERSE IMAGE SEARCH INSTRUCTIONS
| Service | URL | Notes |
|---------|-----|-------|
| Google Lens | lens.google.com | Upload photo here |
| TinEye | tineye.com | For exact matches |
| FaceCheck.id | facecheck.id | For face recognition |

## CONFIDENCE SCORE: 6/10
## RISK LEVEL: LOW
```

---

## Intelligence Capabilities

### Social Media Coverage
- Facebook (profiles, photos, groups)
- Instagram (profiles, hashtags)
- Twitter/X (profiles, tweets)
- LinkedIn (professional profiles)
- TikTok (profiles)
- YouTube (channels, videos)
- Reddit (profiles, posts)
- GitHub (repositories, commits)

### Data Sources
- Google search (via websearch tool)
- Shodan (internet-wide scanning)
- Have I Been Pwned (breach data)
- crt.sh (certificate transparency)
- DNS records (domain intel)

---

## Limitations

### Tool Constraints
- `webfetch` blocked by Google/Facebook/Instagram/Twitter
- Reverse image search requires manual upload
- Cannot perform facial recognition programmatically
- Limited to publicly available information

### Workarounds
- Use `websearch` instead of `webfetch` for search engines
- Provide manual upload links for reverse image search
- Guide user through each step if needed

---

## Ethical Guidelines

### ✅ Allowed
- Search public information only
- Stay within authorized scope
- Document everything with sources
- Report through proper channels
- Respect rate limits

### ❌ Prohibited
- Access unauthorized systems
- Use stolen credentials
- Social engineer without consent
- Access private accounts
- Share findings publicly

---

## Files

```
~/.agents/skills/shadoweye/
├── SKILL.md      # Auto-execution instructions for opencode
├── README.md     # This file
└── LICENSE       # MIT License
```

---

## License

MIT License — Use freely, attribute appreciated.

---

## Contributing

Contributions welcome! Submit PRs to improve:
- New platform coverage
- Better search strategies
- Improved output formatting
- Tool integration

---

**ShadowEye sees what others miss.**
