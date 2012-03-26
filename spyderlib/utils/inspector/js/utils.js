//----------------------------------------------------------------------------
//  Several utility functions to modify docstring webpages while they are
//  rendered
//
//  Copyright (C) 2012 - The Spyder Team
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
    
    // Change docstring headers from h1 to h2
    // It can only be an h1 and that's the page title
    // Taken from http://forum.jquery.com/topic/how-to-replace-h1-h2
    $(document).find('div.section h1').replaceWith(function () {
        return '<h2>' + $(this).text() + '</h2>';
    });
});
