# Name audit: lp-data-foundations (Portfolio Answer Desk)

**Status (2026-10-25):** zero real-organisation names next to synthetic facts after the fixes below. Four close calls were found during the build and renamed, because the names policy in `CLAUDE.md` requires invented names. Remaining residual risk: generated company names use invented syllables and were not each searched. PM to confirm before publishing.

**Policy used:** `context-library/README.md` (names policy section). Public sources stay named and linked.

## Found and replaced (applied during the build, under the names policy)

| Where | Was | Now | Why |
|---|---|---|---|
| `src/answerdesk/world.py`, brief's spelling list | CPG Holdings | Calderwick Holdings | Web search: "CPG International" is a real private-equity-owned company; "CPG Holdings" reads as it |
| `world.py` planted companies | Juno Software | Junavel Software | Several real firms trade as "Juno Software" |
| `world.py` planted companies | Sable Security, Kelso Dental, Nordhavn Logistics, Brisa Packaging, Marl Packaging, Wyre Packaging | Sabrel Security, Kelmara Dental, Nordvale Logistics, Brisolen Packaging, Marlowen Packaging, Wyrecombe Packaging | Close to real brands or firms (a security product named Sable, Kelso & Company, Nordhavn yachts, Brisa); renamed to be safe |
| `world.py` generated companies | word list from Secondaries Radar (e.g. "Verity", "Lumen", "Ember" + a sector) | invented syllable words | Real-word pairs like "Verity Health" can be real companies |

## Searched and kept

| Name | Where | Result |
|---|---|---|
| Calder Packaging Ltd | brief, everywhere | No exact match. A packaging-machinery firm uses a longer name ("Calder Packaging Machinery", 2009 item). Kept because the brief defines it; flagged for the PM |
| Aldermoor Pension Plan (the LP) | everywhere | No match |
| Halvane, Brennick, Tellmar, Ostrova, Selbrook, Quillon, Wexcombe, Marrowby, Thornhale, Caskel, Arkwell, Dunmere, Varrow, Orlaith, Pellam, Fenlow (managers) | `world.py` | No exact matches (near names only, such as Arkview, Halyard) |
| Mara Ellingsby, Tomas Reyvik, Ilse Varnholt, Joel Brandtke (partners) | `world.py` | No matches |
| Calderwick Holdings, Junavel, Kelmara, Sabrel, Nordvale, Brisolen, Marlowen, Wyrecombe | `world.py` | No exact matches |

## Public sources kept (they back numbers or licences)

Preqin 2025 report, CSC 2023 survey via Real Deals, ILPA templates, DuckDB docs, DuckPGQ, MetricFlow and dbt Labs, Boring Semantic Layer, Cube, The Register (Kùzu archived), Neo4j licensing, Secondaries Radar (the PM's own public repo). Every link returned 200 on 2026-10-25.

## Never present

- The PM's employer, clients, prospects: searched for the PM's own domain name and found nothing. No real investor appears as "the LP".
- Domains in demo data: all synthetic addresses use the reserved `.example` TLD (`halvane.example`, `secondaries-desk.example`).

## Repo hygiene

- No keys in the repo or its history (searched every commit for `sk-ant-`: 0 hits). `.env` and `logs/` are git-ignored.
- Repo name `lp-data-foundations` and remote `github.com/alexandrecela10/lp-data-foundations` name no organisation.
- No PDFs, images or videos to check by eye.
