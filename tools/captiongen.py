# -*- coding: utf-8 -*-
"""Caption drafting from a narration script. Kept separate so it can be
tested on its own."""
import re

PROMPTS_NEUTRAL = [
    "Did anyone explain it to you this way at school?",
    "Guess before you scroll, then check.",
    "Who else was taught this wrong?",
    "Send this to whoever argues about it.",
    "What did you think the reason was?",
    "Which part of this surprised you?",
]
PROMPTS_TRYIT = [
    "Try it tonight and tell me what happened.",
    "Go and test it, then report back.",
    "Check it at home and tell me what you saw.",
]
EVERYDAY = re.compile(r"\b(kitchen|pan|kettle|fridge|bottle|straw|cup|mug|"
                      r"shirt|cloth|bike|bicycle|door|window|shower|spoon|"
                      r"microwave|tap|towel|soap|coffee|tea)\b", re.I)

# word-boundary matching, most specific first, scored by distinct hits
TOPIC = [
    (r"\bneutrino|\bquark|\bhiggs|\bhadron|\bmuon\b", ["#particlephysics", "#quantumphysics"]),
    (r"\bnucle(us|ar|i)\b|\bradioactiv|\bisotope|\balpha decay", ["#nuclearphysics", "#radioactivity"]),
    (r"\brelativi|\bspacetime|\btime dilation|\blorentz", ["#relativity", "#spacetime"]),
    (r"\bblack hole|\bgalax|\bstar\b|\borbit|\bcomet|\bplanet", ["#astrophysics", "#astronomy"]),
    (r"\bgravit", ["#gravity"]),
    (r"\bsuperconduct|\bband gap|\bsemiconduct|\bcrystal|\blattice", ["#solidstatephysics", "#materialscience"]),
    (r"\bquantum|\bwavefunction|\bentangl|\bqubit|\benergy level", ["#quantumphysics"]),
    (r"\belectron\b|\batom\b|\bion\b", ["#atomicphysics"]),
    (r"\bmagnet|\beddy current|\binduct|\bfaraday", ["#electromagnetism", "#magnetism"]),
    (r"\bvoltage|\bcurrent\b|\bcircuit|\bresistor|\bcapacit", ["#electricity", "#circuits"]),
    (r"\brefract|\blens\b|\bmirror|\bprism|\bpolaris|\binterferen|\bdiffract", ["#optics", "#lightandoptics"]),
    (r"\bphoton|\bwavelength|\bspectr", ["#lightandoptics", "#waveoptics"]),
    (r"\bsound|\bpitch\b|\bacoustic|\bresonan", ["#acoustics", "#soundwaves"]),
    (r"\bwave(s|length)?\b|\bvibrat|\bstring\b|\btension\b|\boscillat|"
     r"\bamplitude|\bfrequency|\bharmonic|\bstanding wave", ["#waves", "#oscillations"]),
    (r"\bsurface tension|\bdroplet|\bcapillar", ["#surfacetension", "#fluidmechanics"]),
    (r"\bdiffusion|\bbrownian|\brandom walk", ["#statisticalphysics", "#diffusion"]),
    (r"\bbuoyan|\bfloat\b|\bdensity\b", ["#buoyancy", "#fluidmechanics"]),
    (r"\bheat\b|\btemperature|\bthermal|\bentropy|\blatent|\bboil", ["#thermodynamics", "#heattransfer"]),
    (r"\bpressure|\bfluid|\bviscos|\bflow\b|\bbubble|\bsurface tension", ["#fluidmechanics"]),
    (r"\bangular momentum|\btorque|\bspin\b|\brotat", ["#rotationaldynamics", "#angularmomentum"]),
    (r"\bfriction|\bmomentum|\bimpulse|\bnewton|\bforce\b|\bacceleration", ["#classicalmechanics", "#mechanics"]),
    (r"\benergy\b|\bwork\b|\bconservation", ["#energy", "#conservationlaws"]),
    (r"\bprobabilit|\bstatistic|\brandom|\balgorithm", ["#mathematics", "#probability"]),
    (r"\bsampl(e|es|ing)\b|\balias|\bframe(s)? a second|\bsnapshot|"
     r"\bbandwidth|\bsignal\b|\bfourier", ["#signalprocessing", "#waves"]),
    (r"\bcamera|\bimage\b|\bblur|\bresolution|\bpixel|\bmicroscop|"
     r"\btelescop|\baperture", ["#optics", "#imaging"]),
    (r"\bmeasure|\buncertaint|\berror bar|\bcalibrat|\bprecision|"
     r"\bdetector\b", ["#experimentalphysics", "#measurement"]),
    (r"\bfriction|\bgrip\b|\bslid(e|ing)\b|\broll(ing)?\b", ["#friction", "#mechanics"]),
    (r"\bpendulum|\bspring\b|\bstiff", ["#oscillations", "#mechanics"]),
]
EXAM = [["#jeephysics", "#neetphysics", "#class11physics"],
        ["#jeeadvanced", "#apphysics", "#class12physics"],
        ["#alevelphysics", "#ibphysics", "#physicsstudent"],
        ["#neetphysics", "#jeemains", "#physicsstudent"],
        ["#jeephysics", "#apphysics", "#undergradphysics"]]
