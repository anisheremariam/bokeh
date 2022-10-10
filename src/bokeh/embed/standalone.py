#-----------------------------------------------------------------------------
# Copyright (c) 2012 - 2022, Anaconda, Inc., and Bokeh Contributors.
# All rights reserved.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------
'''

'''

#-----------------------------------------------------------------------------
# Boilerplate
#-----------------------------------------------------------------------------
from __future__ import annotations

import logging # isort:skip
log = logging.getLogger(__name__)

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Standard library imports
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Literal,
    Sequence,
    Type,
    TypedDict,
    Union,
    cast,
    overload,
)

# External imports
from jinja2 import Template
from typing_extensions import TypeAlias

# Bokeh imports
from .. import __version__
from ..core.templates import (
    AUTOLOAD_JS,
    AUTOLOAD_TAG,
    FILE,
    MACROS,
    ROOT_DIV,
)
from ..document.document import DEFAULT_TITLE, Document
from ..model import Model
from ..resources import CSSResources, JSResources, Resources
from ..themes import Theme
from .bundle import Script, bundle_for_objs_and_resources
from .elements import html_page_for_render_items, script_for_render_items
from .util import (
    FromCurdoc,
    OutputDocumentFor,
    RenderRoot,
    standalone_docs_json,
    standalone_docs_json_and_render_items,
)
from .wrappers import wrap_in_onload

if TYPE_CHECKING:
    from ..core.types import ID
    from ..document.document import DocJson

#-----------------------------------------------------------------------------
# Globals and constants
#-----------------------------------------------------------------------------

__all__ = (
    'autoload_static',
    'components',
    'file_html',
    'json_item',
)

ModelLike: TypeAlias = Union[Model, Document]
ModelLikeCollection: TypeAlias = Union[Sequence[ModelLike], Dict[str, ModelLike]]

#-----------------------------------------------------------------------------
# General API
#-----------------------------------------------------------------------------

ThemeLike: TypeAlias = Union[None, Theme, Type[FromCurdoc]]

def autoload_static(model: Model | Document, resources: Resources, script_path: str) -> tuple[str, str]:
    ''' Return JavaScript code and a script tag that can be used to embed
    Bokeh Plots.

    The data for the plot is stored directly in the returned JavaScript code.

    Args:
        model (Model or Document) :

        resources (Resources) :

        script_path (str) :

    Returns:
        (js, tag) :
            JavaScript code to be saved at ``script_path`` and a ``<script>``
            tag to load it

    Raises:
        ValueError

    '''
    # TODO: maybe warn that it's not exactly useful, but technically possible
    # if resources.mode == 'inline':
    #     raise ValueError("autoload_static() requires non-inline resources")

    if isinstance(model, Model):
        models = [model]
    elif isinstance (model, Document):
        models = model.roots
    else:
        raise ValueError("autoload_static expects a single Model or Document")

    with OutputDocumentFor(models):
        (docs_json, [render_item]) = standalone_docs_json_and_render_items([model])

    bundle = bundle_for_objs_and_resources(None, resources)
    bundle.add(Script(script_for_render_items(docs_json, [render_item])))

    (_, elementid) = list(render_item.roots.to_json().items())[0]

    js = wrap_in_onload(AUTOLOAD_JS.render(bundle=bundle, elementid=elementid))

    tag = AUTOLOAD_TAG.render(
        src_path = script_path,
        elementid = elementid,
    )

    return js, tag

@overload
def components(models: Model, wrap_script: bool = ..., # type: ignore[misc] # XXX: mypy bug
    wrap_plot_info: Literal[True] = ..., theme: ThemeLike = ...) -> tuple[str, str]: ...
@overload
def components(models: Model, wrap_script: bool = ..., wrap_plot_info: Literal[False] = ...,
    theme: ThemeLike = ...) -> tuple[str, RenderRoot]: ...

