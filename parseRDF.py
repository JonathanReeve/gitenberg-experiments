"""Extract metadata from Project Gutenberg RDF catalog into a Python dict.

Based on https://bitbucket.org/c-w/gutenberg/

>>> md = readmetadata()
>>> md[123]
{'LCC': {'PS'},
 'author': u'Burroughs, Edgar Rice',
 'authoryearofbirth': 1875,
 'authoryearofdeath': 1950,
 'downloads': 401,
 'formats': {'application/epub+zip': 'http://www.gutenberg.org/ebooks/123.epub.noimages',
  'application/prs.plucker': 'http://www.gutenberg.org/ebooks/123.plucker',
  'application/x-mobipocket-ebook': 'http://www.gutenberg.org/ebooks/123.kindle.noimages',
  'application/x-qioo-ebook': 'http://www.gutenberg.org/ebooks/123.qioo',
  'text/html; charset=iso-8859-1': 'http://www.gutenberg.org/files/123/123-h.zip',
  'text/plain': 'http://www.gutenberg.org/ebooks/123.txt.utf-8',
  'text/plain; charset=us-ascii': 'http://www.gutenberg.org/files/123/123.zip'},
 'id': 123,
 'language': ['en'],
 'subjects': {'Adventure stories',
  'Earth (Planet) -- Core -- Fiction',
  'Fantasy fiction',
  'Science fiction'},
 'title': u"At the Earth's Core",
 'type': 'Text'}

"""

import os
import re
import gzip
import tarfile
import urllib
import xml.etree.cElementTree as ElementTree
try:
	import cPickle as pickle
except ImportError:
	import pickle

PICKLEFILE = '/tmp/md.pickle.gz'  # The Python dict produced by this module
RDFFILES = '/tmp/rdf-files.tar.bz2'  # The catalog downloaded from Gutenberg
RDFURL = r'http://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.bz2'
META_FIELDS = ('id', 'author', 'title', 'downloads', 'formats', 'type', 'LCC',
		'subjects', 'authoryearofbirth', 'authoryearofdeath', 'language')
