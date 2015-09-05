//----------------------------------------------------------------------------
//  Move Outline section to be the first one
//
//  Copyright 2014 by The Spyder development team
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
