"""
Build a Qualtrics survey (.qsf) that repeats the PsychoPy end-of-session
video ratings (video_rating loop in Biosignals2_internalcamera_Psychopy_lastrun.py)
for a participant whose session crashed before those ratings.

Per video, same screens/wording as PsychoPy:
  1. stimuli_emo_rating  : "How did you feel while watching this video?" (one word)
                           + "How intense was this feeling?" (not intense at all .. very intense)
  2./3. valence + arousal, order alternating across videos (stim_rating_order logic)
  4. approach_rating     : "How much did you want to watch this?"
All sliders: 1-7, 7 ticks, endpoint labels only, no numbers shown, response required.

Usage:  python make_remote_ratings_qsf.py
Edit the SETTINGS block first (image URLs, rating_start, seed).
Writes remote_video_ratings.qsf (+ remote_video_ratings_advanced.txt fallback).
"""
import json
import random
from datetime import datetime

# ---------------- SETTINGS ----------------
# Same meaning as rating_start in the PsychoPy script (set per participant).
RATING_START = "valence_first"
# Video order: PsychoPy used method='random'. Drawn once here (fixed seed so the
# order is recorded and reproducible). Set SEED = None for a fresh draw.
SEED = 20261028
# Screenshot URLs (upload stimuli/<ID>_screenshot.png to Qualtrics Library >
# Graphics, copy each image URL here). Leave "" to show a red placeholder.
IMAGE_URLS = {
    "N007": "https://universityofsussex.eu.qualtrics.com/ControlPanel/Graphic.php?IM=IM_OKCqj24y9R8ZLNZ",
    "N01": "https://universityofsussex.eu.qualtrics.com/ControlPanel/Graphic.php?IM=IM_Mi7EOEJlbrzqruF",
    "P02": "https://universityofsussex.eu.qualtrics.com/ControlPanel/Graphic.php?IM=IM_kfMqqAAQUljNSrQ",  # given as "P01" - check it is the tube-carriage still
    "P0141": "https://universityofsussex.eu.qualtrics.com/ControlPanel/Graphic.php?IM=IM_aAomISIF1NiTgxq",
}
SURVEY_NAME = "Biosignals2 - remote video ratings (crash recovery)"
# ------------------------------------------

VIDEOS = ["N007", "N01", "P02", "P0141"]  # rating_images.csv
SURVEY_ID = "SV_3kBs2RemRat8wQ"  # Qualtrics-style: SV_ + 15 chars
SLIDER_HINT = "Click on the slider to select your answer."

INTRO = (
    "<p>Thank you again for taking part in our study.</p>"
    "<p>Your session ended before the final questions about the videos could be "
    "shown, so we would be grateful if you could answer them here. It takes about "
    "5 minutes.</p>"
    "<p>You will see a still image from each of the four videos you watched. "
    "For each one, please think back to how you felt <b>while you were watching "
    "that video in the lab</b>, and answer the questions.</p>"
    "<p>Please note that two of the videos contained upsetting content. "
    "You only need to see a single still image from each.</p>"
)
END = "Thank you! That was the last question."

stim_rating_start = "arousal_first" if RATING_START == "valence_first" else "valence_first"
rng = random.Random(SEED)
order = VIDEOS[:]
rng.shuffle(order)

questions, blocks, flow = [], [], []
qn = 0


def image_html(vid):
    url = IMAGE_URLS.get(vid, "")
    if url:
        return f'<div style="text-align:center"><img src="{url}" style="max-height:260px;max-width:100%"></div><br>'
    return (f'<div style="text-align:center;color:#c00;font-weight:bold">'
            f'[SCREENSHOT {vid} - insert image here]</div><br>')


def base(qid, tag, text, qtype, selector, desc):
    return {"QuestionText": text, "DefaultChoices": False, "DataExportTag": tag,
            "QuestionType": qtype, "Selector": selector,
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": desc, "Validation": {"Settings": {"Type": "None"}},
            "GradingData": [], "Language": [], "NextChoiceId": 4, "NextAnswerId": 1,
            "QuestionID": qid}


def add(payload):
    questions.append(payload)
    return payload["QuestionID"]


def new_qid():
    global qn
    qn += 1
    return f"QID{qn}"


def text_q(tag, html):
    q = base(new_qid(), tag, html, "DB", "TB", tag)
    q["ChoiceOrder"] = []
    return add(q)


def entry_q(tag, html, required=True):
    q = base(new_qid(), tag, html, "TE", "SL", tag)
    q["Configuration"]["InputWidth"] = 300
    q["SearchSource"] = {"AllowFreeResponse": "false"}
    if required:
        q["Validation"] = {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}}
    return add(q)


