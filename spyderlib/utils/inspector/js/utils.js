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
    // Remove header anchor links.
    // They're used by Sphinx to create crossrefs, so we don't need them
    $('a.headerlink').remove();
});
