# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

extensions = [
    'autoapi.extension',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.ifconfig',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx.ext.autodoc',
    'sphinx.ext.inheritance_diagram',
]
source_suffix = '.rst'
master_doc = 'index'
project = 'R2B2'
year = '2019-2020'
author = 'R2B2 Team'
copyright = '{0}, {1}'.format(year, author)
version = release = '0.1.0'

# autoapi configuration
autoapi_type = 'python'
autoapi_dirs = ['../src/r2b2']
autoapi_add_toctree_entry = False
# Options: https://sphinx-autoapi.readthedocs.io/en/latest/reference/config.html#customisation-options
autoapi_options = [
    'members',
    'inherited-members',
    'private-members',
    'special-members',
    'show-inheritance',
]
autoapi_python_class_content = 'both'

pygments_style = 'trac'
templates_path = ['.']
extlinks = {
    'issue': ('https://github.com/gwexploratoryaudits/r2b2/issues/%s', '#'),
    'pr': ('https://github.com/gwexploratoryaudits/r2b2/pull/%s', 'PR #'),
}
# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only set the theme if we're building docs locally
    html_theme = 'sphinx_rtd_theme'

html_use_smartypants = True
html_last_updated_fmt = '%b %d, %Y'
html_split_index = False
html_sidebars = {
   '**': ['searchbox.html', 'globaltoc.html', 'sourcelink.html'],
}
html_short_title = '%s-%s' % (project, version)

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False


# temporary fix for requires.io timeout problem
linkcheck_ignore = [r'https://requires.io*']