NS = dict(
		pg='http://www.gutenberg.org/2009/pgterms/',
		dc='http://purl.org/dc/terms/',
		dcam='http://purl.org/dc/dcam/',
		rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#')
LINEBREAKRE = re.compile(ur'[ \t]*[\n\r]+[ \t]*')
ETEXTRE = re.compile(r'''
	e(text|b?ook)
	\s*
	(\#\s*(?P<etextid_front>\d+)
	|
	(?P<etextid_back>\d+)\s*\#)
	''', re.IGNORECASE | re.VERBOSE)


def readmetadata():
	"""Read/create cached metadata dump of Gutenberg catalog.

	Returns:
		A dictionary with the following fields:

		id (int): Gutenberg identifier of text
		author (str): Last name, First name
		title (str): title of work
		subjects (list of str): list of descriptive subjects; a subject may be
			hierarchical, e.g:
			'England -- Social life and customs -- 19th century -- Fiction'
		LCC (list of str): a list of two letter Library of Congress
			Classifications, e.g., 'PS'
		language (list of str): list of two letter language codes.
		type (str): 'Text', 'Sound', ...
		formats (dict of str, str pairs): keys are MIME types, values are URLs.
		download count (int): the number of times this ebook has been
			downloaded from the Gutenberg site in the last 30 days.

	Fields that are not part of the metadata are set to None.
	http://www.gutenberg.org/wiki/Gutenberg:Help_on_Bibliographic_Record_Page
	"""
	if os.path.exists(PICKLEFILE):
		metadata = pickle.load(gzip.open(PICKLEFILE, 'rb'))
	else:
		metadata = {}
		for xml in getrdfdata():
			ebook = xml.find(r'{%(pg)s}ebook' % NS)
			if ebook is None:
				continue
			result = parsemetadata(ebook)
			if result is not None:
				metadata[result['id']] = result
		pickle.dump(metadata, gzip.open(PICKLEFILE, 'wb'), protocol=-1)
	return metadata


def getrdfdata():
	"""Downloads Project Gutenberg RDF catalog.

	Yields:
		xml.etree.ElementTree.Element: An etext meta-data definition.

	"""
	if not os.path.exists(RDFFILES):
		_, _ = urllib.urlretrieve(RDFURL, RDFFILES)
	with tarfile.open(RDFFILES) as archive:
		for tarinfo in archive:
			yield ElementTree.parse(archive.extractfile(tarinfo))


def parsemetadata(ebook):
	"""Parses an etext meta-data definition to extract fields.

	Args:
		ebook (xml.etree.ElementTree.Element): An ebook meta-data definition.

	"""
	result = dict.fromkeys(META_FIELDS)
	# get etext no
	about = ebook.get('{%(rdf)s}about' % NS)
	result['id'] = int(os.path.basename(about))
	# author
	creator = ebook.find('.//{%(dc)s}creator' % NS)
	if creator is not None:
		name = creator.find('.//{%(pg)s}name' % NS)
		if name is not None:
			result['author'] = safeunicode(name.text, encoding='utf-8')
		birth = creator.find('.//{%(pg)s}birthdate' % NS)
		if birth is not None:
			result['authoryearofbirth'] = int(birth.text)
		death = creator.find('.//{%(pg)s}deathdate' % NS)
		if death is not None:
			result['authoryearofdeath'] = int(death.text)
	# title
	title = ebook.find('.//{%(dc)s}title' % NS)
	if title is not None:
		result['title'] = fixsubtitles(
				safeunicode(title.text, encoding='utf-8'))
	# subject lists
	result['subjects'], result['LCC'] = set(), set()
	for subject in ebook.findall('.//{%(dc)s}subject' % NS):
		res = subject.find('.//{%(dcam)s}memberOf' % NS)
		if res is None:
			continue
		res = res.get('{%(rdf)s}resource' % NS)
		value = subject.find('.//{%(rdf)s}value' % NS).text
		if res == ('%(dc)sLCSH' % NS):
			result['subjects'].add(value)
		elif res == ('%(dc)sLCC' % NS):
			result['LCC'].add(value)
	# formats
	result['formats'] = {file.find('{%(dc)s}format//{%(rdf)s}value' % NS).text:
			file.get('{%(rdf)s}about' % NS)
			for file in ebook.findall('.//{%(pg)s}file' % NS)}
	# type
	booktype = ebook.find('.//{%(dc)s}type//{%(rdf)s}value' % NS)
	if booktype is not None:
		result['type'] = booktype.text
	# languages
	lang = ebook.findall('.//{%(dc)s}language//{%(rdf)s}value' % NS)
	result['language'] = [a.text for a in lang] or None
	# download count
	downloads = ebook.find('.//{%(pg)s}downloads' % NS)
	if downloads is not None:
		result['downloads'] = int(downloads.text)
	return result


def etextno(lines):
	"""Retrieves the id for an etext.

	Args:
		lines (iter): The lines of the etext to search.

	Returns:
		int: The id of the etext.

	Raises:
		ValueError: If no etext id was found.

	Examples:
		>>> etextno(['Release Date: March 17, 2004 [EBook #11609]'])
		11609

		>>> etextno(['Release Date: July, 2003 [Etext# 4263]'])
		4263

		>>> etextno(['Release Date: November 29, 2003 [Eook #10335]'])
		10335

		>>> etextno(['December, 1998  [Etext 1576#]'])
		1576

		>>> etextno(['Some lines', 'without', 'Any [Etext] Number'])
		Traceback (most recent call last):
			...
		ValueError: no etext-id found
	"""
	for line in lines:
		match = ETEXTRE.search(line)
		if match is not None:
			front_match = match.group('etextid_front')
			back_match = match.group('etextid_back')
			if front_match is not None:
				return int(front_match)
			elif back_match is not None:
				return int(back_match)
			else:
				raise ValueError('no regex match (this should never happen')
	raise ValueError('no etext-id found')


def fixsubtitles(title):
	"""Introduce any subtitle with (semi)colons instead of newlines.

	The first subtitle is introduced with a colon, the rest with semicolons.

	>>> fixsubtitles(u'First Across ...\r\nThe Story of ... \r\n'
	... 'Being an investigation into ...')
	u'First Across ...: The Story of ...; Being an investigation into ...'"""
	tmp = LINEBREAKRE.sub(': ', title, 1)
	return LINEBREAKRE.sub('; ', tmp)


def safeunicode(arg, *args, **kwargs):
	"""Coerce argument to unicode, if it's not already."""
	return arg if isinstance(arg, unicode) else unicode(arg, *args, **kwargs)

__all__ = ['readmetadata']