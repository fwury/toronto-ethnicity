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


# (broad, sub) -> list of member IDs
GROUPS = {
    # ---------------------------------------------------------------- INDIGENOUS
    ("Indigenous North American", "First Nations"): ids(
        5,  # North American Indigenous, n.o.s.
        *[i for i in range(7, 124) if i not in (9, 20, 29, 37, 60, 63, 71, 79, 84, 93, 95, 108, 115)],
    ),
    ("Indigenous North American", "Métis"): ids(128),
    ("Indigenous North American", "Inuit"): ids(125, 126, 127),

    # ---------------------------------------------------- NON-INDIGENOUS N. AMERICAN
    ("Non-Indigenous North American", "Canadian"): ids(
        137, 134, 136, 138, 142, 143, 144, 145, 146, 148, 150,  # Canadian + provincial
        151,  # United Empire Loyalist
        152,  # Other North American origins, n.i.e.
    ),
    ("Non-Indigenous North American", "French North American"): ids(140, 149, 130, 139, 141),
    ("Non-Indigenous North American", "American (USA)"): ids(135),

    # ------------------------------------------------------------------ EUROPEAN
    ("European", "British and Irish"): ids((156, 167), 245),  # + Celtic, n.o.s.
    ("European", "French"): ids((169, 174), 522),  # + Huguenot
    ("European", "German"): ids(183, 178, 147, 510, 523, 525),  # Bavarian, Pennsylvania Dutch, Amish, Hutterite, Mennonite
    ("European", "Other Western European"): ids(176, 177, 179, 180, 181, 182, 184, 185, 186, 187),
    ("European", "Northern European"): ids((189, 196)),
    ("European", "Polish"): ids(238, 235),  # + Kashubian
    ("European", "Russian"): ids(239, 519),  # + Doukhobor
    ("European", "Ukrainian"): ids(242, 240),  # + Ruthenian
    ("European", "Other Eastern European"): ids(
        228, 229, 230, 231, 232, 233, 234, 236, 237, 241, 243,
        219, 221, 224,  # Moldovan, Romanian, Transylvanian
        247,  # Slavic, n.o.s.
    ),
    ("European", "Italian"): ids(204, 207),
    ("European", "Portuguese"): ids(206, 199),  # + Azorean
    ("European", "Spanish"): ids(208, 200, 201, 202),  # + Basque, Catalan, Galician
    ("European", "Greek"): ids(203, 416, 418),  # + Cypriot, Greek Cypriot
    ("European", "Other Balkan"): ids(211, 212, 213, 214, 215, 216, 217, 218, 220, 222, 223, 225, 226),
    ("European", "Other European"): ids(
        154, 198, 209, 248,  # European / Southern European n.o.s. & n.i.e.
        205,  # Maltese
        246,  # Roma
        514,  # Caucasian (White), n.o.s.
    ),

    # ------------------------------------------------ MIDDLE EASTERN & NORTH AFRICAN
    ("Middle Eastern and North African", "Levantine Arab"): ids(428, 434, 430, 423),
    ("Middle Eastern and North African", "Iraqi, Assyrian and Gulf"): ids(421, 412, 515, 426, 429, 433, 441),
    ("Middle Eastern and North African", "Egyptian and North African"): ids(
        (354, 356), 358, (359, 364), 517, 386,  # excl. Dinka; + Coptic, Nubian
    ),
    ("Middle Eastern and North African", "Iranian"): ids(420, 432, 529),  # + Persian, Zoroastrian
    ("Middle Eastern and North African", "Kurdish"): ids(425, 528),  # + Yazidi
    ("Middle Eastern and North African", "Turkish"): ids(437),
    ("Middle Eastern and North African", "Armenian and Caucasian"): ids(411, 413, 415, 417),
    ("Middle Eastern and North African", "Afghan and Central Asian"): ids(
        410, 419, 431, 414, 424, 427, 435, 436, 438, 439, 440,
    ),
    ("Middle Eastern and North African", "Other Arab and Middle Eastern"): ids(511, 409, 442),

    # ---------------------------------------------------- AFRICAN & BLACK DIASPORA
    ("African and Black Diaspora", "Black diaspora"): ids(
        131, 132, 133,  # African American, African Canadian, African Nova Scotian
        308, 405, 512, 370,  # African n.o.s., African n.i.e., Black n.o.s., Bantu n.o.s.
    ),
    ("African and Black Diaspora", "Nigerian"): ids(343, 351, 335, 324, 325, 334),
    ("African and Black Diaspora", "Ghanaian"): ids(332, 311, 313, 326, 327, 329),
    ("African and Black Diaspora", "Other West and Central African"): ids(
        *[i for i in range(310, 353) if i not in (343, 351, 335, 324, 325, 334, 332, 311, 313, 326, 327, 329)],
    ),
    ("African and Black Diaspora", "Horn of Africa"): ids(367, 369, 372, 373, 374, 375, 387, 392, 397),
    ("African and Black Diaspora", "East African"): ids(
        366, 371, 376, 377, 378, 379, 389, 394, 395, 396, 399, 400, 357, 404,
        380, 382, 388, 390,  # Indian Ocean: Malagasy, Mauritian, Réunionnais, Seychellois
    ),
    ("African and Black Diaspora", "Southern African"): ids(368, 381, 383, 384, 385, 391, 393, 398, 401, 402, 403),

    # ----------------------------------------------------------------- CARIBBEAN
    ("Caribbean", "Jamaican"): ids(265, 267),  # + Maroon
    ("Caribbean", "Trinidadian and Tobagonian"): ids(272),
    ("Caribbean", "Guyanese and Indo-Caribbean"): ids(288, 292, 264, 303, 278),  # + Indo-Guyanese, Indo-Caribbean, Surinamese, Arawak
    ("Caribbean", "Other Caribbean"): ids(
        250, 251, 274, 275,  # Caribbean n.o.s., African Caribbean, West Indian n.o.s., n.i.e.
        252, 253, 254, 255, 256, 257, 259, 261, 266, 269, 271, 273,
    ),
    ("Caribbean", "Haitian and Francophone Caribbean"): ids(263, 262, 268),

    # ------------------------------------------------------------ LATIN AMERICAN
    ("Latin American", "Hispanic Caribbean"): ids(258, 260, 270),
    ("Latin American", "Mexican"): ids(295),
    ("Latin American", "Central American"): ids(280, 285, 287, 290, 294, 296, 297, 300, 302),
    ("Latin American", "Andean and Northern South American"): ids(281, 284, 286, 299, 301, 305),
    ("Latin American", "Southern Cone"): ids(279, 283, 293, 298, 304),
    ("Latin American", "Brazilian"): ids(282),
    ("Latin American", "Other Latin American"): ids(277, 289, 291, 306),

    # ---------------------------------------------------------------- EAST ASIAN
    ("East Asian", "Chinese"): ids(471),
    ("East Asian", "Hong Konger"): ids(474),
    ("East Asian", "Taiwanese"): ids(487),
    ("East Asian", "Korean"): ids(481),
    ("East Asian", "Japanese"): ids(478),
    ("East Asian", "Other East Asian"): ids(485, 466, 491),  # Mongolian, E/SE Asian n.o.s. & n.i.e.

    # ----------------------------------------------------------- SOUTHEAST ASIAN
    ("Southeast Asian", "Filipino"): ids(472, 475, 476),  # + Igorot, Ilocano
    ("Southeast Asian", "Vietnamese"): ids(490),
    ("Southeast Asian", "Other Mainland Southeast Asian"): ids(468, 469, 470, 473, 480, 482, 488),
    ("Southeast Asian", "Maritime Southeast Asian"): ids(467, 477, 479, 483, 484, 486),

    # --------------------------------------------------------------- SOUTH ASIAN
    ("South Asian", "Indian"): ids(451, 445),  # + Anglo-Indian
    ("South Asian", "Punjabi and Sikh"): ids(458, 452, 527),  # + Jatt
    ("South Asian", "Gujarati and Western Indian"): ids(450, 454, 449),  # + Maharashtrian, Goan
    ("South Asian", "South Indian"): ids(455, 463),  # Malayali, Telugu
    ("South Asian", "Pakistani"): ids(457, 459, 453),  # + Sindhi, Kashmiri
    ("South Asian", "Sri Lankan and Tamil"): ids(461, 462, 460),
    ("South Asian", "Bangladeshi and Bengali"): ids(446, 447),
    ("South Asian", "Himalayan"): ids(456, 448, 489),  # Nepali, Bhutanese, Tibetan
    ("South Asian", "Other South Asian"): ids(444, 464, 521),  # + Hindu

    # ------------------------------------------------------------------ OCEANIAN
    ("Oceanian", "Australian and New Zealander"): ids(505, 507, 508, 494),
    ("Oceanian", "Pacific Islander"): ids((496, 503), 506),  # + Maori; incl. Indo-Fijian

    # -------------------------------------------------------------------- JEWISH
    ("Jewish", "Jewish and Israeli"): ids(524, 422),

    # --------------------------------------------------------------------- OTHER
    ("Other", "Other"): ids(
        407, 492,  # Asian n.o.s. & n.i.e.
        3, 518, 520, 530,  # North American n.o.s., Creole, Eurasian, Other n.i.e.
    ),
}

# Leaf origins deliberately left off the map: purely religious responses.
EXCLUDED = ids(516, 526, 513)  # Christian n.i.e., Muslim, Buddhist

BROAD_ORDER = [
    "Indigenous North American", "Non-Indigenous North American", "European",
    "Middle Eastern and North African", "African and Black Diaspora", "Caribbean",
    "Latin American", "East Asian", "Southeast Asian", "South Asian", "Oceanian", "Jewish", "Other",
]
