//----------------------------------------------------------------------------
//  Several utility functions to modify docstring webpages while they are
//  rendered
//
//  Copyright (C) Spyder Project Contributors
//
//  Distributed under the terms of the MIT License.
//----------------------------------------------------------------------------

//============================================================================
// On document ready
//============================================================================

$(document).ready(function () {
    // Remove anchor header links.
    // They're used by Sphinx to create crossrefs, so we don't need them
    $('a.headerlink').remove();

    // If the first child in the docstring div is a section, change its class
    // to title. This means that the docstring has a real title and we need
    // to use it.
    // This is really useful to show module docstrings.
    var first_doc_child = $('div.docstring').children(':first-child');
    if( first_doc_child.is('div.section') && $('div.title').length == 0 ) {
        first_doc_child.removeClass('section').addClass('title');
    };

    // Change docstring headers from h1 to h2
    // It can only be an h1 and that's the page title
    // Taken from http://forum.jquery.com/topic/how-to-replace-h1-h2
    $('div.docstring').find('div.section h1').replaceWith(function () {
        return '<h2>' + $(this).text() + '</h2>';
    });
});
