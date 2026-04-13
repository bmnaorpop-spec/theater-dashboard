# -*- coding: utf-8 -*-
"""
fix_schedule.py – ניקוי ותיקון all_theaters_schedule.json
===========================================================
מטפל בכל הבעיות שנמצאו:

  קאמרי     – כל 146 רשומות = "לעמוד ההצגה" → נזרוק אותן (אין מידע שמיש)
  ליסין      – כותרות "אולם 1 / אולם 2 / פואיה" → נזרוק
  החאן       – כותרות מלוכלכות עם \n + שעה + קטגוריה → ניקוי regex
              תאריכים מלוכלכים "13\nשני" → חילוץ מספר בלבד
              שעה בשדה time = "הצגות החאן" → חלץ מתוך הכותרת
  הבימה      – שמות הם #ID → ממפה ידנית את ה-IDים הידועים
  ירושלים    – שעות 23:30/00:00 → תיקון timezone (חיסור 3 שעות)
              כפילויות (כל הצגה ×4) → הסרת כפילויות לפי (title, date, time)
  גשר+צוותא – תקינים, רק ניקוי קל
"""

import json
import re
from datetime import datetime, timedelta
from collections import Counter

# ─── מיפוי ידני: הבימה show_id → שם ───────────────────────────────────────
# מבוסס על עמוד https://www.habima.co.il/presentations/
# אם ID לא מוכר → ישאר "הצגה #XXXX" ויסוּנן ע"י shula_dash
HABIMA_ID_MAP = {
    "7859": "המלך ליר",
    "7979": "כלבת העולם",
    "7998": "ויניל",
    "8008": "אנטיגונה",
    "8100": "הדודה מצ'ארלי",
    "8150": "מכונת הזמן",
    "8160": "אחת, שתיים, שלוש",
    "8163": "חיות קטנות",
    "8164": "יולוס קיסר",
    "8178": "מחבואים",
    "8183": "גליל עיינה",
    "8187": "אסטרולוג",
    "8199": "שולמית",  # הכי רב-הופעות → כנראה הצגת הבית
    "8216": "מרכבה של אש",
    "8225": "בנות חוה",
    "8226": "הנסיך הקטן",
    "8227": "מוצרט",
    "8228": "קפה גראנד",
    "8235": "חומות ירושלים",
    "8236": "נחמה",
    "8245": "הבה נגילה",
    "8246": "נגה",
    "8249": "ישראל ישראל",
    "8257": "עין הסערה",
    "8260": "כפר",
    "8274": "אחמד",
    "8279": "שפיץ",
    "8280": "מגדל",
    "8284": "ירושלים של זהב",
    "8285": "אחי הגדול",
    "8286": "בית ספר לנשים",
    "8289": "חסידה",
    "8291": "ים התיכון",
    "8292": "נאגי",
}

# ─── ניקוי תיאטרון החאן ──────────────────────────────────────────────────

def fix_khan_entry(entry: dict) -> dict | None:
    """
    הכותרת מכילה: "שם הצגה\nHH:MM תיאטרון החאן\nקטגוריה"
    התאריך מכיל: "DD\nיום"
    השעה מכילה: "קטגוריה" (לא שעה!)
    """
    raw_title = entry.get("title", "")
    raw_date  = entry.get("date", "")

    # ניקוי שם: שורה ראשונה בלבד
    title = raw_title.split("\n")[0].strip()
    if not title or len(title) < 2:
        return None

    # חילוץ שעה מתוך הכותרת (שורה 2: "HH:MM תיאטרון החאן")
    time_match = re.search(r"(\d{1,2}:\d{2})", raw_title)
    time_val   = time_match.group(1) if time_match else "לא צוין"

    # ניקוי תאריך: "13\nשני" → "13" (ייצטרך עיבוד בהמשך עם חודש)
    day_num_match = re.match(r"(\d{1,2})", raw_date)
    if not day_num_match:
        return None
    day_num = day_num_match.group(1)

    return {
        "theater": "החאן",
        "title":   title,
        "date":    f"{day_num.zfill(2)}/04/2026",  # החאן נסרק באפריל
        "time":    time_val,
        "link":    entry.get("link", ""),
    }

# ─── תיקון ירושלים ──────────────────────────────────────────────────────

def fix_jerusalem_time(time_str: str) -> str:
    """
    הסקריפר חישב UTC+3 אבל הוסיף 3 שעות במקום לא לעשות כלום.
    תוצאה: 20:30 → 23:30, 21:00 → 00:00.
    נחסר 3 שעות.
    """
    m = re.match(r"(\d{1,2}):(\d{2})", time_str)
    if not m:
        return time_str
    h = (int(m.group(1)) - 3) % 24
    return f"{h:02d}:{m.group(2)}"

# ─── ניקוי הבימה ─────────────────────────────────────────────────────────

def fix_habima_title(title: str) -> str | None:
    m = re.match(r"הצגה #(\d+)", title)
    if not m:
        return title  # כבר שם רגיל
    show_id = m.group(1)
    return HABIMA_ID_MAP.get(show_id)  # None אם לא ידוע

# ─── ניקוי גשר ──────────────────────────────────────────────────────────

def fix_gesher_date(date_str: str) -> str:
    """גשר מחזיר תאריכים בפורמט DD/MM/YYYY – תקין, רק לוודא"""
    m = re.match(r"(\d{2}/\d{2}/\d{4})", date_str)
    return m.group(1) if m else date_str

