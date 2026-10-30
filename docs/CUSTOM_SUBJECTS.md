# Custom question-pack subjects

Question packs accept any nonblank subject name up to 64 characters, including Mathematics, Physics, English and Computer Science. Biology and Chemistry remain valid. The web upload form already accepts typed subject names; validation now matches it.

Both repositories carry the same schema change. Cloud shared domain validation and Pi domain validation use the same nonblank/64-character contract. The cloud database already stores subjects as String(64), so no cloud database migration is required.

Pi migration 0007 removes the historical two-subject SQLite CHECK restriction by rebuilding only question-set metadata. Downloaded questions, exact versions, profile grants, completed history and in-progress attempts retain their original keys and rows. Rebuild, version update and foreign-key validation run in one transaction; enforcement is restored on success or failure. Do not reset the device database.

Rollout: deploy the updated startup-cloud service and update startup on the Pi. The Pi applies migration 0007 automatically when it next opens its database. Updating only the upload schema would allow cloud upload but leave older Pi builds unable to import new subjects. No cloud website redesign is involved.
