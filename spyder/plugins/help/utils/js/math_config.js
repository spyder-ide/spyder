//----------------------------------------------------------------------------
//  Math configuration options and hacks
//
//  Copyright (C) Spyder Project Contributors
//
//  Distributed under the terms of the MIT License.
//----------------------------------------------------------------------------

//============================================================================
// On document ready
//============================================================================

{% if right_sphinx_version and math_on %}

$(document).ready(function () {

    // MathJax config
    // --------------
    MathJax.Hub.Config({
        // We are using SVG instead of HTML-CSS because the last one gives
        // troubles on QtWebkit. See this thread:
        // https://groups.google.com/forum/?fromgroups#!topic/mathjax-users/HKA2lNqv-OQ
        jax: ["input/TeX", "output/SVG"],

        // Menu options are not working. It would be useful to have 'Show TeX
        // commands', but it opens an external browser pointing to css_path.
        // I don't know why that's happening
        showMathMenu: false,
        messageStyle: "none",
        "SVG": {
            blacker: 1
        },

        {% if platform == 'win32' %}
        // Change math preview size so that it doesn't look too big while
        // redendered
        styles: {
            ".MathJax_Preview": {
                color: "#888",
                "font-size": "55%"
            }
        }
        {% endif %}
    });

    // MathJax Hooks
    // -------------
    // Put here any code that needs to be evaluated after MathJax has been
    // fully loaded
    MathJax.Hub.Register.StartupHook("End", function () {
        // Eliminate unnecessary margin-bottom for inline math
        $('span.math svg').css('margin-bottom', '0px');
    });

});

{% else %}

$(document).ready(function () {
    // Show math in monospace
    $('.math').css('font-family', 'monospace');
});

{% endif %}
