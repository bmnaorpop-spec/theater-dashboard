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
    if not date_str or "בדוק" in date_str or "ראה" in date_str: return None
    hebrew_months = {"אפריל": 4, "מאי": 5, "יוני": 6, "יולי": 7}
    for heb, m_num in hebrew_months.items():
        if heb in date_str:
            match = re.search(r'(\d{1,2})\s*(?:ב?-?)' + heb, date_str)
            if match: return datetime(2026, m_num, int(match.group(1)))
    match = re.search(r'(\d{1,2})[\./](\d{1,2})(?:[\./](\d{2,4}))?', date_str)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else 2026
        if year < 100: year += 2000
        if month in [4, 5, 6, 7]: return datetime(year, month, day)
    return None

def process_data():
    try:
        with open('all_theaters_schedule.json', 'r', encoding='utf-8') as f:
            shows = json.load(f)
    except Exception as e:
        print("שגיאה בטעינת הקובץ:", e)
        return []

    filtered_shows = []
    
    for show in shows:
        raw_date_str = show.get('date', '')
        dt = parse_smart_date(raw_date_str)
        if not dt: continue
            
        weekday = dt.weekday()
        if weekday in [1, 4, 5]: continue # סינון שלישי, שישי, שבת
            
        category = categorize_show(show.get('title', ''), show.get('theater', ''))
        days_heb = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
        
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
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>לוח הצגות למורים - 2026</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .filters {{ display: flex; gap: 15px; margin-bottom: 20px; justify-content: center; flex-wrap: wrap; background: #e8f4f8; padding: 15px; border-radius: 8px; }}
            select {{ padding: 10px; border-radius: 5px; border: 1px solid #ccc; font-size: 16px; font-family: inherit; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: right; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #3498db; color: white; font-weight: bold; position: sticky; top: 0; }}
            tr:hover {{ background-color: #f1f1f1; }}
            a.btn {{ display: inline-block; padding: 6px 12px; background-color: #34495e; color: white; border-radius: 4px; text-decoration: none; font-size: 14px; font-weight: bold; text-align: center; }}
            a.btn:hover {{ background-color: #2c3e50; }}
            a.btn-cal {{ background-color: #4285F4; }}
            a.btn-cal:hover {{ background-color: #357ae8; }}
            .cat-crown {{ font-weight: bold; color: #d35400; background-color: #fff3e0; }}
            .cat-study {{ font-weight: bold; color: #2980b9; background-color: #eaf2f8; }}
            .cat-fringe {{ font-weight: bold; color: #8e44ad; background-color: #f4ecf7; }}
            .stats {{ text-align: center; color: #7f8c8d; margin-bottom: 20px; }}
            .actions {{ display: flex; gap: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎭 לוח הצגות למגמות תיאטרון (אפריל - יוני 2026)</h1>
            <p class="stats">הצגות מסוננות (ראשון, שני, רביעי, חמישי בלבד)</p>
            <div class="filters">
                <select id="monthFilter" onchange="renderTable()">
                    <option value="all">🗓️ כל החודשים</option>
                    <option value="4">אפריל</option>
                    <option value="5">מאי</option>
                    <option value="6">יוני</option>
                </select>
                <select id="catFilter" onchange="renderTable()">
                    <option value="all">🏷️ כל הקטגוריות</option>
                    <option value="👑 קלאסיקה">👑 קלאסיקות</option>
                    <option value="📚 חומר לימוד">📚 חומרי לימוד</option>
                    <option value="🎭 שפה בימתית מעניינת">🎭 שפה בימתית מעניינת (פרינג')</option>
                    <option value="⚪ רגיל">⚪ הצגות רגילות</option>
                </select>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>תאריך</th>
                        <th>יום</th>
                        <th>שעה</th>
                        <th>שם ההצגה</th>
                        <th>תיאטרון</th>
                        <th>קטגוריה</th>
                        <th>פעולות</th>
                    </tr>
                </thead>
                <tbody id="tableBody"></tbody>
            </table>
        </div>
        <script>
            const allShows = {shows_json};
            function createGoogleCalendarLink(show) {{
                let dateParts = show.date.split('/');
                let dateStr = dateParts[2] + dateParts[1] + dateParts[0]; 
                let startTime = "200000"; 
                let timeMatch = show.time.match(/(\\d{{1,2}}):(\\d{{2}})/);
                if (timeMatch) {{ startTime = timeMatch[1].padStart(2, '0') + timeMatch[2] + "00"; }}
                let startHour = parseInt(startTime.substring(0,2));
                let endHour = (startHour + 2).toString().padStart(2, '0');
                if (parseInt(endHour) >= 24) endHour = "23"; 
                let endTime = endHour + startTime.substring(2);
                let dates = `${{dateStr}}T${{startTime}}/${{dateStr}}T${{endTime}}`;
                let title = encodeURIComponent(`${{show.title}} | ${{show.theater}}`);
                let details = encodeURIComponent(`סיווג: ${{show.category}}\\n\\nלהזמנת כרטיסים ופרטים:\\n${{show.link}}`);
                let loc = encodeURIComponent(show.theater);
                return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${{title}}&dates=${{dates}}&details=${{details}}&location=${{loc}}`;
            }}
            function renderTable() {{
                const monthFilter = document.getElementById('monthFilter').value;
                const catFilter = document.getElementById('catFilter').value;
                const tbody = document.getElementById('tableBody');
                tbody.innerHTML = "";
                let count = 0;
                allShows.forEach(show => {{
                    if (monthFilter !== 'all' && show.month.toString() !== monthFilter) return;
                    if (catFilter !== 'all' && show.category !== catFilter) return;
                    count++;
                    const tr = document.createElement('tr');
                    let rowClass = '';
                    if (show.category.includes('👑')) rowClass = 'cat-crown';
                    if (show.category.includes('📚')) rowClass = 'cat-study';
                    if (show.category.includes('🎭')) rowClass = 'cat-fringe';
                    let calLink = createGoogleCalendarLink(show);
                    tr.className = rowClass;
                    tr.innerHTML = `
                        <td>${{show.date}}</td>
                        <td>${{show.day_name}}</td>
                        <td>${{show.time}}</td>
                        <td><strong>${{show.title}}</strong></td>
                        <td>${{show.theater}}</td>
                        <td>${{show.category}}</td>
                        <td class="actions">
                            <a href="${{calLink}}" class="btn btn-cal" target="_blank" title="הוסף ליומן גוגל">📅 ליומן</a>
                            ${{show.link && show.link !== '-' ? `<a href="${{show.link}}" class="btn" target="_blank">כרטיסים</a>` : ''}}
                        </td>
                    `;
                    tbody.appendChild(tr);
                }});
                document.querySelector('.stats').innerText = `מציג ${{count}} הופעות שעמדו בסינון`;
            }}
            renderTable();
        </script>
    </body>
    </html>
    """
    
    output_file = 'index.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f">>> הלוח נוצר בהצלחה! פתח את: {{output_file}}")

if __name__ == "__main__":
    filtered_data = process_data()
    if filtered_data:
        generate_html(filtered_data)