def slider_q(tag, html, left, right):
    q = base(new_qid(), tag, html, "Slider", "HSLIDER", tag)
    q["Configuration"].update({"CSSliderMin": 1, "CSSliderMax": 7, "GridLines": 6,
                               "SnapToGrid": True, "NumDecimals": "0", "ShowValue": False,
                               "CustomStart": False, "NotApplicable": False, "MobileFirst": False})
    q["Choices"] = {"1": {"Display": "&nbsp;"}}
    q["ChoiceOrder"] = ["1"]
    q["Labels"] = {"1": {"Display": left}, "2": {"Display": right}}
    q["Validation"] = {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}}
    q["NextChoiceId"] = 2
    return add(q)


_bl_rng = random.Random(7)
def bl_id():
    abc = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "BL_" + "".join(_bl_rng.choice(abc) for _ in range(15))


def block(bid, desc, items, btype="Standard"):
    elems = []
    for i, page in enumerate(items):
        if i:
            elems.append({"Type": "Page Break"})
        elems += [{"Type": "Question", "QuestionID": q} for q in page]
    b = {"Type": btype, "SubType": "", "Description": desc, "ID": bid, "BlockElements": elems}
    blocks.append(b)
    flow.append({"Type": "Block", "ID": bid, "FlowID": f"FL_{len(flow) + 2}"})


# Intro + participant ID
block(bl_id(), "Intro", [[text_q("intro", INTRO),
                             entry_q("participant_id", "Please enter the participant ID we sent you:")]],
      btype="Default")

plan = []
for pos, vid in enumerate(order, start=1):
    first = stim_rating_start if pos % 2 == 1 else ("arousal_first" if stim_rating_start == "valence_first" else "valence_first")
    img = image_html(vid)
    emo_page = [
        entry_q(f"{vid}_emotion", img + "How did you feel while watching this video?<br>"
                "<span style='font-size:90%'>(Please type ONE word below)</span>"),
        slider_q(f"{vid}_intensity", "How intense was this feeling?<br><span style='font-size:85%'>"
                 + SLIDER_HINT + "</span>", "not intense at all", "very intense"),
    ]
    val = [slider_q(f"{vid}_valence", img + "Overall, how did you feel while watching this video?<br>"
                    "<span style='font-size:85%'>" + SLIDER_HINT + "</span>", "very unpleasant", "very pleasant")]
    aro = [slider_q(f"{vid}_arousal", img + "Overall, how did you feel while watching this video?<br>"
                    "<span style='font-size:85%'>" + SLIDER_HINT + "</span>", "not alert at all", "very alert")]
    appr = [slider_q(f"{vid}_approach", img + "How much did you want to watch this?<br>"
                     "<span style='font-size:85%'>" + SLIDER_HINT + "</span>",
                     "Strongly wanted to avoid it", "Strongly wanted to watch it")]
    pages = [emo_page] + ([aro, val] if first == "arousal_first" else [val, aro]) + [appr]
    block(bl_id(), f"Video {pos}: {vid} ({first})", pages)
    plan.append((pos, vid, first))

block(bl_id(), "End", [[text_q("end_text", END + " Please click the arrow below to submit your answers.")]])

# Embedded data recording what was shown (first in flow)
ed = {"Type": "EmbeddedData", "FlowID": "FL_ED", "EmbeddedData": [
    {"Description": k, "Type": "Custom", "Field": k, "VariableType": "String",
     "DataVisibility": [], "AnalyzeText": False, "Value": v}
    for k, v in [("video_order", ";".join(order)),
                 ("stim_rating_orders", ";".join(f"{v}:{f}" for _, v, f in plan)),
                 ("rating_start", RATING_START),
                 ("collection_mode", "remote_qualtrics_after_crash")]]}
flow.insert(0, ed)
for i, f_ in enumerate(flow, start=2):
    f_["FlowID"] = f"FL_{i}"
blocks.append({"Type": "Trash", "Description": "Trash / Unused Questions", "ID": bl_id(), "BlockElements": []})

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
el = lambda e, p, s=None, t=None, payload=None: {"SurveyID": SURVEY_ID, "Element": e, "PrimaryAttribute": p,
                                                 "SecondaryAttribute": s, "TertiaryAttribute": t, "Payload": payload}