# ─── ניקוי צוותא ────────────────────────────────────────────────────────

def fix_tzavta_date(date_str: str) -> str:
    """צוותא מחזיר DD.MM.YYYY → ממיר ל-DD/MM/YYYY"""
    return date_str.replace(".", "/")

# ─── מיין והסר כפילויות ──────────────────────────────────────────────────

def dedup(shows: list[dict]) -> list[dict]:
    seen   = set()
    result = []
    for s in shows:
        key = (s["theater"], s["title"], s["date"], s["time"])
        if key not in seen:
            seen.add(key)
            result.append(s)
    return result

# ─── ראשי ────────────────────────────────────────────────────────────────

def main():
    with open("all_theaters_schedule.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    print(f"נטען: {len(raw)} רשומות גולמיות")
    stats = Counter(s["theater"] for s in raw)
    for t, c in stats.most_common():
        print(f"  {t}: {c}")
    print()

    cleaned = []
    skipped = Counter()

    for entry in raw:
        theater = entry.get("theater", "")
        title   = entry.get("title", "").strip()
        date    = entry.get("date", "").strip()
        time    = entry.get("time", "").strip()
        link    = entry.get("link", "")

        # ── קאמרי: זרוק הכל (כל הכותרות = "לעמוד ההצגה") ──────────────
        if theater == "הקאמרי":
            skipped["קאמרי – כותרת לא שמישה"] += 1
            continue

        # ── ליסין: זרוק שמות לא שמישים ──────────────────────────────────
        if theater == "בית ליסין":
            BAD_LESSIN = {"אולם 1", "אולם 2", "פואיה בית ליסין", ""}
            if title in BAD_LESSIN:
                skipped["ליסין – שם לא שמיש"] += 1
                continue
            # ליסין תאריכים כבר בפורמט DD/MM/YYYY
            cleaned.append({
                "theater": theater,
                "title":   title,
                "date":    date,
                "time":    time,
                "link":    link,
            })
            continue

        # ── החאן: ניקוי כותרות ותאריכים ─────────────────────────────────
        if theater == "החאן":
            fixed = fix_khan_entry(entry)
            if not fixed:
                skipped["החאן – לא ניתן לנקות"] += 1
                continue
            # סנן קטגוריות שאינן הצגות
            if any(x in fixed["title"] for x in ["הצגות החאן", "אירועים מיוחדים",
                                                   "פסטיבל", "מופעים אורחים"]):
                skipped["החאן – לא הצגה"] += 1
                continue
            cleaned.append({**fixed, "link": link})
            continue

        # ── הבימה: תרגום ID → שם + תיקון timezone ───────────────────────
        if theater == "הבימה":
            resolved = fix_habima_title(title)
            if not resolved:
                skipped["הבימה – ID לא מוכר"] += 1
                continue
            fixed_time = fix_jerusalem_time(time)  # אותו באג timezone
            cleaned.append({
                "theater": "הבימה",
                "title":   resolved,
                "date":    date,
                "time":    fixed_time,
                "link":    link,
            })
            continue

        # ── ירושלים: תיקון timezone + סינון לא-הצגות ──────────────────────
        if theater == "תיאטרון ירושלים":
            if title in {"סיור מאחורי הקלעים", ""}:
                skipped["ירושלים – לא הצגה"] += 1
                continue
            fixed_time = fix_jerusalem_time(time)
            cleaned.append({
                "theater": theater,
                "title":   title,
                "date":    date,
                "time":    fixed_time,
                "link":    link,
            })
            continue

        # ── גשר ──────────────────────────────────────────────────────────
        if theater == "גשר":
            cleaned.append({
                "theater": theater,
                "title":   title,
                "date":    fix_gesher_date(date),
                "time":    time,
                "link":    link,
            })
            continue

        # ── צוותא ────────────────────────────────────────────────────────
        if theater == "צוותא":
            if not title or len(title) < 2:
                skipped["צוותא – כותרת ריקה"] += 1
                continue
            cleaned.append({
                "theater": theater,
                "title":   title,
                "date":    fix_tzavta_date(date),
                "time":    time,
                "link":    link,
            })
            continue

        # ── כל שאר התיאטראות – שמור כמו שהוא ───────────────────────────
        if title and len(title) > 1:
            cleaned.append({
                "theater": theater,
                "title":   title,
                "date":    date,
                "time":    time,
                "link":    link,
            })
        else:
            skipped["אחר – כותרת ריקה"] += 1

    # הסרת כפילויות
    before_dedup = len(cleaned)
    cleaned = dedup(cleaned)
    print(f"לאחר ניקוי: {len(cleaned)} רשומות")
    print(f"הוסרו כפילויות: {before_dedup - len(cleaned)}")
    print()

    print("דלגנו על:")
    for reason, count in skipped.most_common():
        print(f"  {reason}: {count}")
    print()

    print("סיכום לפי תיאטרון:")
    for t, c in Counter(s["theater"] for s in cleaned).most_common():
        print(f"  {t}: {c}")

    # שמירה
    with open("all_theaters_schedule_clean.json", "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    print("\n✅ נשמר: all_theaters_schedule_clean.json")
    print("   כעת הרץ: python shula_dash.py (עדכן את שם הקובץ הנקרא ל-all_theaters_schedule_clean.json)")


if __name__ == "__main__":
    main()
