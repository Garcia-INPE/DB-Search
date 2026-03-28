import string

special_chars = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
chars_to_excl = ["“", "”", ":"]
chars_to_incl = ['"', '"', "-"]

chars_to_ignore_in_words = chars_to_incl + [":", "-", "–", ",", "."]
words_ok = ["wildland", "behaviour"]
translation_table = str.maketrans(special_chars, ' ' * len(special_chars))


def adj_title(txt, del_quotes=False):
    ret = txt.strip('\"\' ').replace(" ,", ",").replace(" .", ".").replace("::", ":").replace(" :", ":").replace(" for for ", " for ").replace(
        ";", "-").replace("–", "-").replace("—", "-").replace("\n", " ").replace("‐", "-").replace(" -", "-").replace("- ", "-").rstrip('.')
    ret = " ".join(ret.split())
    if del_quotes:
        ret = ret.replace('"', "")
    return ret

# aTitles = PAPERS.TITLE
def adj_title_array(aTitles, del_quotes=False):
    ret = [""] * len(aTitles)
    idx_title = 0; title = aTitles[idx_title]
    for idx_title, title in enumerate(aTitles):
        idx_char = 0; 
        for idx_char, _ in enumerate(chars_to_excl):
            title = title.replace(chars_to_excl[idx_char], chars_to_incl[idx_char])
        ret[idx_title] = adj_title(title, del_quotes)
    return ret


def clean_word(word):
    return word.translate(translation_table).strip()


def get_db_name(fname):
    db_name = fname.lstrip().upper()
    if db_name.startswith("ACM"):
        db_name = "ACM_DL"
    elif db_name.startswith("GOOGLESCHOLAR"):
        db_name = "SCHOLA"
    elif db_name.startswith("IEEE"):
        db_name = "IEEE_X"
    elif db_name.startswith("SCIENCEDIRECT"):
        db_name = "SC_DIR"
    elif db_name.startswith("SEMANTICSCHOLAR"):
        db_name = "SEMAN"
    elif db_name.startswith("SCOPUS"):
        db_name = "SCOPUS"
    elif db_name.startswith("SPRINGER"):
        db_name = "SPRING"
    elif db_name.startswith("TAYLOR"):
        db_name = "TAYFRA"
    elif db_name.startswith("WILEY"):
        db_name = "WILEYL"    
    return db_name
