from collections import Counter, deque
from typing import Deque, Dict, Any, List
import json
from pathlib import Path
import re

_ALPHA = 0.4  # EMA smoothing
_prev_scores: Dict[str, float] = {}
_last_non_empty_keywords: Counter = Counter()
_last_top_keywords: List[str] = []
_last_snapshot_path: str = ""
# rolling buffer of last 12 snapshots (each snapshot is a list of items)
BUFFER_MAX = 12
_buffer: Deque[List[Dict[str, Any]]] = deque(maxlen=BUFFER_MAX)
# optional DB persistence helper (best-effort)
try:
    from .stability_store import save_snapshot_to_db, get_recent_snapshots
    _HAS_DB = True
except Exception:
    save_snapshot_to_db = None
    _HAS_DB = False

CATEGORY_CONFIG = {
    "energy": (["power","outage","blackout","electricity","grid","energy"], "neg", 60),
    "fuel": (["fuel","petrol","diesel","shortage","price","oil"], "neg", 60),
    "transport": (["strike","accident","traffic","rail","airport","flight"], "neg", 40),
    "economy": (["inflation","economy","gdp","recession","bank","currency","price"], "neg", 30),
    "health": (["hospital","disease","covid","virus","dengue","patients"], "neg", 50),
    "events": (["protest","riot","election","strike","demonstration"], "neg", 20),
    "hazards": (["flood","earthquake","cyclone","disaster","fire","landslide"], "neg", 100),
    "opportunity": (["investment","opportunity","grant","boost","growth","incentive"], "pos", 30),
}

STOPWORDS = set([
    "a","about","above","after","again","against","all","am","an","and","any","are","aren't","as","at","be",
    "because","been","before","being","below","between","both","but","by","can't","cannot","could","couldn't",
    "did","didn't","do","does","doesn't","doing","don't","down","during","each","few","for","from","further",
    "had","hadn't","has","hasn't","have","haven't","having","he","he'd","he'll","he's","her","here","here's",
    "hers","herself","him","himself","his","how","how's","i","i'd","i'll","i'm","i've","if","in","into","is",
    "isn't","it","it's","its","itself","let's","me","more","most","mustn't","my","myself","no","nor","not",
    "of","off","on","once","only","or","other","ought","our","ours","ourselves","out","over","own","same",
    "shan't","she","she'd","she'll","she's","should","shouldn't","so","some","such","than","that","that's",
    "the","their","theirs","them","themselves","then","there","there's","these","they","they'd","they'll",
    "they're","they've","this","those","through","to","too","under","until","up","very","was","wasn't","we",
    "we'd","we'll","we're","we've","were","weren't","what","what's","when","when's","where","where's","which",
    "while","who","who's","whom","why","why's","with","won't","would","wouldn't","you","you'd","you'll",
    "you're","you've","your","yours","yourself","yourselves",
    # Project-specific
    "sri","lanka","media","president","minister","monday","tuesday","wednesday","thursday","friday",
    "saturday","sunday","has","will","its","been","said","million","meta","new","one","first", "adaderana", "hot", "lk", "due",
    "reddit", "people", 
])


def _tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9']{2,}", (text or "").lower()) if t not in STOPWORDS]

def _count_keywords_in_item(item: Dict[str, Any]) -> Counter:
    txt = " ".join(str(item.get(k, "")) for k in ("title","description","source","category"))
    return Counter(_tokenize(txt))

def _compute_raw_scores_for_snapshot(data: List[Dict[str, Any]]) -> Dict[str,float]:
    agg = Counter()
    for it in data:
        agg.update(_count_keywords_in_item(it))
    total = max(len(data), 1)  # avoid division by zero

    scores = {}
    for cat,(keywords,direction,scale) in CATEGORY_CONFIG.items():
        matches = sum(agg.get(k,0) for k in keywords)
        freq = matches/total
        impact = min(1.0,freq*scale)
        raw = max(0.0,100*(1.0-impact)) if direction=="neg" else min(100,100*impact)
        scores[cat] = round(raw,2)
    return scores, agg

def _compute_sentiment(data: List[Dict[str, Any]]) -> float:
    vals=[]
    for it in data:
        s = it.get("sentiment")
        if s is not None:
            try: sv=float(s)
            except: continue
            vals.append(max(0.0,min(100.0,50+sv*50)))
    if not vals: return None
    return round(sum(vals)/len(vals),2)

