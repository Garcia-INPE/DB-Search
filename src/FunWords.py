
import string

special_chars = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'  # string.ponctuation
chars_to_excl = ["“", "”"]
chars_to_incl = ["\"", "\""]

chars_to_ignore_in_words = chars_to_incl + [":", "-", "–", ",", "."]
words_ok = ["wildland", "behaviour"]
translation_table = str.maketrans(
    special_chars, ' ' * len(special_chars))


def adj_title(txt, del_quotes=False):
    # - (ASCII 45) and - (ASCII 8208) are different
    ret = txt.strip('\"\' ').replace(" ,", ",").replace(" .", ".").replace("::", ":").replace(" :", ":").replace(" for for ", " for ").replace(
        ";", "-").replace("–", "-").replace("—", "-").replace("\n", " ").replace("‐", "-").replace(" -", "-").replace("- ", "-").rstrip('.')
    ret = " ".join(ret.split())
    if del_quotes:
        ret = ret.replace("\"", "")
    return (ret)


# aTitles = df.title
def adj_title_array(aTitles, del_quotes=False):
    ret = [""] * len(aTitles)
    # idx_title=0; title=aTitles[idx_title]
    for idx_title, title in enumerate(aTitles):
        # idx_char=0; char=chars_to_excl[idx_char]
        for idx_char, _ in enumerate(chars_to_excl):
            title = title.replace(
                chars_to_excl[idx_char], chars_to_incl[idx_char])
        ret[idx_title] = adj_title(title, del_quotes)
    return (ret)


def clean_word(word):
    # \W matches any non-alphanumeric character (equivalent to [^a-zA-Z0-9_])
    # \s matches any whitespace character (space, tab, newline, etc.)
    # return (re.sub(r'[^\w\s]', '', word).lower())
    # return (re.sub(r'[^a-zA-Z0-9_-\s]', '', word).lower())
    return (word.translate(translation_table).strip())