@overload
def components(models: Sequence[Model], wrap_script: bool = ..., # type: ignore[misc] # XXX: mypy bug
    wrap_plot_info: Literal[True] = ..., theme: ThemeLike = ...) -> tuple[str, Sequence[str]]: ...
@overload
def components(models: Sequence[Model], wrap_script: bool = ..., wrap_plot_info: Literal[False] = ...,
    theme: ThemeLike = ...) -> tuple[str, Sequence[RenderRoot]]: ...

@overload
def components(models: dict[str, Model], wrap_script: bool = ..., # type: ignore[misc] # XXX: mypy bug
    wrap_plot_info: Literal[True] = ..., theme: ThemeLike = ...) -> tuple[str, dict[str, str]]: ...
@overload
def components(models: dict[str, Model], wrap_script: bool = ..., wrap_plot_info: Literal[False] = ...,
    theme: ThemeLike = ...) -> tuple[str, dict[str, RenderRoot]]: ...

def components(models: Model | Sequence[Model] | dict[str, Model], wrap_script: bool = True,
               wrap_plot_info: bool = True, theme: ThemeLike = None) -> tuple[str, Any]:
    ''' Return HTML components to embed a Bokeh plot. The data for the plot is
    stored directly in the returned HTML.

    An example can be found in examples/embed/embed_multiple.py

    The returned components assume that BokehJS resources are **already loaded**.
    The HTML document or template in which they will be embedded needs to
    include scripts tags, either from a local URL or Bokeh's CDN (replacing
    ``x.y.z`` with the version of Bokeh you are using):

    .. code-block:: html

        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-x.y.z.min.js"></script>
        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-widgets-x.y.z.min.js"></script>
        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-tables-x.y.z.min.js"></script>
        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-gl-x.y.z.min.js"></script>
        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-mathjax-x.y.z.min.js"></script>

    Only the Bokeh core library ``bokeh-x.y.z.min.js`` is always required. The
    other scripts are optional and only need to be included if you want to use
    corresponding features:

    * The ``"bokeh-widgets"`` files are only necessary if you are using any of the
      :ref:`Bokeh widgets <ug_interaction_widgets>`.
    * The ``"bokeh-tables"`` files are only necessary if you are using Bokeh's
      :ref:`data tables <ug_interaction_widgets_examples_datatable>`.
    * The ``"bokeh-api"`` files are required to use the
      :ref:`BokehJS API <ug_advanced_bokehjs>` and must be loaded *after* the
      core BokehJS library.
    * The ``"bokeh-gl"`` files are required to enable
      :ref:`WebGL support <ug_output_webgl>`.
    * the ``"bokeh-mathjax"`` files are required to enable
      :ref:`MathJax support <ug_styling_mathtext>`.

    Args:
        models (Model|list|dict|tuple) :
            A single Model, a list/tuple of Models, or a dictionary of keys
            and Models.

        wrap_script (boolean, optional) :
            If True, the returned javascript is wrapped in a script tag.
            (default: True)

        wrap_plot_info (boolean, optional) :
            If True, returns ``<div>`` strings. Otherwise, return
            :class:`~bokeh.embed.RenderRoot` objects that can be used to build
            your own divs. (default: True)

        theme (Theme, optional) :
            Applies the specified theme when creating the components. If None,
            or not specified, and the supplied models constitute the full set
            of roots of a document, applies the theme of that document to the
            components. Otherwise applies the default theme.

    Returns:
        UTF-8 encoded *(script, div[s])* or *(raw_script, plot_info[s])*

    Examples:

        With default wrapping parameter values:

        .. code-block:: python

            components(plot)
            # => (script, plot_div)

            components((plot1, plot2))
            # => (script, (plot1_div, plot2_div))

            components({"Plot 1": plot1, "Plot 2": plot2})
            # => (script, {"Plot 1": plot1_div, "Plot 2": plot2_div})

    Examples:

        With wrapping parameters set to ``False``:

        .. code-block:: python

            components(plot, wrap_script=False, wrap_plot_info=False)
            # => (javascript, plot_root)

            components((plot1, plot2), wrap_script=False, wrap_plot_info=False)
            # => (javascript, (plot1_root, plot2_root))

            components({"Plot 1": plot1, "Plot 2": plot2}, wrap_script=False, wrap_plot_info=False)
            # => (javascript, {"Plot 1": plot1_root, "Plot 2": plot2_root})

    '''
    # 1) Convert single items and dicts into list
    # XXX: was_single_object = isinstance(models, Model) #or isinstance(models, Document)
    was_single_object = False

    if isinstance(models, Model):
        was_single_object = True
        models = [models]

    models = _check_models_or_docs(models) # type: ignore # XXX: this API needs to be refined

    # now convert dict to list, saving keys in the same order
    model_keys = None
    dict_type: Type[dict[Any, Any]] = dict
    if isinstance(models, dict):
        dict_type = models.__class__
        model_keys = models.keys()
        models = list(models.values())

    # 2) Append models to one document. Either pre-existing or new and render
    with OutputDocumentFor(models, apply_theme=theme):
        (docs_json, [render_item]) = standalone_docs_json_and_render_items(models)

    bundle = bundle_for_objs_and_resources(None, None)
    bundle.add(Script(script_for_render_items(docs_json, [render_item])))

    script = bundle.scripts(tag=wrap_script)

    def div_for_root(root: RenderRoot) -> str:
        return ROOT_DIV.render(root=root, macros=MACROS)

    results: list[str] | list[RenderRoot]
    if wrap_plot_info:
        results = [div_for_root(root) for root in render_item.roots]
    else:
        results = list(render_item.roots)

    # 3) convert back to the input shape
    result: Any
    if was_single_object:
        result = results[0]
    elif model_keys is not None:
        result = dict_type(zip(model_keys, results))
    else:
        result = tuple(results)

    return script, result

