# -*- coding: utf-8 -*-
import json
import re
from datetime import datetime

# --- המוח של שולה: סיווג סמנטי ---
CLASSICS = [
    "מדיאה", "הנפש הטובה מסצ'ואן", "רוזנקרנץ וגילדנשטרן", "בית ברנרדה אלבה",
    "אמא קוראז", "החטא ועונשו", "אנה קרנינה", "סלומה", "מכתב אבוד",
    "הקמצן", "טרטיף", "שייקספיר", "צ'כוב", "מולייר", "סופוקלס"
]

STUDY_MATERIALS = [
    "חשמלית ושמה תשוקה", "כפר", "אם זה אדם", "קרום", "המבול",
    "האבא", "סוס אחד נכנס לבר", "בעלת הארמון", "ילדי הצל", "ביבר הזכוכית"
]

FRINGE_THEATERS = ["הבית", "אינקובטור", "ניקו ניתאי", "קליפה", "החנות", "תמונע", "תוצרת בית", "יפו"]
FRINGE_SHOWS = ["חיה להפליא", "מקום טוב הכל רע", "HOLY CAT", "אנטי אייג'ינג", "בוז'ולה", "הסוף", "מייקל"]


def categorize_show(title, theater):
    if any(f in theater for f in FRINGE_THEATERS) or any(s in title for s in FRINGE_SHOWS) or "אנסמבל" in title:
        return "🎭 שפה בימתית מעניינת"
    if any(s in title for s in STUDY_MATERIALS):
        return "📚 חומר לימוד"
    if any(c in title for c in CLASSICS):
        return "👑 קלאסיקה"
    return "⚪ רגיל"


def parse_smart_date(date_str):
    if not date_str or "בדוק" in date_str or "ראה" in date_str:
        return None
    hebrew_months = {"אפריל": 4, "מאי": 5, "יוני": 6, "יולי": 7}
    for heb, m_num in hebrew_months.items():
        if heb in date_str:
            match = re.search(r'(\d{1,2})\s*(?:ב?-?)' + heb, date_str)
            if match:
                return datetime(2026, m_num, int(match.group(1)))
    match = re.search(r'(\d{1,2})[\./](\d{1,2})(?:[\./](\d{2,4}))?', date_str)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else 2026
        if year < 100:
            year += 2000
        if month in [4, 5, 6, 7]:
            return datetime(year, month, day)
    return None


def process_data():
    try:
        with open('all_theaters_schedule_clean.json', 'r', encoding='utf-8') as f:
            shows = json.load(f)
    except Exception as e:
        print("שגיאה בטעינת הקובץ:", e)
        return []

    filtered_shows = []

    for show in shows:
        raw_date_str = show.get('date', '')
        dt = parse_smart_date(raw_date_str)
        if not dt:
            continue

        weekday = dt.weekday()
        if weekday in [1, 4, 5]:  # סינון שלישי, שישי, שבת
            continue

        category = categorize_show(show.get('title', ''), show.get('theater', ''))
        days_heb = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]

        # --- חילוץ שעות חכם לניקו ניתאי ---
        time_str = show.get('time', '').replace('הצגה קרובה: ', '').strip('| ')
        if "כלול" in time_str or not re.search(r'\d{1,2}:\d{2}', time_str):
            time_match = re.search(r'(\d{1,2}:\d{2})', raw_date_str)
            if time_match:
                time_str = time_match.group(1)
            else:
                time_str = "לא צוין"

        filtered_shows.append({
            "theater": show['theater'],
            "title": show['title'],
            "date": dt.strftime("%d/%m/%Y"),
            "day_name": days_heb[weekday],
            "month": dt.month,
            "time": time_str,
            "link": show.get('link', ''),
            "category": category
        })

    filtered_shows.sort(key=lambda x: datetime.strptime(x['date'], "%d/%m/%Y"))
    return filtered_shows


