"""Guide content: EU bachelor+master -> psychotherapist in Switzerland.

Curated 2026-09-09 from BAG/PsyKo pages (see sources[] links). Informational only.
Rendered server-side from this module — no DB needed, easy to correct.
"""
from __future__ import annotations

STEPS = [
    {"n": 1, "t": "Master recognised by PsyKo", "d": "Foreign MSc in psychology must be recognised as equivalent (PsyG Art. 3). Bachelor alone is not recognised — only the Master's level counts."},
    {"n": 2, "t": "Clinical/psychopathology credits", "d": "For a psychotherapy track you need sufficient clinical psychology / psychopathology in your studies (major or minor). The training institute checks this case by case."},
    {"n": 3, "t": "Accredited postgraduate training", "d": "Complete a BAG-accredited psychotherapy programme (2–6 years: theory, 2 yrs clinical practice, 500h own therapy work, supervision, self-experience). Or get a foreign therapy title recognised by PsyKo."},
    {"n": 4, "t": "Federal title + PsyReg entry", "d": "Graduation gives the title «eidg. anerkannte/r Psychotherapeut/in» and entry in the public PsyReg register (fee CHF 250)."},
    {"n": 5, "t": "Cantonal practice licence", "d": "Working on your own professional responsibility needs a licence from the canton where you practise. Employed, supervised roles can be possible earlier — ask the canton."},
    {"n": 6, "t": "Billing (insurance)", "d": "Since 07/2022 the prescription model (Anordnungsmodell) lets recognised psychotherapists bill basic insurance on a doctor's prescription. Check santésuisse listing rules."},
]

SECTIONS = [
    {"id": "who", "t": "Who is this for?",
     "body": ("You hold (or are finishing) a European bachelor's and master's in psychology and want "
              "to practise as a psychotherapist in Switzerland. Swiss law (Psychologieberufegesetz, PsyG, "
              "in force since 01.04.2013) protects two things: the title «Psychologe/in» (needs a recognised "
              "Master's) and the title «eidg. anerkannte/r Psychotherapeut/in» (needs a recognised postgraduate "
              "therapy title). A bachelor's degree alone gives no protected title and no PsyKo certificate.")},
    {"id": "master", "t": "Step 1 — get the Master's recognised (PsyKo)",
     "body": ("Authority: Psychologieberufekommission (PsyKo) at the BAG, Bern. EU/EFTA applications follow "
              "EU Directive 2005/36/EC; third-country applications use the same procedure where possible. "
              "File the «Gesuchsformular Anerkennung Hochschulabschluss Psychologie» with diploma, transcript, "
              "syllabus/ECTS proof and ID. Without this recognition you cannot enter an accredited therapy "
              "programme, and no institute may set its own equivalence criteria for foreign degrees."),
     "links": [("BAG recognition page", "https://www.bag.admin.ch/de/anerkennungen-von-psychologieberufen"),
               ("Application form (Master's)", "https://www.bag.admin.ch/dam/de/sd-web/t0JpD2HgTNsA/gesuchsformular-anerkennung-hochschulabschluss-psychologie.pdf")]},
    {"id": "clinical", "t": "Check the clinical-psychology requirement early",
     "body": ("Art. 7 PsyG: admission to an accredited psychotherapy track additionally requires sufficient "
              "coursework in clinical psychology / psychopathology. A major in clinical psychology always counts; "
              "a minor (or equivalent credits) also counts; anything else is judged case by case by the training "
              "institute. If your EU master was e.g. work & organisational psychology, clarify this with target "
              "institutes BEFORE applying — it is the most common silent rejection reason.")},
    {"id": "training", "t": "Step 2 — accredited postgraduate training in psychotherapy",
     "body": ("Pick a programme from the BAG's list of accredited Weiterbildungsgänge. By law the curriculum "
              "spans 2–6 years and includes: theory, ≥2 years (100%) clinical practice (≥1 year in a "
              "psychotherapeutic-psychiatric setting), ≥500 hours of own therapy work with ≥10 documented, "
              "supervised cases, supervision, and self-experience. Hours completed before the Master's cannot "
              "count. Alternatively: complete a therapy qualification abroad and have PsyKo recognise it as "
              "equivalent (needs the recognised Master's first). 2024 figures: 478 foreign psychology degrees "
              "and 101 foreign therapy titles recognised, mostly from DE/IT/FR."),
     "links": [("Accredited programmes list", "https://www.bag.admin.ch/de/liste-der-akkreditierten-weiterbildungsgaenge"),
               ("PsyG FAQ (BAG)", "https://www.bag.admin.ch/de/haeufige-fragen-faq-zum-psychologieberufegesetz-psyg")]},
    {"id": "title", "t": "Step 3 — federal title + PsyReg + canton licence",
     "body": ("Graduating an accredited programme earns «eidg. anerkannte/r Psychotherapeut/in» (the institute "
              "reports you to the BAG; certificate + PsyReg entry cost CHF 250). Independent practice then needs "
              "a Berufsausübungsbewilligung from the canton of practice. Note: only psychotherapy is licence-gated "
              "this way; the other federal titles (clinical, neuro, health, child/youth psychology) protect the "
              "title but don't gate employment. Verify any licence holder in the public PsyReg register."),
     "links": [("PsyReg register", "https://www.bag.admin.ch/de/psychologieberuferegister-psyreg")]},
    {"id": "money", "t": "Money, language, jobs — the practical side",
     "body": ("Postgraduate therapy training in Switzerland typically costs tens of thousands of CHF and takes "
              "years alongside clinical employment. Working language is the cantonal language (German/French/Italian) "
              "at near-native clinical level — de facto mandatory for therapy roles. Use the Jobs tab here to watch "
              "real openings (jobup.ch: ~200–380 psychology/therapy ads): filter for «in Weiterbildung / en formation» "
              "roles, assistant psychologist posts, and clinic jobs that explicitly accept candidates in accredited "
              "training — these are the realistic entry points while the recognition paperwork runs.")},
    {"id": "eu90", "t": "EU shortcut: 90-day service provision",
     "body": ("If you stay established in your EU home country, you may provide services in Switzerland up to 90 "
              "days/year via the SBFI declaration procedure (Meldeverfahren) instead of full recognition. The "
              "paperwork and cost are similar; the declaration must be renewed each service year. Useful for "
              "testing the market, not for relocating.")},
]