def file_html(models: Model | Document | Sequence[Model],
              resources: Resources | tuple[JSResources | None, CSSResources | None] | None,
              title: str | None = None,
              template: Template | str = FILE,
              template_variables: dict[str, Any] = {},
              theme: ThemeLike = None,
              suppress_callback_warning: bool = False,
              _always_new: bool = False) -> str:
    ''' Return an HTML document that embeds Bokeh Model or Document objects.

    The data for the plot is stored directly in the returned HTML, with
    support for customizing the JS/CSS resources independently and
    customizing the jinja2 template.

    Args:
        models (Model or Document or seq[Model]) : Bokeh object or objects to render
            typically a Model or Document

        resources (Resources or tuple(JSResources or None, CSSResources or None)) :
            A resource configuration for Bokeh JS & CSS assets.

        title (str, optional) :
            A title for the HTML document ``<title>`` tags or None. (default: None)

            If None, attempt to automatically find the Document title from the given
            plot objects.

        template (Template, optional) : HTML document template (default: FILE)
            A Jinja2 Template, see bokeh.core.templates.FILE for the required
            template parameters

        template_variables (dict, optional) : variables to be used in the Jinja2
            template. If used, the following variable names will be overwritten:
            title, bokeh_js, bokeh_css, plot_script, plot_div

        theme (Theme, optional) :
            Applies the specified theme to the created html. If ``None``, or
            not specified, and the function is passed a document or the full set
            of roots of a document, applies the theme of that document.  Otherwise
            applies the default theme.

        suppress_callback_warning (bool, optional) :
            Normally generating standalone HTML from a Bokeh Document that has
            Python callbacks will result in a warning stating that the callbacks
            cannot function. However, this warning can be suppressed by setting
            this value to True (default: False)

    Returns:
        UTF-8 encoded HTML

    '''

    models_seq: Sequence[Model] = []
    if isinstance(models, Model):
        models_seq = [models]
    elif isinstance(models, Document):
        models_seq = models.roots
    else:
        models_seq = models

    with OutputDocumentFor(models_seq, apply_theme=theme, always_new=_always_new) as doc:
        (docs_json, render_items) = standalone_docs_json_and_render_items(models_seq, suppress_callback_warning=suppress_callback_warning)
        title = _title_from_models(models_seq, title)
        bundle = bundle_for_objs_and_resources([doc], resources)
        return html_page_for_render_items(bundle, docs_json, render_items, title=title,
                                          template=template, template_variables=template_variables)

