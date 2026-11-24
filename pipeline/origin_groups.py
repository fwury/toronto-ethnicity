"""Grouping of 2021 Census ethnic or cultural origins into broad and sub categories.

Keys are Statistics Canada member IDs from table 98-10-0356-01
("Ethnic or cultural origin (530)" dimension). Only leaf origins are assigned;
StatCan's own subtotal rows (e.g. "British Isles origins") are never summed in.

Counts for a subcategory are the SUM OF RESPONSES of its member origins, not
persons: someone reporting "Irish" and "Scottish" counts twice in
"British and Irish". The map labels dots as "1 dot = 5 responses".
"""

def ids(*parts):
    out = []
    for p in parts:
        if isinstance(p, tuple):
            out.extend(range(p[0], p[1] + 1))
        else:
            out.append(p)
    return out


# (broad, sub) -> list of member IDs. Authoring order does not matter: the
# subcategories within each broad category are sorted by their mapped
# (DA-level) response totals, with the "Other ..." catch-alls last. See
# sub_totals.json, written by build_origin_groups.py.
_FN_KEEP = (7, 5, 80, 13, 66, 30, 11, 10, 64, 21, 26, 81)
GROUPS = {
    # ---------------------------------------------------------------- INDIGENOUS
    ("Indigenous North American", "First Nations"): ids(*_FN_KEEP),
    ("Indigenous North American", "Métis"): ids(128),
    ("Indigenous North American", "Inuit"): ids(125, 126, 127),

    # ---------------------------------------------------- NON-INDIGENOUS N. AMERICAN
    ("Non-Indigenous North American", "Canadian"): ids(
        137, 140, 146, 144, 130, 149, 145, 151, 143, 139, 148, 138, 142, 150,
        152,  # Other North American origins, n.i.e.
    ),
    ("Non-Indigenous North American", "American (USA)"): ids(135),

    # ------------------------------------------------------------------ EUROPEAN
    ("European", "British and Irish"): ids((156, 167), 245),  # + Celtic, n.o.s.
    ("European", "Italian"): ids(204, 207),  # + Sicilian
    ("European", "German"): ids(183, 178, 147, 510, 523, 525),  # Bavarian, Pennsylvania Dutch, Amish, Hutterite, Mennonite
    ("European", "Polish"): ids(238, 235),  # + Kashubian
    ("European", "Portuguese"): ids(206, 199),  # + Azorean
    ("European", "French"): ids((169, 174), 522),  # + Huguenot
    ("European", "Ukrainian"): ids(242, 240),  # + Ruthenian
    ("European", "Russian"): ids(239, 519),  # + Doukhobor
    ("European", "Greek"): ids(203, 416, 418),  # + Cypriot, Greek Cypriot
    ("European", "Spanish"): ids(208, 200, 201, 202),  # + Basque, Catalan, Galician
    ("European", "Northern European"): ids((189, 196)),
    ("European", "Other Western European"): ids(176, 177, 179, 180, 182, 184, 185, 186, 187),
    ("European", "Other Eastern European"): ids(
        234, 221, 216, 222, 228, 237, 231, 241, 247, 230, 236, 233, 219, 232,
        243, 224, 229,  # n.i.e., Transylvanian, Bohemian
    ),
    ("European", "Other Balkan"): ids(218, 212, 223, 215, 214, 225, 220, 226, 217, 213, 211),
    ("European", "Other European"): ids(
        154, 198, 209, 248,  # European / Southern European n.o.s. & n.i.e.
        514,  # Caucasian (White), n.o.s.
        205,  # Maltese
        246,  # Roma
    ),

    # ------------------------------------------------ MIDDLE EASTERN & NORTH AFRICAN
    ("Middle Eastern and North African", "Iranian"): ids(420, 432, 529),  # + Persian, Zoroastrian
    ("Middle Eastern and North African", "Levantine Arab"): ids(428, 434, 430, 423),
    ("Middle Eastern and North African", "Egyptian and Coptic"): ids(358, 517, 386),  # + Nubian
    ("Middle Eastern and North African", "Iraqi, Assyrian and Gulf"): ids(421, 412, 515, 441, 433, 426, 429),
    ("Middle Eastern and North African", "Caucasian (Caucasus)"): ids(411, 413, 417, 415),  # Armenian, Azerbaijani, Georgian, Circassian
    ("Middle Eastern and North African", "Turkish"): ids(437),
    ("Middle Eastern and North African", "Afghan and Central Asian"): ids(
        410, 431, 435, 419, 414, 424, 427, 436, 438, 439, 440,
    ),
    ("Middle Eastern and North African", "Other North African"): ids(361, 362, 354, 355, 363, 356, 360, 364),
    ("Middle Eastern and North African", "Other Arab and Middle Eastern"): ids(
        511, 409, 442,
        425, 528,  # Kurdish, Yazidi
    ),

    # ---------------------------------------------------- AFRICAN & BLACK DIASPORA
    ("African and Black Diaspora", "Black diaspora"): ids(
        308, 512, 132, 131, 370, 133,  # African n.o.s., Black n.o.s., African Canadian/American, Bantu, African Nova Scotian
        405,  # African n.i.e.
    ),
    ("African and Black Diaspora", "Nigerian"): ids(343, 351, 335, 324, 325, 334),  # + Yoruba, Igbo, Edo, Esan, Hausa
    ("African and Black Diaspora", "Somali"): ids(392),
    ("African and Black Diaspora", "Southern African"): ids(393, 402, 368, 381, 383, 384, 385, 391, 398, 401, 403),
    ("African and Black Diaspora", "Other East African"): ids(
        374, 373, 377, 397, 382, 396, 400, 369, 387, 389, 371,
        366,  # Southern or East African, n.o.s.
        375, 372, 367, 404, 378, 395, 399, 394, 379, 390, 376, 388, 357,
    ),
    ("African and Black Diaspora", "Other West and Central African"): ids(
        332, 311, 313, 326, 327, 329,  # Ghanaian, Akan, Ashanti, Ewe, Fante, Ga-Adangbe
        *[i for i in range(310, 353) if i not in (343, 351, 335, 324, 325, 334, 332, 311, 313, 326, 327, 329, 315, 333, 321)],
    ),

    # ----------------------------------------------------------------- CARIBBEAN
    ("Caribbean", "Jamaican"): ids(265, 267),  # + Maroon
    ("Caribbean", "Trinidadian and Tobagonian"): ids(272),
    ("Caribbean", "Guyanese and Indo-Caribbean"): ids(288, 292, 264, 303, 278),  # + Indo-Guyanese, Indo-Caribbean, Surinamese, Arawak
    ("Caribbean", "Other Caribbean"): ids(
        251, 274, 250, 255, 261, 273, 263, 271,
        275, 252, 253, 254, 256, 257, 259, 266, 269, 262, 268,
    ),

    # ------------------------------------------------------------ LATIN AMERICAN
    ("Latin American", "Brazilian"): ids(282),
    ("Latin American", "Mexican"): ids(295),
    ("Latin American", "Colombian"): ids(284),
    ("Latin American", "Other South American"): ids(286, 305, 283, 299, 279, 304, 298, 281, 301, 293),
    ("Latin American", "Central American"): ids(302, 287, 296, 294, 285, 290, 280, 297, 300),
    ("Latin American", "Hispanic Caribbean"): ids(258, 260, 270),
    ("Latin American", "Other Latin American"): ids(277, 289, 291, 306),

    # ---------------------------------------------------------------- EAST ASIAN
    ("East Asian", "Chinese"): ids(471, 474, 487),  # + Hong Konger, Taiwanese
    ("East Asian", "Korean"): ids(481),
    ("East Asian", "Japanese"): ids(478),
    ("East Asian", "Other East Asian"): ids(466, 485, 491),

    # ----------------------------------------------------------- SOUTHEAST ASIAN
    ("Southeast Asian", "Filipino"): ids(472, 476, 475),  # + Ilocano, Igorot
    ("Southeast Asian", "Vietnamese"): ids(490),
    ("Southeast Asian", "Other Southeast Asian"): ids(
        469, 477, 482, 484, 488, 483, 468, 486, 480, 467, 470, 473, 479,
    ),

    # --------------------------------------------------------------- SOUTH ASIAN
    ("South Asian", "Indian"): ids(451, 450, 449, 455, 463, 445, 454),  # + Gujarati, Goan, Malayali, Telugu, Anglo-Indian, Maharashtrian
    ("South Asian", "Pakistani"): ids(457, 453, 459),  # + Kashmiri, Sindhi
    ("South Asian", "Punjabi and Sikh"): ids(458, 527, 452),  # + Jatt
    ("South Asian", "Sri Lankan and Tamil"): ids(461, 462, 460),
    ("South Asian", "Bangladeshi and Bengali"): ids(446, 447),
    ("South Asian", "Tibetan"): ids(489),
    ("South Asian", "Nepali"): ids(456, 448),  # + Bhutanese
    ("South Asian", "Other South Asian"): ids(521, 444, 464),  # Hindu, South Asian n.o.s. & n.i.e.

    # ------------------------------------------------------------------ OCEANIAN
    ("Oceanian", "Australian and New Zealander"): ids(505, 507, 508, 494),
    ("Oceanian", "Pacific Islander"): ids((496, 503), 506),  # + Maori; incl. Indo-Fijian

    # ------------------------------------------------------- JEWISH AND ISRAELI
    ("Jewish and Israeli", "Jewish and Israeli"): ids(524, 422),

    # --------------------------------------------------------------------- OTHER
    ("Other", "Other"): ids(
        407, 492,  # Asian n.o.s. & n.i.e.
        3, 518, 520, 530,  # North American n.o.s., Creole, Eurasian, Other n.i.e.
    ),
}

