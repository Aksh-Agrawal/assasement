# Knowledge Map on Raspberry Pi

Open **Analytics → Knowledge Map** for the active profile. The attempt selector uses the last 5, 10 or 20 completed assessments. The map loads through the existing background analytics worker from a read-only SQLite snapshot and works with the network disconnected.

- The four squares use only graded answers rated Sure, Not sure or Guessing. Sure is confident. Unrated graded answers, recorded skips and ungraded responses are listed separately. A dash means no denominator is available. Fewer than three rated observations are flagged as limited.
- Topics come from pinned attempt content and authorized, installed practice packs. Each tile shows accuracy over graded answers or labels a topic as unassessed in the current range. Missing metadata appears in an unclassified group. The five-tile pages show up to 120 topics, with topics that have evidence shown first.
- Open a tile for attempt count, last practice date, confidence counts and cached retention status when available. Use **Review answer** for retained answer evidence or **Start downloaded check** for an installed, authorized check.
- Recent accuracy appears with at least two completed assessments containing graded answers. Each bar shows the assessment date, accuracy and graded denominator. The device displays at most the last five such assessments from the selected attempt window.
- A profile’s native records take precedence over cached cloud records with the same attempt UUID. Retained web reviews can contribute after sync. Summary-only history can appear in Analytics Overview with incomplete question evidence in the Knowledge Map.

The app-wide 16-unit touch inset and wallpaper cover this screen. No database migration, new device service or network request is required to render it.
