# Domain notes:
# - YMCA was the old name for Springfield College (Springfield, MA)
# - Midwest, Great Lakes, South, Pacific Coast, East are temporary teams from
#   the 1942 and 1947 outdoor men's 4x400m
# - GBR: Great Britain and JAM: Jamaica are international entries, not schools
# - Monmouth/Illinois is Monmouth College (IL), not Monmouth University (NJ)
# - Penn College = William Penn University (Iowa)
# - USF = University of San Francisco in all cases
# - St. Francis = St. Francis University of Loretto, PA in all cases
# - LIU: Before 2019, LIU Post and LIU Brooklyn were separate teams.
#   After 2019, they merged into LIU Sharks. All "LIU" rows (without qualifier)
#   are LIU Brooklyn.

SCHOOL_TYPOS = {
    'ACU': 'Abilene Christian',
    'Adolphus': 'Gustavus Adolphus',
    'Alababa': 'Alabama',
    'Albama': 'Alabama',
    'American U': 'American',
    'Appy': 'Appalachian State',
    'Appalacian State': 'Appalachian State',
    'Aubuurn': 'Auburn',
    'Austin-Peay': 'Austin Peay',
    'BU': 'Boston University',
    'Boston U': 'Boston University',
    'Baldwin-Wallace': 'Baldwin-Wallace',
    'Balyor': 'Baylor',
    'Boise': 'Boise State',
    'Bowling Green': 'Bowling Green State',
    'Cal': 'California',
    'Cal Poly/SLO': 'Cal Poly SLO',
    'Cemson': 'Clemson',
    'Colorodo State': 'Colorado State',
    'De Paul': 'DePaul',
    'East Tennessee': 'East Tennessee State',
    'ETSU': 'East Tennessee State',
    'FDU': 'Fairleigh Dickinson',
    'Floridal': 'Florida',
    'GM': 'George Mason',
    'Illinos': 'Illinois',
    'Illlinois': 'Illinois',
    'Indy': 'Indiana',
    'LA State': 'Cal State LA',
    'Lousiana-Monroe': 'Louisiana-Monroe',
    'Maryland-Eastern Shore': 'Maryland Eastern Shore',
    'Massachussetts': 'Massachusetts',
    'Middle Tennessee': 'Middle Tennessee State',
    'Misssissippi State': 'Mississippi State',
    'Nebrasla': 'Nebraska',
    'Oregon (all frosh)': 'Oregon',
    'Oregpm': 'Oregon',
    'PennState': 'Penn State',
    'Pitt': 'Pittsburgh',
    'Prairie View': 'Prairie View A&M',
    'SLO': 'Cal Poly SLO',
    'Sam Houston': 'Sam Houston State',
    "St. John's (N.Y.)": "St. John's",
    "St. John's": "St. John's",
    "Saint Joseph's": "St. Joseph's",
    'Tenn': 'Tennessee',
    'Tennesee': 'Tennessee',
    'Texas A&M (all frosh)': 'Texas A&M',
    'UConn': 'Connecticut',
    'Texas A&M CC': 'Texas A&M-Corpus Christi',
    'Texas A&M/CC': 'Texas A&M-Corpus Christi',
    'Texas Southern (Nigeria)': 'Texas Southern',
    "Texas Southern' (Nigeria)": 'Texas Southern',
    'Northwestern Louisiana': 'Northwestern State',
    'UT Pan American': 'UT Pan-American',
    'UTA': 'UT Arlington',
    'UTRGV': 'UT-Rio Grande Valley',
    'Vanderbillt': 'Vanderbilt',
    'Vill': 'Villanova',
    'West Chester State': 'West Chester',
    'WIchita State': 'Wichita State',
    'Winston-Salem': 'Winston-Salem',
    'Wisconsin-LaCrosse': 'Wisconsin-La Crosse',
    'UW-La Crosse': 'Wisconsin-La Crosse',
    'Austin‑Peay': 'Austin Peay',
    'Baldwin‑Wallace': 'Baldwin-Wallace',
    'Winston‑Salem': 'Winston-Salem',
    'Arkansas–Little Rock': 'Arkansas-Little Rock',
    'Arkansas–Pine Bluff': 'Arkansas-Pine Bluff',
    'Illinois–Chicago': 'Illinois-Chicago',
    'Louisiana–Lafayette': 'Louisiana-Lafayette',
    'Louisiana': 'Louisiana-Lafayette',
    'Louisiana–Monroe': 'Louisiana-Monroe',
    'Lousiana–Monroe': 'Louisiana-Monroe',
    'Loyola/Chicago': 'Loyola-Chicago',
    'Loyola': 'Loyola-Chicago',
    'Loyola/LA': 'Loyola Marymount',
    'Maryland–Eastern Shore': 'Maryland Eastern Shore',
    'Nebraska–Omaha': 'Nebraska-Omaha',
    'Omaha': 'Nebraska-Omaha',
    'Texas A&M–Corpus Christi': 'Texas A&M-Corpus Christi',
    'Wisconsin–La Crosse': 'Wisconsin-La Crosse',
    'Wisconsin–LaCrosse': 'Wisconsin-La Crosse',
    'Wisconsin–Milwaukee': 'Wisconsin-Milwaukee',
    "St. John\u2019s": "St. John's",
    "St. Joseph\u2019s": "St. Joseph's",
    "St. Augustine\u2019s": "St. Augustine's",
    "Mt. St. Mary\u2019s": "Mt. St. Mary's",
    '—Mississippi State': 'Mississippi State',
    'LSU¶': 'LSU',
    'TCU¶': 'TCU',
    "Hawai\u2018i": "Hawai'i",
    'San Jos\u00e9 State': 'San Jose State',
    'Notre Dame.': 'Notre Dame',
    'Oregon.': 'Oregon',
    'Farleigh Dickinson': 'Fairleigh Dickinson',
    "Mount St. Mary's": "Mt. St. Mary's",
    "Saint Augustine's": "St. Augustine's",
    "Saint Francis (Pa.)": "St. Francis (Pa.)",
    'St Olaf': 'St. Olaf',
    '-Mississippi State': 'Mississippi State',
    'Iowa 30?': 'Iowa',
    'Mia-SA': 'Miami',
    "So in '43": 'Pacific',
    "So in \u201943": 'Pacific',
    'Rod Purdue': 'Purdue',
    'Central Florida': 'UCF',
    'Miami': 'Miami (Fla.)',
    'Miami/Ohio': 'Miami (Ohio)',
    'UMass': 'Massachusetts',
    'UNC Greensboro': 'UNCG',
    'UNC Wilmington': 'UNC-Wilmington',
    'Fisk (Tenn.)': 'Fisk',
    'Grambling': 'Grambling State',
    'North Central College': 'North Central',
    'N.C. Central': 'North Carolina Central',
    'Sac State': 'Sacramento State',
    'Redlands (Calif.)': 'Redlands',
    'Southern Mississippi': 'Southern Miss',
    'Texas-Arlington': 'UT Arlington',
    'UT San Antonio': 'UTSA',
    'UCI': 'UC Irvine',
    'UCSB': 'UC Santa Barbara',
    'LSU': 'Louisiana State',
    'ULM': 'Louisiana-Monroe',
    'USC': 'Southern California',
    'Ole Miss': 'Mississippi',
    'Penn': 'Pennsylvania',
    'Catholic U': 'Catholic (D.C.)',
    'Ohio U': 'Ohio',
    'Little Rock': 'Arkansas-Little Rock',
    'Monmouth/Illinois': 'Monmouth College',
    'Mt Union': 'Mount Union',
    'Oxy': 'Occidental',
    'Southern U': 'Southern',
    'Penn College': 'William Penn',
    'USF': 'University of San Francisco',
    'San Francisco': 'University of San Francisco',
    'St. Francis': 'St. Francis (Pa.)',
    'Cal Poly': 'Cal Poly SLO',
    'BC': 'Boston College',
    'Army': 'Army West Point',
    'Wheaton': 'Wheaton (Ill.)',
    'Xavier/New Orleans': 'Xavier University of Louisiana',
    'Miss State': 'Mississippi State',
    'Long Beach St.': 'Long Beach State',
    'Washington St.': 'Washington State',
    'Southern Miss.': 'Southern Miss',
    'Colorado St.': 'Colorado State',
    'CSUN': 'Cal State Northridge',
    'CW Post': 'LIU Post',
    'Houston Baptist': 'Houston Christian',
    'UMKC': 'Kansas City',
    'Kent': 'Kent State',
    'UMES': 'Maryland Eastern Shore',
    'VCU': 'Virginia Commonwealth',
    'Western Maryland': 'McDaniel',
    'West Texas State': 'West Texas A&M',
}