def _ema(prev: Dict[str,float], curr: Dict[str,float], alpha:float) -> Dict[str,float]:
    if not prev: return curr.copy()
    out={}
    for k,v in curr.items():
        p = prev.get(k,v)
        out[k] = round(alpha*v + (1-alpha)*p,2)
    return out

def push_snapshot(file_path: str) -> Dict[str, Any]:
    """Incrementally update scores using only new snapshot data"""
    global _prev_scores, _last_non_empty_keywords, _last_top_keywords, _last_snapshot_path, _buffer

    path = Path(file_path).resolve()
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except: data=[]
    if not isinstance(data,list): data=[]

    # append snapshot to rolling buffer (allow empty lists so buffer reflects time)
    try:
        _buffer.append(data)
    except Exception:
        pass
    if not data:
        # If we have a DB available and no in-memory prev scores, try to restore
        if _HAS_DB and not _prev_scores:
            try:
                load_latest_snapshot_from_db()
            except Exception:
                pass

        # derive fallback top keywords from the last non-empty counter when needed
        top_keywords = _last_top_keywords or [k for k, _ in _last_non_empty_keywords.most_common(5)]

        # If we still have no prev_scores, return neutral defaults (not an empty dict)
        if not _prev_scores:
            neutral = {k: 50.0 for k in list(CATEGORY_CONFIG.keys()) + ["sentiment"]}
            composite = 50.0
            cat_scores = neutral
        else:
            cat_scores = _prev_scores
            comp_keys = list(CATEGORY_CONFIG.keys()) + ["sentiment"]
            comp_vals = [float(_prev_scores.get(k, 0.0)) for k in comp_keys]
            composite = round(sum(comp_vals) / len(comp_vals), 2) if comp_vals else 50.0

        return {
            "category_scores": cat_scores,
            "composite_national_stability": composite,
            "top_keywords": top_keywords,
            "buffer_size": len(_buffer),
            "total_items_in_buffer": sum(len(s) for s in _buffer if isinstance(s, list)),
            "last_snapshot_path": str(path)
        }

    # Compute raw impact from new snapshot
    raw_scores, snap_kw = _compute_raw_scores_for_snapshot(data)
    sent = _compute_sentiment(data)
    if sent is not None: raw_scores["sentiment"] = sent

    # EMA smoothing
    smoothed = _ema(_prev_scores, raw_scores, _ALPHA)
    _prev_scores = smoothed

    # Update top keywords incrementally
    _last_non_empty_keywords.update(snap_kw)
    top_keywords = [k for k,_ in _last_non_empty_keywords.most_common(5)]
    _last_top_keywords = top_keywords

    # Composite score
    comp_keys = list(CATEGORY_CONFIG.keys()) + ["sentiment"]
    comp_vals = [smoothed.get(k,0) for k in comp_keys]
    composite = round(sum(comp_vals)/len(comp_vals),2)

    # remember last snapshot path
    _last_snapshot_path = str(path)

    # persist to DB (best-effort) so previous state survives restarts
    if _HAS_DB and callable(save_snapshot_to_db):
        try:
            save_snapshot_to_db(smoothed, composite, top_keywords, len(data), str(path))
        except Exception:
            # ignore DB errors
            pass

    return {
        "category_scores": smoothed,
        "composite_national_stability": composite,
        "top_keywords": top_keywords,
        "buffer_size": 1,
        "total_items_in_buffer": len(data),
        "last_snapshot_path": _last_snapshot_path
    }


def get_current_snapshot() -> Dict[str, Any]:
    """Return the current smoothed snapshot suitable for the frontend.

    If in-memory state is empty, try loading from DB. Returns neutral defaults
    when no data is available.
    """
    # ensure we have the latest restored state if possible
    if not _prev_scores and _HAS_DB:
        try:
            load_latest_snapshot_from_db()
        except Exception:
            pass

    # compute total items in buffer
    total_items = 0
    try:
        for s in _buffer:
            total_items += len(s)
    except Exception:
        total_items = 0

    if _prev_scores:
        comp_keys = list(CATEGORY_CONFIG.keys()) + ["sentiment"]
        comp_vals = [float(_prev_scores.get(k, 0.0)) for k in comp_keys]
        composite = round(sum(comp_vals) / len(comp_vals), 2) if comp_vals else 50.0
        return {
            "category_scores": _prev_scores,
            "composite_national_stability": composite,
            "top_keywords": _last_top_keywords or [k for k, _ in _last_non_empty_keywords.most_common(5)],
            "buffer_size": len(_buffer),
            "total_items_in_buffer": total_items,
            "last_snapshot_path": _last_snapshot_path,
        }

    # no previous scores: return neutral defaults
    neutral = {k: 50.0 for k in list(CATEGORY_CONFIG.keys()) + ["sentiment"]}
    return {
        "category_scores": neutral,
        "composite_national_stability": 50.0,
        "top_keywords": _last_top_keywords or [k for k, _ in _last_non_empty_keywords.most_common(5)],
        "buffer_size": len(_buffer),
        "total_items_in_buffer": total_items,
        "last_snapshot_path": _last_snapshot_path,
    }


