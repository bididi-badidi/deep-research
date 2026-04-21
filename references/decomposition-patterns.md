# Decomposition Patterns

Common research question types and their recommended task splits.

---

## Pattern 1 — Descriptive ("What is / What are")

> "What are the current applications of AI in Southeast Asian hospitals?"

Recommended tasks:
| Task | Category | Sub-question |
|------|----------|--------------|
| T-01 | Background | How has AI in healthcare evolved in Southeast Asia over the past decade? |
| T-02 | Evidence | What specific AI applications are documented in hospitals across Singapore, Thailand, Malaysia, Vietnam, and Indonesia? |
| T-03 | Applied | What are documented outcomes or case studies from these implementations? |
| T-04 | Emerging | What AI healthcare initiatives are currently in pilot or planning phases in the region? |

Split tip: Use geography or institution type to ensure non-overlap between T-02 and T-03.

---

## Pattern 2 — Comparative ("Which is better / How do X and Y differ")

> "How does remote work affect productivity compared to office work?"

Recommended tasks:
| Task | Category | Sub-question |
|------|----------|--------------|
| T-01 | Background | What do major theoretical frameworks say about work environment and productivity? |
| T-02 | Evidence | What does quantitative research (2018–present) show about remote work productivity metrics? |
| T-03 | Evidence | What does quantitative research (2018–present) show about office work productivity metrics? |
| T-04 | Critical | What are the methodological limitations of current remote-vs-office productivity studies? |
| T-05 | Applied | How do industry and role type (creative, analytical, managerial) moderate these findings? |

Split tip: T-02 and T-03 use the same time period but different conditions — non-overlapping by design.

---

## Pattern 3 — Causal ("Why does / What causes")

> "Why are antimicrobial resistance rates rising in low-income countries?"

Recommended tasks:
| Task | Category | Sub-question |
|------|----------|--------------|
| T-01 | Background | What is the current global epidemiology of antimicrobial resistance? |
| T-02 | Evidence | What supply-side factors (antibiotic availability, regulation, counterfeit drugs) drive resistance in low-income settings? |
| T-03 | Evidence | What demand-side factors (patient behaviour, prescriber practice, agricultural use) drive resistance in low-income settings? |
| T-04 | Comparative | How do resistance drivers in low-income countries differ from those in high-income countries? |
| T-05 | Critical | What are the limitations of current surveillance data from low-income countries? |

Split tip: T-02 and T-03 are split by supply vs. demand — same geography, different mechanism.

---

## Pattern 4 — Evaluative ("Is X effective / Does X work")

> "Is mindfulness-based therapy effective for treating anxiety in adolescents?"

Recommended tasks:
| Task | Category | Sub-question |
|------|----------|--------------|
| T-01 | Background | How is mindfulness-based therapy defined and operationalised in clinical settings? |
| T-02 | Evidence | What do randomised controlled trials (2010–present) show about MBT outcomes for adolescent anxiety? |
| T-03 | Comparative | How does MBT compare to CBT and pharmacological interventions for adolescent anxiety? |
| T-04 | Applied | What implementation factors (therapist training, delivery format, session frequency) affect MBT outcomes? |
| T-05 | Critical | What are the methodological criticisms of existing MBT efficacy studies? |

Split tip: T-02 covers RCTs only; T-03 is comparative — different task type prevents overlap.

---

## Pattern 5 — Exploratory ("What is known / What is the state of")

> "What is the current state of hydrogen fuel cell technology for commercial vehicles?"

Recommended tasks:
| Task | Category | Sub-question |
|------|----------|--------------|
| T-01 | Background | What are the core technical principles and current performance benchmarks of hydrogen fuel cells for heavy transport? |
| T-02 | Evidence | What commercial deployments or large-scale pilots of hydrogen fuel cell trucks and buses exist globally? |
| T-03 | Comparative | How does hydrogen fuel cell technology compare to battery-electric for commercial vehicle economics and range? |
| T-04 | Applied | What infrastructure challenges (refuelling networks, production capacity) face commercial adoption? |
| T-05 | Emerging | What R&D and policy initiatives are projected to change the landscape in the next 5 years? |

---

## Anti-Patterns to Avoid

| Anti-pattern                                         | Why it fails                            | Fix                                       |
| ---------------------------------------------------- | --------------------------------------- | ----------------------------------------- |
| Tasks defined by keyword ("find everything about X") | Creates overlap and undefined scope     | Define by sub-question, not by topic      |
| More than 8 tasks                                    | Coordination overhead outweighs benefit | Merge tasks by category or time period    |
| Tasks that share the same source pool                | Subagents will duplicate findings       | Split by sub-question type or methodology |
| Dependent tasks dispatched simultaneously            | Second task has no inputs               | Mark dependency, queue second task        |
| Synthesis task sent to a Subagent                    | Synthesis is the Research Lead's job    | Keep synthesis in-house                   |