CLASS_MAP = {
    'Fr': 'freshman',
    'So': 'sophomore',
    'Jr': 'junior',
    'Sr': 'senior',
    'Fr-Sr': 'senior',
    'So-Jr': 'junior',
    'Jr-Sr': 'senior',
    'FR': 'freshman',
    'SO': 'sophomore',
    'JR': 'junior',
    'SR': 'senior',
    'fr': 'freshman',
    'so': 'sophomore',
    'jr': 'junior',
    'sr': 'senior',
    'St': 'senior',
    'Jfr': 'junior',
    'S0': 'sophomore',
}


def clean_school_name(school: str, year: int = None) -> str:
    import re
    school = re.sub(r'\.{2,}', '', school).strip()
    school = school.rstrip('*').strip()
    school = school.rstrip('\u00b6').strip()
    school = SCHOOL_TYPOS.get(school, school)
    if school == 'LIU':
        school = 'LIU Brooklyn' if year is None or year < 2019 else 'LIU'
    if school in ('UT-Rio Grande Valley', 'UT-Pan American', 'UT Pan-American'):
        school = 'UT-Pan American' if year is None or year <= 2015 else 'UT-Rio Grande Valley'
    return school


def parse_class(class_str: str) -> str:
    import re
    if not class_str:
        return None
    class_str = class_str.strip()
    if class_str in CLASS_MAP:
        return CLASS_MAP[class_str]
    for key, val in CLASS_MAP.items():
        if key in class_str:
            return val
    return None

