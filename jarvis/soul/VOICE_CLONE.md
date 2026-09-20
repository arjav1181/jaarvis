# Voice-clone option — DOCUMENTED ONLY, not implemented (W12)

A household voice clone (the owner's own voice as a soul voice, or a family
member's with their consent) is possible on keyed backends, but it is
**gated on explicit owner consent** and is not wired anywhere in this wave.

## Consent requirements (all must hold before any clone work starts)

1. **Explicit owner consent, in writing** (chat confirmation counts if it is
   unambiguous and logged): whose voice, for which soul slot, revocable how.
2. **Speaker consent** when the voice is not the owner's own — the speaker
   themselves must agree, not via a third party.
3. **No cloning of third parties**: public figures, staff, children — never,
   even with "permission" relayed by someone else.
4. **Revocation path**: the clone voice ID and its replacement default must be
   recorded in `voices.yml` comments so removal is one config edit.

## What implementation would need (future wave, consented only)

- A keyed backend that supports custom voices (ElevenLabs custom voice ID;
  OpenAI has no custom-voice API — Edge has none either).
- The voice ID pinned in `jarvis/personas/voices.yml` under the soul block
  (same schema as today), key via environment — never in the repo.
- A `/voice status` line showing `cloned: true + consent-ref` so the household
  can always see a clone is active.
- L2-by-voice rules stay mandatory: a familiar voice never lowers an approval
  floor (see W8 smart permissions) — clones make social engineering easier,
  so voice-PIN for L2 is non-negotiable.

Until then: `elevenlabs: null` for Ultron/Friday stays null, and no clone
audio is produced anywhere. This file is the whole feature.