SOURCES = [
    ("BAG — recognition of psychology professions", "https://www.bag.admin.ch/de/anerkennungen-von-psychologieberufen"),
    ("BAG — PsyG FAQ", "https://www.bag.admin.ch/de/haeufige-fragen-faq-zum-psychologieberufegesetz-psyg"),
    ("BAG — PsyReg register", "https://www.bag.admin.ch/de/psychologieberuferegister-psyreg"),
    ("BAG — accredited programmes", "https://www.bag.admin.ch/de/liste-der-akkreditierten-weiterbildungsgaenge"),
    ("recognition.swiss portal", "https://www.recognition.swiss/en"),
    ("PsyKo office", "mailto:office@psyko.admin.ch"),
]

PORTALS = [
    ("jobup.ch", "https://www.jobup.ch/en/jobs/?term=psychology", "tracked here — ~217 psychology ads, structured detail pages"),
    ("jobs.ch", "https://www.jobs.ch/de/stellenangebote/?term=psychotherapeut", "~368 ads, same operator (JobCloud)"),
    ("PsychJOB.ch", "https://www.psychjob.ch/jobs", "niche psychology board (~36 ads), bot-protected — check manually"),
    ("therapie-jobs.ch", "https://therapie-jobs.ch/psychotherapeut", "niche therapy board (~134 ads), blocks scrapers — check manually"),
    ("SBAP listings", "https://sbap.ch/aktuell/stellen/", "association board via fhjobs.ch"),
    ("PsyReg", "https://www.bag.admin.ch/de/psychologieberuferegister-psyreg", "verify licence holders, not a job board"),
]
