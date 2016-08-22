//----------------------------------------------------------------------------
//  Move Outline section to be the first one
//
//  Copyright (c) Spyder Project Contributors
//
//  Distributed under the terms of the MIT License
//----------------------------------------------------------------------------

//============================================================================
// On document ready
//============================================================================

$(document).ready(function (){
    var first_section_id = $(".section")[0].id;
    $("#outline").insertBefore("#" + first_section_id);
});
