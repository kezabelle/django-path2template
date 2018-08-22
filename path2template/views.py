# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
from collections import namedtuple
from itertools import chain

from django.template import TemplateDoesNotExist
from django.template.loader import select_template
from django.views.generic import TemplateView
from json import loads as json_loads

try:
    from typing import TYPE_CHECKING, Tuple
except ImportError:
    pass
try:
    from toml import loads as toml_loads

    HAS_TOML = True
except ImportError:

    def toml_loads(*args, **kwargs):
        raise ValueError("You need to install https://pypi.org/project/toml/")

    HAS_TOML = False


Loaded = namedtuple("Loaded", "filename rendered")


class Path2TemplateView(TemplateView):
    loaders = {".json": json_loads, ".toml": toml_loads}
    base_path = None

    def generate_variants(self):
        newpath = tuple(
            part for part in self.request.path.strip("/").split("/") if part
        )
        # If the thing is empty, just return an empty tuple
        if not newpath:
            return ()
        newpath_length = len(newpath) + 1
        variations = (newpath[0:l] for l in range(1, newpath_length))
        return variations

    def get_template_variants(self, filename, suffix):
        # type: (str) -> Tuple[str, ...]
        variants = tuple(self.generate_variants())
        end = "{}.{}".format(filename, suffix)
        formatted_variants = (
            "{}/{}".format("/".join(variant), end) for variant in reversed(variants)
        )
        if self.base_path:
            formatted_variants = (
                "{}/{}".format(self.base_path, formatted)
                for formatted in formatted_variants
            )
        return tuple(formatted_variants)

    def load_context(self, template):
        filename = template.origin.name
        path, extension = os.path.splitext(filename)
        return Loaded(
            filename, self.loaders[extension](template.render(None, self.request))
        )

    def get_template_names(self):
        return self.get_template_variants(filename="index", suffix="html")

    def get_context_data(self, **kwargs):
        context = super(Path2TemplateView, self).get_context_data(**kwargs)
        files = tuple(
            chain(
                *zip(
                    self.get_template_variants(filename="data", suffix="json"),
                    self.get_template_variants(filename="data", suffix="toml"),
                )
            )
        )
        try:
            selected_file = select_template(files)
        except TemplateDoesNotExist:
            filename, extra = None, None
        else:
            filename, extra = self.load_context(selected_file)
        context.update(data=extra, context_files=files, context_file=filename)
        return context


path_to_template = Path2TemplateView.as_view()
