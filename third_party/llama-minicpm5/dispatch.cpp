    } else if (regex_expr == "\\p{N}{1,3}") {
        bpe_offsets = unicode_regex_split_custom_numbers_1_3(text, offsets);
    } else if (
           regex_expr == "(?:'[sS]|'[tT]|'[rR][eE]|'[vV][eE]|'[mM]|'[lL][lL]|'[dD])|[^\\r\\n\\p{L}\\p{N}]?\\p{L}+|\\p{N}+| ?[^\\s\\p{L}\\p{N}]+[\\r\\n]*|\\s*[\\r\\n]+|\\s+(?!\\S)|\\s+") {
        bpe_offsets = unicode_regex_split_custom_minicpm5(text, offsets);
