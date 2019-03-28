# -*- coding: utf-8 -*-
"""
    sphinxcontrib.mscgen
    ~~~~~~~~~~~~~~~~~~~~

    Allow mscgen-formatted :abbr:`MSC (Message Sequence Chart)` graphs to be
    included in Sphinx-generated documents inline.

    See the README file for details.

    :author: Leandro Lucarella <llucax@gmail.com>.
    :license: BOLA, see LICENSE for details.
"""

import os
import sys
from subprocess import Popen, PIPE
from uuid import uuid4

from docutils import nodes

from sphinx.errors import SphinxError
from sphinx.util import ensuredir
from docutils.parsers.rst import Directive


try:
    import cairosvg
    preferred_formats = ['image/svg+xml', 'application/pdf', 'image/png']
except:
    preferred_formats = ['image/svg+xml', 'image/png']


class MscgenError(SphinxError):
    category = 'mscgen error'


class mscgen(nodes.General, nodes.Element):
    pass


class Mscgen(Directive):
    """
    Directive to insert arbitrary mscgen markup.
    """
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        node = mscgen()
        node['code'] = '\n'.join(self.content)
        return [node]


class MscgenSimple(Directive):
    """
    Directive to insert mscgen markup that goes inside ``msc { ... }``.
    """
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        node = mscgen()
        node['code'] = 'msc {\n%s\n}\n' % ('\n'.join(self.content))
        return [node]


def determine_format(supported):
    for fmt in preferred_formats:
        if fmt in supported:
            return fmt
    return None


def render_msc_native(self, code, fmt='svg'):
    mscgen_args = [self.builder.config.mscgen]
    mscgen_args.extend(self.builder.config.mscgen_args)
    mscgen_args.extend(['-T', fmt, '-o', '-'])

    try:
        p = Popen(mscgen_args, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    except OSError as err:
        raise
    img, err = p.communicate(code.encode('iso-8859-1'))
    if p.returncode != 0:
        raise MscgenError('Cannot render the following mscgen code:\n%s\n\nError: %s'.format(code, err))
    return img


def render_msc(self, code, outpath, fmt):
    ensuredir(outpath)

    bname = '%s-%s' % ('mscgen', uuid4())

    # PNG can be directly written
    if fmt == 'image/png':
        ext = 'png'
        fpath = os.path.join(outpath, '%s.%s' % (bname, ext))
        png = render_msc_native(self, code, fmt='png')
        with open(fpath, 'wb') as out:
            out.write(png)
        return bname, ext

    # Create SVG
    svg = render_msc_native(self, code, fmt='svg')

    # SVG can be directly written
    if fmt == 'image/svg+xml':
        ext = 'svg'
        fpath = os.path.join(outpath, '%s.%s' % (bname, ext))
        with open(fpath, 'wb') as out:
            out.write(svg)
        return bname, ext

    # Use CairoSVG to convert SVG to PDF
    if fmt == 'application/pdf':
        ext = 'pdf'
        fpath = os.path.join(outpath, '%s.%s' % (bname, ext))
        cairosvg.svg2pdf(svg, write_to=fpath)
        return bname, ext

    raise MscGenError("No valid mscgen conversion supplied")


def render_msc_html(self, node, code):
    if hasattr(self.builder, 'imgpath') and self.builder.imgpath:
        imgpath = self.builder.imgpath
    else:
        imgpath = '.'
    outdir = os.path.join(self.builder.outdir, imgpath)

    fn, ext = render_msc(self, code, outdir,
            determine_format(self.builder.supported_image_types))

    self.body.append(self.starttag(node, 'p', **{'class': 'mscgen'}))
    self.body.append('<img src="%s.%s" alt="%s"/>\n' %
            (os.path.join(imgpath, fn), ext, self.encode(code).strip()))
    self.body.append('</p>\n')
    raise nodes.SkipNode


def render_msc_html_js(self, node, code):
    self.body.append(self.starttag(node, 'script', type='text/x-mscgen', **{'data-named-style': 'classic'}))
    self.body.append(self.encode(code))
    self.body.append('</script>')
    raise nodes.SkipNode


def html_visit_mscgen(self, node):
    if self.builder.config.mscgen_js is not None:
        render_msc_html_js(self, node, node['code'])
    else:
        render_msc_html(self, node, node['code'])


def render_msc_latex(self, code):
    fn, ext = render_msc(self, code, self.builder.outdir,
            determine_format(self.builder.supported_image_types))
    self.body.append('\n\\noindent\\sphinxincludegraphics{{%s}.%s}\n' % (fn, ext))
    raise nodes.SkipNode


def latex_visit_mscgen(self, node):
    render_msc_latex(self, node['code'])


def builder_inited(app):
    if app.config.mscgen_js is not None:
        app.add_javascript(app.config.mscgen_js)


def setup(app):
    app.add_node(mscgen,
                 html=(html_visit_mscgen, None),
                 latex=(latex_visit_mscgen, None))
    app.add_directive('mscgen', Mscgen)
    app.add_directive('msc', MscgenSimple)
    app.add_config_value('mscgen', 'mscgen', 'html')
    app.add_config_value('mscgen_args', [], 'html')
    app.add_config_value('mscgen_js', None, 'html')
    app.connect('builder-inited', builder_inited)