def generate_html(shows):
    shows_json = json.dumps(shows, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>לוח הצגות למורים - 2026</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: #f0f2f5;
      color: #1a1a2e;
      padding: 24px 16px;
      min-height: 100vh;
    }}

    .container {{ max-width: 1280px; margin: 0 auto; }}

    /* ── כותרת ── */
    .header {{
      text-align: center;
      margin-bottom: 28px;
    }}
    .header h1 {{
      font-size: 28px;
      font-weight: 600;
      color: #1a1a2e;
      margin-bottom: 4px;
    }}
    .header p {{
      font-size: 14px;
      color: #6b7280;
    }}

    /* ── כרטיסי סטטיסטיקה ── */
    .stats-row {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }}
    @media (max-width: 640px) {{
      .stats-row {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    .stat-card {{
      background: white;
      border-radius: 12px;
      border: 1px solid #e5e7eb;
      padding: 16px;
    }}
    .stat-label {{
      font-size: 12px;
      color: #9ca3af;
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .stat-num {{
      font-size: 28px;
      font-weight: 600;
      color: #1a1a2e;
    }}

    /* ── פאנל סינון ── */
    .filters-panel {{
      background: white;
      border-radius: 12px;
      border: 1px solid #e5e7eb;
      padding: 16px 20px;
      margin-bottom: 20px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
    }}
    .search-wrap {{
      flex: 1;
      min-width: 200px;
      position: relative;
    }}
    .search-wrap input {{
      width: 100%;
      padding: 9px 14px 9px 36px;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      font-size: 14px;
      font-family: inherit;
      background: #f9fafb;
      color: #1a1a2e;
      outline: none;
      transition: border-color 0.15s;
    }}
    .search-wrap input:focus {{ border-color: #6366f1; background: white; }}
    .search-icon {{
      position: absolute;
      left: 11px;
      top: 50%;
      transform: translateY(-50%);
      color: #9ca3af;
      font-size: 15px;
      pointer-events: none;
    }}

    .divider {{ width: 1px; height: 32px; background: #e5e7eb; }}
    @media (max-width: 600px) {{ .divider {{ display: none; }} }}

    /* ── פילים ── */
    .pills {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .pill {{
      padding: 7px 16px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 500;
      border: 1px solid #e5e7eb;
      background: #f9fafb;
      color: #6b7280;
      cursor: pointer;
      transition: all 0.15s;
      font-family: inherit;
    }}
    .pill:hover {{ border-color: #d1d5db; color: #374151; }}
    .pill.active {{ background: #1a1a2e; color: white; border-color: #1a1a2e; }}

    /* ── טאבי חודשים ── */
    .month-tabs {{
      display: flex;
      gap: 0;
      border-bottom: 1px solid #e5e7eb;
      margin-bottom: 20px;
    }}
    .mtab {{
      padding: 10px 22px;
      font-size: 14px;
      font-weight: 500;
      font-family: inherit;
      cursor: pointer;
      color: #9ca3af;
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
      transition: all 0.15s;
    }}
    .mtab:hover {{ color: #374151; }}
    .mtab.active {{ color: #1a1a2e; border-bottom-color: #6366f1; }}

    /* ── רשת כרטיסים ── */
    .result-count {{
      font-size: 13px;
      color: #9ca3af;
      margin-bottom: 14px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 14px;
    }}

    /* ── כרטיס הצגה ── */
    .show-card {{
      background: white;
      border-radius: 14px;
      border: 1px solid #e5e7eb;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.12s, box-shadow 0.12s;
      cursor: default;
    }}
    .show-card:hover {{
      transform: translateY(-3px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    }}

    /* פס צבעוני עליון לפי קטגוריה */
    .card-accent {{ height: 4px; width: 100%; }}
    .cat-crown .card-accent  {{ background: #d97706; }}
    .cat-study .card-accent  {{ background: #2563eb; }}
    .cat-fringe .card-accent {{ background: #7c3aed; }}
    .cat-plain .card-accent  {{ background: #d1d5db; }}

    .card-body {{ padding: 14px 16px 10px; flex: 1; }}

    .card-title {{
      font-size: 15px;
      font-weight: 600;
      color: #1a1a2e;
      margin-bottom: 4px;
      line-height: 1.35;
    }}
    .card-theater {{
      font-size: 12px;
      color: #9ca3af;
      margin-bottom: 12px;
    }}

    .card-meta {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; align-items: center; }}

    .chip {{
      font-size: 12px;
      padding: 3px 9px;
      border-radius: 6px;
      font-weight: 500;
      background: #f3f4f6;
      color: #6b7280;
    }}

    .cat-badge {{
      font-size: 11px;
      padding: 3px 9px;
      border-radius: 10px;
      font-weight: 600;
    }}
    .cat-crown  .cat-badge {{ background: #fef3c7; color: #92400e; }}
    .cat-study  .cat-badge {{ background: #dbeafe; color: #1e40af; }}
    .cat-fringe .cat-badge {{ background: #ede9fe; color: #5b21b6; }}
    .cat-plain  .cat-badge {{ background: #f3f4f6; color: #6b7280; }}

    /* ── כפתורי פעולה ── */
    .card-actions {{ display: flex; gap: 8px; padding: 0 16px 14px; }}
    .card-btn {{
      flex: 1;
      padding: 8px 10px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      text-decoration: none;
      text-align: center;
      border: 1px solid #e5e7eb;
      color: #6b7280;
      background: #f9fafb;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.12s;
    }}
    .card-btn:hover {{ background: #f3f4f6; color: #374151; border-color: #d1d5db; }}
    .card-btn.primary {{
      background: #1a1a2e;
      color: white;
      border-color: #1a1a2e;
    }}
    .card-btn.primary:hover {{ background: #2d2d4e; }}

    .empty {{
      grid-column: 1 / -1;
      text-align: center;
      padding: 4rem 1rem;
      color: #9ca3af;
      font-size: 15px;
    }}
  </style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>🎭 לוח הצגות למגמות תיאטרון</h1>
    <p>אפריל – יוני 2026 &nbsp;·&nbsp; ראשון, שני, רביעי, חמישי</p>
  </div>

  <!-- סטטיסטיקות -->
  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-label">סה"כ הצגות</div>
      <div class="stat-num" id="s-total">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">👑 קלאסיקות</div>
      <div class="stat-num" id="s-crown">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">📚 חומר לימוד</div>
      <div class="stat-num" id="s-study">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">🎭 שפה בימתית</div>
      <div class="stat-num" id="s-fringe">—</div>
    </div>
  </div>

  <!-- פאנל סינון -->
  <div class="filters-panel">
    <div class="search-wrap">
      <span class="search-icon">&#9906;</span>
      <input type="text" id="search" placeholder="חיפוש לפי שם הצגה או תיאטרון..." oninput="render()" dir="rtl" />
    </div>
    <div class="divider"></div>
    <div class="pills" id="cat-pills">
      <button class="pill active" onclick="setCat('all', this)">הכל</button>
      <button class="pill" onclick="setCat('👑', this)">👑 קלאסיקות</button>
      <button class="pill" onclick="setCat('📚', this)">📚 חומר לימוד</button>
      <button class="pill" onclick="setCat('🎭', this)">🎭 שפה בימתית</button>
      <button class="pill" onclick="setCat('⚪', this)">⚪ רגיל</button>
    </div>
  </div>

  <!-- טאבי חודשים -->
  <div class="month-tabs">
    <button class="mtab active" onclick="setMonth('all', this)">כל החודשים</button>
    <button class="mtab" onclick="setMonth(4, this)">אפריל</button>
    <button class="mtab" onclick="setMonth(5, this)">מאי</button>
    <button class="mtab" onclick="setMonth(6, this)">יוני</button>
  </div>

  <div class="result-count" id="result-count"></div>
  <div class="grid" id="grid"></div>

</div>

<script>
  const allShows = {shows_json};

  let currentMonth = 'all';
  let currentCat   = 'all';

  function setCat(cat, el) {{
    currentCat = cat;
    document.querySelectorAll('#cat-pills .pill').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
    render();
  }}

  function setMonth(m, el) {{
    currentMonth = m;
    document.querySelectorAll('.mtab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    render();
  }}

  function calLink(show) {{
    const parts = show.date.split('/');
    const ds = parts[2] + parts[1] + parts[0];
    const m  = show.time.match(/(\\d{{1,2}}):(\\d{{2}})/);
    const st = m ? m[1].padStart(2,'0') + m[2] + '00' : '200000';
    const eh = String(Math.min(parseInt(st.substring(0,2)) + 2, 23)).padStart(2,'0');
    const et = eh + st.substring(2);
    const title   = encodeURIComponent(show.title + ' | ' + show.theater);
    const details = encodeURIComponent('סיווג: ' + show.category + '\\n\\nכרטיסים:\\n' + show.link);
    const loc     = encodeURIComponent(show.theater);
    return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${{title}}&dates=${{ds}}T${{st}}/${{ds}}T${{et}}&details=${{details}}&location=${{loc}}`;
  }}

  function catClass(cat) {{
    if (cat.includes('👑')) return 'cat-crown';
    if (cat.includes('📚')) return 'cat-study';
    if (cat.includes('🎭')) return 'cat-fringe';
    return 'cat-plain';
  }}

  function catLabel(cat) {{
    if (cat.includes('👑')) return '👑 קלאסיקה';
    if (cat.includes('📚')) return '📚 חומר לימוד';
    if (cat.includes('🎭')) return '🎭 שפה בימתית';
    return '⚪ רגיל';
  }}

  function render() {{
    const q = document.getElementById('search').value.trim().toLowerCase();

    const filtered = allShows.filter(s => {{
      if (currentMonth !== 'all' && s.month !== currentMonth) return false;
      if (currentCat   !== 'all' && !s.category.includes(currentCat)) return false;
      if (q && !s.title.includes(q) && !s.theater.includes(q)) return false;
      return true;
    }});

    document.getElementById('s-total').textContent  = filtered.length;
    document.getElementById('s-crown').textContent  = filtered.filter(s => s.category.includes('👑')).length;
    document.getElementById('s-study').textContent  = filtered.filter(s => s.category.includes('📚')).length;
    document.getElementById('s-fringe').textContent = filtered.filter(s => s.category.includes('🎭')).length;
    document.getElementById('result-count').textContent = `מציג ${{filtered.length}} הצגות`;

    const grid = document.getElementById('grid');

    if (!filtered.length) {{
      grid.innerHTML = '<div class="empty">לא נמצאו הצגות תואמות לחיפוש</div>';
      return;
    }}

    grid.innerHTML = filtered.map(s => {{
      const cc      = catClass(s.category);
      const ticket  = s.link && s.link !== '-'
        ? `<a href="${{s.link}}" class="card-btn primary" target="_blank">כרטיסים</a>`
        : '';
      return `
        <div class="show-card ${{cc}}">
          <div class="card-accent"></div>
          <div class="card-body">
            <div class="card-title">${{s.title}}</div>
            <div class="card-theater">${{s.theater}}</div>
            <div class="card-meta">
              <span class="chip">${{s.day_name}} ${{s.date}}</span>
              <span class="chip">${{s.time}}</span>
              <span class="cat-badge">${{catLabel(s.category)}}</span>
            </div>
          </div>
          <div class="card-actions">
            <a href="${{calLink(s)}}" class="card-btn" target="_blank">📅 יומן</a>
            ${{ticket}}
          </div>
        </div>`;
    }}).join('');
  }}

  render();
</script>
</body>
</html>"""

    output_file = 'index.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f">>> הלוח נוצר בהצלחה! פתח את: {output_file}")


if __name__ == "__main__":
    filtered_data = process_data()
    if filtered_data:
        generate_html(filtered_data)
