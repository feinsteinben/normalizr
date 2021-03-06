from __future__ import absolute_import, unicode_literals

import codecs
import logging
import os
import re
import string
import sys
import unicodedata

import normalizr.regex as regex

path = os.path.dirname(__file__)

DEFAULT_NORMALIZATIONS = [
    'remove_extra_whitespaces', 'replace_punctuation', 'replace_symbols', 'remove_stop_words'
]


class Normalizr:
    """
    This class offers methods for text normalization.

    Attributes:
        language (string): Language used for normalization.
        lazy_load (boolean): Whether or not lazy load files.
    """
    __punctuation = set(string.punctuation)

    def __init__(self, language='en', lazy_load=False, logger_level=logging.INFO):
        self.__language = language
        self.__logger = self._get_logger(logger_level)
        self.__stop_words = set()
        self.__characters_regexes = dict()

        if not lazy_load:
            self._load_stop_words(language)

    def _get_logger(self, level):
        """
        Initialize logger.

        Params:
            level (integer): Log level as defined in logging.
        """
        logging.basicConfig()
        logger = logging.getLogger("Normalizr")
        logger.setLevel(level)

        return logger

    def _load_stop_words(self, language):
        """
        Load stop words into __stop_words set.

        Stop words will be loaded according to the language code received during instantiation.

        Params:
            language (string): Language code.
        """
        self.__logger.debug('loading stop words')
        with codecs.open(os.path.join(path, 'data/stop-' + language), 'r', 'UTF-8') as file:
            for line in file:
                fields = line.split('|')
                if fields:
                    for word in fields[0].split(): self.__stop_words.add(word.strip())

    def _parse_normalizations(self, normalizations):
        str_type = str if sys.version_info[0] > 2 else (str, unicode)

        for normalization in normalizations:
            yield (normalization, {}) if isinstance(normalization, str_type) else normalization

    def normalize(self, text, normalizations=None):
        """
        Normalize a given text applying all normalizations.

        Normalizations to apply can be specified through a list parameter and will be executed
        in the same order.

        Params:
            text (string): The text to be processed.
            normalizations (list): List of normalizations to apply.

        Returns:
            The text normalized.
        """
        for normalization, kwargs in self._parse_normalizations(normalizations or DEFAULT_NORMALIZATIONS):
            text = getattr(self, normalization)(text, **kwargs)
        return text

    def remove_accent_marks(self, text, excluded=set()):
        """
        Remove accent marks from input text.

        Params:
            text (string): The text to be processed.
            excluded (set): Set of unicode characters to exclude.

        Returns:
            The text without accent marks.
        """
        return unicodedata.normalize('NFKC', ''.join(c for c in unicodedata.normalize('NFKD', text)
                       if unicodedata.category(c) != 'Mn' or c in excluded))

    def remove_extra_whitespaces(self, text):
        """
        Remove extra whitespaces from input text.

        This function removes whitespaces from the beginning and the end of
        the string, but also duplicated whitespaces between words.

        Params:
            text (string): The text to be processed.

        Returns:
            The text without extra whitespaces.
        """
        return ' '.join(text.split())

    def remove_stop_words(self, text, ignore_case=True):
        """
        Remove stop words.

        Stop words are loaded on class instantiation according with the specified language.

        Params:
            text (string): The text to be processed.
            ignore_case (boolean): Whether or not ignore case.

        Returns:
            The text without stop words.
        """
        if not self.__stop_words:
            self._load_stop_words(self.__language)

        return ' '.join(
            word for word in text.split(' ') if (word.lower() if ignore_case else word) not in self.__stop_words)

    def replace_emails(self, text, replacement=''):
        """
        Remove email addresses from input text or replace them with a string if specified.

        Params:
            text (string): The text to be processed.
            replacement (string): New text that will replace email addresses.

        Returns:
            The text without email addresses.
        """
        return re.sub(regex.EMAIL_REGEX, replacement, text)

    def replace_emojis(self, text, replacement=''):
        """
        Remove emojis from input text or replace them with a string if specified.

        Params:
            text (string): The text to be processed.
            replacement (string): New text that will replace emojis.

        Returns:
            The text without hyphens.
        """

        return regex.EMOJI_REGEX.sub(replacement, text)

    def replace_characters(self, text, characters, replacement=''):
        """
        Remove custom characters from input text or replace them with a string if specified.

        Params:
            text (string): The text to be processed.
            characters (string): Characters that will be replaced.
            replacement (string): New text that will replace the custom characters.

        Returns:
            The text without the given characters.
        """
        if not characters:
            return text

        characters = ''.join(sorted(characters))
        if characters in self.__characters_regexes:
            characters_regex = self.__characters_regexes[characters]
        else:
            characters_regex = re.compile("[%s]" % re.escape(characters))
            self.__characters_regexes[characters] = characters_regex

        return characters_regex.sub(replacement, text)

    def replace_hyphens(self, text, replacement=' '):
        """
        Replace hyphens from input text with a whitespace or a string if specified.

        Params:
            text (string): The text to be processed.
            replacement (string): New text that will replace hyphens.

        Returns:
            The text without hyphens.
        """
        return text.replace('-', replacement)

    def replace_punctuation(self, text, excluded=None, replacement=''):
        """
        Remove punctuation from input text or replace them with a string if specified.

        This function will remove characters from string.punctuation.

        Params:
            text (string): The text to be processed.
            excluded (set): Set of characters to exclude.
            replacement (string): New text that will replace punctuation.

        Returns:
            The text without punctuation.
        """
        if excluded is None:
            excluded = set()
        elif not isinstance(excluded, set):
            excluded = set(excluded)
        punct = ''.join(self.__punctuation.difference(excluded))

        return self.replace_characters(text, characters=punct, replacement=replacement)

    def replace_symbols(self, text, format='NFKD', excluded=set(), replacement=''):
        """
        Remove symbols from input text or replace them with a string if specified.

        Params:
            text (string): The text to be processed.
            format (string): Unicode format.
            excluded (set): Set of unicode characters to exclude.
            replacement (string): New text that will replace symbols.

        Returns:
            The text without symbols.
        """
        categories = set(['Mn', 'Sc', 'Sk', 'Sm', 'So'])
        return ''.join(c if unicodedata.category(c) not in categories or c in excluded else replacement
                       for c in unicodedata.normalize(format, text))

    def replace_urls(self, text, replacement=''):
        """
        Remove URLs from input text or replace them with a string if specified.

        Params:
            text (string): The text to be processed.
            replacement (string): New text that will replace URLs.

        Returns:
            The text without URLs.
        """
        return re.sub(regex.URL_REGEX, replacement, text)
