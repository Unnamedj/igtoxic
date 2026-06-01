import re
import unicodedata

MALE_NAMES = {
    'juan', 'carlos', 'jose', 'luis', 'miguel', 'angel', 'david', 'manuel',
    'pedro', 'antonio', 'jorge', 'alejandro', 'fernando', 'rafael', 'alberto',
    'mario', 'andres', 'daniel', 'pablo', 'sergio', 'javier', 'francisco',
    'marcos', 'diego', 'adrian', 'ivan', 'oscar', 'ruben', 'victor', 'jesus',
    'cristian', 'roberto', 'alex', 'martin', 'gustavo', 'eduardo', 'hector',
    'michael', 'james', 'john', 'robert', 'william', 'richard', 'joseph',
    'thomas', 'charles', 'christopher', 'matthew', 'andrew', 'mark', 'steven',
    'kevin', 'brian', 'george', 'xavier', 'kai', 'liam', 'noah', 'oliver',
    'elijah', 'lucas', 'mason', 'ethan', 'aiden', 'ryan', 'jack', 'leo',
    'santiago', 'sebastian', 'nicolas', 'gabriel', 'emilio', 'rodrigo',
    'ignacio', 'mateo', 'tomas', 'franco', 'alan', 'alan', 'raul', 'ernesto',
    'alfredo', 'armando', 'enrique', 'arturo', 'samuel', 'benjamin', 'isaac',
    'aaron', 'adam', 'nathan', 'joshua', 'justin', 'tyler', 'brandon', 'caleb',
    'connor', 'dylan', 'evan', 'jordan', 'kyle', 'logan', 'nathaniel', 'jacob',
}

FEMALE_NAMES = {
    'maria', 'ana', 'laura', 'carmen', 'rosa', 'elena', 'isabel', 'patricia',
    'sandra', 'monica', 'lucia', 'diana', 'andrea', 'alejandra', 'natalia',
    'valeria', 'gabriela', 'daniela', 'carolina', 'paola', 'fernanda',
    'veronica', 'cristina', 'sofia', 'valentina', 'sara', 'paula', 'julia',
    'claudia', 'jessica', 'jennifer', 'emily', 'ashley', 'sarah', 'taylor',
    'madison', 'alyssa', 'samantha', 'elizabeth', 'katherine', 'emma',
    'olivia', 'ava', 'isabella', 'mia', 'lily', 'grace', 'chloe', 'zoey',
    'nora', 'luna', 'camila', 'victoria', 'rebeca', 'beatriz', 'alicia',
    'lorena', 'miriam', 'esther', 'irene', 'eva', 'pilar', 'angeles',
    'leticia', 'mariana', 'adriana', 'fabiola', 'brenda', 'karen', 'vanessa',
    'priscila', 'stefania', 'catalina', 'xiomara', 'guadalupe', 'raquel',
    'nathaly', 'ingrid', 'denise', 'alba', 'lola', 'belen', 'amparo',
    'marisol', 'rocio', 'yolanda', 'susana', 'silvia', 'norma', 'martha',
    'liliana', 'blanca', 'esperanza', 'griselda', 'amanda', 'stephanie',
    'nicole', 'brittany', 'amber', 'megan', 'kayla', 'chelsea', 'rachel',
    'danielle', 'melissa', 'tiffany', 'courtney', 'anna', 'abigail',
}

BRAND_KEYWORDS = {
    'studio', 'agency', 'media', 'digital', 'design', 'brand', 'official',
    'sports', 'football', 'soccer', 'music', 'shop', 'store', 'club', 'team',
    'group', 'photo', 'photography', 'creative', 'productions', 'entertainment',
    'empresa', 'marca', 'tienda', 'negocio', 'servicio', 'corp', 'inc', 'ltd',
    'llc', 'co', 'org', 'noticias', 'news', 'magazine', 'revista', 'fm',
    'radio', 'tv', 'channel', 'canal', 'records', 'management', 'consulting',
    'solutions', 'tech', 'technologies', 'sistemas', 'real', 'estate',
    'inmobiliaria', 'construccion', 'arquitectura', 'restaurant', 'cafe',
    'bar', 'hotel', 'fitness', 'gym', 'coaching', 'academy', 'academia',
    'school', 'escuela', 'foundation', 'fundacion',
}


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize('NFKD', text.lower())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def classify_segment(full_name: str) -> str:
    if not full_name or len(full_name.strip()) < 2:
        return "Segmento Ambiguo"

    name = full_name.strip()
    name_norm = _normalize(name)
    words = name_norm.split()

    if not words:
        return "Segmento Ambiguo"

    # All uppercase multi-word → likely brand
    if name.isupper() and len(words) >= 2:
        return "Marca/Empresa"

    # Brand keyword anywhere in the name
    for word in words:
        clean_word = re.sub(r'[^a-z]', '', word)
        if clean_word in BRAND_KEYWORDS:
            return "Marca/Empresa"

    # Has numbers → username / ambiguous
    if re.search(r'\d', name_norm) and len(words) == 1:
        return "Segmento Ambiguo"

    first = re.sub(r'[^a-z]', '', words[0])

    if not first:
        return "Segmento Ambiguo"

    # Known name lists (highest confidence)
    if first in MALE_NAMES:
        return "Segmento Masculino"
    if first in FEMALE_NAMES:
        return "Segmento Femenino"

    # Suffix-based heuristics (Spanish/Latin patterns)
    FEMININE_SUFFIXES = ('ia', 'ina', 'ita', 'ela', 'uela', 'ette', 'elle', 'lle')
    MASCULINE_SUFFIXES = ('or', 'er', 'on', 'an', 'in', 'us', 'ius')

    for suf in FEMININE_SUFFIXES:
        if first.endswith(suf) and len(first) > len(suf) + 1:
            return "Segmento Femenino"

    if first.endswith('a') and not first.endswith(('ua', 'ea')) and len(first) > 3:
        return "Segmento Femenino"

    for suf in MASCULINE_SUFFIXES:
        if first.endswith(suf) and len(first) > len(suf) + 1:
            return "Segmento Masculino"

    if first.endswith('o') and len(first) > 2:
        return "Segmento Masculino"

    return "Segmento Ambiguo"