def get_buffer_status() -> Dict[str, Any]:
    """Return current stored state: previous smoothed scores and top keywords."""
    return {
        "prev_scores": _prev_scores,
        "top_keywords": _last_top_keywords,
        "last_non_empty_keywords": _last_non_empty_keywords.most_common(10)
    }


def load_latest_snapshot_from_db():
    """Attempt to load the latest persisted StabilitySnapshot from the DB
    and restore `_prev_scores`, `_last_non_empty_keywords`, and `_last_top_keywords`.
    This makes smoothing continue across restarts.
    """
    global _prev_scores, _last_non_empty_keywords, _last_top_keywords
    if not _HAS_DB:
        return None
    try:
        rows = get_recent_snapshots(limit=1)
        if not rows:
            return None
        latest = rows[0]
        # restore
        cat_scores = latest.get("category_scores") or {}
        _prev_scores = {k: float(v) for k, v in cat_scores.items()} if isinstance(cat_scores, dict) else {}
        kws = latest.get("top_keywords") or []
        _last_top_keywords = list(kws)
        # rebuild counter from top keywords (approximate)
        _last_non_empty_keywords = Counter()
        for k in kws:
            _last_non_empty_keywords[k] += 1
        return latest
    except Exception:
        return None


def push_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Accept a list of newly inserted news items and update the rolling buffer
    + smoothed scores immediately (used to push realtime updates when DB rows are added).
    """
    global _prev_scores, _last_non_empty_keywords, _last_top_keywords, _last_snapshot_path, _buffer

    data = items or []
    # append as a snapshot so the buffer reflects a time interval containing these items
    try:
        _buffer.append(data)
    except Exception:
        pass

    # aggregate across buffer
    agg = Counter()
    total_items = 0
    for snap in _buffer:
        if not isinstance(snap, list):
            continue
        for it in snap:
            agg.update(_count_keywords_in_item(it))
            total_items += 1

    # compute raw scores based on aggregated buffer
    raw_scores: Dict[str, float] = {}
    if total_items == 0:
        for cat in CATEGORY_CONFIG.keys():
            raw_scores[cat] = 50.0
    else:
        for cat, (keywords, direction, scale) in CATEGORY_CONFIG.items():
            matches = sum(agg.get(k, 0) for k in keywords)
            freq = matches / total_items
            impact = min(1.0, freq * scale)
            raw = max(0.0, 100 * (1.0 - impact)) if direction == "neg" else min(100.0, 100.0 * impact)
            raw_scores[cat] = round(raw, 2)

    # sentiment aggregated across buffer
    sent = _compute_sentiment([it for snap in _buffer for it in (snap or [])]) if total_items else None
    if sent is not None:
        raw_scores["sentiment"] = sent

    # EMA smoothing
    smoothed = _ema(_prev_scores, raw_scores, _ALPHA)
    _prev_scores = smoothed

    # update keyword counters (keep last non-empty)
    snap_kw = Counter()
    for it in data:
        snap_kw.update(_count_keywords_in_item(it))
    if snap_kw:
        _last_non_empty_keywords.update(snap_kw)
        _last_top_keywords = [k for k, _ in _last_non_empty_keywords.most_common(5)]

    # composite score
    comp_keys = list(CATEGORY_CONFIG.keys()) + ["sentiment"]
    comp_vals = [smoothed.get(k, 50.0) for k in comp_keys]
    composite = round(sum(comp_vals) / len(comp_vals), 2) if comp_vals else 50.0

    # persist (best-effort)
    try:
        if _HAS_DB and callable(save_snapshot_to_db):
            save_snapshot_to_db(smoothed, composite, _last_top_keywords, total_items, _last_snapshot_path or "")
    except Exception:
        pass

    return {
        "category_scores": smoothed,
        "composite_national_stability": composite,
        "top_keywords": _last_top_keywords,
        "buffer_size": len(_buffer),
        "total_items_in_buffer": total_items,
        "last_snapshot_path": _last_snapshot_path or "",
    }
