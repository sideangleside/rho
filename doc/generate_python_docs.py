#!/bin/python
#
# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""Extract a list of facts from our documentation.

The documentation is formatted as reStructured Text. We want to
extract one specific list in a structured way so we can return it from
'rho facts list'.

We check that the entries are in alphabetical order and write the fact
list as a Python source file containing a dictionary. This lets us
only maintain a single copy of the fact list while not adding an
additional source of errors at runtime.
"""

import collections
import logging
import os.path
import sys

import docutils
import docutils.parsers.rst

COMMAND_SYNTAX_USAGE_RST = 'command_syntax_usage.rst'

# The description nodes in the tree all have this prefix
DESCRIPTION_PREFIX = ' - '


def get_fact_docs(doc_dir):
    """Return the fact list.

    :param base_dir: path to the base of the rho source tree.
    :returns: a collections.OrderedDict mapping fact names to
    descriptions, sorted by fact name.
    """

    # Find the documentation and read it
    rst_path = os.path.join(doc_dir, COMMAND_SYNTAX_USAGE_RST)
    raw_rst = open(rst_path, 'r').read()

    # Parse it using docutils
    parser = docutils.parsers.rst.Parser()
    settings = docutils.frontend.OptionParser(
        components=(docutils.parsers.rst.Parser,)).get_default_values()
    document = docutils.utils.new_document(COMMAND_SYNTAX_USAGE_RST, settings)
    parser.parse(raw_rst, document)

    # Find the list we need
    output = find_doc_elt_with_id(document, 'output')
    fact_list = None
    for elt in output.children:
        if isinstance(elt, docutils.nodes.bullet_list):
            fact_list = elt
            break
    if not fact_list:
        raise ValueError("Couldn't find the fact list in the documentation.")

    # Turn it into a dictionary
    fact_docs = collections.OrderedDict()
    for elt in fact_list:
        logging.debug('extracting data from %s', elt)
        assert isinstance(elt, docutils.nodes.list_item)
        assert len(elt) == 1
        assert isinstance(elt[0], docutils.nodes.paragraph)

        # The paragraph starts with a literal containing the fact
        # name, then ' - ', and then a variable number of nodes
        # containing the documentation.
        fact_name = elt[0][0].astext()
        paragraph = elt[0].astext()

        prefix = fact_name + DESCRIPTION_PREFIX

        assert paragraph.startswith(prefix)
        description = paragraph[len(prefix):]

        fact_docs[fact_name] = description

    return fact_docs


def find_doc_elt_with_id(root, elt_id):
    """Find a docutils tree element with a given id.

    :param root: the root of the element tree to search.
    :param elt_id: the ID of the element to find.
    :returns: a docutils Element, or None if not found.
    """

    logging.debug('visiting %s', repr(root))

    if hasattr(root, 'get') and root.get('ids', None) == [elt_id]:
        return root

    for elt in root.children:
        logging.debug('descending from %s', repr(root))

        val = find_doc_elt_with_id(elt, elt_id)

        if val:
            return val

    return None


def write_docs_as_python(fact_docs, out_file):
    """Write the fact docs in Python format.

    Writes Python code to out_file such that if the code were loaded
    as a Python module, the module would have a single element called
    'FACT_DOCS' which would be a collections.OrderedDict with the same
    contents as od.

    :param od: a collections.OrderedDict mapping strings to strings.
    """

    out_file.write("""# THIS FILE IS AUTOMATICALLY GENERATED.

# Do not edit this file. Instead, edit 'doc/generate_python_docs.py'
# to make the change you want to see, and run 'make docs' to generate
# a new version of this.

'''Documentation for individual Rho facts.'''

import collections

FACT_DOCS = collections.OrderedDict([
""")

    for key, value in fact_docs.items():
        out_file.write('    ({0}, {1}),\n'.format(repr(key), repr(value)))

    out_file.write('])\n')


def main(argv):
    """Run the script."""

    doc_dir = os.path.dirname(argv[0])

    fact_docs = get_fact_docs(doc_dir)

    with open('fact_docs.py', 'w') as out_file:
        write_docs_as_python(fact_docs, out_file)


if __name__ == '__main__':
    main(sys.argv)