qsf = {
    "SurveyEntry": {"SurveyID": SURVEY_ID, "SurveyName": SURVEY_NAME, "SurveyDescription": None,
                    "SurveyOwnerID": "UR_0", "SurveyBrandID": "universityofsussex", "DivisionID": None, "SurveyLanguage": "EN",
                    "SurveyActiveResponseSet": "RS_default", "SurveyStatus": "Inactive",
                    "SurveyStartDate": "0000-00-00 00:00:00", "SurveyExpirationDate": "0000-00-00 00:00:00",
                    "SurveyCreationDate": now, "CreatorID": "UR_0", "LastModified": now,
                    "LastAccessed": "0000-00-00 00:00:00", "LastActivated": "0000-00-00 00:00:00", "Deleted": None},
    "SurveyElements": [
        el("BL", "Survey Blocks", payload=blocks),
        el("FL", "Survey Flow", payload={"Type": "Root", "FlowID": "FL_1", "Flow": flow,
                                         "Properties": {"Count": len(flow) + 1}}),
        el("SO", "Survey Options", payload={
            "BackButton": "false", "SaveAndContinue": "true", "SurveyProtection": "PublicSurvey",
            "BallotBoxStuffingPrevention": "false", "NoIndex": "Yes", "SecureResponseFiles": "true",
            "SurveyExpiration": None, "SurveyTermination": "DefaultMessage", "Header": "", "Footer": "",
            "ProgressBarDisplay": "None", "PartialData": "+1 week", "ValidationMessage": "",
            "PreviousButton": "", "NextButton": "", "SurveyTitle": "Biosignals study - final questions"}),
        el("SCO", "Scoring", payload={"ScoringCategories": [], "ScoringCategoryGroups": [],
                                      "ScoringSummaryCategory": None, "ScoringSummaryAfterQuestions": 0,
                                      "ScoringSummaryAfterSurvey": 0, "DefaultScoringCategory": None,
                                      "AutoScoringCategory": None}),
        el("PROJ", "CORE", None, "1.1.0", {"ProjectCategory": "CORE", "SchemaVersion": "1.1.0"}),
        el("STAT", "Survey Statistics", payload={"MobileCompatible": True, "ID": "Survey Statistics"}),
        el("QC", "Survey Question Count", str(len(questions))),
        el("RS", "RS_default", "Default Response Set"),
    ] + [el("SQ", q["QuestionID"], q["DataExportTag"], None, q) for q in questions],
}

with open("remote_video_ratings.qsf", "w", encoding="utf-8") as f:
    json.dump(qsf, f, ensure_ascii=False, indent=1)

# ---- Fallback: Qualtrics "Advanced format" TXT (no sliders -> 7-point radio scale) ----
def scale(left, right):
    return "\n".join([f"1 - {left}"] + [str(i) for i in range(2, 7)] + [f"7 - {right}"])

lines = ["[[AdvancedFormat]]", "", "[[Block:Intro]]", "",
         "[[Question:DB]]", INTRO, "", "[[Question:TE:SingleLine]]", "[[ID:participant_id]]",
         "Please enter the participant ID we sent you:", ""]
for pos, vid, first in plan:
    lines += [f"[[Block:Video {pos} {vid}]]", "", f"[[Question:DB]]", image_html(vid), "",
              "[[Question:TE:SingleLine]]", f"[[ID:{vid}_emotion]]",
              "How did you feel while watching this video? (Please type ONE word below)", "",
              "[[Question:MC:SingleAnswer:Horizontal]]", f"[[ID:{vid}_intensity]]",
              "How intense was this feeling?", "[[Choices]]", scale("not intense at all", "very intense"), "",
              "[[PageBreak]]", ""]
    va = [("valence", "very unpleasant", "very pleasant"), ("arousal", "not alert at all", "very alert")]
    if first == "arousal_first":
        va.reverse()
    for name, l, r in va:
        lines += ["[[Question:MC:SingleAnswer:Horizontal]]", f"[[ID:{vid}_{name}]]",
                  image_html(vid) + "Overall, how did you feel while watching this video?", "[[Choices]]", scale(l, r), "",
                  "[[PageBreak]]", ""]
    lines += ["[[Question:MC:SingleAnswer:Horizontal]]", f"[[ID:{vid}_approach]]",
              image_html(vid) + "How much did you want to watch this?", "[[Choices]]",
              scale("Strongly wanted to avoid it", "Strongly wanted to watch it"), ""]
with open("remote_video_ratings_advanced.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Video order:", order)
for pos, vid, first in plan:
    print(f"  {pos}. {vid}: emotion+intensity -> {'arousal, valence' if first == 'arousal_first' else 'valence, arousal'} -> approach")
print(f"{len(questions)} questions written to remote_video_ratings.qsf")
