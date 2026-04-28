# Retired: part12_questionnaire_005
Retired on: 2026-04-27
Reason: Bundled extraction returned two distinct allottees as two dicts
inside a list (instead of the standard single-dict extraction structure).
Source pages 10-11 contain Warren Real Rider's questionnaire (allot 226);
pages 12-13 contain Jesse Peters's (allot 728). Both notarized November 26,
1928, at Pawnee Agency, Pawnee, Oklahoma.
Superseded by:
  part12_questionnaire_005a.json (Warren Real Rider, allot 226, sold to C.E. Vandervoort for $2000)
  part12_questionnaire_005b.json (Jesse Peters, allot 728, mortgaged to R.C. Spinning for $1700, sold for $2000, allottee received $65)
The bundled JSON's extraction structure (list of 2 dicts) was a Sonnet output
anomaly; most multi-allottee bundled records concatenate fields with semicolons
(e.g. Ely+King). This one was already cleanly structured and only needed
promotion to standalone records.