# Leaf origins deliberately left off the map: purely religious responses.
EXCLUDED = ids(516, 526, 513)  # Christian n.i.e., Muslim, Buddhist

# Origins dropped from the grouping: no published responses in any Toronto DA.
REMOVED = ids(
    *[i for i in range(7, 124) if i not in (9, 20, 29, 37, 60, 63, 71, 79, 84, 93, 95, 108, 115) + _FN_KEEP],
    134, 136, 141,  # Albertan, British Columbian, Gaspesian
    181,  # Flemish
    359,  # Kabyle
    380,  # Malagasy
    315, 333, 321,  # Bamileke, Guinean, Central African
)

BROAD_ORDER = [
    "Indigenous North American", "Non-Indigenous North American", "European",
    "Middle Eastern and North African", "African and Black Diaspora", "Caribbean",
    "Latin American", "East Asian", "Southeast Asian", "South Asian", "Oceanian",
    "Jewish and Israeli", "Other",
]


def _sort_groups():
    """Within each broad category: subcategories by mapped responses, "Other ..." last."""
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "data/sub_totals.json"
    if not p.exists():
        return GROUPS
    tot = json.loads(p.read_text())
    key = lambda k: (BROAD_ORDER.index(k[0]), k[1].startswith("Other"), -tot.get(" / ".join(k), 0))
    return dict(sorted(GROUPS.items(), key=lambda kv: key(kv[0])))


GROUPS = _sort_groups()
