import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def _roc_date_to_western(roc_date_str):
    """Convert '112年10月20日' → '2023/10/20'"""
    m = re.match(r'(\d+)年(\d+)月(\d+)日', roc_date_str.strip())
    if m:
        return f"{int(m.group(1)) + 1911}/{int(m.group(2))}/{int(m.group(3))}"
    return None


def _roc_date_to_academic_year(roc_date_str):
    """Return academic year string like '1121' from ROC date string '112年09月16日'"""
    m = re.match(r'(\d+)年(\d+)月', roc_date_str.strip())
    if not m:
        return ''
    roc_year, month = int(m.group(1)), int(m.group(2))
    if month >= 8:
        return f"{roc_year}1"
    elif month == 1:
        return f"{roc_year - 1}1"
    else:
        return f"{roc_year - 1}2"


def _get_visible_text(td):
    """Extract text from td, skipping white-colored font elements (anti-scraping OO0 trick)"""
    texts = []
    for font in td.find_all('font'):
        color = (font.get('color') or '').lower()
        if color not in ('white', '#ffffff', '#fff'):
            t = font.get_text(strip=True)
            if t:
                texts.append(t)
    if texts:
        return ' '.join(texts).strip()
    return td.get_text(strip=True)


def _counts_to_action(col_names, counts):
    """Convert name+count pairs to action string, e.g. ('嘉獎', 1) → '嘉獎乙次'"""
    num_ch = {1: '乙', 2: '貳', 3: '參', 4: '肆', 5: '伍', 6: '陸', 7: '柒', 8: '捌', 9: '玖'}
    for name, count in zip(col_names, counts):
        if count > 0:
            return f"{name}{num_ch.get(count, str(count))}次"
    return ''


def parse_merit_demerit_records(html):
    """
    解析獎懲紀錄，回傳 [merits, demerits] 各為 list of dict
    """
    soup = BeautifulSoup(html, 'html.parser')
    merits, demerits = [], []
    merit_cols = ['大功', '小功', '嘉獎', '優點']
    demerit_cols = ['大過', '小過', '警告', '缺點']

    current = None
    col_names = None
    awaiting_header = False

    for row in soup.find_all('tr'):
        row_text = row.get_text()
        tds = row.find_all('td')

        if '歷年獎勵明細' in row_text and '懲罰' not in row_text:
            current, col_names, awaiting_header = 'merits', merit_cols, True
        elif '歷年懲罰明細' in row_text and '特殊' not in row_text:
            current, col_names, awaiting_header = 'demerits', demerit_cols, True
        elif '歷年特殊懲罰明細' in row_text:
            current = None
        elif awaiting_header and '發生日期' in row_text:
            awaiting_header = False
        elif current and not awaiting_header and len(tds) >= 12:
            texts = [td.get_text(strip=True) for td in tds]
            date_approved_raw, date_occurred_raw, reason = texts[0], texts[1], texts[2]

            counts = []
            for i in range(4, 8):
                try:
                    counts.append(int(texts[i]))
                except (ValueError, IndexError):
                    counts.append(0)

            revoked_raw = texts[10] if len(texts) > 10 else ''
            date_revoked = None
            if revoked_raw and revoked_raw.lower() != 'n/a':
                date_revoked = _roc_date_to_western(revoked_raw)

            record = {
                'date_occurred': _roc_date_to_western(date_occurred_raw) or date_occurred_raw,
                'date_approved': _roc_date_to_western(date_approved_raw) or date_approved_raw,
                'reason': reason,
                'action': _counts_to_action(col_names, counts),
                'date_revoked': date_revoked,
                'year': _roc_date_to_academic_year(date_occurred_raw),
            }
            (merits if current == 'merits' else demerits).append(record)

    return [merits, demerits]


def parse_absence_records(absence):
    """
    解析出勤紀錄，回傳 list of dict
    每筆 dict: {academic_term, date, weekday, period, cell}
    """
    soup = BeautifulSoup(absence, 'html.parser')
    cell_map = {
        '曠課': '曠', '遲到早退': '遲', '公假': '公',
        '事假': '事', '病假': '病', '喪假': '喪',
        '生理假': '生', '防疫病假': '防病', '防疫事假': '防事',
        '疫苗接種假': '疫', '早讀': '早', '升旗': '旗', '午休': '午',
    }
    records = []

    for row in soup.find_all('tr'):
        tds = row.find_all('td')
        if len(tds) != 7:
            continue
        texts = [_get_visible_text(td) for td in tds]
        # Data rows have a ROC date in the first cell; skip header/other rows
        if not re.match(r'^\d+年\d+月\d+日$', texts[0]):
            continue

        date = _roc_date_to_western(texts[0])
        if not date:
            continue
        weekday = texts[1]
        academic_term = '上' if texts[3] == '1' else '下'
        cell = cell_map.get(texts[5], texts[5])

        for period in texts[6].split(','):
            period = period.strip()
            if period:
                records.append({
                    'academic_term': academic_term,
                    'date': date,
                    'weekday': weekday,
                    'period': period,
                    'cell': cell,
                })

    return records


def parse_curriculum(raw):
    """
    解析課表
    將 response.json 格式轉換成 curriculum.json 格式
    """
    soup = BeautifulSoup(raw, 'html.parser')
    num_to_ch = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五',
                 6: '六', 7: '七', 8: '八', 9: '九'}
    weekdays = ['一', '二', '三', '四', '五']
    curriculum = {}

    # Find the timetable (contains period rows like 第1節)
    timetable = None
    for table in soup.find_all('table'):
        if re.search(r'第\W*1\W*節', table.get_text()):
            timetable = table
            break
    if not timetable:
        return curriculum

    for row in timetable.find_all('tr'):
        cells = row.find_all('td')
        if not cells:
            continue
        m = re.search(r'第\W*(\d+)\W*節', cells[0].get_text())
        if not m:
            continue
        period_ch = num_to_ch.get(int(m.group(1)), m.group(1))

        # cells[0]=period label, cells[1]=label column, cells[2..6]=Mon-Fri
        for i, weekday in enumerate(weekdays):
            idx = i + 2
            if idx >= len(cells):
                break
            cell = cells[idx]
            if '空堂' in cell.get_text():
                continue

            subject_font = cell.find('font', style=lambda s: s and 'darkred' in s)
            if not subject_font:
                continue
            subject = subject_font.get_text(strip=True)
            if not subject:
                continue

            room_font = cell.find('font', style=lambda s: s and 'darkblue' in s)
            room = room_font.get_text(strip=True) if room_font else None

            entry = {'weekday': weekday, 'period': period_ch}
            # Include room only if it's not just the homeroom class name (e.g. 英三甲)
            if room and room[-1] not in '甲乙丙丁':
                entry['room'] = room

            if subject not in curriculum:
                curriculum[subject] = {'count': 0, 'schedule': []}
            curriculum[subject]['count'] += 1
            curriculum[subject]['schedule'].append(entry)

    return curriculum


def parse_semester_grades(grades_data, grade=1):
    """
    解析學期成績
    將 gradeOneJson / gradeTwoJson / gradeThreeJson 格式轉換成 semester_scores 格式

    Args:
        grades_data: 包含 gradeOneJson / gradeTwoJson / gradeThreeJson 的完整資料
        grade: 年級 (1, 2, 3)
    """

def parse_exam_results(exam):
    """
    解析考試成績
    """