BROAD = [["#physicsfacts", "#sciencereels", "#learnphysics"],
         ["#everydayphysics", "#scienceexplained", "#physics"],
         ["#howthingswork", "#sciencefacts", "#learnphysics"],
         ["#physicsinreallife", "#sciencereels", "#physics"]]


def clean(t):
    return re.sub(r"\s+", " ", t.replace("**", "")).strip()


# words that are never the name of a concept - the naive "last bolded term"
# rule used to yield things like "That is nanometres."
_NOT_A_CONCEPT = re.compile(
    r"^(?:[\d.,]+\s*)?(nanometre|micrometre|metre|centimetre|kilometre|second|"
    r"minute|hour|degree|kelvin|joule|watt|volt|ohm|hertz|newton|pascal|gram|"
    r"kilogram|electronvolt|percent|times|more|less|fast|slow|hot|cold|it|this|"
    r"that|them|you|your)s?$", re.I)

_NAMING = (
    r"(?:is|are)\s+called\s+(?:the\s+|a\s+|an\s+)?\*\*([^*]+)\*\*",
    r"That(?:\'s| is)\s+(?:called\s+)?(?:the\s+|a\s+|an\s+)?\*\*([^*]+)\*\*",
    r"known as\s+(?:the\s+)?\*\*([^*]+)\*\*",
    r"we call (?:it|this|that)\s+(?:the\s+)?\*\*([^*]+)\*\*",
    r"(?:That|This|It)\s+(?:limit|trade|effect|rule|law|idea|settling|"
    r"splitting|trapping|self-correcting|difference)\s+is\s+(?:called\s+)?"
    r"(?:the\s+|a\s+|an\s+)?\*\*([^*]+)\*\*",
)


def principle(cues):
    """The named concept. Returns (phrase, named_anywhere).

    named_anywhere is False only when the script never names a concept at
    all - that is the case worth a human look, not merely an unusual phrasing.
    """
    summaries = [c["vo"] for c in cues if c.get("kind") == "summary"]
    for vo in summaries:
        for pat in _NAMING:
            m = re.search(pat, vo, re.I)
            if m:
                term = m.group(1).strip().rstrip(".")
                if not _NOT_A_CONCEPT.match(term):
                    return term, True
    # fall back to a trailing bolded term in the summary, if it looks like a
    # concept rather than a unit or a pronoun
    for vo in summaries:
        bolds = re.findall(r"\*\*([^*]+)\*\*", vo)
        if bolds:
            term = bolds[-1].strip().rstrip(".")
            if not _NOT_A_CONCEPT.match(term) and len(term.split()) <= 6:
                return term, True
    return None, False


def topic_tags(blob, limit=4):
    hits = []
    for pat, tags in TOPIC:
        n = len(set(re.findall(pat, blob, re.I)))
        if n:
            hits.append((n, tags))
    hits.sort(key=lambda t: -t[0])
    out = []
    for _, tags in hits:
        for t in tags:
            if t not in out:
                out.append(t)
        if len(out) >= limit:
            break
    return out[:limit]


def draft(cues, idx):
    body_all = [clean(c["vo"]) for c in cues]
    hook = body_all[0]
    summary = next((clean(c["vo"]) for c in cues if c.get("kind") == "summary"), None)
    app_i = next((i for i, c in enumerate(cues) if c.get("kind") == "application"), None)

    mech = [clean(c["vo"]) for i, c in enumerate(cues[1:], 1)
            if (app_i is None or i < app_i) and c.get("kind") != "summary"]
    apps = []
    if app_i is not None:
        for c in cues[app_i:]:
            t = clean(c["vo"])
            if ("how we teach" in t.lower() or t.lower().startswith("other examples")
                    or not t):
                continue
            apps.append(t)

    pr, confident = principle(cues)
    if summary:
        summary = summary.strip()

    parts = [hook, ""]
    parts.append(" ".join(mech[:3]))
    if len(mech) > 3:
        parts += ["", " ".join(mech[3:6])]
    if len(mech) > 6:
        parts += ["", " ".join(mech[6:])]
    if summary:
        parts += ["", summary]
    # only name the principle separately if the summary has not already done so
    named_in_summary = bool(summary and pr and pr.lower() in summary.lower())
    if pr and not named_in_summary:
        article = "" if re.match(r"(the|a|an)\s", pr, re.I) else "the "
        parts += ["", f"That is called {article}{pr}."]
    if apps:
        parts += ["", " ".join(apps[:2])]

    blob = " ".join(body_all)
    core_blob = " ".join([hook] + mech + ([summary] if summary else []))
    prompts = PROMPTS_TRYIT if EVERYDAY.search(blob) else PROMPTS_NEUTRAL
    parts += ["", prompts[idx % len(prompts)]]

    tags = topic_tags(core_blob)
    if len(tags) < 2:                      # thin signal: allow applications in
        for t in topic_tags(blob):
            if t not in tags:
                tags.append(t)
        tags = tags[:4]
    tags += EXAM[idx % len(EXAM)] + BROAD[(idx // 3) % len(BROAD)]
    tags = list(dict.fromkeys(tags)) + ["#fermi"]
    parts += ["", " ".join(tags)]

    caption = "\n".join(parts)
    while len(caption) > 2100:
        parts.pop(len(parts) - 6)
        caption = "\n".join(parts)
    return caption, tags, confident