class StandaloneEmbedJson(TypedDict):
    target_id: ID | None
    root_id: ID
    doc: DocJson
    version: str

def json_item(model: Model, target: ID | None = None, theme: ThemeLike = None) -> StandaloneEmbedJson:
    ''' Return a JSON block that can be used to embed standalone Bokeh content.

    Args:
        model (Model) :
            The Bokeh object to embed

        target (string, optional)
            A div id to embed the model into. If None, the target id must
            be supplied in the JavaScript call.

        theme (Theme, optional) :
            Applies the specified theme to the created html. If ``None``, or
            not specified, and the function is passed a document or the full set
            of roots of a document, applies the theme of that document.  Otherwise
            applies the default theme.

    Returns:
        JSON-like

    This function returns a JSON block that can be consumed by the BokehJS
    function ``Bokeh.embed.embed_item``. As an example, a Flask endpoint for
    ``/plot`` might return the following content to embed a Bokeh plot into
    a div with id *"myplot"*:

    .. code-block:: python

        @app.route('/plot')
        def plot():
            p = make_plot('petal_width', 'petal_length')
            return json.dumps(json_item(p, "myplot"))

    Then a web page can retrieve this JSON and embed the plot by calling
    ``Bokeh.embed.embed_item``:

    .. code-block:: html

        <script>
        fetch('/plot')
            .then(function(response) { return response.json(); })
            .then(function(item) { Bokeh.embed.embed_item(item); })
        </script>

    Alternatively, if is more convenient to supply the target div id directly
    in the page source, that is also possible. If `target_id` is omitted in the
    call to this function:

    .. code-block:: python

        return json.dumps(json_item(p))

    Then the value passed to ``embed_item`` is used:

    .. code-block:: javascript

        Bokeh.embed.embed_item(item, "myplot");

    '''
    with OutputDocumentFor([model], apply_theme=theme) as doc:
        doc.title = ""
        [doc_json] = standalone_docs_json([model]).values()

    root_id = doc_json["roots"][0]["id"]

    return StandaloneEmbedJson(
        target_id = target,
        root_id   = root_id,
        doc       = doc_json,
        version   = __version__,
    )

#-----------------------------------------------------------------------------
# Dev API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Private API
#-----------------------------------------------------------------------------

def _check_models_or_docs(models: ModelLike | ModelLikeCollection) -> ModelLikeCollection:
    '''

    '''
    input_type_valid = False

    # Check for single item
    if isinstance(models, (Model, Document)):
        models = [models]

    # Check for sequence
    if isinstance(models, Sequence) and all(isinstance(x, (Model, Document)) for x in models):
        input_type_valid = True

    if isinstance(models, dict) and \
        all(isinstance(x, str) for x in models.keys()) and \
        all(isinstance(x, (Model, Document)) for x in models.values()):
        input_type_valid = True

    if not input_type_valid:
        raise ValueError(
            'Input must be a Model, a Document, a Sequence of Models and Document, or a dictionary from string to Model and Document'
        )

    return models

def _title_from_models(models: Sequence[Model | Document], title: str | None) -> str:
    # use override title
    if title is not None:
        return title

    # use title from any listed document
    for p in models:
        if isinstance(p, Document):
            return p.title

    # use title from any model's document
    for p in cast(Sequence[Model], models):
        if p.document is not None:
            return p.document.title

    # use default title
    return DEFAULT_TITLE

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------
